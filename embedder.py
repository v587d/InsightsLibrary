import os
import threading
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from logger import setup_logger
from config import config
from models import ContentModel, FileModel

logger = setup_logger(__name__)

class Embedder:
    """Singleton class for generating and managing text embeddings using SentenceTransformer."""
    _instance = None
    _lock = threading.Lock()

    EMBEDDING_DIM = 1024  # Default embedding dimension
    PAGE_IDS_FILE = "page_ids.npy"  # File name for storing page ID mapping

    def __new__(cls):
        """Ensure singleton instance and initialize SentenceTransformer model."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super(Embedder, cls).__new__(cls)
                    try:
                        # Load model from local path if provided, otherwise use default model
                        if config.eb_model_local_path:
                            instance.model = SentenceTransformer(
                                config.eb_model_local_path,
                                local_files_only=True,
                                device=config.eb_device,
                            )
                            logger.info(f"Loaded model from local path: {config.eb_model_local_path}")
                        else:
                            instance.model = SentenceTransformer(
                                "Qwen/Qwen3-Embedding-0.6B",
                                device=config.eb_device or "cpu"
                            )
                            logger.info("Downloaded and loaded Qwen3-Embedding-0.6B model")
                        logger.info(f"Model running on device: {config.eb_device or 'cpu'}")
                        cls._instance = instance
                    except Exception as e:
                        logger.error(f"Failed to load model: {str(e)}")
                        raise RuntimeError(
                            "Failed to initialize embedding model, you could use another methods for search. "
                            f"The error message: {str(e)}") from e
        return cls._instance

    def precalculation(self):
        """
        Generate embeddings for all unembedded content and build FAISS index.
        Updates content records to mark them as embedded.
        """
        try:
            logger.info("Starting content embedding precalculation...")
            content_model = ContentModel()

            # Retrieve all unembedded content records
            all_abstracts = self._get_abstract(content_model)
            if not all_abstracts:
                logger.warning("No abstract records found in database")
                return

            logger.info(f"Found {len(all_abstracts)} abstract records")

            # Initialize FAISS index with inner product metric
            index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
            page_ids = []

            # Process content in batches
            batch_size = 32
            total_batches = (len(all_abstracts) + batch_size - 1) // batch_size
            logger.info(f"Generating embeddings with batch size {batch_size}")

            for i in tqdm(
                range(0, len(all_abstracts), batch_size),
                total=total_batches,
                desc="Generating embeddings",
                unit="batch"
            ):
                batch = all_abstracts[i:i + batch_size]
                texts = [item['abstract'] for item in batch]
                batch_page_ids = [item['page_id'] for item in batch]

                # Generate embeddings (calculation)
                embeddings = self.model.encode(
                    texts,
                    normalize_embeddings=True,
                    batch_size=batch_size,
                    show_progress_bar=False
                )

                # Add embeddings to FAISS index
                index.add(np.array(embeddings, dtype=np.float32))
                page_ids.extend(batch_page_ids)

            # Save FAISS index and page ID mapping
            self._save_faiss_index(index, page_ids)
            logger.info("Abstract embedding precalculation completed successfully")

        except Exception as e:
            logger.error(f"Precalculation failed: {str(e)}")
            raise RuntimeError(f"Precalculation failed: {str(e)}") from e

    @staticmethod
    def _get_abstract(content_model: ContentModel) -> list:
        try:
            abstract_records = [
                cnt for cnt in content_model.contents
                if cnt.get("abstract") != ""
            ]
            return abstract_records

        except Exception as e:
            logger.error(f"Failed to fetch abstract records: {str(e)}")
            raise RuntimeError(f"Abstract retrieval failed: {str(e)}") from e

    @staticmethod
    def _full_path(file_path: str) -> Optional[str]:
        # Convert file path to complete absolute path for Windows and macOS
        try:
            if not file_path or not isinstance(file_path, str):
                return None
            custom_root = os.path.dirname(os.path.abspath(__file__))
            file_name = os.path.basename(file_path)
            full_path = os.path.join(custom_root, "library_files", file_name)
            if os.path.isfile(full_path):
                return os.path.normpath(full_path)
            return None
        except Exception as e:
            logger.error(f"File path conversion failed for '{file_path}': {e}")
            return None

    @staticmethod
    def _path2url(file_path: str) -> str:
        prefix_url = "http://www.smartapp.market/static/assets/insights/"
        normalized_path = file_path.replace('\\', '/')
        return prefix_url + normalized_path

    def _save_faiss_index(self, index, page_ids):
        """
        Save FAISS index and page ID mapping to disk.

        Args:
            index: FAISS index containing embeddings.
            page_ids: List of page IDs corresponding to embeddings.
        """
        try:
            # Save FAISS index
            index_path = os.path.join(config.faiss_index_dir, "faiss_index.index")
            faiss.write_index(index, index_path)
            logger.info(f"Saved FAISS index to: {index_path}")

            # Save page ID mapping
            ids_path = os.path.join(config.faiss_index_dir, self.PAGE_IDS_FILE)
            np.save(ids_path, np.array(page_ids))
            logger.info(f"Saved page ID mapping to: {ids_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index or page IDs: {str(e)}")
            raise RuntimeError(f"Index saving failed: {str(e)}") from e

    def retrieve(
            self,
            query_text: str,
            instruction: str = "Retrieve relevant passages for the query",
            k: int = 10,
            recall_threshold: float = 0.30
    )->list:
        """
        Search for top-k relevant content based on query text using FAISS index, filtered by recall threshold.

        Args:
            query_text: The input query text.
            instruction: Instruction to prepend to query (default: "Retrieve relevant passages for the query").
            k: Number of top results to return (default: 5).
            recall_threshold: Similarity threshold for recall (default: 0.30).

        Returns:
            List of dictionaries with 'page_id' and 'similarity' for each result.
        """
        try:
            # Load FAISS index and page IDs
            index_path = os.path.join(config.faiss_index_dir, "faiss_index.index")
            ids_path = os.path.join(config.faiss_index_dir, self.PAGE_IDS_FILE)
            if not os.path.exists(index_path) or not os.path.exists(ids_path):
                logger.error(f"Missing index or page IDs file: {index_path}, {ids_path}")
                raise FileNotFoundError("FAISS index or page IDs file not found")

            index = faiss.read_index(index_path)
            page_ids = np.load(ids_path)
            file_model = FileModel()
            content_model = ContentModel()

            # Build query input
            query_input = f"Instruct: {instruction}\nQuery: {query_text}"

            # Generate query embedding
            query_embedding = self.model.encode(
                [query_input],
                normalize_embeddings=True,
                batch_size=1,
                show_progress_bar=False,
            )

            # Search for top-k similar results with a larger k to ensure threshold coverage
            search_k = max(100, k)  # Search a larger k to cover threshold filtering
            distances, indices = index.search(
                np.array(query_embedding, dtype=np.float32), search_k
            )

            # Filter results based on recall threshold
            filtered_results = []
            for idx, sim in zip(indices[0], distances[0]):
                if sim >= recall_threshold:
                    page_id = str(page_ids[idx])
                    filtered_results.append({"page_id": page_id, "similarity": float(sim)})
                else:
                    break


            if len(filtered_results) > k:
                filtered_results = filtered_results[:k]

            result = []
            if filtered_results:
                page_ids = [item["page_id"] for item in filtered_results]
                file_ids = set()
                page_id_to_item = {item["page_id"]: item for item in filtered_results}

                contents = content_model.get_contents_by_page_ids(page_ids)

                for content in contents:
                    if content:
                        file_ids.add(content["file_id"])
                files = file_model.get_files_by_ids(list(file_ids))
                file_map = {file["file_id"]: file for file in files if file}

                for content in contents:
                    if not content:
                        continue
                    page_id = content["page_id"]
                    file_id = content["file_id"]
                    file = file_map.get(file_id)

                    if not file:
                        continue

                    if file.get("uploader") != "admin":
                        file["full_path"] = self._full_path(file.get("file_path"))
                    else:
                        file["download_url"] = self._path2url(file.get("file_path"))

                    page_info = {
                        "page_number": content["page_number"],
                        "page_title": content["title"],
                        "page_abstract": content["abstract"],
                        "page_content": content["content"],
                        "local_path": file.get("full_path", None),
                        "download_url": file.get("download_url", None),
                        "file_name": file["file_name"],
                        "published_by": file["source"],
                        "published_date": file["published_date"],
                        "vector_similarity": page_id_to_item[page_id]["similarity"]
                    }
                    result.append(page_info)
            return result

        except Exception as e:
            logger.error(f"Search query failed: {str(e)}")
            raise RuntimeError(f"Search query failed: {str(e)}") from e

if __name__ == "__main__":
    pass
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional, List

import uuid
from tinydb import TinyDB, Query
from config import config

from logger import setup_logger

logger = setup_logger(__name__)

class TinyDBManager:
    """Manage TinyDB instance as a singleton with indexes."""
    _instance = None
    _file_index = {}  # Index for files: {file_id: doc_id, file_path: doc_id}
    _content_index = {}  # Index for contents: {page_id: doc_id, file_id: set(doc_ids)}

    def __new__(cls):
        if cls._instance is None:
            os.makedirs(os.path.dirname(config.DB_TEST_PATH), exist_ok=True)
            cls._instance = super().__new__(cls)
            try:
                cls._instance.db = TinyDB(config.DB_TEST_PATH)
                cls._build_indexes()
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise RuntimeError(f"Database initialization failed: {e}") from e
        return cls._instance

    @classmethod
    def _build_indexes(cls):
        """Build in-memory indexes for files and contents tables."""
        db = cls._instance.db
        files_table = db.table('files')
        contents_table = db.table('contents')

        # Build file index
        for doc in files_table.all():
            doc_id = doc.doc_id
            cls._file_index[doc['file_id']] = doc_id
            cls._file_index[os.path.normpath(doc['file_path'])] = doc_id

        # Build content index
        for doc in contents_table.all():
            doc_id = doc.doc_id
            cls._content_index[doc['page_id']] = doc_id
            cls._content_index.setdefault(doc['file_id'], set()).add(doc_id)

class FileModel:
    """Model for file metadata storage."""
    def __init__(self):
        self.manager = TinyDBManager()
        self.db = self.manager.db
        self.files = self.db.table('files')
        self.query = Query()

    def get_file_by_path(self, file_path: str) -> Optional[Dict]:
        """Retrieve file record by file path using index."""
        normalized_path = None
        try:
            # Normalize file path for consistency
            normalized_path = os.path.normpath(file_path)
            doc_id = self.manager._file_index.get(normalized_path)
            if doc_id is None:
                logger.warning(f"File record not found: {normalized_path}")
                return None
            file_record = self.files.get(doc_id=doc_id)
            if file_record is None:
                logger.warning(f"No file record found for doc_id: {doc_id}")
                return None
            return file_record
        except Exception as e:
            logger.error(f"Failed to query file: {normalized_path}, error: {e}")
            raise RuntimeError(f"File query failed: {e}") from e

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Retrieve file record by file ID using index."""
        try:
            doc_id = self.manager._file_index.get(file_id)
            if doc_id is None:
                logger.warning(f"File record not found: {file_id}")
                return None
            return self.files.get(doc_id=doc_id)
        except Exception as e:
            logger.error(f"Failed to query file: {file_id}, error: {e}")
            raise RuntimeError(f"File query failed: {e}") from e

    def create_file(
            self,
            file_path: str,
            file_name: str,
            file_hash: str,
            last_modified: float,
            opt_msg: str = "initial",
            source: str = "",
            uploader: str = "",
            language: str = "zh",
            topic: str = "",
            published_date: str = ""
    ) -> int:
        """Create a new file record and update index."""
        # Normalize file path for consistency
        normalized_path = os.path.normpath(file_path)
        if self.get_file_by_path(normalized_path):
            logger.warning(f"Failed to create file, path already exists: {normalized_path}")
            raise ValueError(f"File path already exists: {normalized_path}")

        file_id = str(uuid.uuid4())
        file_data = {
            "file_id": file_id,
            "file_path": normalized_path,
            "file_name": file_name,
            "file_hash": file_hash,
            "last_modified": last_modified,
            "processed_at": datetime.now().isoformat(),
            "pages": [],
            "tags": [],
            "file_desc": None,
            "opt_msg": opt_msg,
            "source": source,
            "uploader": uploader,
            "language": language,
            "topic": topic,
            "published_date": published_date
        }

        try:
            doc_id = self.files.insert(file_data)
            # Update file index
            self.manager._file_index[file_id] = doc_id
            self.manager._file_index[normalized_path] = doc_id
            logger.info(f"Created file record and updated index for: {normalized_path}, doc_id: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to create file: {normalized_path}, error: {e}")
            raise RuntimeError(f"File creation failed: {e}") from e

    def update_file(self, file_id: str, **kwargs: Any) -> None:
        """Dynamically update file record and sync index if file_path changes."""
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            logger.warning(f"Failed to update file, no valid fields: {file_id}")
            raise ValueError("No valid update fields")

        if "opt_msg" in kwargs:
            logger.warning(f"Updating operation status: {file_id} => {kwargs['opt_msg']}")

        try:
            file_record = self.get_file_by_id(file_id)
            if not file_record:
                logger.warning(f"Failed to update file, not found: {file_id}")
                raise ValueError(f"File not found: {file_id}")

            # If file_path is updated, sync _file_index
            old_path = file_record['file_path']
            new_path = updates.get('file_path')
            if new_path and new_path != old_path:
                new_path = os.path.normpath(new_path)
                self.manager._file_index.pop(os.path.normpath(old_path), None)
                self.manager._file_index[new_path] = file_record.doc_id # type: ignore
                logger.info(f"Updated file index: {old_path} -> {new_path}, doc_id: {file_record.doc_id}") # type: ignore

            updated = self.files.update(updates, self.query.file_id == file_id)  # type: ignore
            if not updated:
                logger.warning(f"Failed to update file, not found: {file_id}")
                raise ValueError(f"File not found: {file_id}")
        except Exception as e:
            logger.error(f"Failed to update file: {file_id}, error: {e}")
            raise RuntimeError(f"File update failed: {e}") from e

    def update_pages_aigc_status(
            self,
            file_id: str,
            page_numbers: List[int],  # Changed to page_numbers
            is_aigc: bool = True
    ) -> bool:
        """
        Update AIGC status for specific pages in a file by page number

        Args:
            file_id: Target file ID
            page_numbers: List of page numbers to update
            is_aigc: AIGC status to set (default: True)

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Locate file by ID using index
            doc_id = self.manager._file_index.get(file_id)
            if not doc_id:
                logger.warning(f"File not found: {file_id}")
                return False

            file_record = self.files.get(doc_id=doc_id)
            if not file_record:
                logger.warning(f"File record missing: {file_id}")
                return False

            pages = file_record.get('pages', [])
            if not pages:
                logger.warning(f"No pages in file: {file_id}")
                return False

            # Create mapping: page_number → index
            page_num_to_idx = {}
            for idx, page in enumerate(pages):
                if 'page_number' in page:
                    page_num_to_idx[page['page_number']] = idx

            updated = False
            # Update specified pages
            for page_num in page_numbers:
                if page_num in page_num_to_idx:
                    idx = page_num_to_idx[page_num]
                    pages[idx]['is_aigc'] = is_aigc # type: ignore
                    updated = True
                else:
                    logger.warning(f"Page {page_num} not found in {file_id}")

            if updated:
                # Update only pages field
                self.files.update({'pages': pages}, doc_ids=[doc_id])
                return True

            return False

        except Exception as e:
            logger.error(f"Update failed: {file_id}, error: {str(e)}")
            return False

    def delete_file(self, file_id: str) -> None:
        """Delete file record and remove from index."""
        try:
            file_record = self.get_file_by_id(file_id)
            if not file_record:
                logger.warning(f"Failed to delete file, not found: {file_id}")
                raise ValueError(f"File not found: {file_id}")

            remove = self.files.remove(self.query.file_id == file_id)  # type: ignore
            if not remove:
                logger.warning(f"Failed to delete file, not found: {file_id}")
                raise ValueError(f"File not found: {file_id}")

            # Remove from file index
            file_path = file_record['file_path']
            self.manager._file_index.pop(file_id, None)
            self.manager._file_index.pop(os.path.normpath(file_path), None)
            logger.info(f"Removed file index entries for file_id: {file_id}, file_path: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file: {file_id}, error: {e}")
            raise RuntimeError(f"File deletion failed: {e}") from e

    def clean_up_file_pages(self, file_id: str) -> None:
        """Clean up all page records for a file."""
        try:
            updated = self.files.update({"pages": []}, self.query.file_id == file_id)  # type: ignore
            if not updated:
                logger.warning(f"Failed to delete pages, file not found: {file_id}")
                raise ValueError(f"File not found: {file_id}")
        except Exception as e:
            logger.error(f"Failed to delete pages: {file_id}, error: {e}")
            raise RuntimeError(f"Page deletion failed: {e}") from e

    def add_pages(self, file_id: str, page_data_list: List[Dict]) -> bool:
        """Add page data in bulk."""
        try:
            file_record = self.files.get(self.query.file_id == file_id)  # type: ignore
            if not file_record:
                return False

            doc_id = file_record.doc_id
            current_pages = file_record.get('pages', [])
            updated_pages = current_pages + page_data_list

            self.files.update({"pages": updated_pages}, doc_ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Failed to add pages: {file_id}, error: {e}")
            return False

    def get_all_files(self) -> List[Dict]:
        """Retrieve all file records."""
        try:
            files = self.files.all()
            return files
        except Exception as e:
            logger.error(f"Failed to get all files: {e}")
            raise RuntimeError(f"File retrieval failed: {e}") from e

    def is_file_changed(self, file_path: str) -> bool:
        """Check if file has changed."""
        # Normalize file path for consistency
        normalized_path = os.path.normpath(file_path)
        if not os.path.exists(normalized_path):
            logger.warning(f"File deleted or not found: {normalized_path}")
            return True

        try:
            file_record = self.get_file_by_path(normalized_path)
        except RuntimeError:
            logger.warning(f"File status check failed, considered changed: {normalized_path}")
            return True

        if not file_record:
            logger.warning(f"New file detected: {normalized_path}")
            return True

        try:
            current_hash = self.calculate_md5(normalized_path)
            current_mtime = os.path.getmtime(normalized_path)

            if file_record["file_hash"] != current_hash:
                logger.warning(f"File hash changed: {normalized_path}")
                return True

            if abs(file_record["last_modified"] - current_mtime) > 0.001:
                logger.warning(f"File modification time changed: {normalized_path}")
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to check file change: {normalized_path}, error: {e}")
            return True

    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate MD5: {file_path}, error: {e}")
            raise IOError(f"MD5 calculation failed: {e}") from e

    def get_files_by_ids(self, file_ids: List[str]) -> List[Dict]:
        """Batch retrieve file records by file IDs using index."""
        try:
            doc_ids = [self.manager._file_index.get(fid) for fid in file_ids]
            doc_ids = [did for did in doc_ids if did is not None]
            return self.files.get(doc_ids=doc_ids)
        except Exception as e:
            logger.error(f"Failed to batch query files: {e}")
            return []

class ContentModel:
    """Model for content metadata storage."""
    def __init__(self):
        self.manager = TinyDBManager()
        self.db = self.manager.db
        self.contents = self.db.table('contents')
        self.query = Query()

    def create_content(
            self,
            file_id: str,
            page_number: int,
            content: str,
            title: str = "",
            prop: str = "",
            abstract: str = "",
            keywords: List[str] = None,
            **kwargs
    ) -> str:
        """Create a new content record and update index."""
        page_id = str(uuid.uuid4())
        content_data = {
            "page_id": page_id,
            "file_id": file_id,
            "page_number": page_number,
            "content": content,
            "title": title,
            "property": prop,
            "abstract": abstract,
            "keywords": keywords or [],
            "created_at": kwargs.get("created_at") or datetime.now().isoformat(),
            "updated_at": kwargs.get("updated_at") or datetime.now().isoformat()
        }

        try:
            doc_id = self.contents.insert(content_data)
            # Update content index
            self.manager._content_index[page_id] = doc_id
            self.manager._content_index.setdefault(file_id, set()).add(doc_id)
            logger.info(f"Created content record and updated index for page_id: {page_id}, file_id: {file_id}, doc_id: {doc_id}")
            return page_id
        except Exception as e:
            logger.error(f"Failed to create content: page_id: {page_id}, error: {e}")
            raise RuntimeError(f"Content creation failed: {e}") from e

    def update_content(self, page_id: str, **kwargs) -> None:
        """Update content record with allowed fields."""
        allowed_fields = ["content", "keywords", "updated_at", "title", "property", "abstract"]
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.now().isoformat()

        try:
            updated = self.contents.update(update_data, self.query.page_id == page_id)  # type: ignore
            if not updated:
                logger.warning(f"Failed to update content, not found: page_id: {page_id}")
                raise ValueError(f"Content not found: {page_id}")
        except Exception as e:
            logger.error(f"Failed to update content: page_id: {page_id}, error: {e}")
            raise RuntimeError(f"Content update failed: {e}") from e

    def get_content_by_page_id(self, page_id: str) -> Optional[Dict]:
        """Retrieve content record by page ID using index."""
        try:
            doc_id = self.manager._content_index.get(page_id)
            if doc_id is None:
                logger.warning(f"Content record not found: {page_id}")
                return None
            return self.contents.get(doc_id=doc_id)
        except Exception as e:
            logger.error(f"Failed to query content: {page_id}, error: {e}")
            return None

    def get_contents_by_file_id(self, file_id: str) -> List[Dict]:
        """Retrieve all content records by file ID using index with batch query."""
        try:
            doc_ids = self.manager._content_index.get(file_id, set())
            if not doc_ids:
                logger.warning(f"No content records found for file: {file_id}")
                return []
            # Batch query using doc_ids
            results = self.contents.get(doc_ids=list(doc_ids))
            return [r for r in results if r is not None]
        except Exception as e:
            logger.error(f"Failed to query contents: {file_id}, error: {e}")
            return []

    def delete_content(self, page_id: str) -> bool:
        """Delete content record by page ID and remove from index."""
        try:
            content_record = self.get_content_by_page_id(page_id)
            if not content_record:
                logger.warning(f"Failed to delete content, not found: page_id: {page_id}")
                return False

            removed = self.contents.remove(self.query.page_id == page_id)  # type: ignore
            if not removed:
                logger.warning(f"Failed to delete content, not found: page_id: {page_id}")
                return False

            # Remove from content index
            file_id = content_record['file_id']
            doc_id = self.manager._content_index.pop(page_id, None)
            if doc_id and file_id in self.manager._content_index:
                self.manager._content_index[file_id].discard(doc_id)
                if not self.manager._content_index[file_id]:
                    self.manager._content_index.pop(file_id)
            logger.info(f"Removed content index entries for page_id: {page_id}, file_id: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete content: page_id: {page_id}, error: {e}")
            return False

    def delete_contents_by_file_id(self, file_id: str) -> int:
        """Delete all content records by file ID and remove from index."""
        try:
            contents = self.get_contents_by_file_id(file_id)
            removed_count = len(self.contents.remove(self.query.file_id == file_id))  # type: ignore
            if not removed_count:
                logger.warning(f"Failed to delete contents, no records found: file_id: {file_id}")
                return 0

            # Remove from content index
            for content in contents:
                page_id = content['page_id']
                self.manager._content_index.pop(page_id, None)
            self.manager._content_index.pop(file_id, None)
            logger.info(f"Removed {removed_count} content index entries for file_id: {file_id}")
            return removed_count
        except Exception as e:
            logger.error(f"Failed to delete contents: file_id: {file_id}, error: {e}")
            return 0

    def get_contents_by_page_ids(self, page_ids: List[str]) -> List[Dict]:
        """Batch retrieve content records by page IDs using index."""
        try:
            doc_ids = [self.manager._content_index.get(pid) for pid in page_ids]
            doc_ids = [did for did in doc_ids if did is not None]
            return self.contents.get(doc_ids=doc_ids)
        except Exception as e:
            logger.error(f"Failed to batch query contents: {e}")
            return []

if __name__ == "__main__":
    pass
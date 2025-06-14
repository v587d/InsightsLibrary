import os
import shutil
from datetime import datetime
import io
from typing import List

import fitz  # PyMuPDF
from PIL import Image
from PIL.Image import Resampling

from models import FileModel
from config import config
from logger import setup_logger

logger = setup_logger(__name__)

class PDFExtractor:
    """PDF Extraction: Handles PDF file scanning, page extraction, and database updates"""

    def __init__(
            self,
            files_dir: str = config.FILES_DIR,
            pages_dir: str = config.PAGES_DIR
    ) -> None:
        """Initialize PDF extraction"""
        self.files_dir = files_dir
        self.pages_dir = pages_dir
        self.file_model = FileModel()
        self.file_cache = {}  # Cache for file MD5 and mtime
        logger.info(f"PDF extraction initialized | Files directory: {files_dir} | Pages directory: {pages_dir}")

    def run(self) -> None:
        """Scan directory for changed files (include new created or added) and process them"""
        # Ensure directories exist
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.pages_dir, exist_ok=True)
        logger.info(f"Starting scan of directory: {self.files_dir}")
        file_count = 0
        processed_count = 0
        error_count = 0
        # Get all PDF files
        pdf_files = [f for f in os.listdir(self.files_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            logger.info("No PDF files found in directory")
            return
        logger.info(f"Found {len(pdf_files)} PDF files")

        # Preload file cache
        for pdf in pdf_files:
            file_path = os.path.join(self.files_dir, pdf)
            try:
                file_hash = FileModel.calculate_md5(file_path)
                last_modified = os.path.getmtime(file_path)
                self.file_cache[file_path] = (file_hash, last_modified)
            except Exception as e:
                logger.error(f"Failed to cache file: {pdf} | Error: {e}")

        updates = []  # Batch updates
        for pdf in pdf_files:
            file_count += 1
            file_path = os.path.join(self.files_dir, pdf)
            try:
                cached_hash, cached_mtime = self.file_cache.get(file_path, (None, None))
                if cached_hash is None or self.file_model.is_file_changed(file_path):
                    logger.info(f"Detected changed file: {pdf}")

                    # Get or create file record
                    file_record = self.file_model.get_file_by_path(file_path)
                    if not file_record:
                        file_hash = FileModel.calculate_md5(file_path)
                        last_modified = os.path.getmtime(file_path)
                        self.file_model.create_file(
                            file_path,
                            pdf,
                            file_hash,
                            last_modified,
                            opt_msg="initial",
                        )
                        file_record = self.file_model.get_file_by_path(file_path)
                        if file_record is None:
                            logger.error(f"Failed to retrieve file record for {file_path}, skipping")
                            continue
                        updates.append((file_record["file_id"], {
                            "file_hash": file_hash,
                            "last_modified": last_modified,
                            "opt_msg": "pending_processing"
                        }))

                    # Process file using file_id
                    self.process_file(file_record["file_id"])
                    processed_count += 1

                    # Prepare update after processing
                    current_hash = FileModel.calculate_md5(file_path)
                    current_mtime = os.path.getmtime(file_path)
                    updates.append((file_record["file_id"], {
                        "file_hash": current_hash,
                        "last_modified": current_mtime,
                        "opt_msg": "processed"
                    }))
                else:
                    pass
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to process file: {pdf} | Error: {e}")
                logger.error(f"Detailed error for file: {pdf}", exc_info=True)

        # Batch update file records
        for file_id, update_data in updates:
            self.file_model.update_file(file_id, **update_data)

        logger.info(f"Scan completed | Total files: {file_count} | Processed: {processed_count} | Failed: {error_count}")

    def process_file(self, file_id: str) -> None:
        """Process a single PDF file using file_id"""
        try:
            # Retrieve file record by file_id
            file_record = self.file_model.get_file_by_id(file_id)
            if not file_record:
                logger.error(f"File record not found: file_id={file_id}")
                return

            file_path = file_record["file_path"]
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            page_subdir = os.path.join(self.pages_dir, base_name)

            # Update status using class method
            self._update_status(file_id, "initial" if file_record.get("opt_msg") != "initial" else file_record["opt_msg"])
            self._update_status(file_id, "pages_updating")

            # Perform cleanup
            self._cleanup_invalid_pages(file_id, page_subdir)

            # Process PDF file with parallel rendering
            pages_paths = self._pdf_to_pages(file_path, self.pages_dir)

            # Add page records
            success_count = 0
            page_data_list = []
            for i, img_path in enumerate(pages_paths):
                page_data_list.append({
                    "page_number": i + 1,
                    "page_path": img_path,
                    "abstract": None,
                    "keywords": [],
                    "is_aigc": False,
                    "processed_at": datetime.now().isoformat()
                })

            if self.file_model.add_pages(file_id, page_data_list):
                success_count = len(page_data_list)

            self._update_status(file_id, "completed")
            logger.info(f"Processing completed | File: {file_name} | Pages: {success_count}/{len(pages_paths)}")

        except Exception as e:
            current_file = self.file_model.get_file_by_id(file_id) or {}
            opt_status = current_file.get("opt_msg", "unknown")
            file_name = current_file.get("file_name", "unknown")
            if opt_status == "pages_updating":
                logger.error(f"Critical error: File {file_name} cleanup done but update incomplete!")
                self._update_status(file_id, "needs_recovery")
            else:
                logger.error(f"Failed to process file: {file_name} | Stage: {opt_status} | Error: {e}")
            logger.error(f"Detailed error for file processing", exc_info=True)

    def _cleanup_invalid_pages(self, file_id: str, page_dir: str) -> None:
        """Cleanup invalid data (database records and image files)"""
        try:
            # Clean up database page records
            self.file_model.clean_up_file_pages(file_id)
            logger.info(f"Clean up database page records: file_id={file_id}")
            # Remove image directory if it exists
            if os.path.exists(page_dir):
                shutil.rmtree(page_dir)
                logger.info(f"Cleaned up old page images: {os.path.basename(page_dir)}")
        except Exception as e:
            logger.error(f"Failed to cleanup old pages: file_id={file_id}, Error: {e}")

    def _update_status(self, file_id: str, status: str) -> None:
        """Update the operation status of a file"""
        self.file_model.update_file(file_id, opt_msg=status)

    @staticmethod
    def _pdf_to_pages(
            pdf_path: str,
            output_dir: str,
            dpi: int = 200,
            max_size: int = 1600
    ) -> List[str]:
        """
        Convert PDF pages to optimized JPEG images

        Args:
            pdf_path: Path to the PDF file
            output_dir: Output directory
            dpi: Rendering resolution (default 200)
            max_size: Maximum image size (default 1600px)

        Returns:
            List of generated image paths
        """
        # Create subdirectory based on filename
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_output_dir = os.path.join(output_dir, pdf_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        page_paths = []
        doc = None

        try:
            logger.info(f"Starting PDF conversion: {os.path.basename(pdf_path)}")
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # Sequential processing
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                img.thumbnail((max_size, max_size), Resampling.LANCZOS)
                img_buffer = io.BytesIO()
                img.save(img_buffer, "JPEG", quality=90, optimize=True)
                img_path = os.path.join(pdf_output_dir, f"page_{page_num + 1}.jpg")
                with open(img_path, "wb") as f:
                    f.write(img_buffer.getvalue())
                page_paths.append(img_path)
                logger.debug(f"Processed page {page_num + 1} for {pdf_path}")

            logger.info(f"Conversion completed | Total pages: {total_pages} | Output directory: {pdf_output_dir}")
            return page_paths

        except Exception as e:
            logger.error(f"Failed to convert PDF: {os.path.basename(pdf_path)} | Error: {e}")
            if page_paths:
                try:
                    shutil.rmtree(pdf_output_dir)
                    logger.info(f"Cleaned up failed conversion directory: {pdf_output_dir}")
                except (OSError, PermissionError, FileNotFoundError) as cleanup_error:
                    logger.error(f"Failed to cleanup conversion directory: {pdf_output_dir} | Error: {cleanup_error}")
                except Exception as unexpected_error:
                    logger.error(f"Unexpected error during cleanup: {unexpected_error}", exc_info=True)
            return []
        finally:
            if doc:
                doc.close()


# async def main():
#     import time
#     start_time = time.time()
#     print("--------------Starting decomposition--------------")
#     pdf_ext = PDFExtractor()
#     pdf_ext.run()
#     print("--------------End decomposition--------------")
#     end_time = time.time()
#     print(f"Total time: {end_time - start_time} seconds")
#
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())
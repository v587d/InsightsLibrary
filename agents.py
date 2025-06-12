import os
import platform
from enum import Enum
from urllib.parse import quote
from typing import List, Dict, Union
from abc import ABC, abstractmethod
from datetime import datetime
from unicodedata import normalize

from pydantic import BaseModel, field_validator

from models import FileModel, ContentModel
from logger import setup_logger

logger = setup_logger(__name__)

class MatchLogic(str, Enum):
    # Match logic options for keyword searches
    AND = "AND"
    OR = "OR"

    @classmethod
    def from_string(cls, value: str) -> 'MatchLogic':
        # Convert string to MatchLogic enum, case-insensitive, raise error for invalid input
        if not isinstance(value, str):
            error_msg = f"Expected string, got {type(value).__name__}"
            logger.error(error_msg)
            raise TypeError(error_msg)
        try:
            return cls[value.upper()] # type: ignore
        except KeyError:
            valid_options = ", ".join(cls.__members__.keys())
            error_msg = f"Invalid match_logic: {value}. Must be one of: {valid_options}"
            logger.error(error_msg)
            raise ValueError(error_msg)

class SearchCriteria(BaseModel):
    keywords: List[str] = []
    match_logic: MatchLogic = MatchLogic.OR
    publisher: str = ""
    title: str = ""
    content: str = ""
    start_date: Union[datetime, None] = None
    end_date: Union[datetime, None] = None

    @field_validator("match_logic", mode="before")
    def validate_match_logic(cls, value):
        # Convert string input to MatchLogic enum using MatchLogic.from_string
        if isinstance(value, str):
            return MatchLogic.from_string(value)
        return value


class BaseAgent(ABC):
    def __init__(self):
        self._file_model = None
        self._content_model = None

    @property
    def file_model(self):
        if self._file_model is None:
            try:
                self._file_model = FileModel()
            except Exception as e:
                logger.error(f"FileModel initialization failed: {str(e)}")
                raise
        return self._file_model

    @property
    def content_model(self):
        if self._content_model is None:
            try:
                self._content_model = ContentModel()
            except Exception as e:
                logger.error(f"ContentModel initialization failed: {str(e)}")
                raise
        return self._content_model

    @abstractmethod
    def run(self, criteria: SearchCriteria, idx: int = 1) -> Dict:
        # Abstract method for agent execution with pagination
        pass

    @staticmethod
    def _normalize_text(text: str) -> str:
        # Normalize text: lowercase, remove accents, punctuation, standardize spaces
        normalized = normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        normalized = normalized.lower()
        normalized = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in normalized)
        return ' '.join(normalized.split())

    @staticmethod
    def _parse_date(date: Union[datetime, str]) -> datetime:
        # Parse date for sorting, return datetime.min if invalid
        try:
            return datetime.fromisoformat(date) if isinstance(date, str) else date
        except (ValueError, TypeError):
            return datetime.min

    @staticmethod
    def _path2uri(file_path: str):
        # Convert file path to URI
        try:
            system = platform.system()
            file_name = os.path.basename(file_path)
            custom_root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
            file_path = os.path.join(custom_root, "library_files", file_name)  # type: ignore
            if os.path.isfile(file_path):
                if system == "Windows":
                    uri_path = file_path.replace("\\", "/")
                    if ":" in uri_path:
                        drive, path_without_drive = uri_path.split(":", 1)
                        uri_path = f"/{drive}:{path_without_drive}"
                    return "file://" + quote(uri_path)  # type: ignore
                return "file://" + quote(file_path)  # type: ignore
            return None
        except Exception as e:
            logger.error(f"File path conversion failed: {e}")
            return None

class BaseRetriever(BaseAgent):
    def __init__(self, max_results: int = 1):
        super().__init__()
        self.max_results = max_results

    def run(self, criteria: SearchCriteria, idx: int = 1) -> Dict:
        pass

    @staticmethod
    def _match_keywords(target_keywords: List[str], criteria: SearchCriteria) -> tuple[bool, List[str]]:
        # Match keywords with AND/OR logic, return match status and matched keywords
        if not criteria.keywords:
            return True, []
        matched_keywords = []
        for query_kw in criteria.keywords:
            clean_query = query_kw.strip()
            found = False
            for target_kw in target_keywords:
                clean_target = target_kw.strip()
                if clean_query == clean_target or clean_query.lower() == clean_target.lower():
                    found = True
                    matched_keywords.append(query_kw)
                    break
            if criteria.match_logic == "AND" and not found:
                return False, []
        if criteria.match_logic == "OR" and not matched_keywords:
            return False, []
        return True, matched_keywords

    @staticmethod
    def _match_text(target_text: str, search_text: str) -> bool:
        # Case-insensitive text matching
        return search_text.strip().lower() in target_text.lower() if search_text.strip() else True

    @staticmethod
    def _match_date(target_date: Union[datetime, str], criteria: SearchCriteria) -> bool:
        # Match date against criteria range
        if isinstance(target_date, str):
            try:
                if 'T' in target_date:
                    dt = datetime.fromisoformat(target_date)
                elif len(target_date) == 10:
                    dt = datetime.strptime(target_date, "%Y-%m-%d")
                else:
                    dt = datetime.fromisoformat(target_date)
                target_date = dt
            except (ValueError, TypeError):
                logger.warning(f"Date parsing failed: {target_date}")
                return False
        target_date = target_date.date() if isinstance(target_date, datetime) else None
        if not target_date:
            return False
        if criteria.start_date and target_date < criteria.start_date.date():
            return False
        if criteria.end_date and target_date > criteria.end_date.date():
            return False
        return True

class FileRetriever(BaseRetriever):
    def __init__(self, max_results: int = 2):
        super().__init__(max_results)

    def _get_all_files(self) -> List[Dict]:
        # Fetch all file records
        return self.file_model.get_all_files()

    def run(self, criteria: SearchCriteria, idx: int = 1) -> Dict:
        try:
            # Validate page index
            if idx < 1:
                logger.error(f"Invalid page index: {idx}. Must be >= 1")
                return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

            # Fetch all files
            files = self._get_all_files()
            if not files:
                logger.error("No file records in database")
                return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

            # Precompute URIs
            for file in files:
                file["uri"] = self._path2uri(file.get("file_path"))

            # Process files with optimized filtering
            results = []
            for file in files:
                # Check if file is processed
                if file.get("opt_msg") != "processed":
                    continue

                # Date filter (skip if no date criteria)
                if (criteria.start_date or criteria.end_date) and not self._match_date(file.get("published_date"), criteria):
                    continue

                # Publisher filter (skip if empty)
                publisher = file.get("source", "")
                if criteria.publisher and not self._match_text(publisher, criteria.publisher):
                    continue

                # Title filter (skip if empty)
                title = file.get("file_name", "")
                if criteria.title and not self._match_text(title, criteria.title):
                    continue

                # Keyword filter (skip if empty)
                file_tags = file.get("tags", [])
                if criteria.keywords:
                    match_ok, matched_kws = self._match_keywords(file_tags, criteria)
                    if not match_ok:
                        continue
                else:
                    matched_kws = []

                # Content filter (skip if empty)
                content = file.get("file_desc", "")
                if criteria.content and not self._match_text(content, criteria.content):
                    continue

                # Build result
                results.append({
                    "file_name": title,
                    "topic": file.get("topic"),
                    "content": content,
                    "published_by": publisher,
                    "published_date": file.get("published_date"),
                    "file_uri": file.get("uri"),
                    "matched_keywords": matched_kws
                })

            # Sort results
            if criteria.keywords:
                # Sort by number of matched keywords (descending)
                results = sorted(results, key=lambda x: len(x["matched_keywords"]), reverse=True)
            else:
                # Sort by published_date (descending)
                results = sorted(results, key=lambda x: self._parse_date(x["published_date"]), reverse=True)

            # Pagination
            page_size = self.max_results
            total_matches = len(results)
            total_pages = (total_matches + page_size - 1) // page_size

            # Validate page index against total pages
            if idx > total_pages and total_matches > 0:
                logger.error(f"Invalid page index: {idx}. Exceeds total pages: {total_pages}")
                return {"results": [], "current_page": idx, "total_pages": total_pages, "total_matches": total_matches}

            # Slice results for the requested page
            start = (idx - 1) * page_size
            end = start + page_size
            paginated_results = results[start:end]

            return {
                "results": paginated_results,
                "current_page": idx,
                "total_pages": total_pages,
                "total_matches": total_matches
            }

        except Exception as e:
            logger.error(f"File retrieval failed: {str(e)}")
            return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

class ContentRetriever(BaseRetriever):
    def __init__(self, max_results: int = 5):
        super().__init__(max_results)

    def _get_file_info(self, file_id: str) -> Dict:
        # Retrieve file info by file_id
        return self.file_model.get_file_by_id(file_id)

    def _get_all_contents(self) -> List[Dict]:
        # Fetch all content records
        return self.content_model.contents.all()

    def run(self, criteria: SearchCriteria, idx: int = 1) -> Dict:
        try:
            # Validate page index
            if idx < 1:
                logger.error(f"Invalid page index: {idx}. Must be >= 1")
                return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

            # Fetch all contents
            contents = self._get_all_contents()
            if not contents:
                logger.error("No content records in database")
                return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

            # Cache file info and precompute URIs
            all_files = self.file_model.get_all_files()
            file_info_map = {file["file_id"]: file for file in all_files}
            for file in file_info_map.values():
                file["uri"] = self._path2uri(file.get("file_path"))

            # Process contents with optimized filtering
            results = []
            for content in contents:
                # Check if property is main
                if content.get("property") != "main":
                    continue

                # Get file info
                file_id = content.get("file_id")
                if not file_id or file_id not in file_info_map:
                    continue
                file_info = file_info_map[file_id]

                # Date filter (skip if no date criteria)
                if (criteria.start_date or criteria.end_date) and not self._match_date(file_info.get("published_date"), criteria):
                    continue

                # Publisher filter (skip if empty)
                publisher = file_info.get("source", "")
                if criteria.publisher and not self._match_text(publisher, criteria.publisher):
                    continue

                # Title filter (skip if empty)
                title = file_info.get("file_name", "")
                if criteria.title and not self._match_text(title, criteria.title):
                    continue

                # Keyword filter (skip if empty)
                content_keywords = content.get("keywords", [])
                if criteria.keywords:
                    match_ok, matched_kws = self._match_keywords(content_keywords, criteria)
                    if not match_ok:
                        continue
                else:
                    matched_kws = []

                # Content filter (skip if empty)
                content_text = content.get("content", "")
                if criteria.content and not self._match_text(content_text, criteria.content):
                    continue

                # Build result
                results.append({
                    "file_name": title,
                    "page_number": content.get("page_number"),
                    "page_abstract": content.get("abstract"),
                    "page_content": content_text,
                    "page_keywords": content_keywords,
                    "published_by": publisher,
                    "published_date": file_info.get("published_date"),
                    "file_uri": file_info.get("uri"),
                    "matched_keywords": matched_kws
                })

            # Sort results
            if criteria.keywords:
                # Sort by number of matched keywords (descending)
                results = sorted(results, key=lambda x: len(x["matched_keywords"]), reverse=True)
            else:
                # Sort by published_date (descending)
                results = sorted(results, key=lambda x: self._parse_date(x["published_date"]), reverse=True)

            # Pagination
            page_size = self.max_results
            total_matches = len(results)
            total_pages = (total_matches + page_size - 1) // page_size

            # Validate page index against total pages
            if idx > total_pages and total_matches > 0:
                logger.error(f"Invalid page index: {idx}. Exceeds total pages: {total_pages}")
                return {"results": [], "current_page": idx, "total_pages": total_pages, "total_matches": total_matches}

            # Slice results for the requested page
            start = (idx - 1) * page_size
            end = start + page_size
            paginated_results = results[start:end]

            return {
                "results": paginated_results,
                "current_page": idx,
                "total_pages": total_pages,
                "total_matches": total_matches
            }

        except Exception as e:
            logger.error(f"Content retrieval failed: {str(e)}")
            return {"results": [], "current_page": idx, "total_pages": 0, "total_matches": 0}

if __name__ == "__main__":
    pass


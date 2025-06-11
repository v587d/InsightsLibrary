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
    """TinyDB 管理类"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # 确保数据库目录存在
            os.makedirs(os.path.dirname(config.DB_TEST_PATH), exist_ok=True)

            cls._instance = super().__new__(cls)
            try:
                cls._instance.db = TinyDB(config.DB_TEST_PATH)
                # logger.info(f"数据库初始化成功: {config.DB_TEST_PATH}")
            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
                raise RuntimeError(f"数据库初始化失败: {e}") from e
        return cls._instance

class FileModel:
    """文件模型"""

    def __init__(self):
        self.manager = TinyDBManager()
        self.db = self.manager.db
        self.files = self.db.table('files')
        self.query = Query()
        # logger.info("FileModel 初始化完成")

    def get_file_by_path(self, file_path: str) -> Optional[Dict]:
        """根据文件路径获取文件记录

        Args:
            file_path: 文件完整路径

        Returns:
            文件记录字典，如果不存在则返回None
        """
        try:
            result = self.files.get(self.query.file_path == file_path) # type: ignore
            if result:
                logger.debug(f"找到文件记录: {file_path}")
            else:
                logger.debug(f"未找到文件记录: {file_path}")
            return result
        except Exception as e:
            logger.error(f"查询文件失败: {file_path}, 错误: {e}")
            raise RuntimeError(f"文件查询失败: {e}") from e

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """根据文件路径获取文件记录

        Args:
            file_id: 文件ID

        Returns:
            文件记录字典，如果不存在则返回None
        """
        try:
            result = self.files.get(self.query.file_id == file_id) # type: ignore
            if result:
                logger.debug(f"找到文件记录: {file_id}")
            else:
                logger.debug(f"未找到文件记录: {file_id}")
            return result
        except Exception as e:
            logger.error(f"查询文件失败: {file_id}, 错误: {e}")
            raise RuntimeError(f"文件查询失败: {e}") from e

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
            topic:  str = "",
            published_date: str = ""
    ) -> int:
        """创建新的文件记录

        Args:
            file_path: 文件完整路径
            file_name: 文件名
            file_hash: 文件哈希值
            last_modified: 最后修改时间戳
            opt_msg: 操作信息描述，默认为"initial"
            source: 文件来源
            uploader: 上传人
            language: 语种
            topic: 主题
            published_date: 发布日期
        Returns:
            新创建文件的文档ID (doc_id)

        Raises:
            ValueError: 如果文件路径已存在
            RuntimeError: 数据库操作失败
        """
        # 检查文件是否已存在
        if self.get_file_by_path(file_path):
            logger.warning(f"创建文件失败，路径已存在: {file_path}")
            raise ValueError(f"文件路径已存在: {file_path}")

        # 生成唯一文件ID
        file_id = str(uuid.uuid4())

        file_data = {
            "file_id": file_id,
            "file_path": file_path,
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
            logger.info(f"创建文件成功: {file_path}, doc_id={doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"创建文件失败: {file_path}, 错误: {e}")
            raise RuntimeError(f"文件创建失败: {e}") from e

    def update_file(
            self,
            file_id: str,
            **kwargs: Any  # 接收所有更新字段
    ) -> None:
        """动态更新文件记录

        Args:
            file_id: 文件ID（查询条件）
            **kwargs: 需要更新的字段（如 file_name="new.pdf"）
                      None值会被自动忽略

        Raises:
            ValueError: 无有效更新字段或文件不存在
            RuntimeError: 数据库操作失败
        """
        # 过滤掉None值
        updates = {k: v for k, v in kwargs.items() if v is not None}

        if not updates:
            logger.warning(f"更新文件失败，无有效更新字段: {file_id}")
            raise ValueError("无有效更新字段")

        if "opt_msg" in kwargs:
            logger.debug(f"更新操作状态: {file_id} => {kwargs['opt_msg']}")

        try:
            # 使用file_id进行查询
            updated = self.files.update(updates, self.query.file_id == file_id)  # type: ignore
            if not updated:
                logger.warning(f"更新文件失败，文件不存在: {file_id}")
                raise ValueError(f"文件不存在: {file_id}")
            logger.info(f"更新文件成功: {file_id}, 更新字段: {list(updates.keys())}")
        except Exception as e:
            logger.error(f"更新文件失败: {file_id}, 错误: {e}")
            raise RuntimeError(f"文件更新失败: {e}") from e

    def delete_file(self, file_id: str) -> None:
        """删除文件记录"""
        try:
            remove = self.files.remove(self.query.file_id == file_id) # type: ignore
            if not remove:
                logger.warning(f"删除文件失败，文件不存在: {file_id}")
                raise ValueError(f"文件不存在: {file_id}")
        except Exception as e:
            logger.error(f"删除文件失败: {file_id}, 错误: {e}")
            raise RuntimeError(f"文件删除失败: {e}") from e


    def delete_file_pages(self, file_id: str) -> None:
        """删除文件的所有页面记录

        Args:
            file_id: 文件ID

        Raises:
            ValueError: 文件不存在
            RuntimeError: 数据库操作失败
        """
        try:
            # 使用file_id进行查询
            updated = self.files.update({"pages": []}, self.query.file_id == file_id)  # type: ignore
            if not updated:
                logger.warning(f"删除页面失败，文件不存在: {file_id}")
                raise ValueError(f"文件不存在: {file_id}")
            logger.info(f"删除页面成功: {file_id}")
        except Exception as e:
            logger.error(f"删除页面失败: {file_id}, 错误: {e}")
            raise RuntimeError(f"页面删除失败: {e}") from e

    def add_pages(self, file_id: str, page_data_list: list) -> bool:
        """批量添加页面信息

        Args:
            file_id (str): 文件ID
            page_data_list (list): 页面数据列表，每个元素为字典格式的页面信息

        Returns:
            bool: 添加成功返回True，否则返回False
        """
        try:
            # 使用file_id获取记录
            file_record = self.files.get(self.query.file_id == file_id)  # type: ignore
            if not file_record:
                return False

            doc_id = file_record.doc_id
            current_pages = file_record.get('pages', [])
            updated_pages = current_pages + page_data_list

            self.files.update({"pages": updated_pages}, doc_ids=[doc_id])
            logger.info(f"批量添加 {len(page_data_list)} 个页面成功: {file_id}")
            return True
        except Exception as e:
            logger.error(f"批量添加页面失败: {file_id}, 错误: {e}")
            return False

    def get_all_files(self) -> List[Dict]:
        """获取所有文件记录

        Returns:
            文件记录列表
        """
        try:
            files = self.files.all()
            logger.debug(f"获取所有文件记录，数量: {len(files)}")
            return files
        except Exception as e:
            logger.error(f"获取所有文件失败: {e}")
            raise RuntimeError(f"文件获取失败: {e}") from e

    def is_file_changed(self, file_path: str) -> bool:
        """
        检查文件是否变更

        Args:
            file_path: 文件路径

        Returns:
            bool: 如果文件是新的、已删除或内容改变则返回True
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.info(f"文件已删除或不存在: {file_path}")
            return True
        # 获取数据库中的文件记录
        try:
            file_record = self.get_file_by_path(file_path)
        except RuntimeError:
            # 如果查询出错，视为文件已变更
            logger.warning(f"文件状态查询失败，视为已变更: {file_path}")
            return True
        if not file_record:
            logger.info(f"新文件: {file_path}")
            return True
        # 计算当前文件的MD5哈希
        try:
            current_hash = self.calculate_md5(file_path)
            current_mtime = os.path.getmtime(file_path)

            # 比较哈希值和修改时间
            if file_record["file_hash"] != current_hash:
                logger.info(
                    f"文件哈希值改变: {file_path} (旧哈希: {file_record['file_hash'][:8]}..., 新哈希: {current_hash[:8]}...)")
                return True

            # 使用时间差比较，避免浮点数精度问题
            if abs(file_record["last_modified"] - current_mtime) > 0.001:
                logger.info(
                    f"文件修改时间改变: {file_path} (旧时间: {file_record['last_modified']}, 新时间: {current_mtime})")
                return True

            logger.debug(f"文件未改变: {file_path}")
            return False
        except Exception as e:
            logger.error(f"文件变更检查失败: {file_path}, 错误: {e}")
            # 发生错误时视为文件已变更，确保安全
            return True

    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """计算文件的MD5哈希

        Args:
            file_path: 文件路径

        Returns:
            文件MD5哈希值

        Raises:
            IOError: 文件读取失败
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算MD5失败: {file_path}, 错误: {e}")
            raise IOError(f"MD5计算失败: {e}") from e

class ContentModel:
    """内容模型：存储页面内容信息"""

    def __init__(self):
        self.manager = TinyDBManager()
        self.db = self.manager.db
        self.contents = self.db.table('contents')
        self.query = Query()
        # logger.info("ContentModel 初始化完成")

    def create_content(
            self,
            file_id: str,
            page_number: int,
            content: str,
            title: str = "",
            prop: str = "",
            abstract: str = "",
            keywords: List[str] = None,
            ** kwargs  # 添加此参数以接收额外字段
    ) -> str:
        """
        创建新的内容记录

        Args:
            file_id: 关联的文件ID
            page_number: 页码
            content: 页面内容文本
            title: 页面标题
            prop: 页面属性
            abstract: 页面摘要
            keywords: 关键词列表（可选）
            kwargs: 其他可选字段（如created_at等）

        Returns:
            新创建内容的page_id
        """
        # 生成唯一页面ID
        page_id = str(uuid.uuid4())

        content_data = {
            "page_id": page_id,
            "file_id": file_id,
            "page_number": page_number,
            "content": content,
            "title": title,  # 新增字段
            "property": prop,  # 新增字段
            "abstract": abstract,  # 新增字段
            "keywords": keywords or [],  # 默认为空列表
            "created_at": kwargs.get("created_at") or datetime.now().isoformat(),
            "updated_at": kwargs.get("updated_at") or datetime.now().isoformat()
        }

        try:
            self.contents.insert(content_data)
            logger.info(f"创建内容成功: page_id={page_id} | 文件: {file_id} | 页码: {page_number}")
            return page_id
        except Exception as e:
            logger.error(f"创建内容失败: {e}")
            raise RuntimeError(f"内容创建失败: {e}") from e

    def update_content(self, page_id, **kwargs):
        """
        更新内容记录（过滤不可更新字段）

        Args:
            page_id: 要更新的页面ID
            kwargs: 更新字段（自动过滤created_at等不可变字段）
        """
        # 过滤不允许更新的字段
        allowed_fields = [
            "content", "keywords", "updated_at",
            "title", "property", "abstract"  # 新增字段
        ]
        update_data = {
            k: v for k, v in kwargs.items()
            if k in allowed_fields  # 只允许更新特定字段
        }

        # 添加更新时间戳
        update_data["updated_at"] = datetime.now().isoformat()

        try:
            # 使用TinyDB的更新语法
            self.contents.update(
                update_data,
                self.query.page_id == page_id # type: ignore
            )
            logger.info(f"内容更新成功: page_id={page_id}")
        except Exception as e:
            logger.error(f"内容更新失败: {e}")
            raise RuntimeError(f"内容更新失败: {e}") from e

    def get_content_by_page_id(self, page_id: str) -> Optional[Dict]:
        """
        根据页面ID获取内容记录

        Args:
            page_id: 页面ID

        Returns:
            内容记录字典，如果不存在则返回None
        """
        try:
            result = self.contents.get(self.query.page_id == page_id) # type: ignore
            if result:
                logger.debug(f"找到内容记录: {page_id}")
            else:
                logger.debug(f"未找到内容记录: {page_id}")
            return result
        except Exception as e:
            logger.error(f"查询内容失败: {page_id}, 错误: {e}")
            return None

    def get_contents_by_file_id(self, file_id: str) -> List[Dict]:
        """
        根据文件ID获取所有相关内容记录

        Args:
            file_id: 文件ID

        Returns:
            内容记录列表
        """
        try:
            results = self.contents.search(self.query.file_id == file_id) # type: ignore
            logger.info(f"找到 {len(results)} 条内容记录 | 文件: {file_id}")
            return results
        except Exception as e:
            logger.error(f"查询文件内容失败: {file_id}, 错误: {e}")
            return []

    def delete_content(self, page_id: str) -> bool:
        """
        删除内容记录

        Args:
            page_id: 页面ID

        Returns:
            是否成功删除
        """
        try:
            removed = self.contents.remove(self.query.page_id == page_id) # type: ignore
            if removed:
                logger.info(f"删除内容成功: {page_id}")
                return True
            logger.warning(f"删除内容失败，符合条件的记录不存在: page_id: {page_id}")
            return False
        except Exception as e:
            logger.error(f"删除内容失败: page_id: {page_id}, 错误: {e}")
            return False

    def delete_contents_by_file_id(self, file_id: str) -> int:
        """
        根据文件ID删除所有内容记录

        Args:
            file_id: 文件ID

        Returns:
            删除的记录数
        """
        try:
            removed = self.contents.remove(self.query.file_id == file_id) # type: ignore
            if removed:
                logger.info(f"删除文件内容成功: {file_id}")
                return True
            logger.warning(f"删除文件内容失败，符合条件的记录不存在: file_id: {file_id}")
            return False

        except Exception as e:
            logger.error(f"删除内容失败: file_id: {file_id}, 错误: {e}")
            return False


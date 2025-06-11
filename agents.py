import json
import random
import time
import os
import platform
from urllib.parse import quote
from typing import List, Dict, Optional, Union, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
from unicodedata import normalize

from openai import OpenAI

from models import FileModel, ContentModel
from config import config
from prompts import Prompts
from logger import setup_logger

logger = setup_logger(__name__)

# 基类定义
class BaseAgent(ABC):
    def  __init__(self):
        self.file_model = FileModel()
        self.content_model = ContentModel()

    @abstractmethod
    def run(self, user_query: str) -> Dict:
        """Agent核心功能"""
        pass

    @staticmethod
    def _parse_ai_response(ai_response: str) -> dict:
        """解析AI返回的JSON响应"""
        try:
            # 提取JSON部分（可能包含非JSON前缀）
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]

            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON解析失败: {e}\n原始响应: {ai_response}\n")
            return {}

    @staticmethod
    def _safe_json_dump(data: dict) -> str:
        """带错误处理的JSON序列化"""
        try:
            return json.dumps(data, ensure_ascii=False)
        except TypeError as e:
            logger.error(f"JSON序列化失败: {e}")
            # 自动过滤无法序列化的值
            cleaned = {k: str(v) for k, v in data.items()}
            return json.dumps(cleaned, ensure_ascii=False)


class KeywordsExtractor(BaseAgent):
    def __init__(self, max_retries: int = 3):
        super().__init__()
        self.max_retries = max_retries  # 最大重试次数
        self.llm_client = OpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
        )

    def run(self, user_query: str) -> Dict:
        """提取关键词组，带重试机制"""
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                messages = [
                    {"role": "system", "content": Prompts.get_prompt("keywords_extractor")["system"]},
                    {"role": "user", "content": user_query},
                ]

                completion = self.llm_client.chat.completions.create(  # type: ignore
                    model=config.llm_model_name,
                    messages=messages,
                    max_tokens=200,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    stream=False,
                )

                ai_response = completion.choices[0].message.content
                logger.debug(f"原始AI响应: {ai_response}")

                parsed_dict = KeywordsExtractor._parse_ai_response(ai_response)
                keywords_zh = parsed_dict.get("keywords_zh", [])
                keywords_en = parsed_dict.get("keywords_en", [])

                all_keywords = list(set(keywords_zh + keywords_en))

                # 验证关键词质量
                if all_keywords:
                    return {
                        "user_query": user_query,
                        "keywords": all_keywords
                    }

                # 如果没有关键词但没报错，也触发重试
                logger.warning(f"无关键词返回，重试 {retry_count + 1}/{self.max_retries}")

            except Exception as e:
                logger.error(f"关键词组提取失败 (尝试 {retry_count + 1}/{self.max_retries}): {e}")

            # 准备重试
            retry_count += 1
            if retry_count < self.max_retries:
                # 计算随机等待时间 (指数退避 + 随机抖动)
                base_delay = 0.5  # 基础等待时间
                max_delay = 5.0  # 最大等待时间
                delay = min(base_delay * (2 ** retry_count), max_delay)  # 指数退避
                jitter = random.uniform(0.5, 1.5)  # 随机抖动因子
                wait_time = delay * jitter

                logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)

        # 所有重试都失败后返回默认结果
        logger.error(f"关键词提取失败，已重试 {self.max_retries} 次")
        return {"user_query": user_query}

class SearchCriteria:
    """支持中英文混合的搜索条件"""

    def __init__(
            self,
            keywords: List[str] = None,
            title: str = "",
            content: str = "",
            publisher: str = "",
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            match_logic: str = "OR"
    ):
        """
        初始化搜索条件

        Args:
            keywords: 关键词列表（中英文混合）
            title: 标题搜索词（支持中英文）
            content: 内容搜索词（支持中英文）
            publisher: 发布者名称（支持中英文）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
            match_logic: 匹配逻辑 ("AND" 或 "OR")
        """
        self.source = set([file["source"] for file in FileModel().files])
        # 验证逻辑类型
        if match_logic not in ["AND", "OR"]:
            raise ValueError("match_logic 必须是 'AND' 或 'OR'")

        if publisher != "" and publisher not in self.source:
            raise ValueError(f"'publisher' 字段必须在这些其中之一: {self.source}")

        if keywords is None:
            keywords = []

        self.keywords = keywords
        self.title = title
        self.content = content
        self.publisher = publisher
        self.start_date = start_date
        self.end_date = end_date
        self.match_logic = match_logic

    def __repr__(self):
        return (f"SearchCriteria(keywords={self.keywords}, title='{self.title}', "
                f"content='{self.content[:20]}...', publisher='{self.publisher}', "
                f"start_date={self.start_date}, end_date={self.end_date}, "
                f"match_logic='{self.match_logic}')")


class BaseRetriever(BaseAgent):
    """检索器基类，包含通用匹配逻辑"""

    def __init__(self, max_results: int = 10):
        super().__init__()
        self.max_results = max_results

    @abstractmethod
    def run(self, criteria: SearchCriteria) -> List[Dict]:
        """执行检索"""
        pass

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        文本规范化处理：
        1. 转换为小写
        2. 移除变音符号（如é->e）
        3. 移除标点符号
        4. 标准化空格
        """
        # 移除变音符号
        normalized = normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        # 转换为小写
        normalized = normalized.lower()
        # 移除标点符号（保留字母数字和空格）
        normalized = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in normalized)
        # 标准化空格（合并多个空格）
        return ' '.join(normalized.split())

    @staticmethod
    def _match_keywords(
            target_keywords: List[str],
            criteria: SearchCriteria
    ) -> Tuple[bool, List[str]]:
        """关键词匹配逻辑（支持中英文混合）
        1. 保留原始大小写比较
        2. 支持大小写不敏感地备选匹配
        3. 返回匹配结果和匹配到的关键词列表
        """
        if not criteria.keywords:
            return True, []  # 无关键词条件，视为匹配

        matched_keywords = []

        for query_kw in criteria.keywords:
            # 清理查询关键词（保留原始大小写）
            clean_query = query_kw.strip()
            found = False

            for target_kw in target_keywords:
                # 清理目标关键词
                clean_target = target_kw.strip()

                # 1. 精确匹配（保留大小写）
                if clean_query == clean_target:
                    found = True
                    matched_keywords.append(query_kw)
                    break

                # 2. 大小写不敏感匹配（备选）
                if clean_query.lower() == clean_target.lower():
                    found = True
                    matched_keywords.append(query_kw)
                    break

            # AND逻辑需要所有关键词都匹配
            if criteria.match_logic == "AND" and not found:
                return False, []

        # OR逻辑只需至少一个匹配
        if criteria.match_logic == "OR" and not matched_keywords:
            return False, []

        return True, matched_keywords

    @staticmethod
    def _match_text(target_text: str, search_text: str) -> bool:
        """文本模糊匹配（修复大小写处理）"""
        if not search_text.strip():
            return True

        # 使用大小写不敏感匹配
        return search_text.strip().lower() in target_text.lower()
    @staticmethod
    def _match_date(
            target_date: Union[datetime, str],
            criteria: SearchCriteria
    ) -> bool:
        # 转换为日期对象
        if isinstance(target_date, str):
            try:
                # 尝试解析ISO格式（含时间）
                if 'T' in target_date:
                    dt = datetime.fromisoformat(target_date)
                # 尝试解析标准日期格式
                elif len(target_date) == 10:  # YYYY-MM-DD
                    dt = datetime.strptime(target_date, "%Y-%m-%d")
                # 其他格式尝试自动解析
                else:
                    dt = datetime.fromisoformat(target_date)
                target_date = dt
            except (ValueError, TypeError):
                logger.warning(f"日期解析失败: {target_date}")
                return False

        # 提取日期部分（忽略时间）
        if isinstance(target_date, datetime):
            target_date = target_date.date()

        # 检查日期范围
        if criteria.start_date:
            start_date = criteria.start_date.date()
            if target_date < start_date:
                return False

        if criteria.end_date:
            end_date = criteria.end_date.date()
            if target_date > end_date:
                return False

        return True

    @staticmethod
    def _path2uri(file_path: str):
        try:
            system = platform.system()

            # 提取纯文件名（去掉路径部分）
            file_name = os.path.basename(file_path)

            # 获取当前脚本所在目录作为根目录（使用正斜杠）
            custom_root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")

            # 构建完整文件路径
            file_path = os.path.join(custom_root, "library_files", file_name) # type: ignore

            result = {}

            # 检查文件是否存在
            if os.path.isfile(file_path):
                # 构建PDF URI
                if system == "Windows":
                    uri_path = file_path.replace("\\", "/")
                    if ":" in uri_path:
                        drive, path_without_drive = uri_path.split(":", 1)
                        uri_path = f"/{drive}:{path_without_drive}"

                    return "file://" + quote(uri_path) # type: ignore
                else:
                    return "file://" + quote(file_path) # type: ignore

            # 文件不存在时返回None
            return None
        except Exception as e:
            logger.error(f"文件路径转换失败: {e}")
            return None

class FileRetriever(BaseRetriever):
    """文件检索器（支持多条件查询）"""

    def __init__(self, max_results: int = 10):
        super().__init__(max_results)
        logger.info(f"FileRetriever 初始化 | 最大返回文件数: {max_results}")


    def _get_all_files(self) -> List[Dict]:
        return self.file_model.files.all()

    def run(self, criteria: SearchCriteria) -> List[Dict]:
        """多条件文件检索"""
        try:
            logger.info(f"文件检索 | 条件: {criteria}")
            files = self._get_all_files()
            if not files:
                logger.info("数据库中无文件记录")
                return []

            results = []
            for file in files:
                if file.get("opt_msg") != "processed":
                    continue

                # 日期检查
                file_date = file.get("published_date")
                if not self._match_date(file_date, criteria):
                    continue

                # 发布者检查
                publisher = file.get("source", "")
                if not self._match_text(publisher, criteria.publisher):

                    continue

                # 标题检查
                title = file.get("file_name", "")
                if not self._match_text(title, criteria.title):
                    continue

                # 关键词检查
                file_tags = file.get("tags", [])
                match_ok, matched_kws = self._match_keywords(file_tags, criteria)
                if not match_ok:
                    continue

                # 内容检查
                content = file.get("file_desc", "")
                if criteria.content and not self._match_text(content, criteria.content):
                    continue

                # 添加到结果
                results.append({
                    "file_name": file.get("file_name"),
                    "topic": file.get("topic"),
                    "content": content,
                    "published_by": publisher,
                    "published_date": file_date,
                    # "tags": file_tags,
                    "file_uri": self._path2uri(file.get("file_path")),
                    "matched_keywords": matched_kws  # 添加匹配的关键词
                })

            return results[:self.max_results]

        except Exception as e:
            logger.error(f"文件检索失败: {str(e)}", exc_info=True)
            return []


class ContentRetriever(BaseRetriever):
    def __init__(self, max_results: int = 10):
        super().__init__(max_results)
        logger.info(f"ContentRetriever 初始化 | 最大返回页面数: {max_results}")

    def _get_file_info(self, file_id: str) -> Dict:
        return self.file_model.get_file_by_id(file_id)

    def _get_all_contents(self) -> List[Dict]:
        return self.content_model.contents.all()

    def run(self, criteria: SearchCriteria) -> List[Dict]:
        try:
            logger.info(f"内容检索 | 条件: {criteria}")
            contents = self._get_all_contents()
            if not contents:
                logger.info("数据库中无内容记录")
                return []

            results = []
            for content in contents:
                if content.get("property") != "main":
                    continue

                file_id = content.get("file_id")
                if not file_id:
                    continue

                try:
                    file_info = self._get_file_info(file_id)
                except Exception as e:
                    logger.warning(f"获取文件信息失败: {file_id} - {str(e)}")
                    continue

                # 日期检查
                file_date = file_info.get("published_date")
                if not self._match_date(file_date, criteria):
                    continue

                # 发布者检查
                publisher = file_info.get("source", "")
                if not self._match_text(publisher, criteria.publisher):
                    continue

                # 标题检查
                title = file_info.get("file_name", "")
                if not self._match_text(title, criteria.title):
                    continue

                # 内容检查
                content_text = content.get("content", "")
                if criteria.content and not self._match_text(content_text, criteria.content):
                    continue

                # 关键词检查
                content_keywords = content.get("keywords", [])
                match_ok, matched_kws = self._match_keywords(content_keywords, criteria)
                if not match_ok:
                    continue

                # 添加到结果
                results.append({
                    "file_name": title,
                    "page_number": content.get("page_number"),
                    "page_abstract": content.get("abstract"),
                    "page_content": content_text,
                    "page_keywords": content_keywords,
                    "published_by": publisher,
                    "published_date": file_date,
                    "file_uri": self._path2uri(file_info.get("file_path")),
                    "matched_keywords": matched_kws  # 使用匹配的关键词
                })

            return results[:self.max_results]

        except Exception as e:
            logger.error(f"内容检索失败: {str(e)}", exc_info=True)
            return []

if __name__ == "__main__":
    pass



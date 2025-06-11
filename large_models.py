import base64
import os
import asyncio
import json
from datetime import datetime

from openai import AsyncOpenAI

from models import FileModel, ContentModel
from decoder import PDFDecoder
from config import config
from prompts import Prompts
from logger import setup_logger

logger = setup_logger(__name__, use_emoji=True)

class IMGRecognizer:
    def __init__(self):
        self.file_db = FileModel()
        self.content_db = ContentModel()
        self.decoder = PDFDecoder()
        self.vlm_client = AsyncOpenAI(
            api_key=config.vlm_api_key,
            base_url=config.vlm_base_url,
        )
        self.model = config.vlm_model_name

    async def image_understanding(self):
        """调用qwen2.5-vl-72b-instruct模型，生成满足pages中所有信息"""
        # 获取需处理的页面
        file_pages = await self._get_unidentified()
        if not file_pages:
            logger.info("没有需要处理的页面")
            return

        # 展开所有待处理页面
        all_pages = []
        for file_group in file_pages:
            for page_info in file_group["info"]:
                all_pages.append({
                    "file_id": file_group["file_id"],
                    "page_number": page_info["page_number"],
                    "page_path": page_info["page_path"]
                })

        logger.info(f"📖 开始处理文件份数：[{len(file_pages)}]份，共 {len(all_pages)} 页")

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(5)

        # 创建任务列表
        tasks = []
        for page in all_pages:
            task = asyncio.create_task(
                self._process_page_with_retry(page, semaphore)
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        success_count = 0
        for result in results:
            if not isinstance(result, Exception) and result:
                success_count += 1

        logger.info(f"✅ 处理完成！成功处理页数: {success_count}页，失败页数: {len(results) - success_count}页")

    async def _process_page_with_retry(self, page: dict, semaphore: asyncio.Semaphore):
        """带重试机制的页面处理"""
        max_retries = 3
        retry_delay = 2.0  # 初始延迟2秒

        async with semaphore:
            for attempt in range(max_retries):
                try:
                    # 调用大模型处理页面
                    ai_response = await self.process_page(page)
                    if not ai_response:
                        raise ValueError("AI返回空响应")

                    # 解析AI返回的JSON
                    ai_data = IMGRecognizer._parse_ai_response(ai_response)
                    if not ai_data:
                        raise ValueError("AI响应解析失败")

                    # 更新数据库
                    await self._update_models(page, ai_data)
                    return True

                except Exception as e:
                    logger.warning(f"页面处理尝试 {attempt + 1}/{max_retries} 失败 | "
                                   f"文件: {page['file_id']} 页: {page['page_number']} | "
                                   f"错误: {str(e)}")

                    # 最后一次尝试仍然失败
                    if attempt == max_retries - 1:
                        logger.error(f"❌ 页面处理失败 | "
                                     f"文件: {page['file_id']} 页: {page['page_number']} | "
                                     f"最终错误: {str(e)}")
                        return False

                    # 指数退避重试
                    await asyncio.sleep(retry_delay * (2 ** attempt))

        return False
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

    async def _update_models(self, page: dict, ai_data: dict):
        """更新FileModel和ContentModel"""
        file_id = page["file_id"]
        page_number = page["page_number"]
        now = datetime.now().isoformat()

        # 1. 更新FileModel中的页面状态
        file_record = self.file_db.get_file_by_id(file_id)
        if not file_record:
            raise ValueError(f"文件ID不存在: {file_id}")

        # 在文件记录的pages数组中查找并更新对应页面
        updated_pages = []
        page_found = False

        for p in file_record["pages"]:
            if p["page_number"] == page_number:
                # 更新页面状态
                p.update({
                    "is_aigc": True,
                    "processed_at": now,
                    "property": ai_data.get("property", ""),
                    "title": ai_data.get("title", ""),
                    "abstract": ai_data.get("abstract", ""),
                    "keywords": ai_data.get("keywords", [])
                })
                page_found = True
            updated_pages.append(p)

        if not page_found:
            raise ValueError(f"文件中未找到页码: {page_number}")

        # 更新整个pages数组
        self.file_db.files.update(
            {"pages": updated_pages},
            self.file_db.query.file_id == file_id
        )

        # 2. 更新文件级别的tags和file_desc字段
        # 重新获取更新后的文件记录（包含所有页面最新数据）
        updated_file_record = self.file_db.get_file_by_id(file_id)
        if not updated_file_record:
            raise ValueError(f"更新后文件ID不存在: {file_id}")

        # 收集所有页面的keywords
        all_keywords = []
        for p in updated_file_record["pages"]:
            if p.get("keywords") and isinstance(p["keywords"], list):
                all_keywords.extend(p["keywords"])

        # 去重并过滤空值
        unique_keywords = list(set(filter(None, all_keywords)))

        # 收集所有页面的abstract（按页码排序）
        abstracts = []
        for p in sorted(updated_file_record["pages"], key=lambda x: x["page_number"]):
            if p.get("abstract"):
                abstracts.append(p["abstract"])

        # 用换行符连接abstracts
        file_desc = "\n".join(abstracts)

        # 更新文件记录的tags和file_desc字段
        self.file_db.files.update(
            {
                "tags": unique_keywords,
                "file_desc": file_desc
            },
            self.file_db.query.file_id == file_id
        )

        # 3. 创建/更新ContentModel记录
        # 创建新记录时需要的数据
        content_data = {
            "file_id": file_id,
            "page_number": page_number,
            "content": ai_data.get("content", ""),
            "title": ai_data.get("title", ""),  # 新增字段
            "prop": ai_data.get("property", ""),  # 新增字段
            "abstract": ai_data.get("abstract", ""),  # 新增字段
            "keywords": ai_data.get("keywords", []),
            "created_at": now  # 只在创建时使用
        }

        # 检查是否已存在内容记录
        existing_content = self.content_db.contents.get(
            (self.content_db.query.file_id == file_id) &
            (self.content_db.query.page_number == page_number)
        )

        if existing_content:
            # 更新现有记录 - 移除创建时间字段
            update_data = content_data.copy()
            update_data.pop("created_at", None)

            self.content_db.update_content(
                existing_content["page_id"],
                **update_data
            )
            logger.debug(f"内容记录更新 | 文件: {file_id} 页: {page_number}")
        else:
            # 创建新记录（包含所有字段）
            self.content_db.create_content(**content_data)
            logger.debug(f"内容记录创建 | 文件: {file_id} 页: {page_number}")

        logger.info(f"✅ 更新完成 | 文件: {file_id} 页: {page_number}")

    async def process_page(self, page: dict) -> str:
        """处理单个页面并获取AI描述"""
        page_path = page.get("page_path")
        if not page_path or not os.path.exists(page_path):
            logger.warning(f"页面图片不存在：{page_path}")
            return f"[缺失页面 {page.get('page_number')}]"
        # 获取优化后的图像编码
        base64_image = await self._image_to_base64(page_path)
        if not base64_image:
            return ""

        # 获取提示模板
        try:
            prompt = Prompts.get_prompt(self.model)
            system_prompt = prompt["system"]
            user_message = prompt["user"]
        except ValueError as e:
            logger.error(f"提示获取失败: {str(e)}")
            return ""

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                    {
                        "type": "text",
                        "text": user_message
                    },
                ],
            }
        ]

        try:
            # 调用Qwen VL模型
            response = await self.vlm_client.chat.completions.create(
                model=self.model,  # qwen-vl-72b-instruct
                messages=messages,  # type: ignore
                temperature=0.3,  # 低温度确保输出稳定性
                max_tokens=2500  # 合理控制token量
            )

            content = response.choices[0].message.content
            return content

        except Exception as e:
            logger.error(f"页面处理失败 P{page['page_number']} | {str(e)}")
            return f"[处理失败 P{page['page_number']}]"

    async def _get_unidentified(self):
        files = self.file_db.get_all_files()
        result = []
        for file in files:
            file_id = file.get("file_id", "未知文件ID")
            pages = file.get("pages", [])
            item = [
                {
                    "page_number": page["page_number"],
                    "page_path": page["page_path"]
                }
                for page in pages if page.get("is_aigc") is False
            ]
            result.append({
                "file_id": file_id,
                "info": item
            })
        return result

    # 图像转base64
    @staticmethod
    async def _image_to_base64(image_path: str) -> str:
        if not os.path.exists(image_path):
            logger.warning(f"图片不存在：{image_path}")
            return ""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')


if __name__ == "__main__":
    recognizer = IMGRecognizer()
    asyncio.run(recognizer.image_understanding())

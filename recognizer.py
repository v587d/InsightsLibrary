import base64
import os
import json
import asyncio
import time
from datetime import datetime

from openai import AsyncOpenAI

from models import FileModel, ContentModel
from config import config
from prompts import Prompts
from logger import setup_logger

logger = setup_logger(__name__)

class IMGRecognizer:
    def __init__(self):
        self.file_model = FileModel()
        self.content_model = ContentModel()
        self.vlm_client = AsyncOpenAI(
            api_key=config.vlm_api_key,
            base_url=config.vlm_base_url,
        )
        self.model = config.vlm_model_name
        self.prompt_cache = {}  # Cache for prompt templates

    async def image_understanding(self):
        """Process unidentified pages using VLM model."""
        file_pages = await self._get_unidentified()
        if not file_pages:
            logger.info("No pages to process.")
            return

        all_pages = []
        for file_group in file_pages:
            for page_info in file_group["info"]:
                all_pages.append({
                    "file_id": file_group["file_id"],
                    "page_number": page_info["page_number"],
                    "page_path": page_info["page_path"]
                })

        logger.info(f"Starting to process {len(file_pages)} files with {len(all_pages)} pages.")

        # Use semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(2)

        # Process pages one by one with concurrency control
        tasks = []
        for page in all_pages:
            task = asyncio.create_task(self._process_page_with_retry(page, semaphore))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for result in results if not isinstance(result, Exception) and result)
        logger.info(f"Processing completed. Success: {success_count} pages, Failed: {len(results) - success_count} pages.")

    async def _process_page_with_retry(self, page: dict, semaphore: asyncio.Semaphore):
        """Process page with retry mechanism."""
        max_retries = 3
        retry_delay = 5.0

        async with semaphore:
            for attempt in range(max_retries):
                try:
                    ai_response = await self.process_page(page)
                    if not ai_response:
                        raise ValueError("Empty AI response")
                    ai_data = self._parse_ai_response(ai_response)
                    if not ai_data:
                        raise ValueError("Failed to parse AI response")
                    await self._update_models(page, ai_data)
                    return True

                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for file {page['file_id']} page {page['page_number']}: {str(e)}")
                    if attempt == max_retries - 1:
                        if "429" in str(e):
                            logger.error(
                                f"Max retries reached due to rate limit for file {page['file_id']} page {page['page_number']}: {str(e)}. Skipping further processing.")
                            return False
                        else:
                            logger.error(
                                f"Max retries reached for file {page['file_id']} page {page['page_number']}: {str(e)}. Marking as processed.")
                            await self._update_models(page, {})
                            return False

                    if "429" in str(e):
                        reset_time = int(
                            e.args[0].get('metadata', {}).get('headers', {}).get('X-RateLimit-Reset', 0)) - int(time.time() * 1000)
                        if reset_time > 0:
                            await asyncio.sleep(reset_time / 1000 + 1)
                    await asyncio.sleep(retry_delay * (2 ** attempt))
        return False

    @staticmethod
    def _parse_ai_response(ai_response: str) -> dict:
        """Parse JSON response from AI."""
        if ai_response.startswith("[Processing failed"):
            logger.warning(f"Skipping parse for failed response: {ai_response}")
            return {}
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parsing failed: {e}, Response: {ai_response}")
            return {}

    async def _update_models(self, page: dict, ai_data: dict):
        """Update FileModel and ContentModel with AI data."""
        file_id = page["file_id"]
        page_number = page["page_number"]
        now = datetime.now().isoformat()

        file_record = self.file_model.get_file_by_id(file_id)
        if not file_record:
            raise ValueError(f"File ID not found: {file_id}")

        updated_pages = []
        page_found = False
        for p in file_record["pages"]:
            if p["page_number"] == page_number:
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
            raise ValueError(f"Page {page_number} not found in file")

        self.file_model.files.update(
            {"pages": updated_pages},
            self.file_model.query.file_id == file_id
        )

        updated_file_record = self.file_model.get_file_by_id(file_id)
        if not updated_file_record:
            raise ValueError(f"Updated file ID not found: {file_id}")

        all_keywords = [kw for p in updated_file_record["pages"] for kw in p.get("keywords", []) if kw]
        unique_keywords = list(set(all_keywords))

        abstracts = [p["abstract"] for p in sorted(updated_file_record["pages"], key=lambda x: x["page_number"]) if p.get("abstract")]
        file_desc = "\n".join(abstracts)

        self.file_model.files.update(
            {"tags": unique_keywords, "file_desc": file_desc},
            self.file_model.query.file_id == file_id
        )

        if ai_data:
            content_data = {
                "file_id": file_id,
                "page_number": page_number,
                "content": ai_data.get("content", ""),
                "title": ai_data.get("title", ""),
                "prop": ai_data.get("property", ""),
                "abstract": ai_data.get("abstract", ""),
                "keywords": ai_data.get("keywords", []),
                "created_at": now
            }


            existing_content = self.content_model.contents.get(
                (self.content_model.query.file_id == file_id) &
                (self.content_model.query.page_number == page_number)
            )

            if existing_content:
                update_data = {k: v for k, v in content_data.items() if k != "created_at"}
                self.content_model.update_content(existing_content["page_id"], **update_data)
                logger.debug(f"Updated content for file {file_id} page {page_number}")
            else:
                self.content_model.create_content(**content_data)
                logger.debug(f"Created content for file {file_id} page {page_number}")

            logger.info(f"Updated file {file_id} page {page_number}")

    async def process_page(self, page: dict) -> str:
        """Process a single page and get AI description."""
        page_path = page.get("page_path")
        if not page_path or not os.path.exists(page_path):
            logger.warning(f"Page image not found: {page_path}")
            return f"[Missing page {page.get('page_number')}]"

        base64_image = self._image_to_base64(page_path)
        if not base64_image:
            return ""

        if self.model not in self.prompt_cache:
            self.prompt_cache[self.model] = Prompts.get_prompt(self.model)
        prompt = self.prompt_cache[self.model]

        messages = [
            {"role": "system", "content": [{"type": "text", "text": prompt["system"]}]},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                {"type": "text", "text": prompt["user"]}
            ]}
        ]

        try:
            response = await self.vlm_client.chat.completions.create(
                model=self.model,
                messages=messages, # type: ignore
                temperature=0.3,
                max_tokens=2000, # Original: 2500
                timeout = 30.0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to process page {page['page_number']}: {str(e)}")
            return f"[Processing failed P{page['page_number']}]"

    async def _get_unidentified(self):
        """Get all unidentified pages from files."""
        files = self.file_model.get_all_files()
        result = []
        for file in files:
            file_id = file.get("file_id", "unknown")
            pages = file.get("pages", [])
            item = [
                {"page_number": page["page_number"], "page_path": page["page_path"]}
                for page in pages if page.get("is_aigc") is False
            ]
            if item:
                result.append({"file_id": file_id, "info": item})
        return result

    @staticmethod
    def _image_to_base64(image_path: str) -> str:
        """Convert image to base64 synchronously."""
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return ""
        with open(image_path, "rb") as fp:
            return base64.b64encode(fp.read()).decode('utf-8')

if __name__ == "__main__":
    recognizer = IMGRecognizer()
    asyncio.run(recognizer.image_understanding())


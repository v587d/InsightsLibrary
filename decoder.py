import os
import shutil
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image
from PIL.Image import Resampling
from typing import List

from models import FileModel
from config import config
from logger import setup_logger

logger = setup_logger(__name__, use_emoji=True)

class PDFDecoder:
    """PDF解码器：负责PDF文件扫描、页面提取和数据库更新"""

    def __init__(
            self,
            files_dir: str = config.FILES_DIR,
            pages_dir: str = config.PAGES_DIR
    ) -> None:
        """
        初始化PDF解码器

        Args:
            files_dir: 源PDF文件目录
            pages_dir: 页面图片输出目录
        """
        self.files_dir = files_dir
        self.pages_dir = pages_dir
        self.file_model = FileModel()
        logger.info(f"📂 PDF解码器初始化 | 文件目录: {files_dir} | 页面目录: {pages_dir}")

    def scan_files(self) -> None:
        """扫描文件目录，检测变更文件并处理"""
        # 确保目录存在
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.pages_dir, exist_ok=True)
        logger.info(f"🔍 开始扫描目录: {self.files_dir}")
        file_count = 0
        processed_count = 0
        error_count = 0
        # 获取所有PDF文件列表
        pdf_files = [f for f in os.listdir(self.files_dir)
                     if f.lower().endswith('.pdf')]
        if not pdf_files:
            logger.info("📭 目录中没有PDF文件")
            return
        logger.info(f"📄 发现 {len(pdf_files)} 个PDF文件")
        for pdf in pdf_files:
            file_count += 1
            file_path = os.path.join(self.files_dir, pdf)
            try:
                # 检查文件是否变更
                if self.file_model.is_file_changed(file_path):
                    logger.info(f"🔄 检测到变更文件: {pdf}")

                    # 获取或创建文件记录
                    file_record = self.file_model.get_file_by_path(file_path)
                    if not file_record:
                        # 新文件创建记录
                        file_hash = FileModel.calculate_md5(file_path)
                        last_modified = os.path.getmtime(file_path)
                        self.file_model.create_file(
                            file_path,
                            pdf,
                            file_hash,
                            last_modified,
                            opt_msg="initial",
                        )
                        # 关键修复：创建后立即更新文件状态
                        file_record = self.file_model.get_file_by_path(file_path)
                        self.file_model.update_file(
                            file_record["file_id"],
                            file_hash=file_hash,
                            last_modified=last_modified,
                            opt_msg="pending_processing"  # 添加新状态
                        )

                    # 使用file_id处理文件
                    self.process_file(file_record["file_id"])
                    processed_count += 1

                    # 关键修复：处理完成后更新文件状态
                    current_hash = FileModel.calculate_md5(file_path)
                    current_mtime = os.path.getmtime(file_path)
                    self.file_model.update_file(
                        file_record["file_id"],
                        file_hash=current_hash,
                        last_modified=current_mtime,
                        opt_msg="processed"
                    )
                else:
                    logger.debug(f"✅ 文件未变更: {pdf}")
            except Exception as e:
                error_count += 1
                logger.error(f"🚨 处理文件失败: {pdf} | 错误: {e}")
                logger.exception(f"文件处理错误详情: {pdf}")
        # 扫描结果总结
        logger.success(
            f"📊 扫描完成 | 总文件: {file_count} | "
            f"处理文件: {processed_count} | 失败文件: {error_count}"
        )

    def process_file(self, file_id: str) -> None:
        """
        处理单个PDF文件（使用file_id标识）

        Args:
            file_id: 文件的唯一标识符
        """
        try:
            # 通过file_id获取文件记录
            file_record = self.file_model.get_file_by_id(file_id)
            if not file_record:
                logger.error(f"🚨 文件记录不存在: file_id={file_id}")
                return

            file_path = file_record["file_path"]
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            page_subdir = os.path.join(self.pages_dir, base_name)

            # ===== 事务状态标记 =====
            # 步骤1: 设置操作状态为"initial"（如果尚未设置）
            if file_record.get("opt_msg") != "initial":
                self.file_model.update_file(file_id, opt_msg="initial")

            # 步骤2: 清理前标记为"pages_updating"
            self.file_model.update_file(file_id, opt_msg="pages_updating")

            # 执行清理操作
            self._cleanup_invalid_pages(file_id, page_subdir)

            # 步骤3: 处理PDF文件（需要文件路径）
            pages_paths = self._pdf_to_pages(file_path, self.pages_dir)

            # 步骤4: 添加页面记录
            success_count = 0
            page_data_list = []
            for i, img_path in enumerate(pages_paths):
                page_data_list.append({
                    "page_number": i + 1,
                    "page_path": img_path,
                    # "text_content": None,
                    "abstract": None,
                    "keywords": [],
                    "is_aigc": False,
                    "processed_at": datetime.now().isoformat()
                })

            # 使用file_id批量添加页面
            if self.file_model.add_pages(file_id, page_data_list):
                success_count = len(page_data_list)

            # 步骤5: 操作完成标记为"completed"
            self.file_model.update_file(file_id, opt_msg="completed")
            logger.success(f"📚 完成处理 | 文件: {file_name} | 页数: {success_count}/{len(pages_paths)}")
            # ===== 状态标记结束 =====

        except Exception as e:
            # 获取当前操作状态
            current_file = self.file_model.get_file_by_id(file_id) or {}
            opt_status = current_file.get("opt_msg", "unknown")
            file_name = current_file.get("file_name", "unknown")
            # 根据状态进行错误处理
            if opt_status == "pages_updating":
                logger.error(f"🚨 严重错误: 文件 {file_name} 已清理但未完成更新！")
                self.file_model.update_file(file_id, opt_msg="needs_recovery")
            else:
                logger.error(f"⚠️ 处理文件失败: {file_name} | 阶段: {opt_status} | 错误: {e}")
            logger.exception(f"文件处理错误详情")

    def _cleanup_invalid_pages(self, file_id: str, page_dir: str) -> None:
        """
        清理失效数据（数据库记录和图片文件）

        Args:
            file_id: 文件的唯一标识符（用于数据库操作）
            page_dir: 页面图片目录（用于文件系统操作）
        """
        try:
            # 删除数据库中的页面记录（使用file_id）
            self.file_model.delete_file_pages(file_id)
            logger.debug(f"🗑️ 已删除数据库页面记录: file_id={file_id}")
            # 删除对应的图片目录（如果存在）
            if os.path.exists(page_dir):
                shutil.rmtree(page_dir)
                logger.info(f"🧹 已清理旧页面图片: {os.path.basename(page_dir)}")
        except Exception as e:
            logger.error(f"⚠️ 清理旧页面失败: file_id={file_id}, 错误: {e}")

    @staticmethod
    def _pdf_to_pages(
            pdf_path: str,
            output_dir: str,
            dpi: int = 200,
            max_size: int = 1600
    ) -> List[str]:
        """
        将PDF每页转换为优化后的JPEG图像

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            dpi: 渲染分辨率（默认200）
            max_size: 最大尺寸（默认1600px）

        Returns:
            生成的图片路径列表
        """
        # 创建基于文件名的子目录
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_output_dir = os.path.join(output_dir, pdf_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        page_paths = []
        doc = None

        try:
            logger.info(f"🖨️ 开始转换PDF: {os.path.basename(pdf_path)}")
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            for i in range(total_pages):
                page = doc.load_page(i)
                # 渲染PDF页面为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))

                # 转换为PIL图像并优化
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                img.thumbnail((max_size, max_size), Resampling.LANCZOS)

                # 保存优化图像
                img_path = os.path.join(pdf_output_dir, f"page_{i + 1}.jpg")
                img.save(img_path, "JPEG", quality=90, optimize=True)
                page_paths.append(img_path)

                if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                    logger.debug(f"  已转换: {i + 1}/{total_pages} 页")

            logger.success(f"🖼️ 转换完成 | 总页数: {total_pages} | 输出目录: {pdf_output_dir}")
            return page_paths

        except Exception as e:
            logger.error(f"⚠️ PDF转换失败: {os.path.basename(pdf_path)} | 错误: {e}")
            # 清理部分生成的图片（仅当有图片生成时才清理）
            if page_paths:
                try:
                    # 只捕获预期的清理异常
                    shutil.rmtree(pdf_output_dir)
                    logger.info(f"🧹 已清理失败转换的图片目录: {pdf_output_dir}")
                except (OSError, PermissionError, FileNotFoundError) as cleanup_error:
                    # 处理文件系统相关的清理错误
                    logger.warning(
                        f"⚠️ 清理失败转换的图片目录时出错: {pdf_output_dir} | "
                        f"错误类型: {type(cleanup_error).__name__} | "
                        f"详情: {cleanup_error}"
                    )
                except Exception as unexpected_error:
                    # 捕获其他意外错误并记录堆栈
                    logger.error(
                        f"🚨 清理过程中发生意外错误: {unexpected_error}",
                        exc_info=True
                    )
            return []
        finally:
            if doc:
                doc.close()


if __name__ == "__main__":
    decoder = PDFDecoder()
    decoder.scan_files()

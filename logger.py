import logging
import sys
from logging.handlers import RotatingFileHandler

# 在模块层定义自定义日志级别常量
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, 'SUCCESS')


class UTF8StreamHandler(logging.StreamHandler):
    """支持 UTF-8 编码的控制台日志处理器"""

    def emit(self, record):
        try:
            msg = self.format(record)
            # 确保使用 UTF-8 编码写入控制台
            stream = self.stream
            stream.buffer.write(msg.encode('utf-8'))
            stream.buffer.write(self.terminator.encode('utf-8'))
            self.flush()
        except Exception as e:
            # 处理错误时避免递归
            print(f"⚠️ 日志处理器错误: {str(e)}", file=sys.stderr)
            self.handleError(record)


def setup_logger(name, use_emoji=False):
    logger = logging.getLogger(name)
    if hasattr(logger, 'success'):  # 防止重复初始化
        return logger

    logger.setLevel(logging.DEBUG)

    # 创建支持 UTF-8 的控制台处理器
    console_handler = UTF8StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 设置控制台格式（保留原有格式选项）
    console_format = (
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        if use_emoji
        else '[%(levelname)s] %(name)s: %(message)s'
    )
    console_handler.setFormatter(logging.Formatter(console_format))

    # 文件处理器（不需要修改，默认使用 UTF-8）
    file_handler = RotatingFileHandler(
        'application.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'  # 确保文件也使用 UTF-8
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # 移除可能存在的默认处理器
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 添加自定义 success 方法
    def success(msg, *args, **kwargs):
        if logger.isEnabledFor(SUCCESS_LEVEL):
            logger._log(SUCCESS_LEVEL, msg, args, **kwargs)

    logger.success = success

    return logger

import os
import platform
from urllib.parse import quote


def generate_pdf_uri(report_name):
    """
    为PDF报告生成URI链接

    参数：
    report_name -- 报告文件名或路径（如"library_files\\【亿欧智库】2024中国新能源智能汽车产业链出海战略研究报告.pdf"）

    返回：
    str: 成功时返回URI链接，失败时返回原始report_name
    """
    system = platform.system()

    # 提取纯文件名（去掉路径部分）
    file_name = os.path.basename(report_name)

    # 获取当前脚本所在目录作为根目录（使用正斜杠）
    custom_root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")

    # 构建完整文件路径
    file_path = os.path.join(custom_root, "library_files", file_name)

    # 检查文件是否存在
    if os.path.isfile(file_path):
        # 构建PDF URI
        if system == "Windows":
            uri_path = file_path.replace("\\", "/")
            if ":" in uri_path:
                drive, path_without_drive = uri_path.split(":", 1)
                uri_path = f"/{drive}:{path_without_drive}"
            return "file://" + quote(uri_path)
        else:
            return "file://" + quote(file_path)

    # 文件不存在时返回原始输入
    return report_name


if __name__ == "__main__":
    # 示例输入（可以是带路径的文件名）
    report_name = "library_files\\【亿欧智库】2024中国新能源智能汽车产业链出海战略研究报告.pdf"

    # 生成URI
    uri = generate_pdf_uri(report_name)

    # 打印结果
    if uri.startswith("file://"):
        print(f"✅ 成功生成PDF URI:")
        print(uri)
        print(f"\nMarkdown使用示例: [查看报告]({uri})")
    else:
        print(f"❌ 文件未找到，返回原始输入: {uri}")

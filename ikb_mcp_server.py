
from typing import Optional, List
from datetime import datetime


from mcp.server.fastmcp import FastMCP

from agents import SearchCriteria, FileRetriever, ContentRetriever

mcp = FastMCP("Insights Knowledge Base")

# @mcp.tool()
# async def get_latest_report() -> str:
    # import re
    # import asyncio
    # from collections import defaultdict
    # from models import FileModel
#     """
#     该方法实现了获取 **各主题最新的** 的报告集合。
#     """
#     try:
#         file_model = FileModel()
#         all_files = file_model.files.all()
#         # 如果没有文件记录
#         if not all_files:
#             return "当前没有可用的洞察报告"
#
#         # 按主题分组，并记录每个主题的最新报告
#         topic_reports = defaultdict(list)
#
#         for file in all_files:
#             topic = file.get('topic', '未分类')
#             # 只处理有发布日期的报告
#             if 'published_date' in file and file['published_date']:
#                 topic_reports[topic].append(file)
#
#         # 如果没有找到任何有日期的报告
#         if not topic_reports:
#             return "未找到包含发布日期的报告"
#
#         # 准备结果字符串
#         result = []
#
#         # 为每个主题找到最新报告
#         for topic, reports in topic_reports.items():
#             # 按日期倒序排序（最近的在前）
#             reports.sort(
#                 key=lambda x: datetime.strptime(x['published_date'], "%Y-%m-%d"),
#                 reverse=True
#             )
#
#             latest_report = reports[0]
#             file_name = latest_report.get('file_name', '未知报告')
#             publisher = latest_report.get('source', '未知发布者')
#             language = latest_report.get('language', '未知语言')
#             pages = len(latest_report.get('pages', 0))
#             tags = latest_report.get('tags', [])[:10]
#
#             # 按指定格式添加报告摘要
#             result.append(
#                 f"# Topic: {topic}\n\n"
#                 f"## Insights report name: {file_name}\n\n"
#                 f"- Publisher: {publisher}"
#                 f"- Language: {language}"
#                 f"- Pages: {pages}"
#                 f"- Partial Tags: {tags}"
#             )
#
#         # 用两个换行符分隔不同主题的报告
#         return "\n\n".join(result)
#
#     except Exception as e:
#         # 记录错误日志（实际项目中）
#         return f"获取报告失败: {str(e)}"

@mcp.tool()
async def search_report_profile(
        keywords: List[str] = None,
        title: str = "",
        content: str = "",
        publisher: str = "",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        match_logic: str = "OR",

):
    """该方法用于查询多条件组合的报告概况。LLM需根据用户输入的消息(user_message)提炼出以下参数。
    ️⚠️注意：当LLM引用该方法返回的结果时，必须用markdown格式明确、醒目告知用户引自哪篇报告和具体访问地址！
    比如“(以上观点引自《Open source technology in the age of AI》)[<如果"file_uri"不为空，这里完整填入file_uri>]”

    参数：
        keywords: List[str] = [], 整篇报告的关键词。**非常重要！如果没有keywords则传一个空列表。**
        ⚠️注意：
            - 将每个关键词自动翻译为中英双语
            - 例如用户输入"帮我查询下科技上市公司前景哈？" → 应转换为["科技", "technology", "上市公司", "publicly listed company"， "前景", "prospect"]

        title: str = "", 报告标题包含词。
        content: str = "", 报告内容包含词。
        publisher: str = "", 报告发布者。
        start_date: Optional[datetime] = None, 报告查询开始日期。
        end_date: Optional[datetime] = None, 报告查询结束日期。
        match_logic: str = "OR", 匹配逻辑。"OR" 或者 "AND"，二选一，**优先用 "OR"**。

    返回：
        "file_name": 报告名称
        "topic": 报告主题
        "content": 报告整体摘要
        "published_by": 发布机构
        "published_date": 发布日期
        "file_uri": 报告存放于本地地址（⚠️使用时以markdown格式展示给用户，方便直接打开）
        "matched_keywords": 匹配关键词组
    """
    criteria = SearchCriteria(
        keywords=keywords,
        title=title,
        content=content,
        publisher=publisher,
        start_date=start_date,
        end_date=end_date,
        match_logic=match_logic,
    )

    retriever = FileRetriever()
    result = retriever.run(criteria)
    return result

@mcp.tool()
async def search_content_detail(
        keywords: List[str] = None,
        title: str = "",
        content: str = "",
        publisher: str = "",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        match_logic: str = "OR"
):
    """该方法用于查询符合多条件组合的报告详情页面。LLM需根据用户输入的消息(user_message)提炼出以下参数。
    ⚠️注意：当LLM引用该方法返回的结果时，必须用markdown格式明确、醒目告知用户引自哪篇报告和具体访问地址！
    比如“(以上观点引自《21世纪CEO的成功法则》第10、16页)[<如果"file_uri"不为空，这里完整填入file_uri>]”

    参数：
        keywords: List[str] = [], 报告详情页的关键词。**非常重要！如果没有keywords则传一个空列表。**
            ⚠️注意：
            - 将每个关键词自动翻译为中英双语
            - 例如用户输入"帮我查询下科技上市公司前景哈？" → 应转换为["科技", "technology", "上市公司", "publicly listed company"， "前景", "prospect"]
        
        title: str = "", 报告详情页标题包含词。
        content: str = "", 报告详情页内容包含词。
        publisher: str = "", 报告发布者。
        start_date: Optional[datetime] = None, 报告查询开始日期。
        end_date: Optional[datetime] = None, 报告查询结束日期。
        match_logic: str = "OR", 匹配逻辑。"OR" 或者 "AND"，二选一，**优先用 "OR"**。

    返回：
        file_name: 详情页来自于哪份报告名
        page_number: 页码
        page_abstract: 摘要
        page_content: 完整内容
        page_keywords: 详情页关键词
        published_by: 报告发布机构
        published_date:报告发布日期
        file_uri: 报告存放于本地地址（⚠️使用时以markdown格式展示给用户，方便直接打开）
        matched_keywords: 匹配关键词组
    """
    criteria = SearchCriteria(
        keywords=keywords,
        title=title,
        content=content,
        publisher=publisher,
        start_date=start_date,
        end_date=end_date,
        match_logic=match_logic,
    )
    retriever = ContentRetriever()
    result = retriever.run(criteria)
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")


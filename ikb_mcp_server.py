from typing import Optional, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from agents import SearchCriteria, FileRetriever, ContentRetriever

mcp = FastMCP("Insights Knowledge Base")

@mcp.tool()
async def search_report_profile(
        keywords: List[str] = None,
        title: str = "",
        content: str = "",
        publisher: str = "",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        match_logic: str = "OR",
        page_index: int = 1

):
    """该方法用于查询多条件组合的报告概况。LLM需根据用户输入的消息(user_message)提炼出以下参数。
    ️⚠️注意：当LLM引用该方法返回的结果时，必须用markdown格式明确、醒目告知用户引自哪篇报告和具体访问地址！
    比如“**观点引自《Open source technology in the age of AI》**
    > <如果"file_uri"不为空，这里完整填入file_uri>”

    参数：
        keywords: List[str] = None, 整篇报告的关键词。
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
        results：报告概览
          - "file_name": 报告名称
          - "topic": 报告主题
          - "content": 报告整体摘要
          - "published_by": 发布机构
          - "published_date": 发布日期
          - "file_uri": 报告存放于本地地址（⚠️使用时以markdown格式展示给用户，方便直接打开）
          - "matched_keywords": 匹配关键词组
        current_page：当前页码。⚠️当前页码小于总页码时，LLM需在结尾处提示用户可输入“下一页”查询更多记录。
        total_pages： 总页数
        total_matches： 总匹配记录条数
    """
    keywords = [] if keywords is "" or keywords is None else keywords
    criteria = SearchCriteria(
        keywords=keywords,
        title=title,
        content=content,
        publisher=publisher,
        start_date=start_date,
        end_date=end_date,
        match_logic=match_logic, # type: ignore
    )

    retriever = FileRetriever()
    result = retriever.run(criteria, page_index)
    return result

@mcp.tool()
async def search_content_detail(
        keywords: List[str] = None,
        title: str = "",
        content: str = "",
        publisher: str = "",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        match_logic: str = "OR",
        page_index: int = 1
):
    """该方法用于查询符合多条件组合的报告详情页面。LLM需根据用户输入的消息(user_message)提炼出以下参数。
    ⚠️注意：当LLM引用该方法返回的结果时，必须用markdown格式明确、醒目告知用户引自哪篇报告和具体访问地址！
    比如“**观点引自《21世纪CEO的成功法则》第10、16页**
    > <如果"file_uri"不为空，这里完整填入file_uri>”

    参数：
        keywords: List[str] = None, 报告详情页的关键词。
            ⚠️注意：
            - 将每个关键词自动翻译为中英双语
            - 例如用户输入"帮我查询下科技上市公司前景哈？" → 应转换为["科技", "technology", "上市公司", "publicly listed company"， "前景", "prospect"]
        
        title: str = "", 报告详情页标题包含词。
        content: str = "", 报告详情页内容包含词。
        publisher: str = "", 报告发布者。
        start_date: Optional[datetime] = None, 报告查询开始日期。
        end_date: Optional[datetime] = None, 报告查询结束日期。
        match_logic: str = "OR", 匹配逻辑。"OR" 或者 "AND"，二选一，**优先用 "OR"**。
        page_index: int = 1, 页码，默认仅显示第一页。

    返回：
        results：报告详情
          - file_name: 详情页来自于哪份报告名
          - page_number: 页码
          - page_abstract: 摘要
          - page_content: 完整内容
          - page_keywords: 详情页关键词
          - published_by: 报告发布机构
          - published_date:报告发布日期
          - file_uri: 报告存放于本地地址（⚠️使用时以markdown格式展示给用户，方便直接打开）
          - matched_keywords: 匹配关键词组
        current_page：当前页码。⚠️当前页码小于总页码时，LLM需在结尾处提示用户可输入“下一页”查询更多记录。
        total_pages： 总页数
        total_matches： 总匹配记录条数

    """
    keywords = [] if keywords is "" or keywords is None else keywords
    criteria = SearchCriteria(
        keywords=keywords,
        title=title,
        content=content,
        publisher=publisher,
        start_date=start_date,
        end_date=end_date,
        match_logic=match_logic, # type: ignore

    )
    retriever = ContentRetriever()
    result = retriever.run(criteria, page_index)
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
    # import asyncio
    # res = asyncio.run(search_report_profile(["ai agent"], end_date="2026-01-01"))
    # print(res)


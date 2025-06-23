# 研报知识库 MCP 服务器 

[>>>English Version](https://github.com/v587d/InsightsLibrary/blob/main/README.md)

>🍭一个免费的、即插即用的知识库。内置10,000+份高质量洞察报告(Research Report、Insights Report)、封装成MCP Server、本地数据安全存储。

⚠️⚠️ 本项目所有采集的研报，均来自各研报官网免费资源。⚠️⚠️

## 特点
1. 🍾无需任何配置，主打一个即插即用。
2. 🚀内置`Qwen3-Embedding-0.6B`嵌入模型，可通过向量检索相关报告。📢亦可通过关键词检索报告详情。
3. 🍥目前已收录McKinsey、PwC、BAIN等知名咨询机构洞察报告100+篇，6,000+报告单页，覆盖70+种主题。
4. 💎可在`MCP Client`中实时在线浏览报告全文。
5. 🎉极速查询。所有`Function_call`返回时长一般不超过1秒，其中关键词精准查询返回时长在150ms以内。
6. 🎨可将本地私有文档粘贴至`library_files`文件夹中（无项目没有该文件夹请自行创建，注意文件夹名称不能有误！）。并在`.env` 配置VLM模型和相关参数，如：`VLM_MODEL_NAME=qwen2.5-vl-72b-instruct`等，即可实现本地文档提取、解析、识别。
7. 🦉永久免费，无需考虑浪费心智收集报告资源。欢迎大家通过`issue`分享可靠的、无版权纠纷研报资源。
8. 🔔承诺至少每周一次研报资源，但改bug就看个人心情了，毕竟我不是工程师🤭。

## 截至于6月22日的优化
1. 新建`embedder.py`，实现基于本地模型`Qwen3-Embedding-0.6B`的文本向量化索引，并存于本地`fass_index`文件夹。
2. 修改`main.py`，实现`PDFExtractor` -> `IMGRecognizer` -> `Embedder` (可选) 业务流程闭环。
3. 新增`@mcp.tool(): get_similar_content_by_rag`，该方法用于通过计算用户输入与文档内容向量之间相似度，进而找到最相似的文档内容，即RAG。
4. 由admin创建的所有报告文件，均支持在线浏览。因此原项目中`library_files`文件夹及所有文件均从项目中移除。项目包体积再度缩小。
5. 新增2000+页报告。

## 未来工作方向
1. 持续更新报告
2. 优化提示词

## 最新报告概况
```JSON
{
    "statistics": {
        "total_files": 113,
        "total_pages": 6526,
        "unique_publishers": 7,
        "unique_topics": 76,
        "last_updated": "2025-06-23T08:32:01.350555"
    },
    "details": {
        "publishers": [
            "Accenture",
            "BAIN",
            "BCG",
            "CBS",
            "McKinsey",
            "PWC",
            "亿欧"
        ],
        "topics": [
            "AI",
            "AI Agent",
            "Africa",
            "Aftermarket",
            "Asian American",
            "Auto",
            "Aviation",
            "Beauty",
            "Business",
            "Chemical industry",
            "Chemicals",
            "Consumer Goods",
            "Decarbonation",
            "Decarbonization",
            "Digital",
            "Economy",
            "Economy and Trade",
            "Education",
            "Employment",
            "Energy",
            "Europe",
            "Fashion",
            "Finance",
            "Financial Technology",
            "Financial service",
            "Fintech",
            "Food-meatless",
            "Gen Z",
            "Global banking",
            "Global energy",
            "Global insurance",
            "Global macroeconomic",
            "Global materials",
            "Global private market",
            "Global private markets",
            "Global trade",
            "Grocery",
            "Grocery retail",
            "Health",
            "Healthcare",
            "Human capital",
            "Insurance",
            "Investing",
            "Labor market",
            "Latinos",
            "Low-altitude Economy",
            "Luxury Goods",
            "M&A",
            "Maritime",
            "Media",
            "Medical Health",
            "Medtech",
            "Net zero",
            "New Energy Vehicle",
            "New era",
            "Payments",
            "Pet Food",
            "Population",
            "Private Equity",
            "Private market",
            "Productivity",
            "Quantum",
            "Real estate",
            "Retail Digitalization",
            "Retailers",
            "Risk",
            "Small business",
            "Smart Home",
            "Sporting goods",
            "Sustainability",
            "Sustainable",
            "Technology",
            "Travel",
            "United Kingdom",
            "Wealth management",
            "Workplace"
        ]
    }
}

```

## 安装方法（对无编程基础用户友好）

>💡tips: 若实在搞不定，可将该页面拖到LLM客户端（比如[DeepSeek](https://chat.deepseek.com/)）让AI一步步教您安装🦾。其实以下安装步骤也是DeepSeek帮我写的......

#### 前置要求  Python 3.12+ 官网下载并安装（添加环境变量）
    
安装 UV

```BASH
pip install uv
```
#### 1. 克隆项目（确定已安装git和git lfs）

```BASH
git clone https://github.com/v587d/InsightsLibrary.git
cd InsightsLibrary
git lfs pull
```

#### 2. 创建虚拟环境

```BASH
uv venv .venv  # 创建专用虚拟环境

# 激活环境
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
```

#### 3. 安装核心依赖

```BASH
uv install .  # 注意结尾的点，表示当前目录
```

#### 4. 创建环境变量（以备不时之需）

```BASH
notepad .env  # Windows
# 或
nano .env     # Mac/Linux

```
#### 5.配置MCP Server

- VSCode.Cline
> 注意：`<Your Project Root Directory!!!>`请替换成项目根目录。
```json
{
  "mcpServers": {
    "ikb-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "<Your Project Root Directory!!!>", 
        "run",
        "ikb_mcp_server.py"
      ]
    }
  }
}
```
- Cherry Studio

    - 命令： `uv`

    - 参数： 
```text
--directory
<Your Project Root Directory!!!>
run
ikb_mcp_server.py
```

## 将私有文档加入ikb_mcp_server
1. `.env` 可配置VLM模型和相关参数：
    ```text
    VLM_API_KEY=<API Key>
    VLM_BASE_URL=<Base URL> # https://openrouter.ai/api/v1
    VLM_MODEL_NAME=<Model Name> # qwen/qwen2.5-vl-72b-instruct:free
    ```
2. 将pdf文档上传至项目根目录下的 `library_files` 文件夹内
3. 手动运行main.py

```Bash
# cd 项目根目录
# 激活虚拟环境
uv run main.py

(InsightsLibrary) PS D:\Projects\mcp\InsightsLibrary> uv run main.py
[INFO] extractor: PDF extraction initialized | Files directory: library_files | Pages directory: library_pages
[INFO] extractor: Starting scan of directory: library_files
[INFO] extractor: Found 69 PDF files
[INFO] extractor: Scan completed | Total files: 69 | Processed: 0 | Failed: 0
[INFO] recognizer: No pages to process.
# 已更新数据库
============================================================
Confirm if you need to create text vector embeddings
⚠️ This process may take approximately 20 minutes
============================================================
Create embeddings? (Enter Y or N): 
# Y: 创建文本向量索引
# N: 跳过文本向量，并退出main程序
```

[LICENSE](https://github.com/v587d/InsightsLibrary/blob/main/LICENSE) 详情

## 截至于6月17日的优化
1. 💡优化`models.py`: 数据查询效率提升1,000%
2. 💡优化`extractor.py`: 略微提升PDF抽取效率
3. 💡优化`recognizer.py`: 图片理解效率提升50%
4. 💡优化`ikb_mcp_server.py`: 
   - 新增分页
   - 显示引用文件本地所在路径
5. 💡新增 MIT License
6. **📦项目整体压缩包体积下降约 50%**
7. 💡简化处理私有文档流程
8. 💡修复其他已发现的bugs



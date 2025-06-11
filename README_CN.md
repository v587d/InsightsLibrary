# 研报知识库 MCP 服务器 

[>>>English Version](https://github.com/v587d/InsightsLibrary/blob/main/README.md)

>🍭一个免费的、即插即用的知识库。内置10,000+份高质量洞察报告(Research Report、Insight Report)、封装成MCP Server、本地数据安全存储。

⚠️⚠️ 本项目所有采集的研报，均来自各研报官网免费资源。⚠️⚠️
## 特点
1. 🍾无需任何配置，主打一个即插即用。若您需解析私有文档，`.env` 可配置VLM模型和相关参数，如：`VLM_MODEL_NAME=qwen2.5-vl-72b-instruct`。
2. 🦉永久免费，无需考虑浪费心智收集报告资源。欢迎大家通过`issue`分享可靠的、无版权纠纷研报资源。
3. 📢承诺至少每周一次研报资源，但改bug就看个人心情了，毕竟我不是程序员🤭。


## 安装方法（对无编程基础用户友好）

>💡tips: 若实在搞不定，可将该页面拖到LLM客户端（比如[DeepSeek](https://chat.deepseek.com/)）让AI一步步教您安装🦾。其实以下安装步骤也是DeepSeek帮我写的......

#### 前置要求  Python 3.12+ 官网下载并安装（添加环境变量）
    
安装 UV

```BASH
pip install uv
```
#### 1. 克隆项目

```BASH
git clone https://github.com/v587d/InsightsLibrary.git
cd insights-library
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
uv pip install -e .  # 注意结尾的点，表示当前目录
```

#### 4. 创建环境变量（以备不时之需）

```BASH
notepad .env  # Windows
# 或
nano .env     # Mac/Linux

```
#### 5.配置MCP Server

- VSCODE
> 注意：`<Your Project Root Directory!!!>`请替换成项目根目录。
```json
{
  "mcpServers": {
    "ikb-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "", 
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

## 解析私有文档
> 0.1.0 就将就下，后面会完善这部分。😎
1. 将pdf文档上传至 `library_files` 文件夹内
2. 手动运行python脚本

```Bash
# cd 项目根目录
# 激活虚拟环境
uv run decoder.py
# 等运行结束
uv run large_models.py
# 等运行结束
# 此时数据已更新至数据库
```






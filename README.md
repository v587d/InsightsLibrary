# Insights Knowledge Base(IKB) MCP Server
[>>>中文版](https://github.com/v587d/InsightsLibrary/blob/main/README_CN.md)
> A free, plug-and-play knowledge base. Built-in with 10,000+ high-quality insight reports, packaged as MCP Server, and secure local data storage.

⚠️⚠️ All collected reports in this project come from free resources on official research report websites. ⚠️⚠️
## Features
1. 🍾 No configuration needed, truly plug-and-play. For private document parsing, configure VLM models and parameters in `.env` (e.g., `VLM_MODEL_NAME=qwen2.5-vl-72b-instruct`).
2. 🦉 Permanently free - no need to waste effort collecting report resources. Welcome to share reliable, copyright-free report sources via `issues`.
3. 📢 Committed to weekly report updates, but bug fixes depend on my mood (I'm not a programmer 🤭).

## Installation (Beginner-Friendly)

>💡Pro tip: Stuck? Drag this page to an LLM client (like [DeepSeek](https://chat.deepseek.com/)) for step-by-step guidance. Actually, these instructions were written by DeepSeek too...

#### Prerequisites: Python 3.12+ (Download from official website and ADD ENVIRONMENT PATH)

Install UV:

```BASH
pip install uv
```

#### 1. Clone the project

```BASH
git clone https://github.com/v587d/InsightsLibrary.git
cd InsightsLibrary
```

#### 2. Create virtual environment

```BASH
uv venv .venv  # Create dedicated virtual environment

# Activate environment
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
```

#### 3. Install core dependencies

```BASH
uv pip install -e .  # Note the trailing dot indicating current directory
```

#### 4. Create environment variables (for future needs)

```BASH
notepad .env  # Windows
# Or
nano .env     # Mac/Linux
```

#### 5. Configure MCP Server

- VSCODE
> Note: Replace `<Your Project Root Directory!!!>` with actual root directory.
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
    - Command: `uv`
    - Arguments: 
```text
--directory
<Your Project Root Directory!!!>
run
ikb_mcp_server.py
```

## Parse Private Documents
> Version 0.1.0 has basic functionality - we'll improve this later. 😎
1. Upload PDF documents to the `library_files` folder
2. Manually run Python scripts:

```Bash
# cd to project root
# Activate virtual environment
uv run decoder.py
# Wait for completion
uv run large_models.py
# Wait for completion
# Data is now updated in the database
```
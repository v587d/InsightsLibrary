# Insights Knowledge Base(IKB) MCP Server
[>>>中文版](https://github.com/v587d/InsightsLibrary/blob/main/README_CN.md)
> 🍭A free, plug-and-play knowledge base. Built-in with 10,000+ high-quality insights reports, packaged as MCP Server, and secure local data storage.

⚠️⚠️ All collected reports in this project come from free resources on official research report websites. ⚠️⚠️
## Features
1. 🍾 No configuration needed, truly plug-and-play. For private document parsing, configure VLM models and parameters in `.env` (e.g., `VLM_MODEL_NAME=qwen2.5-vl-72b-instruct`).
2. 🦉 Permanently free - no need to waste effort collecting report resources. Welcome to share reliable, copyright-free report sources via `issues`.
3. 📢 Committed to weekly report updates, but bug fixes depend on my mood (Actually I'm not a engineer 🤭).

## Optimization Updates as of June 17th

1. 💡Optimized `models.py`: Improved data query efficiency by 1,000%
2. 💡Optimized `extractor.py`: Slightly enhanced PDF extraction efficiency
3. 💡Optimized `recognizer.py`:  Boosted image comprehension efficiency by 50%
4. 💡Optimized `ikb_mcp_server.py`:
   - Added pagination functionality
   - Displayed local paths of referenced files
5. Add MIT License(https://github.com/v587d/InsightsLibrary/pull/1#issuecomment-2969226661)
6. **📦 Overall compressed project package size reduced by approximately 50%**  
7. 💡Streamline Private Document Handling  
8. 💡Fixed other identified bugs

## Future Work Directions  
1. **Embedding Model Integration**  
   - Implement sentence-transformers for document embeddings  
   - Create Function Tools endpoints for vector search  
2. **Reporting System Enhancement**  
   - Daily automated report generation  
   - Real-time update notifications

## Newest Files Profile
```JSON
{
    "statistics": {
        "total_files": 61,
        "total_pages": 3031,
        "unique_publishers": 7,
        "unique_topics": 45,
        "last_updated": "2025-06-17T10:36:52.437453"
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
            "Asian American",
            "Aviation",
            "Business",
            "Chemicals",
            "Consumer Goods",
            "Decarbonation",
            "Decarbonization",
            "Digital",
            "Economy and Trade",
            "Education",
            "Employment",
            "Fashion",
            "Financial Technology",
            "Fintech",
            "Food-meatless",
            "Gen Z",
            "Global banking",
            "Global energy",
            "Global insurance",
            "Global macroeconomic",
            "Global materials",
            "Global private market",
            "Global trade",
            "Health",
            "Human capital",
            "Insurance",
            "Low-altitude Economy",
            "Luxury Goods",
            "Maritime",
            "Media",
            "Medical Health",
            "Net zero",
            "New Energy Vehicle",
            "Pet Food",
            "Population",
            "Private Equity",
            "Real estate",
            "Retail Digitalization",
            "Small business",
            "Smart Home",
            "Sustainability",
            "Technology",
            "Travel"
        ]
    }
}
```

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

- VSCode.Cline
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

## Adding Private Documents to ikb_mcp_server
1. Configure VLM models and parameters in `.env`:
    ```text
    VLM_API_KEY=<API Key>
    VLM_BASE_URL=<Base URL> # https://openrouter.ai/api/v1
    VLM_MODEL_NAME=<Model Name> # qwen/qwen2.5-vl-72b-instruct:free
    ```
2. Upload the PDF document to the `library_files` folder under the project root directory.
3. Manually run main.py.

```bash
# Navigate to the project root directory
# Activate the virtual environment
uv run main.py
# [INFO]PDF extraction initialized | Files directory: library_files | Pages directory: library_pages
# ... Please waiting for a while
# [INFO]Processing completed. Success: xxx pages, Failed: 0 pages.
# Data has been updated to the database
```

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/v587d/InsightsLibrary/blob/main/LICENSE) file for details.
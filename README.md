# Insights Knowledge Base(IKB) MCP Server
[>>>中文版](https://github.com/v587d/InsightsLibrary/blob/main/README_CN.md)
> 🍭A free, plug-and-play knowledge base. Built-in with 10,000+ high-quality insights reports, packaged as MCP Server, and secure local data storage.

⚠️⚠️ All collected reports in this project come from free resources on official research report websites. ⚠️⚠️

## Features
1. 🍾 Zero configuration required, designed for *plug-and-play* usage.
2. 🚀 Built-in `Qwen3-Embedding-0.6B` embedding model, related reports can be retrieved through **vector search**.📢 Report details can also be searched via **keyword retrieval**.
3. 🍥 over 100 insights reports from well-known consulting firms such as McKinsey, PwC, and BAIN have been collected, including 6,000+ report pages, covering 70+ topics.
4. 💎 *Real-time* online browsing of full reports in MCP Client.
5. 🎉 *Ultra-fast* response: All Function_call returns typically <1 second, keyword-based queries <150ms.
6. 🎨 Paste *private local documents* into the library_files folder (create it manually if absent; name must match). Configure VLM models/parameters in .env (e.g., VLM_MODEL_NAME=qwen2.5-vl-72b-instruct) for local document extraction, parsing, and recognition.
7. 🦉 Permanently *free—no* wasted effort collecting reports. Share reliable, copyright-compliant resources via issues.
8. 🔔 Commit to *weekly report updates*; bug fixes depend on personal whim (I'm not an engineer 🤭).

## Optimizations as of June 22
1. Added `embedder.py`: Implements text vectorization indexing via local Qwen3-Embedding-0.6B model, stored in faiss_index.
2. Modified `main.py`: Closed-loop workflow *PDFExtractor → IMGRecognizer → Embedder (optional)*.
3. New `@mcp.tool(): get_similar_content_by_rag`: Finds most similar document content via vector similarity (RAG).
4. All admin-uploaded reports now support online viewing → Removed library_files folder to reduce project size.
5. Added **2000+** report pages.

## Future Directions
1. Continuous report updates.
2. Prompt engineering optimization.

## Newest Files Profile
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

## Installation (Beginner-Friendly)

>💡Pro tip: Stuck? Drag this page to an LLM client (like [DeepSeek](https://chat.deepseek.com/)) for step-by-step guidance. Actually, these instructions were written by DeepSeek too...

#### Prerequisites: Python 3.12+ (Download from official website and ADD ENVIRONMENT PATH)

Install UV:

```BASH
pip install uv
```

#### 1. Clone the project(Confirm successfully installed Git and Git LFS)

```BASH
git clone https://github.com/v587d/InsightsLibrary.git
cd InsightsLibrary
git lfs pull
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
uv install .  # Note the trailing dot indicating current directory
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
(InsightsLibrary) PS D:\Projects\mcp\InsightsLibrary> uv run main.py
[INFO] extractor: PDF extraction initialized | Files directory: library_files | Pages directory: library_pages
[INFO] extractor: Starting scan of directory: library_files
[INFO] extractor: Found 69 PDF files
[INFO] extractor: Scan completed | Total files: 69 | Processed: 0 | Failed: 0
[INFO] recognizer: No pages to process.
# Data has been updated to the database
============================================================
Confirm if you need to create text vector embeddings
⚠️ This process may take approximately 20 minutes
============================================================
Create embeddings? (Enter Y or N): 
# Y: create text vector embeddings
# N: Skip text vector embeddings and exit program
```

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/v587d/InsightsLibrary/blob/main/LICENSE) file for details.

## Optimization Updates as of June 17th

1. 💡Optimized `models.py`: Improved data query efficiency by 1,000%
2. 💡Optimized `extractor.py`: Slightly enhanced PDF extraction efficiency
3. 💡Optimized `recognizer.py`:  Boosted image comprehension efficiency by 50%
4. 💡Optimized `ikb_mcp_server.py`:
   - Added pagination functionality
   - Displayed local paths of referenced files
5. 💡Add MIT License(https://github.com/v587d/InsightsLibrary/pull/1#issuecomment-2969226661)
6. **📦 Overall compressed project package size reduced by approximately 50%**  
7. 💡Streamline Private Document Handling  
8. 💡Fixed other identified bugs
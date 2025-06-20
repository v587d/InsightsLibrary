import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 文件路径配置
    FILES_DIR = os.getenv("FILES_DIR", "library_files")
    PAGES_DIR = os.getenv("PAGES_DIR", "library_pages")

    # TinyDB 路径
    DB_TEST_PATH = os.getenv("DB_TEST_PATH", "library_db/tinydb_test.json")
    DB_PRD_PATH = os.getenv("DB_PRD_PATH", "library_db/tinydb_prd.json")

    # 确保目录存在
    os.makedirs(FILES_DIR, exist_ok=True)
    os.makedirs(PAGES_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DB_TEST_PATH), exist_ok=True)

    # 大模型
    vlm_api_key = os.getenv("VLM_API_KEY", "")
    vlm_base_url = os.getenv("VLM_BASE_URL", "")
    vlm_model_name = os.getenv("VLM_MODEL_NAME", "")

    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_model_name = os.getenv("LLM_MODEL_NAME", "")

    eb_model_local_path = os.getenv("EMBEDDING_MODEL_LOCAL_PATH", "eb_model")
    eb_device = os.getenv("EMBEDDING_MODEL_DEVICE", "cpu").lower()
    faiss_index_dir = os.getenv("FAISS_INDEX_DIR", "faiss_index")
    os.makedirs(faiss_index_dir, exist_ok=True)

config = Config()



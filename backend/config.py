from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


def _split_csv_env(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default

BASE_DIR = Path(os.getenv("BASE_DIR", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
RAW_DOCS_DIR = Path(os.getenv("RAW_DOCS_DIR", DATA_DIR / "raw_docs"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", DATA_DIR / "chroma"))
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", DATA_DIR / "state.db"))
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("ARK_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("ARK_BASE_URL", "https://api.minimaxi.com/v1"))
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("ARK_MODEL", "MiniMax-M2.7"))
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3"))
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
LARK_CLI_PATH = os.getenv("LARK_CLI_PATH", "lark-cli")
LARK_DOC_IDENTITY = os.getenv("LARK_DOC_IDENTITY", os.getenv("LARK_CLI_IDENTITY", "user"))
LARK_MESSAGE_IDENTITY = os.getenv("LARK_MESSAGE_IDENTITY", "bot")
DISTRIBUTION_SUBDIRECTORY = os.getenv("DISTRIBUTION_SUBDIRECTORY", "lark_docs")
DISTRIBUTION_DOCS = _split_csv_env("DISTRIBUTION_DOCS")
DISTRIBUTION_DEFAULT_CHAT_IDS = _split_csv_env("DISTRIBUTION_DEFAULT_CHAT_IDS")
DISTRIBUTION_DEFAULT_USER_IDS = _split_csv_env("DISTRIBUTION_DEFAULT_USER_IDS")
DISTRIBUTION_INTERVAL_MINUTES = _get_int_env("DISTRIBUTION_INTERVAL_MINUTES", 10)

from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
RAW_DOCS_DIR = Path(os.getenv("RAW_DOCS_DIR", DATA_DIR / "raw_docs"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", DATA_DIR / "chroma"))
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", DATA_DIR / "state.db"))
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("ARK_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("ARK_BASE_URL", "https://api.minimaxi.com/v1"))
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("ARK_MODEL", "MiniMax-M2.7"))
LARK_CLI_PATH = os.getenv("LARK_CLI_PATH", "lark-cli")
LARK_CLI_IDENTITY = os.getenv("LARK_CLI_IDENTITY", "user")

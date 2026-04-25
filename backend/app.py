from fastapi import FastAPI

from backend.api import answer_router, feishu_events_router, openclaw_router, retrieval_router
from backend.config import (
    CHROMA_DIR,
    DATA_DIR,
    LARK_DOC_IDENTITY,
    LARK_MESSAGE_IDENTITY,
    LLM_BASE_URL,
    LLM_MODEL,
    RAW_DOCS_DIR,
    SQLITE_PATH,
)


app = FastAPI(title="Feishu Knowledge Agent")

app.include_router(answer_router)
app.include_router(feishu_events_router)
app.include_router(openclaw_router)
app.include_router(retrieval_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_dir": str(DATA_DIR),
        "raw_docs_dir": str(RAW_DOCS_DIR),
        "chroma_dir": str(CHROMA_DIR),
        "sqlite_path": str(SQLITE_PATH),
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
        "lark_doc_identity": LARK_DOC_IDENTITY,
        "lark_message_identity": LARK_MESSAGE_IDENTITY,
    }

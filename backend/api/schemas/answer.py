from pydantic import BaseModel, Field

from backend.api.schemas.retrieval import RetrievalHitResponse


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    subdirectory: str = Field(default="lark_docs")
    top_k: int = Field(default=5, ge=1, le=20)
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


class AnswerResponse(BaseModel):
    question: str
    answer: str
    model: str | None
    document_count: int
    chunk_count: int
    hits: list[RetrievalHitResponse]

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    subdirectory: str = Field(default="lark_docs")
    top_k: int = Field(default=5, ge=1, le=20)
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    retrieval_mode: str = Field(default="bm25")
    vector_top_k: int | None = Field(default=None, ge=1, le=50)


class RetrievalHitResponse(BaseModel):
    score: float
    doc_id: str
    title: str
    source_url: str
    chunk_id: str
    chunk_index: int
    start_offset: int
    end_offset: int
    text_preview: str


class RetrievalResponse(BaseModel):
    query: str
    retrieval_mode: str
    document_count: int
    chunk_count: int
    hits: list[RetrievalHitResponse]

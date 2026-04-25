from pydantic import BaseModel, Field


class OpenClawTarget(BaseModel):
    target_type: str = Field(default="chat", min_length=1)
    target_id: str = Field(min_length=1)
    target_name: str = ""


class OpenClawQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    subdirectory: str = Field(default="lark_docs")
    top_k: int = Field(default=5, ge=1, le=20)
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    retrieval_mode: str = Field(default="bm25")
    vector_top_k: int | None = Field(default=None, ge=1, le=50)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


class OpenClawCitation(BaseModel):
    title: str
    source_url: str
    chunk_id: str
    text_preview: str
    score: float


class OpenClawQueryResponse(BaseModel):
    question: str
    answer: str
    model: str | None
    retrieval_mode: str
    document_count: int
    chunk_count: int
    citations: list[OpenClawCitation]


class OpenClawSubscribeRequest(BaseModel):
    doc_id: str = Field(min_length=1)
    subdirectory: str = Field(default="lark_docs")
    targets: list[OpenClawTarget] = Field(min_length=1)
    replace_existing: bool = False
    source: str = Field(default="openclaw", min_length=1)


class OpenClawSubscribeResponse(BaseModel):
    doc_id: str
    subdirectory: str
    metadata_path: str
    target_count: int
    replaced_existing: bool
    source: str

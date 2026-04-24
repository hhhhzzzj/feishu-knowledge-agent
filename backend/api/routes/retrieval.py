from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas.retrieval import RetrievalHitResponse, RetrievalRequest, RetrievalResponse
from backend.config import RAW_DOCS_DIR
from backend.services import EmptyCorpusError, InvalidRetrievalRequestError, LocalRetrievalService

router = APIRouter(tags=["retrieval"])


def get_retrieval_service() -> LocalRetrievalService:
    return LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR)


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve_documents(
    request: RetrievalRequest,
    service: LocalRetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    try:
        result = service.retrieve(
            query=request.query,
            subdirectory=request.subdirectory,
            top_k=request.top_k,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except EmptyCorpusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidRetrievalRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RetrievalResponse(
        query=result.query,
        document_count=result.document_count,
        chunk_count=result.chunk_count,
        hits=[
            RetrievalHitResponse(
                score=hit.score,
                doc_id=hit.chunk.doc_id,
                title=hit.chunk.title,
                source_url=hit.chunk.source_url,
                chunk_id=hit.chunk.chunk_id,
                chunk_index=hit.chunk.chunk_index,
                start_offset=hit.chunk.start_offset,
                end_offset=hit.chunk.end_offset,
                text_preview=hit.chunk.text_preview,
            )
            for hit in result.hits
        ],
    )

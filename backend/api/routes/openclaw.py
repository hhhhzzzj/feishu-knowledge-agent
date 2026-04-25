from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas.openclaw import (
    OpenClawCitation,
    OpenClawQueryRequest,
    OpenClawQueryResponse,
    OpenClawSubscribeRequest,
    OpenClawSubscribeResponse,
)
from backend.clients import EmbeddingConfigurationError, EmbeddingInvocationError, LLMChatClient, LLMConfigurationError, LLMInvocationError
from backend.config import CHROMA_DIR, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, RAW_DOCS_DIR
from backend.models.distribution import DistributionTarget
from backend.services import AnswerService, EmptyCorpusError, InvalidRetrievalRequestError, LocalRetrievalService, OpenClawService

router = APIRouter(prefix="/api/openclaw", tags=["openclaw"])


def get_openclaw_service() -> OpenClawService:
    answer_service = AnswerService(
        retrieval_service=LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR, chroma_dir=CHROMA_DIR),
        llm_client=LLMChatClient(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, model=LLM_MODEL),
    )
    return OpenClawService(answer_service=answer_service, raw_docs_dir=RAW_DOCS_DIR)


@router.post("/query", response_model=OpenClawQueryResponse)
def openclaw_query(
    request: OpenClawQueryRequest,
    service: OpenClawService = Depends(get_openclaw_service),
) -> OpenClawQueryResponse:
    try:
        result = service.query(
            question=request.question,
            subdirectory=request.subdirectory,
            top_k=request.top_k,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            retrieval_mode=request.retrieval_mode,
            vector_top_k=request.vector_top_k,
            temperature=request.temperature,
        )
    except EmptyCorpusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidRetrievalRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmbeddingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EmbeddingInvocationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return OpenClawQueryResponse(
        question=result.question,
        answer=result.answer,
        model=result.model,
        retrieval_mode=result.retrieval_mode,
        document_count=result.document_count,
        chunk_count=result.chunk_count,
        citations=[
            OpenClawCitation(
                title=hit.chunk.title,
                source_url=hit.chunk.source_url,
                chunk_id=hit.chunk.chunk_id,
                text_preview=hit.chunk.text_preview,
                score=hit.score,
            )
            for hit in result.hits
        ],
    )


@router.post("/subscribe", response_model=OpenClawSubscribeResponse)
def openclaw_subscribe(
    request: OpenClawSubscribeRequest,
    service: OpenClawService = Depends(get_openclaw_service),
) -> OpenClawSubscribeResponse:
    try:
        result = service.save_subscription(
            doc_id=request.doc_id,
            subdirectory=request.subdirectory,
            targets=[
                DistributionTarget(
                    target_type=target.target_type,
                    target_id=target.target_id,
                    target_name=target.target_name,
                )
                for target in request.targets
            ],
            replace_existing=request.replace_existing,
            source=request.source,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return OpenClawSubscribeResponse(
        doc_id=result.doc_id,
        subdirectory=result.subdirectory,
        metadata_path=str(result.metadata_path),
        target_count=len(result.targets),
        replaced_existing=result.replaced_existing,
        source=result.source,
    )

from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas.answer import AnswerRequest, AnswerResponse
from backend.api.schemas.retrieval import RetrievalHitResponse
from backend.clients import LLMChatClient, LLMConfigurationError, LLMInvocationError
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, RAW_DOCS_DIR
from backend.services import AnswerService, EmptyCorpusError, InvalidRetrievalRequestError, LocalRetrievalService

router = APIRouter(tags=["answer"])


def get_answer_service() -> AnswerService:
    return AnswerService(
        retrieval_service=LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR),
        llm_client=LLMChatClient(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, model=LLM_MODEL),
    )


@router.post("/answer", response_model=AnswerResponse)
def answer_question(
    request: AnswerRequest,
    service: AnswerService = Depends(get_answer_service),
) -> AnswerResponse:
    try:
        result = service.answer(
            question=request.question,
            subdirectory=request.subdirectory,
            top_k=request.top_k,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            temperature=request.temperature,
        )
    except EmptyCorpusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidRetrievalRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnswerResponse(
        question=result.question,
        answer=result.answer,
        model=result.model,
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

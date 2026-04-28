from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas.feishu_events import FeishuEventRequest, FeishuEventResponse
from backend.clients import (
    EmbeddingConfigurationError,
    EmbeddingInvocationError,
    LarkCLIClient,
    LarkCLIError,
    LLMChatClient,
    LLMConfigurationError,
    LLMInvocationError,
)
from backend.config import CHROMA_DIR, LARK_CLI_PATH, LARK_MESSAGE_IDENTITY, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, RAW_DOCS_DIR
from backend.services import AnswerService, EmptyCorpusError, FeishuBotService, InvalidRetrievalRequestError, LocalRetrievalService

router = APIRouter(prefix="/feishu", tags=["feishu"])


def get_feishu_bot_service() -> FeishuBotService:
    answer_service = AnswerService(
        retrieval_service=LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR, chroma_dir=CHROMA_DIR),
        llm_client=LLMChatClient(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, model=LLM_MODEL),
    )
    message_client = LarkCLIClient(cli_path=LARK_CLI_PATH, identity=LARK_MESSAGE_IDENTITY)
    return FeishuBotService(answer_service=answer_service, message_client=message_client)


@router.post("/events", response_model=FeishuEventResponse)
def receive_feishu_event(
    request: FeishuEventRequest,
    service: FeishuBotService = Depends(get_feishu_bot_service),
) -> FeishuEventResponse:
    if request.challenge:
        return FeishuEventResponse(challenge=request.challenge)

    header = request.header or {}
    try:
        result = service.handle_event(header=header, event=request.event or {}, fallback_event_type=request.type or "")
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
    except LarkCLIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return FeishuEventResponse(
        code=0,
        msg="ok",
        event_type=result.event_type,
        tenant_key=result.tenant_key,
        handled=result.handled,
        replied=result.replied,
        skipped_reason=result.skipped_reason,
        message_id=result.message_id,
        chat_id=result.chat_id,
        question=result.question,
    )

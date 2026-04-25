from fastapi import APIRouter

from backend.api.schemas.feishu_events import FeishuEventRequest, FeishuEventResponse

router = APIRouter(prefix="/feishu", tags=["feishu"])


@router.post("/events", response_model=FeishuEventResponse)
def receive_feishu_event(request: FeishuEventRequest) -> FeishuEventResponse:
    if request.challenge:
        return FeishuEventResponse(challenge=request.challenge)

    header = request.header or {}
    return FeishuEventResponse(
        code=0,
        msg="ok",
        event_type=header.get("event_type") or request.type,
        tenant_key=header.get("tenant_key"),
    )

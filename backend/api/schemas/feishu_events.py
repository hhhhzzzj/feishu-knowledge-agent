from typing import Any

from pydantic import BaseModel, ConfigDict


class FeishuEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge: str | None = None
    token: str | None = None
    type: str | None = None
    header: dict[str, Any] | None = None
    event: dict[str, Any] | None = None


class FeishuEventResponse(BaseModel):
    challenge: str | None = None
    code: int = 0
    msg: str = "ok"
    event_type: str | None = None
    tenant_key: str | None = None
    handled: bool = False
    replied: bool = False
    skipped_reason: str | None = None
    message_id: str | None = None
    chat_id: str | None = None
    question: str | None = None

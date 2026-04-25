from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeishuEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge: str | None = None
    token: str | None = None
    type: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    header: dict[str, Any] | None = None
    event: dict[str, Any] | None = None


class FeishuEventResponse(BaseModel):
    challenge: str | None = None
    code: int = 0
    msg: str = "ok"
    event_type: str | None = None
    tenant_key: str | None = None

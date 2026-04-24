from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LarkDocSearchResult:
    title: str
    entity_type: str
    doc_type: str
    token: str
    url: str
    owner_name: str
    edit_user_name: str
    update_time_iso: str
    summary_highlighted: str
    title_highlighted: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LarkDocSearchResult":
        meta = payload.get("result_meta", {})
        return cls(
            title=_strip_highlight_tags(payload.get("title_highlighted", "")) or meta.get("title", ""),
            entity_type=payload.get("entity_type", ""),
            doc_type=meta.get("doc_types", ""),
            token=meta.get("token", ""),
            url=meta.get("url", ""),
            owner_name=meta.get("owner_name", ""),
            edit_user_name=meta.get("edit_user_name", ""),
            update_time_iso=meta.get("update_time_iso", ""),
            summary_highlighted=payload.get("summary_highlighted", ""),
            title_highlighted=payload.get("title_highlighted", ""),
        )


@dataclass(slots=True)
class LarkDocSearchPage:
    results: list[LarkDocSearchResult]
    total: int
    has_more: bool
    page_token: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LarkDocSearchPage":
        data = payload.get("data", {})
        raw_results = data.get("results", [])
        return cls(
            results=[LarkDocSearchResult.from_dict(item) for item in raw_results],
            total=data.get("total", 0),
            has_more=data.get("has_more", False),
            page_token=data.get("page_token", ""),
        )


@dataclass(slots=True)
class FetchedLarkDocument:
    doc_id: str
    title: str
    markdown: str
    raw_markdown_length: int
    total_length: int
    offset: int
    log_id: str
    message: str
    source_url: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, source_url: str) -> "FetchedLarkDocument":
        data = payload.get("data", {})
        return cls(
            doc_id=data.get("doc_id", ""),
            title=data.get("title", ""),
            markdown=data.get("markdown", ""),
            raw_markdown_length=data.get("length", 0),
            total_length=data.get("total_length", 0),
            offset=data.get("offset", 0),
            log_id=data.get("log_id", ""),
            message=data.get("message", ""),
            source_url=source_url,
        )


def _strip_highlight_tags(value: str) -> str:
    return value.replace("<h>", "").replace("</h>", "")

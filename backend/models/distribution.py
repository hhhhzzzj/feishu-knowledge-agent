from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class DistributionTarget:
    target_type: str
    target_id: str
    target_name: str = ""


@dataclass(slots=True)
class DocumentSnapshot:
    doc_id: str
    title: str
    source_url: str
    markdown: str
    content_hash: str
    fetched_at: datetime
    update_time_iso: str = ""
    owner_name: str = ""
    edit_user_name: str = ""
    extra_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ChangeSummary:
    has_changes: bool
    summary: str
    change_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DistributionEvent:
    doc_id: str
    title: str
    source_url: str
    content_hash: str
    change_summary: ChangeSummary
    targets: list[DistributionTarget] = field(default_factory=list)
    message_text: str = ""

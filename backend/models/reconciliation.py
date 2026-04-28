from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TrackedItem:
    item_id: str
    title: str
    owner: str = ""
    due_date: str = ""
    status: str = ""
    blocker: str = ""
    source_title: str = ""
    source_url: str = ""
    evidence: str = ""


@dataclass(slots=True)
class ItemChange:
    change_type: str  # added / completed / delayed / blocked / owner_changed / updated
    before: TrackedItem | None = None
    after: TrackedItem | None = None
    summary: str = ""
    risk_level: str = "low"  # low / medium / high


@dataclass(slots=True)
class ReconciliationReport:
    source_title: str
    source_url: str
    items: list[TrackedItem] = field(default_factory=list)
    changes: list[ItemChange] = field(default_factory=list)
    summary: str = ""

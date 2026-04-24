from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LocalDocument:
    doc_id: str
    title: str
    source_url: str
    markdown: str
    markdown_path: Path | None = None
    metadata_path: Path | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    doc_id: str
    title: str
    source_url: str
    chunk_index: int
    start_offset: int
    end_offset: int
    text: str
    text_preview: str


@dataclass(slots=True)
class RetrievalHit:
    chunk: DocumentChunk
    score: float

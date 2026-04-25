from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.clients.lark_cli import LarkCLIClient
from backend.models.lark_docs import FetchedLarkDocument, LarkDocSearchPage


@dataclass(slots=True)
class StoredDocumentArtifact:
    doc_id: str
    title: str
    source_url: str
    markdown_path: Path
    metadata_path: Path


@dataclass(slots=True)
class DocumentIngestionService:
    client: LarkCLIClient
    raw_docs_dir: Path

    def search_documents(self, *, query: str, page_size: int = 10, page_token: str | None = None) -> LarkDocSearchPage:
        return self.client.search_docs(query=query, page_size=page_size, page_token=page_token)

    def fetch_document(self, *, doc: str, offset: int | None = None, limit: int | None = None) -> FetchedLarkDocument:
        return self.client.fetch_doc(doc=doc, offset=offset, limit=limit)

    def ingest_document(self, *, doc: str, subdirectory: str = "lark_docs") -> StoredDocumentArtifact:
        fetched = self.fetch_document(doc=doc)
        return self.store_document(document=fetched, subdirectory=subdirectory)

    def store_document(
        self,
        *,
        document: FetchedLarkDocument,
        subdirectory: str = "lark_docs",
        extra_metadata: dict | None = None,
    ) -> StoredDocumentArtifact:
        markdown_path, metadata_path = self.resolve_storage_paths(
            doc_id=document.doc_id,
            title=document.title,
            subdirectory=subdirectory,
        )
        markdown_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = self._load_existing_metadata(metadata_path)
        metadata.update(extra_metadata or {})
        metadata.update(self._build_metadata(document))

        markdown_path.write_text(document.markdown, encoding="utf-8")
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return StoredDocumentArtifact(
            doc_id=document.doc_id,
            title=document.title,
            source_url=document.source_url,
            markdown_path=markdown_path,
            metadata_path=metadata_path,
        )

    def resolve_storage_paths(self, *, doc_id: str, title: str, subdirectory: str = "lark_docs") -> tuple[Path, Path]:
        target_dir = self.raw_docs_dir / subdirectory / self._safe_name(doc_id or title)
        return target_dir / "content.md", target_dir / "metadata.json"

    @staticmethod
    def _build_metadata(document: FetchedLarkDocument) -> dict:
        return {
            "doc_id": document.doc_id,
            "title": document.title,
            "source_url": document.source_url,
            "raw_markdown_length": document.raw_markdown_length,
            "total_length": document.total_length,
            "offset": document.offset,
            "log_id": document.log_id,
            "message": document.message,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _load_existing_metadata(metadata_path: Path) -> dict:
        if not metadata_path.exists():
            return {}
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _safe_name(value: str) -> str:
        sanitized = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value.strip())
        compacted = "_".join(part for part in sanitized.split("_") if part)
        return compacted or "document"

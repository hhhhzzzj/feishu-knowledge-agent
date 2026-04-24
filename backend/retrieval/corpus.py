from __future__ import annotations

import json
from pathlib import Path

from backend.models.retrieval import LocalDocument


class LocalDocumentCorpus:
    def __init__(self, raw_docs_dir: Path) -> None:
        self.raw_docs_dir = raw_docs_dir

    def load_documents(self, *, subdirectory: str | None = None) -> list[LocalDocument]:
        base_dir = self.raw_docs_dir / subdirectory if subdirectory else self.raw_docs_dir
        if not base_dir.exists():
            return []

        documents: list[LocalDocument] = []
        for metadata_path in sorted(base_dir.rglob("metadata.json")):
            content_path = metadata_path.with_name("content.md")
            if not content_path.exists():
                continue

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            markdown = content_path.read_text(encoding="utf-8")
            documents.append(
                LocalDocument(
                    doc_id=metadata.get("doc_id", content_path.parent.name),
                    title=metadata.get("title", content_path.parent.name),
                    source_url=metadata.get("source_url", ""),
                    markdown=markdown,
                    markdown_path=content_path,
                    metadata_path=metadata_path,
                    extra_metadata=metadata,
                )
            )
        return documents

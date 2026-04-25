from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.models.distribution import DistributionEvent


@dataclass(slots=True)
class StoredDistributionState:
    doc_id: str
    content_hash: str
    last_updated: str
    markdown_path: str
    metadata_path: str
    source_url: str
    title: str


class DistributionStateRepository:
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.sqlite_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS distribution_state (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    markdown_path TEXT NOT NULL,
                    metadata_path TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS distribution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def get_state(self, doc_id: str) -> StoredDistributionState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT doc_id, content_hash, last_updated, markdown_path, metadata_path, source_url, title FROM distribution_state WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
        if not row:
            return None
        return StoredDistributionState(
            doc_id=row[0],
            content_hash=row[1],
            last_updated=row[2],
            markdown_path=row[3],
            metadata_path=row[4],
            source_url=row[5],
            title=row[6],
        )

    def upsert_state(
        self,
        *,
        doc_id: str,
        title: str,
        source_url: str,
        content_hash: str,
        last_updated: str,
        markdown_path: str,
        metadata_path: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO distribution_state (doc_id, title, source_url, content_hash, last_updated, markdown_path, metadata_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title = excluded.title,
                    source_url = excluded.source_url,
                    content_hash = excluded.content_hash,
                    last_updated = excluded.last_updated,
                    markdown_path = excluded.markdown_path,
                    metadata_path = excluded.metadata_path
                """,
                (doc_id, title, source_url, content_hash, last_updated, markdown_path, metadata_path),
            )

    def log_distribution(self, event: DistributionEvent) -> None:
        if not event.targets:
            return
        created_at = datetime.utcnow().isoformat()
        rows = [
            (
                event.doc_id,
                event.content_hash,
                target.target_type,
                target.target_id,
                target.target_name,
                json.dumps(event.change_summary.change_points, ensure_ascii=False),
                event.message_text,
                created_at,
            )
            for target in event.targets
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO distribution_log (doc_id, content_hash, target_type, target_id, target_name, summary, message_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

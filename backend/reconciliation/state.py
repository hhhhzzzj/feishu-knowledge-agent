from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.models.reconciliation import TrackedItem


class ReconciliationStateRepository:
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.sqlite_path))

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tracked_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    owner TEXT NOT NULL DEFAULT '',
                    due_date TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    blocker TEXT NOT NULL DEFAULT '',
                    source_title TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL DEFAULT '',
                    extracted_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tracked_items_doc_id
                ON tracked_items(doc_id)
                """
            )

    def save_snapshot(self, *, doc_id: str, content_hash: str, items: list[TrackedItem]) -> None:
        extracted_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("DELETE FROM tracked_items WHERE doc_id = ?", (doc_id,))
            rows = [
                (
                    doc_id,
                    content_hash,
                    item.item_id,
                    item.title,
                    item.owner,
                    item.due_date,
                    item.status,
                    item.blocker,
                    item.source_title,
                    item.source_url,
                    item.evidence,
                    extracted_at,
                )
                for item in items
            ]
            connection.executemany(
                """
                INSERT INTO tracked_items (doc_id, content_hash, item_id, title, owner, due_date, status, blocker, source_title, source_url, evidence, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def load_previous_snapshot(self, doc_id: str) -> list[TrackedItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT item_id, title, owner, due_date, status, blocker, source_title, source_url, evidence
                FROM tracked_items WHERE doc_id = ?
                """,
                (doc_id,),
            ).fetchall()
        return [
            TrackedItem(
                item_id=row[0],
                title=row[1],
                owner=row[2],
                due_date=row[3],
                status=row[4],
                blocker=row[5],
                source_title=row[6],
                source_url=row[7],
                evidence=row[8],
            )
            for row in rows
        ]

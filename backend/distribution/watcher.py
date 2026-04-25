from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from backend.clients import LarkCLIClient, LLMChatClient
from backend.distribution.differ import ChangeDiffer
from backend.distribution.dispatcher import DispatchMessageBuilder
from backend.distribution.impact import MetadataImpactAnalyzer
from backend.distribution.state import DistributionStateRepository
from backend.ingestion import DocumentIngestionService
from backend.models.distribution import DistributionEvent, DistributionTarget
from backend.models.lark_docs import FetchedLarkDocument


@dataclass(slots=True)
class WatcherRunResult:
    checked: int = 0
    changed: int = 0
    events: list[DistributionEvent] = field(default_factory=list)


@dataclass(slots=True)
class DistributionWatcher:
    ingestion_service: DocumentIngestionService
    state_repository: DistributionStateRepository
    differ: ChangeDiffer
    impact_analyzer: MetadataImpactAnalyzer
    message_builder: DispatchMessageBuilder
    scheduler: BackgroundScheduler | None = None

    def check_documents(self, *, docs: list[str], subdirectory: str = "lark_docs") -> WatcherRunResult:
        result = WatcherRunResult()
        for doc in docs:
            event = self.check_document(doc=doc, subdirectory=subdirectory)
            result.checked += 1
            if event is not None:
                result.changed += 1
                result.events.append(event)
        return result

    def check_document(self, *, doc: str, subdirectory: str = "lark_docs") -> DistributionEvent | None:
        fetched = self.ingestion_service.fetch_document(doc=doc)
        content_hash = self._hash_markdown(fetched.markdown)
        previous_state = self.state_repository.get_state(fetched.doc_id)
        markdown_path, metadata_path = self.ingestion_service.resolve_storage_paths(
            doc_id=fetched.doc_id,
            title=fetched.title,
            subdirectory=subdirectory,
        )
        previous_markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""

        extra_metadata = {
            "distribution": {
                "content_hash": content_hash,
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        stored = self.ingestion_service.store_document(document=fetched, subdirectory=subdirectory, extra_metadata=extra_metadata)
        self.state_repository.upsert_state(
            doc_id=fetched.doc_id,
            title=fetched.title,
            source_url=fetched.source_url,
            content_hash=content_hash,
            last_updated=fetched.message or fetched.log_id or datetime.now(timezone.utc).isoformat(),
            markdown_path=str(stored.markdown_path),
            metadata_path=str(stored.metadata_path),
        )

        if previous_state is None or previous_state.content_hash == content_hash:
            return None

        change_summary = self.differ.summarize_changes(old_markdown=previous_markdown, new_markdown=fetched.markdown)
        if not change_summary.has_changes:
            return None

        targets = self.impact_analyzer.analyze(
            metadata_path=stored.metadata_path,
            title=fetched.title,
            source_url=fetched.source_url,
            change_summary=change_summary.summary,
            change_points=change_summary.change_points,
            markdown_excerpt=fetched.markdown[:2000],
        )
        event = DistributionEvent(
            doc_id=fetched.doc_id,
            title=fetched.title,
            source_url=fetched.source_url,
            content_hash=content_hash,
            change_summary=change_summary,
            targets=targets,
        )
        event.message_text = self.message_builder.build(event=event)
        self.state_repository.log_distribution(event)
        return event

    def start(self, *, docs: list[str], subdirectory: str = "lark_docs", interval_minutes: int = 10) -> None:
        if self.scheduler is not None:
            return
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            self.check_documents,
            "interval",
            minutes=interval_minutes,
            kwargs={"docs": docs, "subdirectory": subdirectory},
            id="distribution-watcher",
            replace_existing=True,
        )
        scheduler.start()
        self.scheduler = scheduler

    def stop(self) -> None:
        if self.scheduler is None:
            return
        self.scheduler.shutdown(wait=False)
        self.scheduler = None

    @staticmethod
    def build_default(
        *,
        raw_docs_dir: Path,
        sqlite_path: Path,
        lark_cli_path: str,
        lark_doc_identity: str,
        llm_api_key: str,
        llm_base_url: str,
        llm_model: str,
        default_targets: list[DistributionTarget] | None = None,
    ) -> "DistributionWatcher":
        client = LarkCLIClient(cli_path=lark_cli_path, identity=lark_doc_identity)
        ingestion_service = DocumentIngestionService(client=client, raw_docs_dir=raw_docs_dir)
        llm_client = None
        if llm_api_key and llm_model:
            llm_client = LLMChatClient(api_key=llm_api_key, base_url=llm_base_url, model=llm_model)
        return DistributionWatcher(
            ingestion_service=ingestion_service,
            state_repository=DistributionStateRepository(sqlite_path=sqlite_path),
            differ=ChangeDiffer(llm_client=llm_client),
            impact_analyzer=MetadataImpactAnalyzer(default_targets=default_targets or [], llm_client=llm_client),
            message_builder=DispatchMessageBuilder(),
        )

    @staticmethod
    def _hash_markdown(markdown: str) -> str:
        return hashlib.sha1(markdown.encode("utf-8")).hexdigest()

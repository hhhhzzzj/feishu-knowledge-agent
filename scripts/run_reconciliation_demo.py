from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.clients import LarkCLIClient, LarkCLIError
from backend.config import (
    DISTRIBUTION_DEFAULT_CHAT_IDS,
    DISTRIBUTION_DOCS,
    DISTRIBUTION_INTERVAL_MINUTES,
    DISTRIBUTION_SUBDIRECTORY,
    LARK_CLI_PATH,
    LARK_DOC_IDENTITY,
    LARK_MESSAGE_IDENTITY,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    RAW_DOCS_DIR,
    SQLITE_PATH,
)
from backend.distribution.dispatcher import LarkMessageDispatcher
from backend.distribution.state import DistributionStateRepository
from backend.ingestion import DocumentIngestionService
from backend.models.distribution import DistributionTarget
from backend.models.reconciliation import ReconciliationReport
from backend.reconciliation import ReconciliationStateRepository, TaskReconciliationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="事项抽取、对账与风险提醒 Demo")
    parser.add_argument("doc", nargs="?", help="飞书文档 URL 或 token（不传则用 DISTRIBUTION_DOCS[0]）")
    parser.add_argument("--subdirectory", default=DISTRIBUTION_SUBDIRECTORY)
    parser.add_argument("--chat-id", action="append", default=[], help="目标群 chat_id，可重复指定")
    parser.add_argument("--send", action="store_true", help="真实发送飞书消息")
    parser.add_argument("--watch", action="store_true", help="持续轮询")
    parser.add_argument("--interval-minutes", type=int, default=DISTRIBUTION_INTERVAL_MINUTES)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="即使未检测到变化也抽取并保存快照（用于首次运行）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    doc = args.doc or (DISTRIBUTION_DOCS[0] if DISTRIBUTION_DOCS else None)
    if not doc:
        raise SystemExit("请指定文档 URL/token，或在 .env 中配置 DISTRIBUTION_DOCS")

    chat_ids: list[str] = [*DISTRIBUTION_DEFAULT_CHAT_IDS, *args.chat_id]

    doc_client = LarkCLIClient(cli_path=LARK_CLI_PATH, identity=LARK_DOC_IDENTITY)
    ingestion = DocumentIngestionService(client=doc_client, raw_docs_dir=RAW_DOCS_DIR)
    dist_state = DistributionStateRepository(sqlite_path=SQLITE_PATH)
    recon_state = ReconciliationStateRepository(sqlite_path=SQLITE_PATH)

    llm_client = None
    if LLM_API_KEY and LLM_MODEL:
        from backend.clients.llm import LLMChatClient
        llm_client = LLMChatClient(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, model=LLM_MODEL)
    service = TaskReconciliationService(llm_client=llm_client)

    msg_client = LarkCLIClient(cli_path=LARK_CLI_PATH, identity=LARK_MESSAGE_IDENTITY)
    dispatcher = LarkMessageDispatcher(client=msg_client)

    if args.watch:
        run_count = 0
        try:
            while True:
                run_count += 1
                output = _execute_once(
                    doc=doc,
                    ingestion=ingestion,
                    dist_state=dist_state,
                    recon_state=recon_state,
                    service=service,
                    dispatcher=dispatcher,
                    chat_ids=chat_ids,
                    subdirectory=args.subdirectory,
                    send_enabled=args.send,
                    force=args.force,
                )
                output["watch"] = {"enabled": True, "run": run_count, "interval_minutes": args.interval_minutes}
                print(json.dumps(output, ensure_ascii=False, indent=2))
                if args.max_runs is not None and run_count >= args.max_runs:
                    break
                time.sleep(args.interval_minutes * 60)
        except KeyboardInterrupt:
            raise SystemExit("Watcher stopped.") from None
        return

    output = _execute_once(
        doc=doc,
        ingestion=ingestion,
        dist_state=dist_state,
        recon_state=recon_state,
        service=service,
        dispatcher=dispatcher,
        chat_ids=chat_ids,
        subdirectory=args.subdirectory,
        send_enabled=args.send,
        force=args.force,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _execute_once(
    *,
    doc: str,
    ingestion: DocumentIngestionService,
    dist_state: DistributionStateRepository,
    recon_state: ReconciliationStateRepository,
    service: TaskReconciliationService,
    dispatcher: LarkMessageDispatcher,
    chat_ids: list[str],
    subdirectory: str,
    send_enabled: bool,
    force: bool,
) -> dict:
    try:
        fetched = ingestion.fetch_document(doc=doc)
    except LarkCLIError as exc:
        raise SystemExit(str(exc)) from exc

    content_hash = hashlib.sha1(fetched.markdown.encode("utf-8")).hexdigest()
    previous_state = dist_state.get_state(fetched.doc_id)

    markdown_path, metadata_path = ingestion.resolve_storage_paths(
        doc_id=fetched.doc_id,
        title=fetched.title,
        subdirectory=subdirectory,
    )
    stored = ingestion.store_document(document=fetched, subdirectory=subdirectory)
    dist_state.upsert_state(
        doc_id=fetched.doc_id,
        title=fetched.title,
        source_url=fetched.source_url,
        content_hash=content_hash,
        last_updated=fetched.message or fetched.log_id or "",
        markdown_path=str(stored.markdown_path),
        metadata_path=str(stored.metadata_path),
    )

    changed = previous_state is None or previous_state.content_hash != content_hash
    if not changed and not force:
        return {
            "doc_id": fetched.doc_id,
            "title": fetched.title,
            "source_url": fetched.source_url,
            "content_hash": content_hash,
            "changed": False,
            "message": "文档未发生变化。如需强制抽取请加 --force。",
        }

    old_items = recon_state.load_previous_snapshot(fetched.doc_id)
    new_items = service.extract_items(
        markdown=fetched.markdown,
        source_title=fetched.title,
        source_url=fetched.source_url,
    )
    recon_state.save_snapshot(doc_id=fetched.doc_id, content_hash=content_hash, items=new_items)
    if not old_items:
        return {
            "doc_id": fetched.doc_id,
            "title": fetched.title,
            "source_url": fetched.source_url,
            "content_hash": content_hash,
            "changed": True if changed else "forced",
            "baseline_established": True,
            "items": [
                {
                    "item_id": item.item_id,
                    "title": item.title,
                    "owner": item.owner,
                    "due_date": item.due_date,
                    "status": item.status,
                    "blocker": item.blocker,
                    "evidence": item.evidence,
                }
                for item in new_items
            ],
            "changes": [],
            "risk_message": f"已建立事项基线：共 {len(new_items)} 个事项。后续文档变化将进行对账和风险提醒。",
            "dry_run_commands": [],
            "send_enabled": send_enabled,
        }

    changes = service.compare_items(old_items=old_items, new_items=new_items)
    report = ReconciliationReport(
        source_title=fetched.title,
        source_url=fetched.source_url,
        items=new_items,
        changes=changes,
        summary=f"共 {len(new_items)} 个事项，{len(changes)} 项变化" if changes else "未检测到事项变化",
    )
    risk_message = service.build_risk_message(report=report)

    targets = [DistributionTarget(target_type="chat", target_id=cid) for cid in chat_ids]

    result: dict = {
        "doc_id": fetched.doc_id,
        "title": fetched.title,
        "source_url": fetched.source_url,
        "content_hash": content_hash,
        "changed": True if changed else "forced",
        "items": [
            {
                "item_id": item.item_id,
                "title": item.title,
                "owner": item.owner,
                "due_date": item.due_date,
                "status": item.status,
                "blocker": item.blocker,
                "evidence": item.evidence,
            }
            for item in new_items
        ],
        "changes": [
            {
                "change_type": change.change_type,
                "summary": change.summary,
                "risk_level": change.risk_level,
            }
            for change in changes
        ],
        "risk_message": risk_message,
        "dry_run_commands": dispatcher.dry_run_post_commands(targets=targets, message_text=risk_message),
        "send_enabled": send_enabled,
    }

    if send_enabled and targets and changes:
        result["send_results"] = dispatcher.send_post(targets=targets, message_text=risk_message)
    elif send_enabled and targets:
        result["send_skipped"] = "no changes detected; not sending an empty risk reminder"

    return result


if __name__ == "__main__":
    main()

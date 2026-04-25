from __future__ import annotations

import argparse
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
    DISTRIBUTION_DEFAULT_USER_IDS,
    DISTRIBUTION_DOCS,
    DISTRIBUTION_INTERVAL_MINUTES,
    DISTRIBUTION_SUBDIRECTORY,
    LARK_DOC_IDENTITY,
    LARK_MESSAGE_IDENTITY,
    LARK_CLI_PATH,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    RAW_DOCS_DIR,
    SQLITE_PATH,
)
from backend.distribution import DistributionWatcher, LarkMessageDispatcher
from backend.models.distribution import DistributionTarget


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("docs", nargs="*", help="Lark document URLs or tokens to check")
    parser.add_argument("--subdirectory", default=DISTRIBUTION_SUBDIRECTORY)
    parser.add_argument("--chat-id", action="append", default=[])
    parser.add_argument("--user-id", action="append", default=[])
    parser.add_argument("--watch", action="store_true", help="Keep polling documents on an interval")
    parser.add_argument("--interval-minutes", type=int, default=DISTRIBUTION_INTERVAL_MINUTES)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--send", action="store_true", help="Actually send Lark messages for changed documents")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs = args.docs or DISTRIBUTION_DOCS
    if not docs:
        raise SystemExit("No documents configured. Pass doc URLs/tokens or set DISTRIBUTION_DOCS in .env.")

    default_targets = _build_targets(
        chat_ids=[*DISTRIBUTION_DEFAULT_CHAT_IDS, *args.chat_id],
        user_ids=[*DISTRIBUTION_DEFAULT_USER_IDS, *args.user_id],
    )
    watcher = DistributionWatcher.build_default(
        raw_docs_dir=RAW_DOCS_DIR,
        sqlite_path=SQLITE_PATH,
        lark_cli_path=LARK_CLI_PATH,
        lark_doc_identity=LARK_DOC_IDENTITY,
        llm_api_key=LLM_API_KEY,
        llm_base_url=LLM_BASE_URL,
        llm_model=LLM_MODEL,
        default_targets=default_targets,
    )
    dispatcher = LarkMessageDispatcher(client=LarkCLIClient(cli_path=LARK_CLI_PATH, identity=LARK_MESSAGE_IDENTITY))

    if args.watch and args.interval_minutes < 1:
        raise SystemExit("--interval-minutes must be >= 1 when --watch is enabled.")
    if args.max_runs is not None and args.max_runs < 1:
        raise SystemExit("--max-runs must be >= 1.")

    if args.watch:
        run_count = 0
        try:
            while True:
                run_count += 1
                output = _execute_once(
                    watcher=watcher,
                    dispatcher=dispatcher,
                    docs=docs,
                    subdirectory=args.subdirectory,
                    default_targets=default_targets,
                    send_enabled=args.send,
                )
                output["watch"] = {
                    "enabled": True,
                    "run": run_count,
                    "interval_minutes": args.interval_minutes,
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
                if args.max_runs is not None and run_count >= args.max_runs:
                    break
                time.sleep(args.interval_minutes * 60)
        except KeyboardInterrupt:
            raise SystemExit("Watcher stopped.") from None
        return

    output = _execute_once(
        watcher=watcher,
        dispatcher=dispatcher,
        docs=docs,
        subdirectory=args.subdirectory,
        default_targets=default_targets,
        send_enabled=args.send,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _execute_once(
    *,
    watcher: DistributionWatcher,
    dispatcher: LarkMessageDispatcher,
    docs: list[str],
    subdirectory: str,
    default_targets: list[DistributionTarget],
    send_enabled: bool,
) -> dict:
    try:
        result = watcher.check_documents(docs=docs, subdirectory=subdirectory)
    except LarkCLIError as exc:
        raise SystemExit(str(exc)) from exc

    output_events = []
    for event in result.events:
        event_output = {
            "doc_id": event.doc_id,
            "title": event.title,
            "source_url": event.source_url,
            "summary": event.change_summary.summary,
            "change_points": event.change_summary.change_points,
            "targets": [
                {
                    "target_type": target.target_type,
                    "target_id": target.target_id,
                    "target_name": target.target_name,
                }
                for target in event.targets
            ],
            "message_text": event.message_text,
            "dry_run_commands": dispatcher.dry_run_commands(targets=event.targets, message_text=event.message_text),
        }
        if send_enabled and event.targets:
            event_output["send_results"] = dispatcher.send_text(targets=event.targets, message_text=event.message_text)
        output_events.append(event_output)

    return {
        "checked": result.checked,
        "changed": result.changed,
        "doc_identity": LARK_DOC_IDENTITY,
        "message_identity": LARK_MESSAGE_IDENTITY,
        "events": output_events,
        "used_default_targets": [
            {
                "target_type": target.target_type,
                "target_id": target.target_id,
                "target_name": target.target_name,
            }
            for target in default_targets
        ],
        "send_enabled": send_enabled,
    }


def _build_targets(*, chat_ids: list[str], user_ids: list[str]) -> list[DistributionTarget]:
    targets: list[DistributionTarget] = []
    seen: set[tuple[str, str]] = set()
    for target_type, values in (("chat", chat_ids), ("user", user_ids)):
        for value in values:
            normalized = value.strip()
            key = (target_type, normalized)
            if not normalized or key in seen:
                continue
            seen.add(key)
            targets.append(DistributionTarget(target_type=target_type, target_id=normalized))
    return targets


if __name__ == "__main__":
    main()

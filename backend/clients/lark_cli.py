from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from backend.models.lark_docs import FetchedLarkDocument, LarkDocSearchPage


class LarkCLIError(RuntimeError):
    pass


@dataclass(slots=True)
class LarkCLIClient:
    cli_path: str
    identity: str
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        self.cli_path = self._resolve_cli_path(self.cli_path)

    def search_docs(
        self,
        *,
        query: str,
        page_size: int = 10,
        page_token: str | None = None,
    ) -> LarkDocSearchPage:
        command = [
            self.cli_path,
            "docs",
            "+search",
            "--as",
            self.identity,
            "--query",
            query,
            "--page-size",
            str(page_size),
            "--format",
            "json",
        ]
        if page_token:
            command.extend(["--page-token", page_token])
        payload = self._run_json_command(command)
        return LarkDocSearchPage.from_dict(payload)

    def fetch_doc(
        self,
        *,
        doc: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> FetchedLarkDocument:
        command = [
            self.cli_path,
            "docs",
            "+fetch",
            "--as",
            self.identity,
            "--doc",
            doc,
            "--format",
            "json",
        ]
        if offset is not None:
            command.extend(["--offset", str(offset)])
        if limit is not None:
            command.extend(["--limit", str(limit)])
        payload = self._run_json_command(command)
        return FetchedLarkDocument.from_dict(payload, source_url=doc)

    def build_send_text_command(
        self,
        *,
        text: str,
        chat_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        command = [self.cli_path, "im", "+messages-send", "--as", self.identity]
        if chat_id:
            command.extend(["--chat-id", chat_id])
        elif user_id:
            command.extend(["--user-id", user_id])
        else:
            raise LarkCLIError("Either chat_id or user_id is required to send a message")
        command.extend(["--text", text])
        if idempotency_key:
            command.extend(["--idempotency-key", idempotency_key])
        if dry_run:
            command.append("--dry-run")
        return command

    def build_send_markdown_command(
        self,
        *,
        markdown: str,
        chat_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        command = [self.cli_path, "im", "+messages-send", "--as", self.identity]
        if chat_id:
            command.extend(["--chat-id", chat_id])
        elif user_id:
            command.extend(["--user-id", user_id])
        else:
            raise LarkCLIError("Either chat_id or user_id is required to send a message")
        command.extend(["--markdown", markdown])
        if idempotency_key:
            command.extend(["--idempotency-key", idempotency_key])
        if dry_run:
            command.append("--dry-run")
        return command

    def build_send_post_command(
        self,
        *,
        content: str,
        chat_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        command = [self.cli_path, "im", "+messages-send", "--as", self.identity]
        if chat_id:
            command.extend(["--chat-id", chat_id])
        elif user_id:
            command.extend(["--user-id", user_id])
        else:
            raise LarkCLIError("Either chat_id or user_id is required to send a message")
        command.extend(["--msg-type", "post", "--content", content])
        if idempotency_key:
            command.extend(["--idempotency-key", idempotency_key])
        if dry_run:
            command.append("--dry-run")
        return command

    def send_text_to_chat(
        self,
        *,
        chat_id: str,
        text: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_text_command(
                chat_id=chat_id,
                text=text,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def send_text_to_user(
        self,
        *,
        user_id: str,
        text: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_text_command(
                user_id=user_id,
                text=text,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def send_markdown_to_chat(
        self,
        *,
        chat_id: str,
        markdown: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_markdown_command(
                chat_id=chat_id,
                markdown=markdown,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def send_markdown_to_user(
        self,
        *,
        user_id: str,
        markdown: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_markdown_command(
                user_id=user_id,
                markdown=markdown,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def send_post_to_chat(
        self,
        *,
        chat_id: str,
        content: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_post_command(
                chat_id=chat_id,
                content=content,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def send_post_to_user(
        self,
        *,
        user_id: str,
        content: str,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return self._run_json_command(
            self.build_send_post_command(
                user_id=user_id,
                content=content,
                idempotency_key=idempotency_key,
                dry_run=dry_run,
            )
        )

    def _run_json_command(self, command: list[str]) -> dict:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise LarkCLIError(f"Lark CLI not found: {self.cli_path}") from exc
        except subprocess.TimeoutExpired as exc:
            raise LarkCLIError(f"Lark CLI command timed out after {self.timeout_seconds}s") from exc

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        raw_output = stdout or stderr

        if completed.returncode != 0:
            raise LarkCLIError(self._build_error_message(raw_output, stderr))

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise LarkCLIError(f"Failed to parse Lark CLI JSON output: {raw_output}") from exc

        if not payload.get("ok", False):
            raise LarkCLIError(self._extract_payload_error(payload))
        return payload

    @staticmethod
    def _extract_payload_error(payload: dict) -> str:
        error = payload.get("error", {})
        message = error.get("message") or payload
        return f"Lark CLI request failed: {message}"

    @staticmethod
    def _build_error_message(raw_output: str, stderr: str) -> str:
        if raw_output:
            try:
                payload = json.loads(raw_output)
            except json.JSONDecodeError:
                return f"Lark CLI command failed: {raw_output}"
            return LarkCLIClient._extract_payload_error(payload)
        return f"Lark CLI command failed: {stderr}"

    @staticmethod
    def _resolve_cli_path(cli_path: str) -> str:
        candidate = Path(cli_path)
        if candidate.is_file():
            return str(candidate)

        resolved = shutil.which(cli_path)
        if resolved:
            return resolved

        if os.name == "nt" and not cli_path.lower().endswith((".cmd", ".bat", ".exe")):
            windows_candidates = [f"{cli_path}.cmd", f"{cli_path}.bat", f"{cli_path}.exe"]
            for item in windows_candidates:
                resolved = shutil.which(item)
                if resolved:
                    return resolved

        return cli_path

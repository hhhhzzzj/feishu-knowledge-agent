from __future__ import annotations

import subprocess
from dataclasses import dataclass

from backend.clients import LarkCLIClient, LarkCLIError
from backend.models.distribution import DistributionEvent, DistributionTarget


@dataclass(slots=True)
class DispatchMessageBuilder:
    def build(self, *, event: DistributionEvent) -> str:
        change_lines = event.change_summary.change_points[:3]
        lines = [
            f"【知识更新】{event.title}",
            f"文档：{event.source_url}",
        ]
        if event.change_summary.summary:
            lines.extend(["", "变更摘要：", event.change_summary.summary])
        if change_lines:
            lines.extend(["", "关键变化：", *[f"- {line}" for line in change_lines]])
        return "\n".join(lines)


@dataclass(slots=True)
class LarkMessageDispatcher:
    client: LarkCLIClient

    def dry_run_commands(self, *, targets: list[DistributionTarget], message_text: str) -> list[list[str]]:
        commands: list[list[str]] = []
        for target in targets:
            command = [self.client.cli_path, "im", "+messages-send", "--as", self.client.identity]
            if target.target_type == "user":
                command.extend(["--user-id", target.target_id])
            else:
                command.extend(["--chat-id", target.target_id])
            command.extend(["--text", message_text])
            commands.append(command)
        return commands

    def send_text(self, *, targets: list[DistributionTarget], message_text: str) -> list[dict]:
        results: list[dict] = []
        for command in self.dry_run_commands(targets=targets, message_text=message_text):
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding="utf-8",
                    timeout=self.client.timeout_seconds,
                )
            except Exception as exc:
                raise LarkCLIError(f"Lark CLI command failed: {exc}") from exc
            if completed.returncode != 0:
                raise LarkCLIError(completed.stderr.strip() or completed.stdout.strip() or "Unknown Lark CLI error")
            results.append({"command": command, "stdout": completed.stdout.strip()})
        return results

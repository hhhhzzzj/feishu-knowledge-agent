from __future__ import annotations

from dataclasses import dataclass
import re

from backend.clients import LarkCLIClient, LarkCLIError
from backend.models.distribution import DistributionEvent, DistributionTarget


@dataclass(slots=True)
class DispatchMessageBuilder:
    def build(self, *, event: DistributionEvent) -> str:
        change_lines = event.change_summary.change_points[:3]
        lines = [f"【知识更新】{event.title}", f"文档：{event.source_url}"]
        if event.change_summary.summary:
            lines.append(f"变更摘要：{self._normalize_text_for_feishu(event.change_summary.summary)}")
        if change_lines:
            normalized_changes = [self._normalize_text_for_feishu(line) for line in change_lines]
            lines.append(f"关键变化：{'； '.join(normalized_changes)}")
        return "  ".join(lines)

    @staticmethod
    def _normalize_text_for_feishu(text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = normalized.replace("\n- ", "； ")
        normalized = normalized.replace("\n## ", "； ")
        normalized = normalized.replace("\n# ", "； ")
        normalized = normalized.replace("\n", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()


@dataclass(slots=True)
class LarkMessageDispatcher:
    client: LarkCLIClient

    def dry_run_commands(self, *, targets: list[DistributionTarget], message_text: str) -> list[list[str]]:
        commands: list[list[str]] = []
        for target in targets:
            if target.target_type == "user":
                command = self.client.build_send_text_command(user_id=target.target_id, text=message_text, dry_run=True)
            else:
                command = self.client.build_send_text_command(chat_id=target.target_id, text=message_text, dry_run=True)
            commands.append(command)
        return commands

    def send_text(self, *, targets: list[DistributionTarget], message_text: str) -> list[dict]:
        results: list[dict] = []
        for target in targets:
            if target.target_type == "user":
                payload = self.client.send_text_to_user(user_id=target.target_id, text=message_text)
                command = self.client.build_send_text_command(user_id=target.target_id, text=message_text)
            else:
                payload = self.client.send_text_to_chat(chat_id=target.target_id, text=message_text)
                command = self.client.build_send_text_command(chat_id=target.target_id, text=message_text)
            if not payload.get("ok", False):
                raise LarkCLIError(self.client._extract_payload_error(payload))
            results.append({"command": command, "payload": payload})
        return results

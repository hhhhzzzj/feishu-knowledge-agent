from __future__ import annotations

from dataclasses import dataclass
import json
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

    def dry_run_markdown_commands(self, *, targets: list[DistributionTarget], markdown_text: str) -> list[list[str]]:
        commands: list[list[str]] = []
        for target in targets:
            if target.target_type == "user":
                command = self.client.build_send_markdown_command(user_id=target.target_id, markdown=markdown_text, dry_run=True)
            else:
                command = self.client.build_send_markdown_command(chat_id=target.target_id, markdown=markdown_text, dry_run=True)
            commands.append(command)
        return commands

    def dry_run_post_commands(self, *, targets: list[DistributionTarget], message_text: str) -> list[list[str]]:
        commands: list[list[str]] = []
        content = _build_post_content(message_text)
        for target in targets:
            if target.target_type == "user":
                command = self.client.build_send_post_command(user_id=target.target_id, content=content, dry_run=True)
            else:
                command = self.client.build_send_post_command(chat_id=target.target_id, content=content, dry_run=True)
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

    def send_markdown(self, *, targets: list[DistributionTarget], markdown_text: str) -> list[dict]:
        results: list[dict] = []
        for target in targets:
            if target.target_type == "user":
                payload = self.client.send_markdown_to_user(user_id=target.target_id, markdown=markdown_text)
                command = self.client.build_send_markdown_command(user_id=target.target_id, markdown=markdown_text)
            else:
                payload = self.client.send_markdown_to_chat(chat_id=target.target_id, markdown=markdown_text)
                command = self.client.build_send_markdown_command(chat_id=target.target_id, markdown=markdown_text)
            if not payload.get("ok", False):
                raise LarkCLIError(self.client._extract_payload_error(payload))
            results.append({"command": command, "payload": payload})
        return results

    def send_post(self, *, targets: list[DistributionTarget], message_text: str) -> list[dict]:
        results: list[dict] = []
        content = _build_post_content(message_text)
        for target in targets:
            if target.target_type == "user":
                payload = self.client.send_post_to_user(user_id=target.target_id, content=content)
                command = self.client.build_send_post_command(user_id=target.target_id, content=content)
            else:
                payload = self.client.send_post_to_chat(chat_id=target.target_id, content=content)
                command = self.client.build_send_post_command(chat_id=target.target_id, content=content)
            if not payload.get("ok", False):
                raise LarkCLIError(self.client._extract_payload_error(payload))
            results.append({"command": command, "payload": payload})
        return results


def _build_post_content(message_text: str) -> str:
    lines = [line.rstrip() for line in message_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    non_empty_lines = [line for line in lines if line.strip()]
    title = non_empty_lines[0] if non_empty_lines else "通知"
    body_lines = lines[1:] if lines else []
    if not body_lines:
        body_lines = [title]
    content = []
    for line in body_lines:
        content.append([{"tag": "text", "text": line if line.strip() else " "}])
    return json.dumps({"zh_cn": {"title": title, "content": content}}, ensure_ascii=False)

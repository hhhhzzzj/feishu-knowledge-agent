from __future__ import annotations

from dataclasses import dataclass
import difflib

from backend.clients import LLMChatClient, LLMConfigurationError, LLMInvocationError
from backend.models.distribution import ChangeSummary


@dataclass(slots=True)
class ChangeDiffer:
    llm_client: LLMChatClient | None = None

    def summarize_changes(self, *, old_markdown: str, new_markdown: str) -> ChangeSummary:
        if old_markdown.strip() == new_markdown.strip():
            return ChangeSummary(has_changes=False, summary="", change_points=[])

        diff_text = self._build_diff(old_markdown=old_markdown, new_markdown=new_markdown)
        change_points = self._extract_change_points(diff_text)
        summary = self._generate_summary(diff_text=diff_text, change_points=change_points)
        return ChangeSummary(has_changes=True, summary=summary, change_points=change_points)

    def _generate_summary(self, *, diff_text: str, change_points: list[str]) -> str:
        if self.llm_client is None:
            return "；".join(change_points[:3]) if change_points else "检测到文档内容发生变化。"
        try:
            result = self.llm_client.generate(
                system_prompt="你是企业知识变更摘要助手。请基于给定 diff，用中文输出 2-3 句简洁摘要，不要编造。",
                user_prompt=f"请总结以下文档变化：\n\n{diff_text[:6000]}",
                temperature=0.1,
            )
            return result.text.strip()
        except (LLMConfigurationError, LLMInvocationError):
            return "；".join(change_points[:3]) if change_points else "检测到文档内容发生变化。"

    @staticmethod
    def _build_diff(*, old_markdown: str, new_markdown: str) -> str:
        old_lines = old_markdown.splitlines()
        new_lines = new_markdown.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile="previous",
                tofile="current",
                lineterm="",
                n=1,
            )
        )
        return "\n".join(diff_lines)

    @staticmethod
    def _extract_change_points(diff_text: str) -> list[str]:
        points: list[str] = []
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                points.append(f"新增：{line[1:].strip()}")
            elif line.startswith("-"):
                points.append(f"删除：{line[1:].strip()}")
            if len(points) >= 5:
                break
        return [point for point in points if point.split("：", 1)[-1]]

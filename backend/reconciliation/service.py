from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date

from backend.clients import LLMChatClient, LLMConfigurationError, LLMInvocationError
from backend.models.reconciliation import ItemChange, ReconciliationReport, TrackedItem

_EXTRACTION_SYSTEM_PROMPT = (
    "你是一个企业项目管理助手，负责从文档中抽取结构化事项。"
    "请严格输出 JSON，格式为 {\"items\": [{\"title\": \"...\", \"owner\": \"...\", \"due_date\": \"...\", \"status\": \"...\", \"blocker\": \"...\", \"evidence\": \"...\"}]}。"
    "抽取规则：\n"
    "- 每个事项必须有 title。\n"
    "- owner: 负责人姓名，不确定就留空字符串。\n"
    "- due_date: 截止日期，统一为 YYYY-MM-DD 格式，不确定就留空字符串。\n"
    "- status: 状态，从\"未开始/进行中/已完成/延期/阻塞\"中选择，不确定填\"未明确\"。\n"
    "- blocker: 阻塞原因，无则留空。\n"
    "- evidence: 从原文摘抄 1-2 句原文作为证据，不超过 200 字。\n"
    "- 不要编造任何信息，不确定就留空。"
)

_STATUS_COMPLETED_KEYWORDS = {"完成", "已完成", "已结束", "已关闭", "done", "completed", "closed"}
_STATUS_BLOCKED_KEYWORDS = {"阻塞", "卡住", "blocked"}
_STATUS_DELAYED_KEYWORDS = {"延期", "推迟", "delayed"}

_TABLE_HEADER_PATTERN = re.compile(
    r"\|?\s*(?:事项|任务|标题|title|item|task)\s*\|",
    re.IGNORECASE,
)
_KV_PATTERNS: list[tuple[str, str]] = [
    (r"[-*]\s*\*{0,2}事项[：:]\s*(.+)", "title"),
    (r"[-*]\s*\*{0,2}任务[：:]\s*(.+)", "title"),
    (r"[-*]\s*\*{0,2}负责人[：:]\s*(.+)", "owner"),
    (r"[-*]\s*\*{0,2}截止(?:时间|日期)[：:]\s*(.+)", "due_date"),
    (r"[-*]\s*\*{0,2}状态[：:]\s*(.+)", "status"),
    (r"[-*]\s*\*{0,2}阻塞(?:原因)?[：:]\s*(.+)", "blocker"),
]


@dataclass(slots=True)
class TaskReconciliationService:
    llm_client: LLMChatClient | None = None

    def extract_items(self, *, markdown: str, source_title: str = "", source_url: str = "") -> list[TrackedItem]:
        rule_items = self._extract_via_rules(markdown=markdown, source_title=source_title, source_url=source_url)
        if rule_items:
            return rule_items
        if self.llm_client is not None:
            try:
                return self._extract_via_llm(markdown=markdown, source_title=source_title, source_url=source_url)
            except (LLMConfigurationError, LLMInvocationError):
                pass
        return []

    def _extract_via_llm(self, *, markdown: str, source_title: str, source_url: str) -> list[TrackedItem]:
        user_prompt = f"请从以下文档内容中抽取所有事项：\n\n{markdown[:8000]}"
        result = self.llm_client.generate(
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
        )
        raw_items = self._parse_llm_items(result.text)
        return [
            self._build_item(
                raw=item,
                source_title=source_title,
                source_url=source_url,
            )
            for item in raw_items
        ]

    @staticmethod
    def _parse_llm_items(text: str) -> list[dict]:
        payload = text.strip()
        json_block = _extract_json_block(payload)
        if json_block:
            payload = json_block
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
            return [item for item in parsed["items"] if isinstance(item, dict)]
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return []

    def _extract_via_rules(self, *, markdown: str, source_title: str, source_url: str) -> list[TrackedItem]:
        items: list[TrackedItem] = []
        items.extend(self._extract_from_lark_tables(markdown=markdown, source_title=source_title, source_url=source_url))
        if items:
            return items
        items.extend(self._extract_from_tables(markdown=markdown, source_title=source_title, source_url=source_url))
        if items:
            return items
        items.extend(self._extract_from_kv_blocks(markdown=markdown, source_title=source_title, source_url=source_url))
        return items

    def _extract_from_lark_tables(self, *, markdown: str, source_title: str, source_url: str) -> list[TrackedItem]:
        items: list[TrackedItem] = []
        table_blocks = re.findall(r"<lark-table\b[^>]*>(.*?)</lark-table>", markdown, flags=re.DOTALL | re.IGNORECASE)
        for table in table_blocks:
            rows: list[list[str]] = []
            row_blocks = re.findall(r"<lark-tr\b[^>]*>(.*?)</lark-tr>", table, flags=re.DOTALL | re.IGNORECASE)
            for row_block in row_blocks:
                cells = [
                    _strip_lark_tags(cell).strip()
                    for cell in re.findall(r"<lark-td\b[^>]*>(.*?)</lark-td>", row_block, flags=re.DOTALL | re.IGNORECASE)
                ]
                if cells:
                    rows.append(cells)
            if len(rows) < 2:
                continue
            headers = rows[0]
            col_map = _map_table_columns(headers)
            for row in rows[1:]:
                raw: dict[str, str] = {field: "" for field in ["title", "owner", "due_date", "status", "blocker"]}
                for idx, cell in enumerate(row):
                    field = col_map.get(idx)
                    if field:
                        raw[field] = cell
                if not raw["title"].strip():
                    continue
                raw["evidence"] = " | ".join(cell for cell in row if cell)
                items.append(self._build_item(raw=raw, source_title=source_title, source_url=source_url))
        return items

    def _extract_from_tables(self, *, markdown: str, source_title: str, source_url: str) -> list[TrackedItem]:
        table_sections = _split_table_sections(markdown)
        items: list[TrackedItem] = []
        for section in table_sections:
            lines = section.strip().splitlines()
            if len(lines) < 2:
                continue
            header_cols: list[str] = []
            data_rows: list[list[str]] = []
            for line in lines:
                if not line.strip().startswith("|"):
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if not cells:
                    continue
                if _is_separator_row(cells):
                    continue
                if not header_cols:
                    header_cols = cells
                    continue
                data_rows.append(cells)
            if not header_cols or not data_rows:
                continue
            col_map = _map_table_columns(header_cols)
            for row in data_rows:
                raw: dict[str, str] = {field: "" for field in ["title", "owner", "due_date", "status", "blocker"]}
                for idx, cell in enumerate(row):
                    field = col_map.get(idx)
                    if field:
                        raw[field] = cell
                if not raw["title"].strip():
                    continue
                items.append(
                    self._build_item(raw=raw, source_title=source_title, source_url=source_url)
                )
        return items

    def _extract_from_kv_blocks(self, *, markdown: str, source_title: str, source_url: str) -> list[TrackedItem]:
        blocks = re.split(r"\n(?=## |### )", markdown)
        items: list[TrackedItem] = []
        for block in blocks:
            raw: dict[str, str] = {field: "" for field in ["title", "owner", "due_date", "status", "blocker"]}
            for pattern, field in _KV_PATTERNS:
                match = re.search(pattern, block)
                if match:
                    raw[field] = match.group(1).strip()
            if not raw["title"].strip():
                heading = re.match(r"^#{1,3}\s+(.+)", block)
                if heading:
                    raw["title"] = heading.group(1).strip()
            if not raw["title"].strip():
                continue
            items.append(
                self._build_item(raw=raw, source_title=source_title, source_url=source_url)
            )
        return items

    @staticmethod
    def _build_item(*, raw: dict[str, str], source_title: str, source_url: str) -> TrackedItem:
        title = raw.get("title", "").strip()
        return TrackedItem(
            item_id=_make_item_id(title),
            title=title,
            owner=raw.get("owner", "").strip(),
            due_date=_normalize_date(raw.get("due_date", "").strip()),
            status=raw.get("status", "").strip() or "未明确",
            blocker=_normalize_empty_value(raw.get("blocker", "").strip()),
            source_title=source_title,
            source_url=source_url,
            evidence=raw.get("evidence", "").strip(),
        )

    @staticmethod
    def compare_items(*, old_items: list[TrackedItem], new_items: list[TrackedItem]) -> list[ItemChange]:
        old_by_id = {item.item_id: item for item in old_items}
        new_by_id = {item.item_id: item for item in new_items}
        changes: list[ItemChange] = []

        for item_id, new_item in new_by_id.items():
            if item_id not in old_by_id:
                changes.append(
                    ItemChange(
                        change_type="added",
                        after=new_item,
                        summary=f"新增事项：{new_item.title}",
                        risk_level="low",
                    )
                )

        for item_id, old_item in old_by_id.items():
            if item_id not in new_by_id:
                change_type = "completed" if _is_completed_status(old_item.status) else "updated"
                changes.append(
                    ItemChange(
                        change_type=change_type,
                        before=old_item,
                        summary=f"{'已完成' if change_type == 'completed' else '移除'}事项：{old_item.title}",
                        risk_level="low",
                    )
                )

        for item_id, new_item in new_by_id.items():
            old_item = old_by_id.get(item_id)
            if old_item is None:
                continue
            change = _detect_field_change(old_item=old_item, new_item=new_item)
            if change is not None:
                changes.append(change)

        return changes

    @staticmethod
    def build_risk_message(*, report: ReconciliationReport) -> str:
        high_risk = [c for c in report.changes if c.risk_level == "high"]
        medium_risk = [c for c in report.changes if c.risk_level == "medium"]
        low_risk = [c for c in report.changes if c.risk_level == "low"]

        lines = [f"【重点事项风险提醒】"]
        if report.source_title:
            lines.append(f"来源文档：{report.source_title}")
        if report.source_url:
            lines.append(f"文档链接：{report.source_url}")
        lines.append("")

        if high_risk:
            lines.append("高风险：")
            for change in high_risk:
                lines.append(f"  - {change.summary}")
                if change.after and change.after.blocker and change.after.blocker not in change.summary:
                    lines.append(f"    阻塞原因：{change.after.blocker}")
                if change.after and change.after.owner:
                    lines.append(f"    负责人：{change.after.owner}")
                if change.after and change.after.evidence:
                    lines.append(f"    原文依据：{change.after.evidence}")
            lines.append("")

        if medium_risk:
            lines.append("中风险：")
            for change in medium_risk:
                lines.append(f"  - {change.summary}")
            lines.append("")

        if low_risk:
            lines.append("其他变化：")
            for change in low_risk:
                lines.append(f"  - {change.summary}")

        if report.summary:
            lines.append(f"\n总结：{report.summary}")

        return "\n".join(lines)


def _make_item_id(title: str) -> str:
    return hashlib.sha1(title.strip().encode("utf-8")).hexdigest()[:12]


def _normalize_date(raw: str) -> str:
    if not raw:
        return ""
    for sep in ("-", "/", "."):
        parts = raw.replace("日", "").replace("号", "").strip().split(sep)
        if len(parts) == 3:
            try:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                date(year, month, day)
                return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, OverflowError):
                pass
    return raw


def _normalize_empty_value(raw: str) -> str:
    normalized = raw.strip()
    if normalized.casefold() in {"", "无", "暂无", "无阻塞", "none", "n/a", "na", "-"}:
        return ""
    return normalized


def _strip_lark_tags(raw: str) -> str:
    without_tags = re.sub(r"</?[^>]+>", "", raw)
    return re.sub(r"\s+", " ", without_tags).strip()


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]


def _split_table_sections(markdown: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    in_table = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            if not in_table:
                if current:
                    sections.append("\n".join(current))
                    current = []
                in_table = True
            current.append(line)
        else:
            if in_table:
                in_table = False
                if current:
                    sections.append("\n".join(current))
                    current = []
            current.append(line)
    if current:
        remaining = "\n".join(current)
        if "|" in remaining:
            sections.append(remaining)
    return sections


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells)


def _map_table_columns(headers: list[str]) -> dict[int, str]:
    field_keywords = [
        ("title", ["事项", "任务", "标题", "item", "task", "title"]),
        ("owner", ["负责人", "owner", "assignee", "负责", "责任人"]),
        ("due_date", ["截止时间", "截止日期", "due", "deadline", "日期", "ddl"]),
        ("status", ["状态", "status", "进展", "进度"]),
        ("blocker", ["阻塞", "blocker", "阻塞原因", "风险", "障碍"]),
    ]
    mapping: dict[int, str] = {}
    for idx, header in enumerate(headers):
        normalized = header.strip().casefold()
        for field, keywords in field_keywords:
            if any(keyword in normalized for keyword in keywords):
                mapping[idx] = field
                break
    return mapping


def _is_completed_status(status: str) -> bool:
    normalized = status.strip().casefold()
    return any(keyword in normalized for keyword in _STATUS_COMPLETED_KEYWORDS)


def _detect_field_change(*, old_item: TrackedItem, new_item: TrackedItem) -> ItemChange | None:
    old_status_norm = old_item.status.strip().casefold()
    new_status_norm = new_item.status.strip().casefold()

    if old_status_norm == new_status_norm and old_item.due_date == new_item.due_date and old_item.owner == new_item.owner and old_item.blocker == new_item.blocker:
        return None

    if any(kw in new_status_norm for kw in _STATUS_COMPLETED_KEYWORDS) and not any(kw in old_status_norm for kw in _STATUS_COMPLETED_KEYWORDS):
        return ItemChange(
            change_type="completed",
            before=old_item,
            after=new_item,
            summary=f"事项已完成：{new_item.title}",
            risk_level="low",
        )

    if any(kw in new_status_norm for kw in _STATUS_BLOCKED_KEYWORDS) and not any(kw in old_status_norm for kw in _STATUS_BLOCKED_KEYWORDS):
        risk_msg = f"事项阻塞：{new_item.title}"
        if new_item.blocker:
            risk_msg += f"，阻塞原因：{new_item.blocker}"
        return ItemChange(
            change_type="blocked",
            before=old_item,
            after=new_item,
            summary=risk_msg,
            risk_level="high",
        )

    if any(kw in new_status_norm for kw in _STATUS_DELAYED_KEYWORDS) and not any(kw in old_status_norm for kw in _STATUS_DELAYED_KEYWORDS):
        risk_msg = f"事项延期：{new_item.title}"
        if old_item.due_date:
            risk_msg += f"，原截止时间 {old_item.due_date}"
        if new_item.due_date:
            risk_msg += f"，新截止时间 {new_item.due_date}"
        return ItemChange(
            change_type="delayed",
            before=old_item,
            after=new_item,
            summary=risk_msg,
            risk_level="high",
        )

    if old_item.due_date and new_item.due_date and new_item.due_date > old_item.due_date:
        risk_msg = f"事项截止时间延后：{new_item.title}，{old_item.due_date} → {new_item.due_date}"
        return ItemChange(
            change_type="delayed",
            before=old_item,
            after=new_item,
            summary=risk_msg,
            risk_level="high",
        )

    if new_item.blocker and not old_item.blocker and not _is_completed_status(new_item.status):
        return ItemChange(
            change_type="blocked",
            before=old_item,
            after=new_item,
            summary=f"事项出现阻塞风险：{new_item.title}，阻塞原因：{new_item.blocker}",
            risk_level="high",
        )

    if old_item.owner and new_item.owner and old_item.owner != new_item.owner:
        return ItemChange(
            change_type="owner_changed",
            before=old_item,
            after=new_item,
            summary=f"负责人变更：{new_item.title}，{old_item.owner} → {new_item.owner}",
            risk_level="medium",
        )

    return ItemChange(
        change_type="updated",
        before=old_item,
        after=new_item,
        summary=f"事项更新：{new_item.title}",
        risk_level="low",
    )

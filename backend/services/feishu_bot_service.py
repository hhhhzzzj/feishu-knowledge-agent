from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any

from backend.clients import LarkCLIClient
from backend.services.answer_service import AnswerResult, AnswerService

_RECENT_EVENT_IDS: dict[str, float] = {}
_RECENT_EVENT_TTL_SECONDS = 600


@dataclass(slots=True)
class FeishuMessageEvent:
    event_id: str
    event_type: str
    message_id: str
    chat_id: str
    sender_type: str = ""
    open_id: str = ""
    user_id: str = ""
    message_type: str = ""
    question: str = ""


@dataclass(slots=True)
class FeishuEventHandleResult:
    event_type: str
    tenant_key: str = ""
    handled: bool = False
    replied: bool = False
    skipped_reason: str | None = None
    message_id: str | None = None
    chat_id: str | None = None
    question: str | None = None


@dataclass(slots=True)
class FeishuBotService:
    answer_service: AnswerService
    message_client: LarkCLIClient
    subdirectory: str = "lark_docs"
    top_k: int = 5
    retrieval_mode: str = "bm25"
    temperature: float = 0.2

    def handle_event(
        self,
        *,
        header: dict[str, Any] | None,
        event: dict[str, Any] | None,
        fallback_event_type: str = "",
    ) -> FeishuEventHandleResult:
        safe_header = header or {}
        safe_event = event or {}
        event_type = str(safe_header.get("event_type") or fallback_event_type or "").strip()
        result = FeishuEventHandleResult(
            event_type=event_type,
            tenant_key=str(safe_header.get("tenant_key") or "").strip(),
        )
        if event_type != "im.message.receive_v1":
            result.skipped_reason = "ignored_event_type"
            return result

        message_event = self._parse_message_event(header=safe_header, event=safe_event, event_type=event_type)
        result.message_id = message_event.message_id or None
        result.chat_id = message_event.chat_id or None
        result.question = message_event.question or None

        if not message_event.chat_id:
            result.skipped_reason = "missing_chat_id"
            return result
        if message_event.sender_type.casefold() in {"app", "bot"}:
            result.skipped_reason = "ignored_bot_message"
            return result
        if self._is_duplicate_event(message_event.event_id):
            result.skipped_reason = "duplicate_event"
            return result
        if message_event.message_type and message_event.message_type != "text":
            self._reply_text(
                chat_id=message_event.chat_id,
                text="暂时只支持文本提问，请直接发送文字问题。",
                idempotency_key=self._build_reply_idempotency_key(message_event),
            )
            result.handled = True
            result.replied = True
            result.skipped_reason = "unsupported_message_type"
            return result
        if not message_event.question:
            self._reply_text(
                chat_id=message_event.chat_id,
                text="请直接发送你的问题，我会基于已索引的飞书文档回答。",
                idempotency_key=self._build_reply_idempotency_key(message_event),
            )
            result.handled = True
            result.replied = True
            result.skipped_reason = "empty_question"
            return result

        answer_result = self.answer_service.answer(
            question=message_event.question,
            subdirectory=self.subdirectory,
            top_k=self.top_k,
            retrieval_mode=self.retrieval_mode,
            temperature=self.temperature,
        )
        self._reply_text(
            chat_id=message_event.chat_id,
            text=self._format_answer_message(answer_result),
            idempotency_key=self._build_reply_idempotency_key(message_event),
        )
        result.handled = True
        result.replied = True
        return result

    def _reply_text(self, *, chat_id: str, text: str, idempotency_key: str) -> dict:
        return self.message_client.send_text_to_chat(
            chat_id=chat_id,
            text=text,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def _parse_message_event(
        *,
        header: dict[str, Any],
        event: dict[str, Any],
        event_type: str,
    ) -> FeishuMessageEvent:
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
        sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
        mentions = event.get("mentions") if isinstance(event.get("mentions"), list) else []
        event_id = str(header.get("event_id") or message.get("message_id") or "").strip()
        text = FeishuBotService._extract_text_from_message_content(message.get("content"))
        question = FeishuBotService._normalize_question(text=text, mentions=mentions)
        return FeishuMessageEvent(
            event_id=event_id,
            event_type=event_type,
            message_id=str(message.get("message_id") or "").strip(),
            chat_id=str(message.get("chat_id") or "").strip(),
            sender_type=str(sender.get("sender_type") or "").strip(),
            open_id=str(sender_id.get("open_id") or "").strip(),
            user_id=str(sender_id.get("user_id") or "").strip(),
            message_type=str(message.get("message_type") or "").strip(),
            question=question,
        )

    @staticmethod
    def _extract_text_from_message_content(content: Any) -> str:
        if isinstance(content, dict):
            return str(content.get("text") or "").strip()
        if not isinstance(content, str):
            return ""
        payload = content.strip()
        if not payload:
            return ""
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return payload
        if isinstance(parsed, dict):
            return str(parsed.get("text") or "").strip()
        return ""

    @staticmethod
    def _normalize_question(text: str, mentions: list[Any]) -> str:
        normalized = text.replace("\u200b", " ").replace("\xa0", " ").strip()
        while normalized.startswith("@"):
            pieces = normalized.split(maxsplit=1)
            normalized = pieces[1].strip() if len(pieces) == 2 else ""
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            name = str(mention.get("name") or "").strip()
            key = str(mention.get("key") or "").strip()
            for token in (f"@{name}" if name else "", f"@{key}" if key else ""):
                if token and normalized.startswith(token):
                    normalized = normalized[len(token) :].strip()
        return normalized

    @staticmethod
    def _format_answer_message(result: AnswerResult) -> str:
        answer_text = FeishuBotService._truncate_text(result.answer.strip(), limit=1500)
        if not answer_text:
            answer_text = "已收到你的问题，但当前回答结果为空，请稍后重试。"
        normalized_answer = FeishuBotService._normalize_text_for_feishu(answer_text)
        lines = [f"【知识问答回复】 {normalized_answer}"]
        if result.hits:
            source_lines = []
            for hit in result.hits[:2]:
                title = hit.chunk.title.strip() or "未命名文档"
                source_lines.append(f"- {title} | {hit.chunk.source_url}")
            normalized_sources = [FeishuBotService._normalize_text_for_feishu(item) for item in source_lines]
            lines.append(f"来源：{'； '.join(normalized_sources)}")
        return "  ".join(lines)

    @staticmethod
    def _truncate_text(text: str, *, limit: int) -> str:
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1].rstrip()}…"
    
    @staticmethod
    def _normalize_text_for_feishu(text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = normalized.replace("\n- ", "； ")
        normalized = normalized.replace("\n## ", "； ")
        normalized = normalized.replace("\n# ", "； ")
        normalized = normalized.replace("\n", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _is_duplicate_event(event_id: str) -> bool:
        normalized = event_id.strip()
        if not normalized:
            return False
        now = time.time()
        expired = [key for key, ts in _RECENT_EVENT_IDS.items() if now - ts > _RECENT_EVENT_TTL_SECONDS]
        for key in expired:
            _RECENT_EVENT_IDS.pop(key, None)
        if normalized in _RECENT_EVENT_IDS:
            return True
        _RECENT_EVENT_IDS[normalized] = now
        return False

    @staticmethod
    def _build_reply_idempotency_key(message_event: FeishuMessageEvent) -> str:
        base = message_event.event_id or message_event.message_id or message_event.chat_id
        return f"feishu-bot-reply-{base}"

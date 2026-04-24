from __future__ import annotations

from dataclasses import dataclass

from backend.clients.llm import LLMChatClient
from backend.models.retrieval import RetrievalHit
from backend.services.retrieval_service import LocalRetrievalService

SYSTEM_PROMPT = (
    "你是企业知识问答助手。"
    "请仅基于给定的检索证据回答问题，不要编造不存在的事实。"
    "如果证据不足，请明确说明根据当前检索结果无法确认。"
    "回答尽量简洁、准确，并优先使用中文。"
)


@dataclass(slots=True)
class AnswerResult:
    question: str
    answer: str
    model: str | None
    document_count: int
    chunk_count: int
    hits: list[RetrievalHit]


@dataclass(slots=True)
class AnswerService:
    retrieval_service: LocalRetrievalService
    llm_client: LLMChatClient

    def answer(
        self,
        *,
        question: str,
        subdirectory: str = "lark_docs",
        top_k: int = 5,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        temperature: float = 0.2,
    ) -> AnswerResult:
        retrieval_result = self.retrieval_service.retrieve(
            query=question,
            subdirectory=subdirectory,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not retrieval_result.hits:
            return AnswerResult(
                question=question,
                answer="未在本地知识库中检索到相关内容，暂时无法基于文档给出可靠回答。",
                model=None,
                document_count=retrieval_result.document_count,
                chunk_count=retrieval_result.chunk_count,
                hits=[],
            )

        completion = self.llm_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self._build_user_prompt(question=question, hits=retrieval_result.hits),
            temperature=temperature,
        )
        return AnswerResult(
            question=question,
            answer=completion.text,
            model=completion.model,
            document_count=retrieval_result.document_count,
            chunk_count=retrieval_result.chunk_count,
            hits=retrieval_result.hits,
        )

    def _build_user_prompt(self, *, question: str, hits: list[RetrievalHit]) -> str:
        evidence_blocks: list[str] = []
        for index, hit in enumerate(hits, start=1):
            evidence_blocks.append(
                "\n".join(
                    [
                        f"[证据 {index}]",
                        f"标题：{hit.chunk.title}",
                        f"来源：{hit.chunk.source_url}",
                        f"相关度：{hit.score:.4f}",
                        "内容：",
                        hit.chunk.text.strip(),
                    ]
                )
            )

        evidence_text = "\n\n".join(evidence_blocks)
        return "\n\n".join(
            [
                f"用户问题：{question.strip()}",
                "检索证据：",
                evidence_text,
                "请基于上述证据回答问题。若无法从证据中确认答案，请明确说明不确定。",
            ]
        )

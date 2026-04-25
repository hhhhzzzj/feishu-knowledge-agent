from __future__ import annotations

import logging

import requests

from backend.models.retrieval import RetrievalHit

log = logging.getLogger("feishu_knowledge_agent")


class Reranker:
    REQUEST_TIMEOUT: int = 10

    def __init__(self, api_key: str, base_url: str, model: str = "BAAI/bge-reranker-v2-m3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        if not documents:
            return []

        if not self.is_available():
            log.debug("Reranker 未配置 API Key，跳过重排")
            return documents[:top_k]

        try:
            return self._call_rerank_api(query, documents, top_k)
        except Exception as exc:
            log.warning("Reranker API 调用失败，降级使用原始排序: %s", exc)
            return documents[:top_k]

    def rerank_hits(self, query: str, hits: list[RetrievalHit], top_k: int = 5) -> list[RetrievalHit]:
        if not hits:
            return []

        documents = [
            {
                "text": hit.chunk.text,
                "metadata": {
                    "chunk_id": hit.chunk.chunk_id,
                    "doc_id": hit.chunk.doc_id,
                    "title": hit.chunk.title,
                    "source_url": hit.chunk.source_url,
                    "chunk_index": hit.chunk.chunk_index,
                    "start_offset": hit.chunk.start_offset,
                    "end_offset": hit.chunk.end_offset,
                    "text_preview": hit.chunk.text_preview,
                },
                "score": hit.score,
                "hit": hit,
            }
            for hit in hits
        ]
        ranked_documents = self.rerank(query=query, documents=documents, top_k=top_k)

        reranked_hits: list[RetrievalHit] = []
        for item in ranked_documents:
            original_hit = item.get("hit")
            if original_hit is None:
                continue
            reranked_hits.append(RetrievalHit(chunk=original_hit.chunk, score=float(item.get("rerank_score", item.get("score", 0.0)))))
        return reranked_hits

    def _call_rerank_api(self, query: str, documents: list[dict], top_k: int) -> list[dict]:
        doc_texts = [doc["text"] for doc in documents]

        url = f"{self.base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "query": query,
            "documents": doc_texts,
            "top_n": min(top_k, len(documents)),
            "return_documents": False,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        ranked = self._parse_rerank_response(data, documents)

        log.info(
            "[Reranker] query='%s' input=%d output=%d top1_score=%.3f",
            query[:30],
            len(documents),
            len(ranked),
            ranked[0]["rerank_score"] if ranked else 0.0,
        )
        return ranked

    @staticmethod
    def _parse_rerank_response(api_response: dict, original_docs: list[dict]) -> list[dict]:
        results = api_response.get("results", [])
        ranked_docs = []

        for item in results:
            idx = item.get("index", -1)
            score = item.get("relevance_score", 0.0)
            if 0 <= idx < len(original_docs):
                doc = dict(original_docs[idx])
                doc["rerank_score"] = round(float(score), 4)
                ranked_docs.append(doc)

        ranked_docs.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)
        return ranked_docs

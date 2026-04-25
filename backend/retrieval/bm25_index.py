from __future__ import annotations

from dataclasses import dataclass
import re

from rank_bm25 import BM25Okapi

from backend.ingestion.chunker import MarkdownChunker
from backend.models.retrieval import DocumentChunk, LocalDocument, RetrievalHit


@dataclass(slots=True)
class BM25Index:
    chunks: list[DocumentChunk]
    _tokenized_chunks: list[list[str]]
    _bm25: BM25Okapi

    @classmethod
    def from_documents(cls, documents: list[LocalDocument], *, chunker: MarkdownChunker) -> "BM25Index":
        chunks: list[DocumentChunk] = []
        for document in documents:
            chunks.extend(chunker.split_document(document))
        return cls.from_chunks(chunks)

    @classmethod
    def from_chunks(cls, chunks: list[DocumentChunk]) -> "BM25Index":
        tokenized_chunks = [tokenize_text(chunk.text) for chunk in chunks]
        bm25 = BM25Okapi(tokenized_chunks) if tokenized_chunks else BM25Okapi([[]])
        return cls(chunks=chunks, _tokenized_chunks=tokenized_chunks, _bm25=bm25)

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        if not self.chunks:
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)

        hits: list[RetrievalHit] = []
        for index, score in ranked:
            if len(hits) >= top_k:
                break
            if score <= 0:
                continue
            hits.append(RetrievalHit(chunk=self.chunks[index], score=float(score)))
        return hits


def tokenize_text(text: str) -> list[str]:
    lowered = text.lower()
    return re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", lowered)

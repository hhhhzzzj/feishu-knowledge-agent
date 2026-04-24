from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.ingestion.chunker import MarkdownChunker
from backend.models.retrieval import RetrievalHit
from backend.retrieval import BM25Index, LocalDocumentCorpus


class EmptyCorpusError(RuntimeError):
    pass


class InvalidRetrievalRequestError(ValueError):
    pass


@dataclass(slots=True)
class RetrievalResult:
    query: str
    document_count: int
    chunk_count: int
    hits: list[RetrievalHit]


@dataclass(slots=True)
class LocalRetrievalService:
    raw_docs_dir: Path

    def retrieve(
        self,
        *,
        query: str,
        subdirectory: str = "lark_docs",
        top_k: int = 5,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> RetrievalResult:
        if chunk_overlap >= chunk_size:
            raise InvalidRetrievalRequestError("chunk_overlap must be smaller than chunk_size")

        corpus = LocalDocumentCorpus(self.raw_docs_dir)
        documents = corpus.load_documents(subdirectory=subdirectory)
        if not documents:
            raise EmptyCorpusError("No local documents found. Please ingest documents first.")

        chunker = MarkdownChunker(chunk_size=chunk_size, overlap_size=chunk_overlap)
        index = BM25Index.from_documents(documents, chunker=chunker)
        hits = index.search(query, top_k=top_k)
        return RetrievalResult(
            query=query,
            document_count=len(documents),
            chunk_count=len(index.chunks),
            hits=hits,
        )

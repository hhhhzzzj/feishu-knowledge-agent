from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from backend.clients.embeddings import OpenAIEmbeddingClient
from backend.config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL, RERANKER_MODEL
from backend.ingestion.chunker import MarkdownChunker
from backend.models.retrieval import DocumentChunk, LocalDocument, RetrievalHit
from backend.retrieval import BM25Index, LocalDocumentCorpus, Reranker, VectorIndex, reciprocal_rank_fusion


class EmptyCorpusError(RuntimeError):
    pass


class InvalidRetrievalRequestError(ValueError):
    pass


@dataclass(slots=True)
class RetrievalArtifacts:
    documents: list[LocalDocument]
    chunks: list[DocumentChunk]
    bm25_index: BM25Index
    vector_index: VectorIndex | None = None


@dataclass(slots=True)
class RetrievalResult:
    query: str
    retrieval_mode: str
    document_count: int
    chunk_count: int
    hits: list[RetrievalHit]


_ARTIFACT_CACHE: dict[tuple[str, str, int, int, str, str], RetrievalArtifacts] = {}


@dataclass(slots=True)
class LocalRetrievalService:
    raw_docs_dir: Path
    chroma_dir: Path
    embedding_api_key: str = EMBEDDING_API_KEY
    embedding_base_url: str = EMBEDDING_BASE_URL
    embedding_model: str = EMBEDDING_MODEL
    reranker_model: str = RERANKER_MODEL

    def retrieve(
        self,
        *,
        query: str,
        subdirectory: str = "lark_docs",
        top_k: int = 5,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        retrieval_mode: str = "bm25",
        vector_top_k: int | None = None,
    ) -> RetrievalResult:
        if chunk_overlap >= chunk_size:
            raise InvalidRetrievalRequestError("chunk_overlap must be smaller than chunk_size")
        if retrieval_mode not in {"bm25", "vector", "hybrid"}:
            raise InvalidRetrievalRequestError("retrieval_mode must be one of: bm25, vector, hybrid")

        documents = self._load_documents(subdirectory=subdirectory)
        if not documents:
            raise EmptyCorpusError("No local documents found. Please ingest documents first.")

        artifacts = self._get_or_build_artifacts(
            documents=documents,
            subdirectory=subdirectory,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            with_vector_index=retrieval_mode in {"vector", "hybrid"},
        )
        if retrieval_mode == "bm25":
            hits = artifacts.bm25_index.search(query, top_k=top_k)
        elif retrieval_mode == "vector":
            hits = (artifacts.vector_index.search(query, top_k=vector_top_k or top_k) if artifacts.vector_index else [])
        else:
            bm25_hits = artifacts.bm25_index.search(query, top_k=max(top_k, vector_top_k or top_k))
            vector_hits = (artifacts.vector_index.search(query, top_k=vector_top_k or max(top_k, 8)) if artifacts.vector_index else [])
            hits = reciprocal_rank_fusion([bm25_hits, vector_hits], top_k=top_k)
            reranker = Reranker(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url,
                model=self.reranker_model,
            )
            hits = reranker.rerank_hits(query=query, hits=hits, top_k=top_k)

        return RetrievalResult(
            query=query,
            retrieval_mode=retrieval_mode,
            document_count=len(documents),
            chunk_count=len(artifacts.chunks),
            hits=hits,
        )

    def _load_documents(self, *, subdirectory: str) -> list[LocalDocument]:
        corpus = LocalDocumentCorpus(self.raw_docs_dir)
        return corpus.load_documents(subdirectory=subdirectory)

    def _get_or_build_artifacts(
        self,
        *,
        documents: list[LocalDocument],
        subdirectory: str,
        chunk_size: int,
        chunk_overlap: int,
        with_vector_index: bool,
    ) -> RetrievalArtifacts:
        fingerprint = self._compute_fingerprint(
            documents=documents,
            subdirectory=subdirectory,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        cache_key = (
            str(self.raw_docs_dir.resolve()),
            subdirectory,
            chunk_size,
            chunk_overlap,
            self.embedding_base_url,
            self.embedding_model,
            fingerprint,
        )
        artifacts = _ARTIFACT_CACHE.get(cache_key)
        if artifacts is None:
            chunker = MarkdownChunker(chunk_size=chunk_size, overlap_size=chunk_overlap)
            chunks: list[DocumentChunk] = []
            for document in documents:
                chunks.extend(chunker.split_document(document))
            artifacts = RetrievalArtifacts(
                documents=documents,
                chunks=chunks,
                bm25_index=BM25Index.from_chunks(chunks),
            )
            _ARTIFACT_CACHE[cache_key] = artifacts

        if with_vector_index and artifacts.vector_index is None:
            embedding_client = OpenAIEmbeddingClient(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url,
                model=self.embedding_model,
            )
            artifacts.vector_index = VectorIndex.from_chunks(
                artifacts.chunks,
                chroma_dir=self.chroma_dir,
                embedding_client=embedding_client,
                collection_name=self._build_collection_name(subdirectory=subdirectory, fingerprint=fingerprint),
            )
        return artifacts

    def _compute_fingerprint(
        self,
        *,
        documents: list[LocalDocument],
        subdirectory: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> str:
        digest = hashlib.sha1()
        digest.update(str(subdirectory).encode("utf-8"))
        digest.update(str(chunk_size).encode("utf-8"))
        digest.update(str(chunk_overlap).encode("utf-8"))
        for document in documents:
            digest.update(document.doc_id.encode("utf-8", errors="ignore"))
            digest.update(document.title.encode("utf-8", errors="ignore"))
            for path in (document.markdown_path, document.metadata_path):
                if path and path.exists():
                    stat = path.stat()
                    digest.update(str(path).encode("utf-8", errors="ignore"))
                    digest.update(str(stat.st_mtime_ns).encode("utf-8"))
                    digest.update(str(stat.st_size).encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _build_collection_name(*, subdirectory: str, fingerprint: str) -> str:
        prefix = subdirectory.replace("/", "-").replace("\\", "-")
        return f"retrieval-{prefix}-{fingerprint[:24]}"

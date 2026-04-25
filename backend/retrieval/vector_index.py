from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import chromadb
from chromadb.config import Settings

from backend.clients.embeddings import EmbeddingClient
from backend.models.retrieval import DocumentChunk, RetrievalHit


@dataclass(slots=True)
class VectorIndex:
    chunks_by_id: dict[str, DocumentChunk]
    collection_name: str
    chroma_dir: Path
    embedding_client: EmbeddingClient

    @classmethod
    def from_chunks(
        cls,
        chunks: list[DocumentChunk],
        *,
        chroma_dir: Path,
        embedding_client: EmbeddingClient,
        collection_name: str,
    ) -> "VectorIndex":
        client = _create_chroma_client(chroma_dir)
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

        if chunks:
            collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                embeddings=embedding_client.embed_documents([chunk.text for chunk in chunks]),
                documents=[chunk.text for chunk in chunks],
                metadatas=[
                    {
                        "doc_id": chunk.doc_id,
                        "title": chunk.title,
                        "source_url": chunk.source_url,
                        "chunk_index": chunk.chunk_index,
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset,
                        "text_preview": chunk.text_preview,
                    }
                    for chunk in chunks
                ],
            )

        return cls(
            chunks_by_id={chunk.chunk_id: chunk for chunk in chunks},
            collection_name=collection_name,
            chroma_dir=chroma_dir,
            embedding_client=embedding_client,
        )

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        if not query.strip() or not self.chunks_by_id:
            return []

        client = _create_chroma_client(self.chroma_dir)
        collection = client.get_collection(name=self.collection_name)
        result = collection.query(
            query_embeddings=[self.embedding_client.embed_query(query)],
            n_results=min(top_k, len(self.chunks_by_id)),
            include=["distances"],
        )

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits: list[RetrievalHit] = []
        for chunk_id, distance in zip(ids, distances):
            chunk = self.chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            score = max(0.0, 1.0 - float(distance))
            if score <= 0:
                continue
            hits.append(RetrievalHit(chunk=chunk, score=score))
        return hits


def build_collection_name(*, prefix: str, fingerprint: str) -> str:
    sanitized_prefix = re.sub(r"[^a-z0-9_-]", "-", prefix.lower()).strip("-") or "docs"
    return f"{sanitized_prefix}-{fingerprint[:24]}"


def _create_chroma_client(chroma_dir: Path) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )

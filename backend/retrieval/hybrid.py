from __future__ import annotations

from backend.models.retrieval import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievalHit]],
    *,
    top_k: int,
    weights: list[float] | None = None,
    rrf_k: int = 60,
) -> list[RetrievalHit]:
    if not ranked_lists:
        return []

    effective_weights = weights or [1.0] * len(ranked_lists)
    fused_scores: dict[str, float] = {}
    chunks: dict[str, RetrievalHit] = {}

    for weight, hits in zip(effective_weights, ranked_lists):
        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit.chunk.chunk_id
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (weight / (rrf_k + rank))
            chunks[chunk_id] = hit

    ranked_chunk_ids = sorted(fused_scores, key=lambda chunk_id: fused_scores[chunk_id], reverse=True)
    return [
        RetrievalHit(chunk=chunks[chunk_id].chunk, score=fused_scores[chunk_id])
        for chunk_id in ranked_chunk_ids[:top_k]
    ]

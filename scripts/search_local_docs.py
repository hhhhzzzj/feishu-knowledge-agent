from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.clients import EmbeddingConfigurationError, EmbeddingInvocationError
from backend.config import CHROMA_DIR, RAW_DOCS_DIR
from backend.services import EmptyCorpusError, InvalidRetrievalRequestError, LocalRetrievalService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Query to search in locally ingested documents")
    parser.add_argument("--subdirectory", default="lark_docs")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    parser.add_argument("--retrieval-mode", default="bm25", choices=["bm25", "vector", "hybrid"])
    parser.add_argument("--vector-top-k", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR, chroma_dir=CHROMA_DIR)
    try:
        result = service.retrieve(
            query=args.query,
            subdirectory=args.subdirectory,
            top_k=args.top_k,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            retrieval_mode=args.retrieval_mode,
            vector_top_k=args.vector_top_k,
        )
    except (EmptyCorpusError, InvalidRetrievalRequestError, EmbeddingConfigurationError, EmbeddingInvocationError) as exc:
        raise SystemExit(str(exc)) from exc

    output = {
        "query": result.query,
        "retrieval_mode": result.retrieval_mode,
        "document_count": result.document_count,
        "chunk_count": result.chunk_count,
        "hits": [
            {
                "score": hit.score,
                "doc_id": hit.chunk.doc_id,
                "title": hit.chunk.title,
                "source_url": hit.chunk.source_url,
                "chunk_id": hit.chunk.chunk_id,
                "chunk_index": hit.chunk.chunk_index,
                "start_offset": hit.chunk.start_offset,
                "end_offset": hit.chunk.end_offset,
                "text_preview": hit.chunk.text_preview,
            }
            for hit in result.hits
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

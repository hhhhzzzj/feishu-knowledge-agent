from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import RAW_DOCS_DIR
from backend.ingestion.chunker import MarkdownChunker
from backend.retrieval import BM25Index, LocalDocumentCorpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Query to search in locally ingested documents")
    parser.add_argument("--subdirectory", default="lark_docs")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corpus = LocalDocumentCorpus(RAW_DOCS_DIR)
    documents = corpus.load_documents(subdirectory=args.subdirectory)
    if not documents:
        raise SystemExit("No local documents found. Please ingest documents first.")

    chunker = MarkdownChunker(chunk_size=args.chunk_size, overlap_size=args.chunk_overlap)
    index = BM25Index.from_documents(documents, chunker=chunker)
    hits = index.search(args.query, top_k=args.top_k)

    output = {
        "query": args.query,
        "document_count": len(documents),
        "chunk_count": len(index.chunks),
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
            for hit in hits
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

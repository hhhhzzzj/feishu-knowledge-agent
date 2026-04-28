from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from backend.models.retrieval import RetrievalHit
from backend.retrieval import BM25Index, LocalDocumentCorpus
from backend.services.retrieval_service import LocalRetrievalService
from backend.config import CHROMA_DIR, RAW_DOCS_DIR

TEST_CASES = [
    {"id": "C001", "category": "exact_match", "query": "项目目标", "expected_keywords": ["项目目标", "SMART"]},
    {"id": "C002", "category": "exact_match", "query": "项目复盘", "expected_keywords": ["项目复盘"]},
    {"id": "C003", "category": "exact_match", "query": "阶段路线图", "expected_keywords": ["阶段", "路线图"]},
    {"id": "C004", "category": "semantic_expansion", "query": "核心结果", "expected_keywords": ["项目目标", "SMART"]},
    {"id": "C005", "category": "semantic_expansion", "query": "分阶段推进", "expected_keywords": ["阶段", "路线图"]},
    {"id": "C006", "category": "semantic_expansion", "query": "回顾总结", "expected_keywords": ["项目复盘"]},
    {"id": "C007", "category": "synonym", "query": "终极 KPI", "expected_keywords": ["项目目标", "SMART"]},
    {"id": "C008", "category": "synonym", "query": "分期往前推", "expected_keywords": ["阶段", "路线图"]},
    {"id": "C009", "category": "synonym", "query": "总结复盘", "expected_keywords": ["项目复盘"]},
    {"id": "C010", "category": "synonym", "query": "衡量标准", "expected_keywords": ["SMART", "可以衡量"]},
]


def has_relevant_result(hits: list[RetrievalHit] | list[dict], expected_keywords: list[str]) -> bool:
    for hit in hits:
        text = ""
        if isinstance(hit, RetrievalHit):
            text = f"{hit.chunk.title} {hit.chunk.text_preview}".lower()
        else:
            text = f"{hit.get('title', '')} {hit.get('text_preview', '')}".lower()
        if any(keyword.lower() in text for keyword in expected_keywords):
            return True
    return False


def keyword_search(service: LocalRetrievalService, query: str) -> list[RetrievalHit]:
    documents = LocalDocumentCorpus(RAW_DOCS_DIR).load_documents(subdirectory="lark_docs")
    artifacts = service._get_or_build_artifacts(
        documents=documents,
        subdirectory="lark_docs",
        chunk_size=800,
        chunk_overlap=120,
        with_vector_index=False,
    )
    return artifacts.bm25_index.search(query, top_k=5)


def hybrid_search_via_api(base_url: str, query: str) -> dict:
    body = json.dumps({"query": query, "top_k": 5, "retrieval_mode": "hybrid", "vector_top_k": 5}).encode("utf-8")
    req = request.Request(f"{base_url.rstrip('/')}/retrieve", data=body, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    service = LocalRetrievalService(raw_docs_dir=RAW_DOCS_DIR, chroma_dir=CHROMA_DIR)
    base_url = "http://localhost:8000"
    bm25_hit = 0
    hybrid_hit = 0
    rows: list[dict] = []

    for case in TEST_CASES:
        bm25_results = keyword_search(service, case["query"])
        hybrid_response = hybrid_search_via_api(base_url, case["query"])
        hybrid_results = hybrid_response.get("hits", [])
        bm25_ok = has_relevant_result(bm25_results, case["expected_keywords"])
        hybrid_ok = has_relevant_result(hybrid_results, case["expected_keywords"])
        bm25_hit += int(bm25_ok)
        hybrid_hit += int(hybrid_ok)
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "bm25_hit": bm25_ok,
                "hybrid_hit": hybrid_ok,
                "bm25_count": len(bm25_results),
                "hybrid_count": len(hybrid_results),
            }
        )

    total = len(TEST_CASES)
    report_lines = [
        "# BM25 vs Hybrid 对比",
        "",
        f"- 测试用例数: {total}",
        f"- BM25 命中率: {bm25_hit}/{total} = {bm25_hit / total:.0%}",
        f"- Hybrid 命中率: {hybrid_hit}/{total} = {hybrid_hit / total:.0%}",
        "",
        "| ID | 分类 | Query | BM25 | Hybrid | BM25 Count | Hybrid Count |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['id']} | {row['category']} | {row['query']} | {row['bm25_hit']} | {row['hybrid_hit']} | {row['bm25_count']} | {row['hybrid_count']} |"
        )

    output_dir = Path(__file__).resolve().parent
    (output_dir / "compare_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    (output_dir / "compare_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

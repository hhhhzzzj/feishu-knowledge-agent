from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from urllib import error, request

from backend.eval.metrics import answer_not_empty, keyword_recall, route_accuracy

log = logging.getLogger("evaluator")


def _call_api(url: str, payload: dict, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"})
    started_at = time.time()
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            data["time_ms"] = round((time.time() - started_at) * 1000, 1)
            return data
    except error.HTTPError as exc:
        return {
            "answer": f"[HTTP {exc.code}]",
            "time_ms": round((time.time() - started_at) * 1000, 1),
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "answer": "[ERROR]",
            "time_ms": round((time.time() - started_at) * 1000, 1),
            "error": str(exc),
        }


def run_evaluation(
    test_cases: list[dict],
    base_url: str = "http://localhost:8000",
    endpoint: str = "/answer",
    retrieval_mode: str = "hybrid",
) -> list[dict]:
    results: list[dict] = []
    url = f"{base_url.rstrip('/')}{endpoint}"

    for index, case in enumerate(test_cases, start=1):
        question = case["question"]
        log.info("[%d/%d] q=%s", index, len(test_cases), question[:40])
        response = _call_api(
            url,
            {
                "question": question,
                "retrieval_mode": retrieval_mode,
            },
        )
        answer = response.get("answer", "")
        actual_route = response.get("retrieval_mode", retrieval_mode)
        metrics = {
            "keyword_recall": keyword_recall(answer, case.get("expected_keywords", [])),
            "answer_valid": answer_not_empty(answer),
            "route_correct": route_accuracy(actual_route, case.get("expected_route", retrieval_mode)) if case.get("expected_route") else None,
        }
        results.append({"case": case, "result": response, "metrics": metrics})
        time.sleep(0.3)

    return results


def summarize(results: list[dict]) -> dict:
    if not results:
        return {
            "total": 0,
            "evaluated": 0,
            "avg_keyword_recall": 0,
            "answer_valid_rate": 0,
            "avg_time_ms": 0,
            "by_category": {},
        }

    keyword_scores = [item["metrics"]["keyword_recall"] for item in results]
    answer_valids = [item["metrics"]["answer_valid"] for item in results]
    times = [item["result"].get("time_ms", 0) for item in results if item["result"].get("time_ms", 0) > 0]
    summary = {
        "total": len(results),
        "evaluated": len(results),
        "avg_keyword_recall": round(sum(keyword_scores) / len(keyword_scores), 4) if keyword_scores else 0,
        "answer_valid_rate": round(sum(answer_valids) / len(answer_valids), 4) if answer_valids else 0,
        "avg_time_ms": round(sum(times) / len(times), 1) if times else 0,
        "by_category": {},
    }

    categories = sorted({item["case"]["category"] for item in results})
    for category in categories:
        category_results = [item for item in results if item["case"]["category"] == category]
        scores = [item["metrics"]["keyword_recall"] for item in category_results]
        summary["by_category"][category] = {
            "count": len(category_results),
            "avg_keyword_recall": round(sum(scores) / len(scores), 4) if scores else 0,
        }

    route_results = [item for item in results if item["metrics"]["route_correct"] is not None]
    if route_results:
        correct = sum(1 for item in route_results if item["metrics"]["route_correct"])
        summary["route_accuracy"] = round(correct / len(route_results), 4)

    return summary


def generate_report(summary: dict, results: list[dict], output_path: str) -> str:
    lines = [
        "# 评测报告",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 测试用例数: {len(results)}",
        "",
        "---",
        "",
        "## 总览",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 平均关键词召回率 | {summary.get('avg_keyword_recall', 0)} |",
        f"| 有效回答率 | {summary.get('answer_valid_rate', 0)} |",
        f"| 平均响应时间 (ms) | {summary.get('avg_time_ms', 0)} |",
        f"| 评测用例数 | {summary.get('evaluated', 0)} |",
    ]

    if "route_accuracy" in summary:
        lines.append(f"| 路由准确率 | {summary['route_accuracy']} |")

    lines.extend(["", "---", "", "## 分类细分（关键词召回率）", "", "| 分类 | 数量 | 平均关键词召回率 |", "| --- | --- | --- |"])
    for category, item in summary.get("by_category", {}).items():
        lines.append(f"| {category} | {item['count']} | {item['avg_keyword_recall']} |")

    low_score_cases = [item for item in results if item["metrics"]["keyword_recall"] < 0.5]
    if low_score_cases:
        lines.extend(["", "---", "", "## 低分用例（关键词召回率 < 0.5）", "", "| ID | 问题 | 分类 | 召回率 | 缺失关键词 |", "| --- | --- | --- | --- | --- |"])
        for item in low_score_cases:
            case = item["case"]
            answer = item["result"].get("answer", "")
            missing = [keyword for keyword in case.get("expected_keywords", []) if keyword not in answer]
            lines.append(f"| {case['id']} | {case['question']} | {case['category']} | {item['metrics']['keyword_recall']} | {', '.join(missing)} |")

    lines.extend(["", "---", "", "## 结论", "", "> 由评测脚本自动生成，具体分析请结合低分用例与检索结果查看。", ""])
    report = "\n".join(lines)
    Path(output_path).write_text(report, encoding="utf-8")
    return report


def save_results(summary: dict, results: list[dict], output_path: str) -> None:
    output = {
        "summary": summary,
        "details": [
            {
                "id": item["case"]["id"],
                "question": item["case"]["question"],
                "category": item["case"]["category"],
                "answer_preview": item["result"].get("answer", "")[:200],
                "time_ms": item["result"].get("time_ms", 0),
                "retrieval_mode": item["result"].get("retrieval_mode", ""),
                "metrics": item["metrics"],
            }
            for item in results
        ],
    }
    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

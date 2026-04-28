from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from urllib import request

from backend.eval.evaluator import generate_report, run_evaluation, save_results, summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="feishu-knowledge-agent 评测")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/answer")
    parser.add_argument("--retrieval-mode", default="hybrid")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    base_dir = Path(__file__).resolve().parent
    cases_path = base_dir / "test_cases.json"
    test_cases = json.loads(cases_path.read_text(encoding="utf-8"))

    with request.urlopen(request.Request(f"{args.base_url.rstrip('/')}/health"), timeout=5) as response:
        response.read()

    results = run_evaluation(
        test_cases=test_cases,
        base_url=args.base_url,
        endpoint=args.endpoint,
        retrieval_mode=args.retrieval_mode,
    )
    summary = summarize(results)

    report_path = Path(args.output) if args.output else base_dir / "report.md"
    json_path = report_path.with_suffix(".json")
    generate_report(summary, results, str(report_path))
    save_results(summary, results, str(json_path))


if __name__ == "__main__":
    main()

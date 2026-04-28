def keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    hits = sum(1 for kw in expected_keywords if kw in answer)
    return round(hits / len(expected_keywords), 4)


def route_accuracy(actual_route: str, expected_route: str) -> bool:
    return actual_route.strip().lower() == expected_route.strip().lower()


def answer_not_empty(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    fail_markers = ["暂无相关信息", "无法回答", "抱歉，我不知道"]
    return not any(marker in cleaned for marker in fail_markers)

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.clients import LLMChatClient
from backend.models.distribution import DistributionTarget


LLM_SYSTEM_PROMPT = (
    "你是企业知识变更分发的影响分析器。"
    "你只能从给定的候选接收对象中挑选，绝对不能编造 target_id。"
    "请严格输出 JSON，格式为 {\"target_ids\": [\"...\"]}。"
    "如果没有合适对象，返回空数组。"
)


@dataclass(slots=True)
class MetadataImpactAnalyzer:
    default_targets: list[DistributionTarget] = field(default_factory=list)
    llm_client: LLMChatClient | None = None

    def analyze(
        self,
        *,
        metadata_path: Path,
        title: str = "",
        source_url: str = "",
        change_summary: str = "",
        change_points: list[str] | None = None,
        markdown_excerpt: str = "",
    ) -> list[DistributionTarget]:
        metadata = self._load_metadata(metadata_path)
        explicit_targets = self._targets_from_metadata(metadata)
        if explicit_targets:
            return explicit_targets

        rule_targets = self._targets_from_rules(
            metadata=metadata,
            title=title,
            source_url=source_url,
            change_summary=change_summary,
            change_points=change_points or [],
            markdown_excerpt=markdown_excerpt,
        )
        if rule_targets:
            return rule_targets

        llm_targets = self._targets_from_llm(
            metadata=metadata,
            title=title,
            source_url=source_url,
            change_summary=change_summary,
            change_points=change_points or [],
            markdown_excerpt=markdown_excerpt,
        )
        if llm_targets:
            return llm_targets

        return list(self.default_targets)

    @staticmethod
    def _load_metadata(metadata_path: Path) -> dict:
        if not metadata_path.exists():
            return {}
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _targets_from_metadata(metadata: dict) -> list[DistributionTarget]:
        raw_targets = metadata.get("distribution_targets") or metadata.get("applicable_targets") or []
        return MetadataImpactAnalyzer._parse_targets(raw_targets)

    @staticmethod
    def _parse_targets(raw_targets: Any) -> list[DistributionTarget]:
        targets: list[DistributionTarget] = []
        for item in raw_targets:
            if not isinstance(item, dict):
                continue
            target_id = str(item.get("target_id", "")).strip()
            if not target_id:
                continue
            targets.append(
                DistributionTarget(
                    target_type=str(item.get("target_type", "chat")).strip() or "chat",
                    target_id=target_id,
                    target_name=str(item.get("target_name", "")).strip(),
                )
            )
        return MetadataImpactAnalyzer._dedupe_targets(targets)

    def _targets_from_rules(
        self,
        *,
        metadata: dict,
        title: str,
        source_url: str,
        change_summary: str,
        change_points: list[str],
        markdown_excerpt: str,
    ) -> list[DistributionTarget]:
        raw_rules = metadata.get("distribution_rules") or metadata.get("impact_rules") or []
        matched_targets: list[DistributionTarget] = []
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                continue
            match_spec = raw_rule.get("match") if isinstance(raw_rule.get("match"), dict) else raw_rule
            if not self._rule_matches(
                match_spec=match_spec,
                metadata=metadata,
                title=title,
                source_url=source_url,
                change_summary=change_summary,
                change_points=change_points,
                markdown_excerpt=markdown_excerpt,
            ):
                continue
            matched_targets.extend(
                self._parse_targets(
                    raw_rule.get("targets")
                    or raw_rule.get("distribution_targets")
                    or raw_rule.get("applicable_targets")
                    or []
                )
            )
        return self._dedupe_targets(matched_targets)

    def _rule_matches(
        self,
        *,
        match_spec: dict,
        metadata: dict,
        title: str,
        source_url: str,
        change_summary: str,
        change_points: list[str],
        markdown_excerpt: str,
    ) -> bool:
        if not isinstance(match_spec, dict):
            return False

        if "title_contains" in match_spec and not self._contains_any(title, match_spec.get("title_contains")):
            return False
        if "source_url_contains" in match_spec and not self._contains_any(source_url, match_spec.get("source_url_contains")):
            return False
        if "change_summary_contains" in match_spec and not self._contains_any(change_summary, match_spec.get("change_summary_contains")):
            return False
        if "change_points_contains" in match_spec and not self._contains_any("\n".join(change_points), match_spec.get("change_points_contains")):
            return False
        if "content_contains" in match_spec and not self._contains_any(markdown_excerpt, match_spec.get("content_contains")):
            return False

        metadata_equals = match_spec.get("metadata_equals") or {}
        if isinstance(metadata_equals, dict):
            for key, expected in metadata_equals.items():
                actual = self._metadata_lookup(metadata, str(key))
                if self._normalize_scalar(actual) != self._normalize_scalar(expected):
                    return False

        metadata_contains = match_spec.get("metadata_contains") or {}
        if isinstance(metadata_contains, dict):
            for key, expected in metadata_contains.items():
                actual = self._metadata_lookup(metadata, str(key))
                if not self._contains_any(self._coerce_text(actual), expected):
                    return False

        return True

    def _targets_from_llm(
        self,
        *,
        metadata: dict,
        title: str,
        source_url: str,
        change_summary: str,
        change_points: list[str],
        markdown_excerpt: str,
    ) -> list[DistributionTarget]:
        if self.llm_client is None:
            return []

        candidates = self._candidate_targets_from_metadata(metadata)
        if not candidates:
            return []

        try:
            completion = self.llm_client.generate(
                system_prompt=LLM_SYSTEM_PROMPT,
                user_prompt=self._build_llm_prompt(
                    metadata=metadata,
                    title=title,
                    source_url=source_url,
                    change_summary=change_summary,
                    change_points=change_points,
                    markdown_excerpt=markdown_excerpt,
                    candidates=candidates,
                ),
                temperature=0.0,
            )
        except Exception:
            return []

        selected_ids = self._parse_llm_target_ids(completion.text)
        if not selected_ids:
            return []
        return self._dedupe_targets([candidate for candidate in candidates if candidate.target_id in selected_ids])

    def _build_llm_prompt(
        self,
        *,
        metadata: dict,
        title: str,
        source_url: str,
        change_summary: str,
        change_points: list[str],
        markdown_excerpt: str,
        candidates: list[DistributionTarget],
    ) -> str:
        payload = {
            "title": title,
            "source_url": source_url,
            "change_summary": change_summary,
            "change_points": change_points,
            "markdown_excerpt": markdown_excerpt[:1500],
            "metadata": metadata,
            "candidate_targets": [
                {
                    "target_type": candidate.target_type,
                    "target_id": candidate.target_id,
                    "target_name": candidate.target_name,
                }
                for candidate in candidates
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _candidate_targets_from_metadata(self, metadata: dict) -> list[DistributionTarget]:
        raw_candidates = (
            metadata.get("candidate_targets")
            or metadata.get("distribution_candidates")
            or metadata.get("suggested_targets")
            or []
        )
        return self._parse_targets(raw_candidates)

    @staticmethod
    def _parse_llm_target_ids(text: str) -> set[str]:
        payload = text.strip()
        for candidate in (payload, MetadataImpactAnalyzer._extract_json_block(payload)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            target_ids = MetadataImpactAnalyzer._extract_target_ids(parsed)
            if target_ids:
                return target_ids
        return set()

    @staticmethod
    def _extract_json_block(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return ""
        return text[start : end + 1]

    @staticmethod
    def _extract_target_ids(payload: Any) -> set[str]:
        if isinstance(payload, dict):
            value = payload.get("target_ids")
            if isinstance(value, list):
                return {str(item).strip() for item in value if str(item).strip()}
            return set()
        if isinstance(payload, list):
            target_ids: set[str] = set()
            for item in payload:
                if isinstance(item, dict) and item.get("target_id"):
                    target_ids.add(str(item.get("target_id")).strip())
                elif isinstance(item, str) and item.strip():
                    target_ids.add(item.strip())
            return target_ids
        return set()

    @staticmethod
    def _metadata_lookup(metadata: dict, key_path: str) -> Any:
        current: Any = metadata
        for part in key_path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    @staticmethod
    def _contains_any(text: str, patterns: Any) -> bool:
        haystack = text.casefold().strip()
        if not haystack:
            return False
        return any(pattern.casefold() in haystack for pattern in MetadataImpactAnalyzer._normalize_patterns(patterns))

    @staticmethod
    def _normalize_patterns(value: Any) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @staticmethod
    def _normalize_scalar(value: Any) -> str:
        return str(value).strip().casefold() if value is not None else ""

    @staticmethod
    def _coerce_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return "\n".join(str(item) for item in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value) if value is not None else ""

    @staticmethod
    def _dedupe_targets(targets: list[DistributionTarget]) -> list[DistributionTarget]:
        deduped: list[DistributionTarget] = []
        seen: set[tuple[str, str]] = set()
        for target in targets:
            key = (target.target_type.strip() or "chat", target.target_id.strip())
            if not key[1] or key in seen:
                continue
            seen.add(key)
            deduped.append(
                DistributionTarget(
                    target_type=key[0],
                    target_id=key[1],
                    target_name=target.target_name.strip(),
                )
            )
        return deduped

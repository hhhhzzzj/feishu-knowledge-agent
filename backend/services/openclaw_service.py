from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.models.distribution import DistributionTarget
from backend.services.answer_service import AnswerResult, AnswerService


@dataclass(slots=True)
class OpenClawSubscriptionResult:
    doc_id: str
    subdirectory: str
    metadata_path: Path
    targets: list[DistributionTarget]
    replaced_existing: bool
    source: str


@dataclass(slots=True)
class OpenClawService:
    answer_service: AnswerService
    raw_docs_dir: Path

    def query(
        self,
        *,
        question: str,
        subdirectory: str = "lark_docs",
        top_k: int = 5,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        retrieval_mode: str = "bm25",
        vector_top_k: int | None = None,
        temperature: float = 0.2,
    ) -> AnswerResult:
        return self.answer_service.answer(
            question=question,
            subdirectory=subdirectory,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retrieval_mode=retrieval_mode,
            vector_top_k=vector_top_k,
            temperature=temperature,
        )

    def save_subscription(
        self,
        *,
        doc_id: str,
        subdirectory: str,
        targets: list[DistributionTarget],
        replace_existing: bool = False,
        source: str = "openclaw",
    ) -> OpenClawSubscriptionResult:
        metadata_path = self._resolve_metadata_path(doc_id=doc_id, subdirectory=subdirectory)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Document metadata not found for doc_id={doc_id} in subdirectory={subdirectory}")

        metadata = self._load_metadata(metadata_path)
        existing_targets = [] if replace_existing else self._targets_from_metadata(metadata)
        merged_targets = self._merge_targets(existing_targets, targets)
        metadata["distribution_targets"] = [self._target_to_dict(target) for target in merged_targets]
        metadata["openclaw_subscription"] = {
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "replace_existing": replace_existing,
            "target_count": len(merged_targets),
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return OpenClawSubscriptionResult(
            doc_id=doc_id,
            subdirectory=subdirectory,
            metadata_path=metadata_path,
            targets=merged_targets,
            replaced_existing=replace_existing,
            source=source,
        )

    def _resolve_metadata_path(self, *, doc_id: str, subdirectory: str) -> Path:
        safe_doc_id = self._safe_name(doc_id)
        return self.raw_docs_dir / subdirectory / safe_doc_id / "metadata.json"

    @staticmethod
    def _load_metadata(metadata_path: Path) -> dict:
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _targets_from_metadata(metadata: dict) -> list[DistributionTarget]:
        raw_targets = metadata.get("distribution_targets") or metadata.get("applicable_targets") or []
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
        return targets

    @staticmethod
    def _merge_targets(existing_targets: list[DistributionTarget], new_targets: list[DistributionTarget]) -> list[DistributionTarget]:
        merged: list[DistributionTarget] = []
        seen: set[tuple[str, str]] = set()
        for target in [*existing_targets, *new_targets]:
            key = (target.target_type.strip() or "chat", target.target_id.strip())
            if not key[1] or key in seen:
                continue
            seen.add(key)
            merged.append(
                DistributionTarget(
                    target_type=key[0],
                    target_id=key[1],
                    target_name=target.target_name.strip(),
                )
            )
        return merged

    @staticmethod
    def _target_to_dict(target: DistributionTarget) -> dict[str, str]:
        return {
            "target_type": target.target_type,
            "target_id": target.target_id,
            "target_name": target.target_name,
        }

    @staticmethod
    def _safe_name(value: str) -> str:
        sanitized = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value.strip())
        compacted = "_".join(part for part in sanitized.split("_") if part)
        return compacted or "document"

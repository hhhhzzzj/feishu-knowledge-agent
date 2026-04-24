from __future__ import annotations

from dataclasses import dataclass
import re

from backend.models.retrieval import DocumentChunk, LocalDocument


@dataclass(slots=True)
class MarkdownChunker:
    chunk_size: int = 800
    overlap_size: int = 120
    min_chunk_size: int = 120

    def split_document(self, document: LocalDocument) -> list[DocumentChunk]:
        normalized = self._normalize_text(document.markdown)
        if not normalized:
            return []

        sections = self._split_sections(normalized)
        chunks: list[DocumentChunk] = []
        cursor = 0

        for section in sections:
            section_text = section.strip()
            if not section_text:
                continue

            for piece in self._window_text(section_text):
                start_offset = normalized.find(piece, max(0, cursor - self.overlap_size))
                if start_offset < 0:
                    start_offset = cursor
                end_offset = start_offset + len(piece)
                chunk_index = len(chunks)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id or document.title}:{chunk_index}",
                        doc_id=document.doc_id,
                        title=document.title,
                        source_url=document.source_url,
                        chunk_index=chunk_index,
                        start_offset=start_offset,
                        end_offset=end_offset,
                        text=piece,
                        text_preview=self._preview(piece),
                    )
                )
                cursor = end_offset

        return chunks

    @staticmethod
    def _normalize_text(value: str) -> str:
        text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    @staticmethod
    def _split_sections(text: str) -> list[str]:
        sections: list[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            if line.startswith("#") and current:
                sections.append("\n".join(current).strip())
                current = [line]
                continue
            current.append(line)
        if current:
            sections.append("\n".join(current).strip())
        return sections

    def _window_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        windows: list[str] = []
        start = 0
        step = max(1, self.chunk_size - self.overlap_size)

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            candidate = text[start:end]
            if end < len(text):
                split_at = max(candidate.rfind("\n\n"), candidate.rfind("\n"), candidate.rfind("。"), candidate.rfind("."))
                if split_at > self.min_chunk_size:
                    end = start + split_at + 1
                    candidate = text[start:end]
            candidate = candidate.strip()
            if candidate:
                if windows and len(candidate) < self.min_chunk_size:
                    windows[-1] = f"{windows[-1]}\n{candidate}".strip()
                else:
                    windows.append(candidate)
            if end >= len(text):
                break
            start = max(end - self.overlap_size, start + step)
        return windows

    @staticmethod
    def _preview(text: str, limit: int = 120) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= limit:
            return compact
        return f"{compact[:limit]}..."

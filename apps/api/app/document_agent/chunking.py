import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 180


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    text: str


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int | None
    content: str


def extract_pages(path: Path, extension: str) -> list[ExtractedPage]:
    if extension == ".pdf":
        reader = PdfReader(path)
        return [
            ExtractedPage(
                page_number=index + 1,
                text=(page.extract_text() or "").strip(),
            )
            for index, page in enumerate(reader.pages)
        ]

    text = path.read_text(encoding="utf-8-sig")
    return [ExtractedPage(page_number=None, text=text.strip())]


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        return []
    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        hard_end = min(start + chunk_size, len(normalized))
        end = hard_end

        if hard_end < len(normalized):
            lower_bound = start + int(chunk_size * 0.6)
            candidates = [
                normalized.rfind("\n\n", lower_bound, hard_end),
                normalized.rfind(". ", lower_bound, hard_end),
                normalized.rfind(" ", lower_bound, hard_end),
            ]
            breakpoint = max(candidates)
            if breakpoint > start:
                end = breakpoint + (
                    2
                    if normalized[breakpoint:breakpoint + 2] == ". "
                    else 0
                )

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break

        next_start = max(end - overlap, start + 1)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def chunk_pages(pages: list[ExtractedPage]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in pages:
        for content in chunk_text(page.text):
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    page_number=page.page_number,
                    content=content,
                )
            )
    return chunks


import re
from dataclasses import dataclass

from sqlalchemy import func, literal, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk

STOP_WORDS = {
    "about",
    "after",
    "before",
    "could",
    "describe",
    "does",
    "document",
    "documents",
    "from",
    "have",
    "information",
    "into",
    "please",
    "say",
    "says",
    "should",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "uploaded",
    "using",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}


def meaningful_terms(question: str) -> list[str]:
    return list(
        dict.fromkeys(
            term.lower()
            for term in re.findall(r"[A-Za-z0-9_]{3,}", question)
            if term.lower() not in STOP_WORDS
        )
    )


@dataclass(frozen=True)
class SearchResult:
    chunk_id: int
    document_id: str
    filename: str
    page_number: int | None
    content: str
    rank: float


class DocumentSearchTool:
    """Search ready document chunks with bounded PostgreSQL full-text retrieval."""

    async def run(
        self,
        session: AsyncSession,
        question: str,
        document_ids: list[str],
        limit: int = 5,
    ) -> list[SearchResult]:
        if not question.strip():
            raise ValueError("Search question cannot be empty.")
        if limit < 1 or limit > 8:
            raise ValueError("Search result limit must be between 1 and 8.")

        terms = meaningful_terms(question)
        if not terms:
            return []

        query = func.websearch_to_tsquery(
            literal_column("'english'::regconfig"),
            " OR ".join(terms[:8]),
        )
        rank = func.ts_rank_cd(DocumentChunk.search_vector, query)
        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.filename,
                DocumentChunk.page_number,
                DocumentChunk.content,
                rank.label("rank"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.status == "ready",
                DocumentChunk.search_vector.op("@@")(query),
            )
            .order_by(rank.desc(), DocumentChunk.id)
            .limit(limit)
        )
        if document_ids:
            statement = statement.where(Document.id.in_(document_ids))

        rows = (await session.execute(statement)).mappings().all()
        if not rows:
            rows = await self._fallback_search(
                session,
                question,
                document_ids,
                limit,
            )

        return [
            SearchResult(
                chunk_id=row["id"],
                document_id=row["document_id"],
                filename=row["filename"],
                page_number=row["page_number"],
                content=row["content"],
                rank=float(row["rank"]),
            )
            for row in rows
        ]

    async def _fallback_search(
        self,
        session: AsyncSession,
        question: str,
        document_ids: list[str],
        limit: int,
    ):
        terms = meaningful_terms(question)
        if not terms:
            return []

        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.filename,
                DocumentChunk.page_number,
                DocumentChunk.content,
                literal(0.01).label("rank"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.status == "ready",
                or_(
                    *[
                        DocumentChunk.content.ilike(f"%{term}%")
                        for term in terms[:8]
                    ]
                ),
            )
            .order_by(DocumentChunk.id)
            .limit(limit)
        )
        if document_ids:
            statement = statement.where(Document.id.in_(document_ids))
        return (await session.execute(statement)).mappings().all()


def select_excerpt(content: str, question: str, max_chars: int = 420) -> str:
    terms = set(meaningful_terms(question))
    normalized_content = re.sub(r"(?<!\n)\n(?!\n)", " ", content)
    sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", normalized_content)
    ranked = sorted(
        (sentence.strip() for sentence in sentences if sentence.strip()),
        key=lambda sentence: len(
            terms.intersection(
                re.findall(r"[A-Za-z0-9_]{3,}", sentence.lower())
            )
        ),
        reverse=True,
    )
    excerpt = ranked[0] if ranked else content.strip()
    if len(excerpt) <= max_chars:
        return excerpt
    return f"{excerpt[:max_chars].rstrip()}…"


def build_grounded_answer(
    question: str,
    results: list[SearchResult],
) -> tuple[str, list[dict]]:
    if not results:
        return (
            "I could not find supporting evidence in the selected documents. "
            "Try a more specific question or upload another synthetic/public document.",
            [],
        )

    citations = []
    bullets = []
    seen_excerpts: set[str] = set()
    for result in results:
        excerpt = select_excerpt(result.content, question)
        if excerpt in seen_excerpts:
            continue
        seen_excerpts.add(excerpt)
        citation_number = len(citations) + 1
        citations.append(
            {
                "number": citation_number,
                "document_id": result.document_id,
                "filename": result.filename,
                "chunk_id": result.chunk_id,
                "page_number": result.page_number,
                "excerpt": excerpt,
                "rank": round(result.rank, 6),
            }
        )
        bullets.append(f"- {excerpt} [{citation_number}]")
        if len(citations) == 3:
            break

    return (
        "Based on the uploaded documents:\n\n"
        + "\n".join(bullets)
        + "\n\nThis is an extractive, source-grounded response.",
        citations,
    )

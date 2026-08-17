import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Document, DocumentChunk
from app.document_agent.chunking import chunk_text


@dataclass
class StoredDocumentResult:
    document_id: str
    filename: str
    chunk_count: int
    sha256: str
    is_duplicate: bool


async def store_medical_document(
    session: AsyncSession,
    filename: str,
    content: str,
    classification: str = "public",
    content_type: str = "text/markdown",
    custom_chunks: list[str] | None = None,
) -> StoredDocumentResult:
    """
    Stores a medical document and its search chunks in Supabase PostgreSQL
    and caches the raw text in the local data directory.
    """
    encoded = content.encode("utf-8")
    checksum = hashlib.sha256(encoded).hexdigest()
    byte_size = len(encoded)

    # Check for existing document by SHA256 checksum
    existing = await session.scalar(
        select(Document).where(Document.sha256 == checksum)
    )
    if existing is not None:
        return StoredDocumentResult(
            document_id=existing.id,
            filename=existing.filename,
            chunk_count=existing.chunk_count,
            sha256=checksum,
            is_duplicate=True,
        )

    document_id = str(uuid4())
    doc_dir = settings.data_dir / "documents" / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(filename).suffix or ".md"
    source_path = doc_dir / f"source{extension}"
    source_path.write_bytes(encoded)

    # Chunk the document content
    raw_chunks = custom_chunks if custom_chunks is not None else chunk_text(content)
    if not raw_chunks:
        raw_chunks = [content[:1200]]

    doc_record = Document(
        id=document_id,
        filename=filename,
        content_type=content_type,
        classification=classification,
        byte_size=byte_size,
        sha256=checksum,
        status="ready",
        page_count=1,
        chunk_count=len(raw_chunks),
        error_message=None,
    )

    try:
        session.add(doc_record)
        await session.flush()

        for idx, chunk_str in enumerate(raw_chunks):
            chunk_record = DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                page_number=1,
                content=chunk_str,
            )
            session.add(chunk_record)

        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(Document).where(Document.sha256 == checksum)
        )
        return StoredDocumentResult(
            document_id=existing.id if existing else document_id,
            filename=filename,
            chunk_count=len(raw_chunks),
            sha256=checksum,
            is_duplicate=True,
        )

    return StoredDocumentResult(
        document_id=document_id,
        filename=filename,
        chunk_count=len(raw_chunks),
        sha256=checksum,
        is_duplicate=False,
    )

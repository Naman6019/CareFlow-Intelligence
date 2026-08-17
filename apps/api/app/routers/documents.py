import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.db.models import Document, DocumentChunk
from app.document_agent.chunking import chunk_pages, extract_pages
from app.schemas.documents import DocumentListResponse, DocumentResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv"}
ALLOWED_CLASSIFICATIONS = {"synthetic", "public"}


def document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        classification=document.classification,
        byte_size=document.byte_size,
        sha256=document.sha256,
        status=document.status,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    documents = (
        await session.scalars(
            select(Document).order_by(Document.created_at.desc())
        )
    ).all()
    return DocumentListResponse(
        documents=[document_response(document) for document in documents]
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    classification: str = Form(...),
    confirm_no_real_patient_data: bool = Form(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise HTTPException(
            status_code=400,
            detail="Classification must be synthetic or public.",
        )
    if not confirm_no_real_patient_data:
        raise HTTPException(
            status_code=400,
            detail="Real patient documents are not allowed in this sandbox.",
        )

    filename = Path(file.filename or "document").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Supported files: PDF, TXT, Markdown, and CSV.",
        )

    document_id = str(uuid4())
    document_dir = settings.data_dir / "documents" / document_id
    document_dir.mkdir(parents=True, exist_ok=False)
    stored_path = document_dir / f"source{extension}"
    digest = hashlib.sha256()
    byte_size = 0

    try:
        with stored_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                byte_size += len(chunk)
                if byte_size > settings.document_max_upload_bytes:
                    raise ValueError("Document exceeds the 10 MB upload limit.")
                digest.update(chunk)
                destination.write(chunk)

        checksum = digest.hexdigest()
        existing = await session.scalar(
            select(Document).where(Document.sha256 == checksum)
        )
        if existing is not None:
            shutil.rmtree(document_dir)
            return document_response(existing)

        document = Document(
            id=document_id,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            classification=classification,
            byte_size=byte_size,
            sha256=checksum,
            status="processing",
            page_count=0,
            chunk_count=0,
        )
        session.add(document)
        await session.flush()

        pages = extract_pages(stored_path, extension)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No readable text was found in the document.")

        session.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    content=chunk.content,
                )
                for chunk in chunks
            ]
        )
        document.status = "ready"
        document.page_count = len(pages)
        document.chunk_count = len(chunks)
        await session.commit()
        await session.refresh(document)
        return document_response(document)
    except ValueError as error:
        await session.rollback()
        shutil.rmtree(document_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        await session.rollback()
        shutil.rmtree(document_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail=f"Document processing failed: {error}",
        ) from error
    finally:
        await file.close()


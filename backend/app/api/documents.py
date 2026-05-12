"""
Documents API router — upload, list, retrieve, delete, get summary & timestamps.
File processing (PDF extraction / Whisper transcription) runs as a background task.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user_id
from app.core.redis_client import cache_get, cache_set, cache_delete, is_rate_limited
from app.models.document import Document, Transcription, FileType, ProcessingStatus
from app.models.user import User  # noqa: F401 — must import to register mapper
from app.schemas.document import (
    DocumentUploadResponse, DocumentResponse, DocumentListResponse,
    SummaryResponse, TimestampsResponse, TimestampEntry,
)
from app.services.pdf_service import PDFService
from app.services.whisper_service import WhisperService
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Allowed MIME types mapped to FileType enum
ALLOWED_CONTENT_TYPES: dict[str, FileType] = {
    "application/pdf": FileType.PDF,
    "audio/mpeg": FileType.MP3,
    "audio/mp3": FileType.MP3,
    "audio/wav": FileType.WAV,
    "audio/x-wav": FileType.WAV,
    "audio/mp4": FileType.M4A,
    "video/mp4": FileType.MP4,
    "audio/m4a": FileType.M4A,
}

EXTENSION_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".mp3": FileType.MP3,
    ".wav": FileType.WAV,
    ".mp4": FileType.MP4,
    ".m4a": FileType.M4A,
}


def _resolve_file_type(filename: str, content_type: str) -> FileType:
    """Determine FileType from extension or content-type."""
    ext = Path(filename).suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    if content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[content_type]
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


# ── Background processing ───────────────────────────────────────────────────────

async def _process_document(document_id: int, file_path: str, file_type: FileType):
    """
    Background task: extract text (PDF) or transcribe (audio/video),
    build FAISS index, and update the DB record.
    """
    logger.info(f"[BG] Starting processing for document {document_id} ({file_path})")

    async with AsyncSessionLocal() as db:
        try:
            # Verify file exists before starting
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Uploaded file not found on disk: {file_path}")

            # Mark as processing
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one()
            doc.status = ProcessingStatus.PROCESSING
            await db.commit()
            logger.info(f"[BG] Document {document_id} marked as PROCESSING")

            extracted_text: str = ""

            if file_type == FileType.PDF:
                # Extract text synchronously (CPU-bound, run in thread)
                loop = asyncio.get_running_loop()
                extracted_text = await loop.run_in_executor(
                    None, PDFService.extract_text, file_path
                )
                logger.info(f"[BG] PDF extracted {len(extracted_text)} chars for doc {document_id}")

            else:
                # Audio/video — transcribe with Whisper
                transcription_data = await WhisperService.transcribe(file_path)
                extracted_text = transcription_data["full_text"]

                # Extract topic timestamps
                timestamps = await WhisperService.extract_topic_timestamps(
                    transcription_data["full_text"],
                    transcription_data["segments"],
                )

                # Save transcription record
                trans = Transcription(
                    document_id=document_id,
                    full_text=extracted_text,
                    timestamps=[t.model_dump() for t in timestamps],
                    duration_seconds=transcription_data["duration_seconds"],
                    language=transcription_data["language"],
                )
                db.add(trans)
                logger.info(f"[BG] Transcription saved for doc {document_id}")

            # Build FAISS index
            if extracted_text.strip():
                loop = asyncio.get_running_loop()
                index_path = await VectorStoreService.build_index(document_id, extracted_text)
                doc.faiss_index_path = index_path
                logger.info(f"[BG] FAISS index built for doc {document_id} at {index_path}")

            # Update document record
            doc.extracted_text = extracted_text
            doc.status = ProcessingStatus.COMPLETED
            await db.commit()
            logger.info(f"[BG] Document {document_id} processing COMPLETED")

        except Exception as exc:
            logger.exception(f"[BG] Processing FAILED for document {document_id}: {exc}")
            await db.rollback()
            # Mark document as failed in a fresh session
            try:
                async with AsyncSessionLocal() as db2:
                    result = await db2.execute(select(Document).where(Document.id == document_id))
                    doc = result.scalar_one_or_none()
                    if doc:
                        doc.status = ProcessingStatus.FAILED
                        doc.error_message = str(exc)[:500]
                        await db2.commit()
                        logger.info(f"[BG] Document {document_id} marked as FAILED")
            except Exception as inner_exc:
                logger.exception(f"[BG] Could not mark document {document_id} as FAILED: {inner_exc}")



# ── Upload ──────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF, MP3, MP4, or WAV file for processing."""
    if await is_rate_limited(f"upload:{user_id}"):
        raise HTTPException(status_code=429, detail="Upload rate limit exceeded.")

    file_type = _resolve_file_type(file.filename or "", file.content_type or "")

    # Read file content and validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.")

    # Save to disk
    upload_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{Path(file.filename or 'file').suffix.lower()}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    # Create DB record
    doc = Document(
        user_id=user_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        file_type=file_type,
        file_size=len(content),
        file_path=str(file_path),
        status=ProcessingStatus.PENDING,
    )
    db.add(doc)
    # Commit NOW so the background task (which opens its own DB session)
    # can see the document row. A flush() alone is not enough.
    await db.commit()
    await db.refresh(doc)

    # Enqueue background processing (runs after response is sent)
    background_tasks.add_task(_process_document, doc.id, str(file_path), file_type)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.original_filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        message="File accepted. Processing started in the background.",
    )


# ── List ─────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of the current user's documents."""
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    total = total_result.scalar_one()

    docs_result = await db.execute(
        select(Document)
        .options(selectinload(Document.transcription))
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    docs = docs_result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Detail ────────────────────────────────────────────────────────────────────────

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return a single document by ID (must belong to current user)."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.transcription))
        .where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse.model_validate(doc)


# ── Delete ─────────────────────────────────────────────────────────────────────────

@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its associated files."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove files from disk
    try:
        Path(doc.file_path).unlink(missing_ok=True)
        VectorStoreService.delete_index(document_id)
    except Exception:
        pass

    await db.delete(doc)
    await cache_delete(f"summary:{document_id}")


# ── Retry processing ─────────────────────────────────────────────────────────────

@router.post("/{document_id}/retry", response_model=DocumentUploadResponse)
async def retry_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger background processing for a stuck pending or failed document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc.status == ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document is already processed.")

    if not Path(doc.file_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Original file is missing from disk ({doc.file_path}). Please re-upload the document."
        )

    # Reset status back to pending and re-queue
    doc.status = ProcessingStatus.PENDING
    doc.error_message = None

    background_tasks.add_task(_process_document, doc.id, doc.file_path, doc.file_type)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.original_filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        message="Processing re-queued. The document will be ready shortly.",
    )



@router.get("/{document_id}/summary", response_model=SummaryResponse)
async def get_summary(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return (or generate and cache) an AI summary for the document."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.transcription))
        .where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.status != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document is not yet processed.")

    # Check DB cache first
    if doc.summary:
        return SummaryResponse(document_id=document_id, summary=doc.summary, cached=True)

    # Check Redis cache
    cache_key = f"summary:{document_id}"
    cached = await cache_get(cache_key)
    if cached:
        return SummaryResponse(document_id=document_id, summary=cached["summary"], cached=True)

    # Generate summary
    text = doc.extracted_text or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text available for summarisation.")

    summary = await LLMService.summarize(document_id, text)

    # Persist to DB and Redis
    doc.summary = summary
    await db.commit()
    await cache_set(cache_key, {"summary": summary}, ttl=86400)

    return SummaryResponse(document_id=document_id, summary=summary, cached=False)


# ── Timestamps ─────────────────────────────────────────────────────────────────────

@router.get("/{document_id}/timestamps", response_model=TimestampsResponse)
async def get_timestamps(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return extracted timestamps for an audio/video document."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.transcription))
        .where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.file_type == FileType.PDF:
        raise HTTPException(status_code=400, detail="Timestamps are only available for audio/video files.")
    if not doc.transcription:
        raise HTTPException(status_code=400, detail="Transcription not yet available.")

    raw_timestamps = doc.transcription.timestamps or []
    timestamps = [TimestampEntry(**t) for t in raw_timestamps]

    return TimestampsResponse(
        document_id=document_id,
        timestamps=timestamps,
        duration_seconds=doc.transcription.duration_seconds,
    )

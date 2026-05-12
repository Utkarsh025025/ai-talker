"""Pydantic schemas for Document, Transcription, and Q&A endpoints."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from app.models.document import FileType, ProcessingStatus


# ── Timestamp entry ─────────────────────────────────────────────────────────────

class TimestampEntry(BaseModel):
    """A single topic-with-timestamp extracted from a transcription."""
    timestamp: float        # seconds from the start of the media
    topic: str              # short topic label
    text: str               # verbatim text at that timestamp


# ── Document schemas ────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Returned immediately after a file is accepted for processing."""
    id: int
    filename: str
    file_type: FileType
    file_size: int
    status: ProcessingStatus
    message: str


class TranscriptionResponse(BaseModel):
    """Serialized transcription with timestamps."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    full_text: str
    timestamps: list[TimestampEntry] | None
    duration_seconds: float | None
    language: str | None
    created_at: datetime


class DocumentResponse(BaseModel):
    """Full document detail including optional transcription."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str
    original_filename: str
    file_type: FileType
    file_size: int
    status: ProcessingStatus
    error_message: str | None
    summary: str | None
    transcription: TranscriptionResponse | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


# ── Q&A schemas ─────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    """Payload for POST /api/qa/{document_id}/ask."""
    question: str


class SourceChunk(BaseModel):
    """A single retrieved text chunk used to ground the answer."""
    text: str
    score: float
    page: Optional[int] = None


class AnswerResponse(BaseModel):
    """The LLM's answer with provenance chunks."""
    question: str
    answer: str
    source_chunks: list[SourceChunk]
    document_id: int


class SummaryResponse(BaseModel):
    """AI-generated summary of a document."""
    document_id: int
    summary: str
    cached: bool = False


class TimestampsResponse(BaseModel):
    """All timestamps extracted from an audio/video document."""
    document_id: int
    timestamps: list[TimestampEntry]
    duration_seconds: float | None

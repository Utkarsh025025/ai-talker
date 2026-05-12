"""Document and Transcription SQLAlchemy ORM models."""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, Integer, Float, ForeignKey,
    DateTime, Enum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class FileType(str, enum.Enum):
    PDF = "pdf"
    MP3 = "mp3"
    MP4 = "mp4"
    WAV = "wav"
    M4A = "m4a"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Processing
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted content
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FAISS index path (per-document shard)
    faiss_index_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")  # noqa: F821
    transcription: Mapped["Transcription | None"] = relationship(
        "Transcription", back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    qa_sessions: Mapped[list["QASession"]] = relationship(
        "QASession", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.status}>"


class Transcription(Base):
    """Stores Whisper transcription output for audio/video files."""

    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), unique=True, index=True, nullable=False
    )

    full_text: Mapped[str] = mapped_column(Text, nullable=False)

    # List of {"timestamp": float, "topic": str, "text": str} dicts
    timestamps: Mapped[list | None] = mapped_column(JSON, nullable=True)

    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="transcription")

    def __repr__(self) -> str:
        return f"<Transcription id={self.id} doc_id={self.document_id}>"


class QASession(Base):
    """Stores individual Q&A exchanges for a document."""

    __tablename__ = "qa_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Source chunks used for the answer
    source_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="qa_sessions")

    def __repr__(self) -> str:
        return f"<QASession id={self.id} doc_id={self.document_id}>"

"""Tests for document upload, list, detail, summary, and timestamps endpoints."""

import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, FileType, ProcessingStatus, Transcription


pytestmark = pytest.mark.asyncio


def make_pdf_bytes() -> bytes:
    """Return a minimal valid-looking PDF byte string for upload tests."""
    return b"%PDF-1.4 minimal test content"


class TestUpload:
    async def test_upload_pdf_accepted(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.documents._process_document", new_callable=AsyncMock):
            response = await client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", make_pdf_bytes(), "application/pdf")},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "pdf"
        assert data["status"] == "pending"

    async def test_upload_unsupported_type(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("doc.docx", b"data", "application/vnd.openxmlformats")},
        )
        assert response.status_code == 400

    async def test_upload_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", make_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 401


class TestListDocuments:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/documents/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/documents/?page=1&page_size=5", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["page"] == 1
        assert response.json()["page_size"] == 5


class TestGetDocument:
    async def _create_doc(self, db_session: AsyncSession, user_id: int) -> Document:
        doc = Document(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type=FileType.PDF,
            file_size=1000,
            file_path="/tmp/test.pdf",
            status=ProcessingStatus.COMPLETED,
            extracted_text="Hello world PDF content.",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        return doc

    async def test_get_existing_document(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = await self._create_doc(db_session, test_user.id)
        response = await client.get(f"/api/documents/{doc.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == doc.id

    async def test_get_nonexistent_document(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/documents/99999", headers=auth_headers)
        assert response.status_code == 404


class TestSummary:
    async def _create_completed_doc(self, db_session: AsyncSession, user_id: int) -> Document:
        doc = Document(
            user_id=user_id,
            filename="summary.pdf",
            original_filename="summary.pdf",
            file_type=FileType.PDF,
            file_size=2000,
            file_path="/tmp/summary.pdf",
            status=ProcessingStatus.COMPLETED,
            extracted_text="Long document text for summarization testing. " * 20,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        return doc

    async def test_get_summary(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = await self._create_completed_doc(db_session, test_user.id)
        with patch(
            "app.api.documents.LLMService.summarize",
            new_callable=AsyncMock,
            return_value="This is a test summary.",
        ):
            response = await client.get(
                f"/api/documents/{doc.id}/summary", headers=auth_headers
            )
        assert response.status_code == 200
        assert "summary" in response.json()

    async def test_summary_pending_document(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = Document(
            user_id=test_user.id,
            filename="pending.pdf",
            original_filename="pending.pdf",
            file_type=FileType.PDF,
            file_size=100,
            file_path="/tmp/pending.pdf",
            status=ProcessingStatus.PENDING,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        response = await client.get(
            f"/api/documents/{doc.id}/summary", headers=auth_headers
        )
        assert response.status_code == 400


class TestTimestamps:
    async def test_timestamps_pdf_raises_error(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = Document(
            user_id=test_user.id,
            filename="file.pdf",
            original_filename="file.pdf",
            file_type=FileType.PDF,
            file_size=500,
            file_path="/tmp/file.pdf",
            status=ProcessingStatus.COMPLETED,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        response = await client.get(
            f"/api/documents/{doc.id}/timestamps", headers=auth_headers
        )
        assert response.status_code == 400

    async def test_timestamps_audio_with_transcription(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = Document(
            user_id=test_user.id,
            filename="audio.mp3",
            original_filename="audio.mp3",
            file_type=FileType.MP3,
            file_size=5000,
            file_path="/tmp/audio.mp3",
            status=ProcessingStatus.COMPLETED,
        )
        db_session.add(doc)
        await db_session.flush()

        trans = Transcription(
            document_id=doc.id,
            full_text="Hello and welcome.",
            timestamps=[{"timestamp": 0.0, "topic": "Intro", "text": "Hello and welcome."}],
            duration_seconds=60.0,
            language="en",
        )
        db_session.add(trans)
        await db_session.commit()
        await db_session.refresh(doc)

        response = await client.get(
            f"/api/documents/{doc.id}/timestamps", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["timestamps"]) == 1
        assert data["timestamps"][0]["topic"] == "Intro"

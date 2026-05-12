"""Tests for Q&A endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, FileType, ProcessingStatus
from app.schemas.document import AnswerResponse, SourceChunk


pytestmark = pytest.mark.asyncio

MOCK_ANSWER = AnswerResponse(
    question="What is this about?",
    answer="This document is about testing.",
    source_chunks=[SourceChunk(text="Test content here.", score=0.95)],
    document_id=1,
)


class TestAskQuestion:
    async def _create_completed_doc(self, db_session: AsyncSession, user_id: int) -> Document:
        doc = Document(
            user_id=user_id,
            filename="qa_test.pdf",
            original_filename="qa_test.pdf",
            file_type=FileType.PDF,
            file_size=1000,
            file_path="/tmp/qa_test.pdf",
            status=ProcessingStatus.COMPLETED,
            extracted_text="This is test content for question answering.",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        return doc

    async def test_ask_question_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = await self._create_completed_doc(db_session, test_user.id)
        mock_answer = AnswerResponse(
            question="What is this about?",
            answer="This document is about testing.",
            source_chunks=[SourceChunk(text="Test content.", score=0.9)],
            document_id=doc.id,
        )

        with patch(
            "app.api.qa.LLMService.answer_question",
            new_callable=AsyncMock,
            return_value=mock_answer,
        ):
            response = await client.post(
                f"/api/qa/{doc.id}/ask",
                headers=auth_headers,
                json={"question": "What is this about?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This document is about testing."
        assert "source_chunks" in data

    async def test_ask_question_pending_document(
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

        response = await client.post(
            f"/api/qa/{doc.id}/ask",
            headers=auth_headers,
            json={"question": "What is this?"},
        )
        assert response.status_code == 400

    async def test_ask_question_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/qa/99999/ask",
            headers=auth_headers,
            json={"question": "test"},
        )
        assert response.status_code == 404

    async def test_ask_question_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/qa/1/ask", json={"question": "test"})
        assert response.status_code == 401


class TestQAHistory:
    async def test_history_empty(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        doc = Document(
            user_id=test_user.id,
            filename="hist.pdf",
            original_filename="hist.pdf",
            file_type=FileType.PDF,
            file_size=100,
            file_path="/tmp/hist.pdf",
            status=ProcessingStatus.COMPLETED,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        response = await client.get(
            f"/api/qa/{doc.id}/history", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_history_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/qa/99999/history", headers=auth_headers)
        assert response.status_code == 404

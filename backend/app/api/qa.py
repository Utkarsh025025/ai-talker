"""
Q&A API router — ask questions about uploaded documents.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.redis_client import cache_get, cache_set, is_rate_limited
from app.models.document import Document, QASession, ProcessingStatus
from app.schemas.document import QuestionRequest, AnswerResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/qa", tags=["Q&A"])


@router.post("/{document_id}/ask", response_model=AnswerResponse)
async def ask_question(
    document_id: int,
    payload: QuestionRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about a document.

    The answer is grounded in semantically retrieved chunks (RAG).
    Answers are cached in Redis for 1 hour to reduce API costs.
    """
    if await is_rate_limited(f"qa:{user_id}"):
        raise HTTPException(status_code=429, detail="Q&A rate limit exceeded. Please slow down.")

    # Verify document ownership and processing status
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready. Current status: {doc.status.value}",
        )

    # Check Redis cache (keyed by document + question)
    cache_key = f"qa:{document_id}:{hash(payload.question)}"
    cached = await cache_get(cache_key)
    if cached:
        return AnswerResponse(**cached)

    # Run RAG-based Q&A
    answer = await LLMService.answer_question(
        document_id=document_id,
        question=payload.question,
        full_text=doc.extracted_text,
    )

    # Persist Q&A exchange to DB
    session = QASession(
        document_id=document_id,
        user_id=user_id,
        question=payload.question,
        answer=answer.answer,
        source_chunks=[c.model_dump() for c in answer.source_chunks],
    )
    db.add(session)
    await db.commit()

    # Cache result for 1 hour
    await cache_set(cache_key, answer.model_dump(), ttl=3600)

    return answer


@router.get("/{document_id}/history")
async def get_qa_history(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return past Q&A sessions for a document."""
    # Verify ownership
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found.")

    sessions_result = await db.execute(
        select(QASession)
        .where(QASession.document_id == document_id, QASession.user_id == user_id)
        .order_by(QASession.created_at.desc())
        .limit(50)
    )
    sessions = sessions_result.scalars().all()

    return [
        {
            "id": s.id,
            "question": s.question,
            "answer": s.answer,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]

"""
Groq-powered LLM service: Q&A over retrieved chunks and document summarisation.
Uses the Groq async client (OpenAI-compatible API surface).
"""

import asyncio
from groq import AsyncGroq
from app.config import get_settings
from app.services.vector_store import VectorStoreService
from app.schemas.document import AnswerResponse, SourceChunk, SummaryResponse

settings = get_settings()

# Shared async Groq client
_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


class LLMService:
    """High-level AI operations: answer questions and generate summaries."""

    # ── Q&A ─────────────────────────────────────────────────────────────────────

    @staticmethod
    async def answer_question(
        document_id: int,
        question: str,
        full_text: str | None = None,
    ) -> AnswerResponse:
        """
        Retrieve relevant chunks from FAISS and use Groq's LLM to answer the
        question (Retrieval-Augmented Generation).

        Args:
            document_id: The DB id of the document.
            question:    The user's natural-language question.
            full_text:   Optional raw text (fallback when no FAISS index exists).
        """
        # Retrieve top-k semantically similar chunks
        try:
            chunks = await VectorStoreService.similarity_search(document_id, question)
        except FileNotFoundError:
            # No vector index yet — fall back to raw truncated text
            chunks = [{"text": (full_text or "")[:4000], "score": 1.0, "chunk_id": 0}]

        context_parts = [f"[Source {i + 1}]:\n{c['text']}" for i, c in enumerate(chunks)]
        context = "\n\n".join(context_parts)

        system_prompt = (
            "You are an expert document assistant. Answer the user's question based ONLY on the "
            "provided context. If the answer is not in the context, say so clearly. "
            "Be concise, accurate, and cite the source numbers when relevant."
        )

        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"

        response = await _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        answer_text = response.choices[0].message.content or ""

        source_chunks = [
            SourceChunk(text=c["text"], score=c["score"])
            for c in chunks
        ]

        return AnswerResponse(
            question=question,
            answer=answer_text,
            source_chunks=source_chunks,
            document_id=document_id,
        )

    # ── Summarisation ────────────────────────────────────────────────────────────

    @staticmethod
    async def summarize(document_id: int, text: str) -> str:
        """
        Generate a structured summary of the document text.

        For long documents a map-reduce strategy is used:
        each chunk is summarised independently, then all partial summaries
        are combined into a single cohesive summary.
        """
        # Groq context windows are large, but we chunk conservatively (~12 000 chars)
        max_chunk = 3000 * 4  # ~4 chars per token
        parts = [text[i: i + max_chunk] for i in range(0, len(text), max_chunk)]

        if len(parts) == 1:
            # Short document — single LLM call
            return await LLMService._summarize_chunk(parts[0])

        # Map: summarise each part concurrently (Groq is very fast)
        chunk_summaries = await asyncio.gather(
            *[LLMService._summarize_chunk(part) for part in parts[:10]]  # cap at 10 chunks
        )

        # Reduce: combine the partial summaries into one
        combined = "\n\n".join(chunk_summaries)
        return await LLMService._summarize_chunk(
            combined,
            instruction="Combine these partial summaries into one cohesive, well-structured summary.",
        )

    @staticmethod
    async def _summarize_chunk(text: str, instruction: str | None = None) -> str:
        """Internal: summarise a single text chunk using Groq."""
        system_prompt = instruction or (
            "You are a summarisation assistant. Produce a clear, well-structured summary "
            "with key points, main themes, and important details. Use markdown bullet points."
        )

        response = await _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            max_tokens=800,
        )

        return response.choices[0].message.content or ""

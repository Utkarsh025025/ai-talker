"""
FAISS vector store service.
Splits text into chunks, embeds them with a local HuggingFace sentence-transformers
model (no API key required), and stores/loads per-document FAISS indexes on disk.

Groq does not provide an embeddings API, so we use sentence-transformers locally.
The default model is 'all-MiniLM-L6-v2' — tiny (22 MB), fast, and high quality.
"""

import asyncio
import shutil
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LCDocument
from app.config import get_settings

settings = get_settings()

# ── Shared singletons (initialised once at import time) ────────────────────────

# HuggingFaceEmbeddings wraps sentence-transformers.
# The underlying model is loaded lazily on first embed call.
_embeddings = HuggingFaceEmbeddings(
    model_name=settings.EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True, "batch_size": 64},
)

_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    length_function=len,
)


def warmup_embeddings() -> None:
    """
    Force-load the sentence-transformers model into memory by running a
    dummy embedding. Call this once at server startup so the first real
    document upload does not pay the model-load penalty.
    """
    _embeddings.embed_query("warmup")


class VectorStoreService:
    """Manages per-document FAISS indexes backed by local embeddings."""

    @staticmethod
    def _index_path(document_id: int) -> Path:
        """Return the directory where a document's FAISS index is stored."""
        return Path(settings.FAISS_INDEX_DIR) / str(document_id)

    @staticmethod
    async def build_index(document_id: int, text: str) -> str:
        """
        Chunk `text`, compute local embeddings in one batched call,
        and persist the FAISS index.

        Returns the path to the saved index directory.
        """
        index_dir = VectorStoreService._index_path(document_id)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Split into overlapping chunks
        chunks = _text_splitter.split_text(text)
        if not chunks:
            raise ValueError("No text chunks produced — document may be empty.")

        # Wrap as LangChain Documents with metadata
        lc_docs = [
            LCDocument(
                page_content=chunk,
                metadata={"chunk_id": i, "document_id": document_id},
            )
            for i, chunk in enumerate(chunks)
        ]

        # Build FAISS index in a thread (CPU-bound sentence-transformers inference).
        # All chunks are embedded in ONE batched call — much faster than per-chunk.
        loop = asyncio.get_running_loop()
        vector_store = await loop.run_in_executor(
            None, lambda: FAISS.from_documents(lc_docs, _embeddings)
        )

        # Persist index to disk
        vector_store.save_local(str(index_dir))
        return str(index_dir)

    @staticmethod
    async def similarity_search(
        document_id: int,
        query: str,
        top_k: int = settings.RETRIEVAL_TOP_K,
    ) -> list[dict]:
        """
        Search the FAISS index for `document_id` and return the top-k
        most similar chunks with their similarity scores.

        Returns list of {"text": str, "score": float, "chunk_id": int}.
        """
        index_dir = VectorStoreService._index_path(document_id)
        if not index_dir.exists():
            raise FileNotFoundError(f"No FAISS index found for document {document_id}.")

        loop = asyncio.get_running_loop()
        vector_store: FAISS = await loop.run_in_executor(
            None,
            lambda: FAISS.load_local(
                str(index_dir),
                _embeddings,
                allow_dangerous_deserialization=True,
            ),
        )

        results = await loop.run_in_executor(
            None,
            lambda: vector_store.similarity_search_with_score(query, k=top_k),
        )

        return [
            {
                "text": doc.page_content,
                "score": float(score),
                "chunk_id": doc.metadata.get("chunk_id"),
            }
            for doc, score in results
        ]

    @staticmethod
    def delete_index(document_id: int) -> None:
        """Remove a document's FAISS index from disk."""
        index_dir = VectorStoreService._index_path(document_id)
        if index_dir.exists():
            shutil.rmtree(str(index_dir))


"""
Application configuration using Pydantic BaseSettings.
All values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────
    APP_NAME: str = "AI Talker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Groq ───────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    # Chat / completion model — defaults to Llama 3.3 70B (fast & capable on Groq)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Groq Whisper model for audio/video transcription
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"
    # Local sentence-transformers model used for FAISS embeddings (no API key needed)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@db:5432/aitalker

    # ── PostgreSQL (legacy — used by docker-compose for local DB) ────
    POSTGRES_USER: str = "aitalker"
    POSTGRES_PASSWORD: str = "aitalker_secret"
    POSTGRES_DB: str = "aitalker"

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str  # e.g. redis://redis:6379/0

    # ── JWT ────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File Storage ───────────────────────────────────────────────
    UPLOAD_DIR: str = "/app/uploads"
    FAISS_INDEX_DIR: str = "/app/faiss_indexes"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: list[str] = [".pdf", ".mp3", ".mp4", ".wav", ".m4a"]

    # ── Rate Limiting ──────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60       # requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # window size in seconds

    # ── Vector Store ───────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()

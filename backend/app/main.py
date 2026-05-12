"""
FastAPI application entry point.
Registers routers, startup/shutdown hooks, middleware, and static file serving.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.database import create_tables
from app.core.redis_client import get_redis, close_redis
from app.services.vector_store import warmup_embeddings
from app.api import auth, documents, qa

settings = get_settings()


# ── Lifespan ────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # Ensure upload / faiss directories exist
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.FAISS_INDEX_DIR).mkdir(parents=True, exist_ok=True)

    # Initialise database tables
    await create_tables()

    # Warm-up Redis connection
    await get_redis()

    # Pre-load the sentence-transformers embedding model into memory.
    # This runs once at startup so the first document upload is fast
    # (avoids 15-30s model-load penalty on first use).
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, warmup_embeddings)

    yield  # <── application runs

    # Graceful shutdown
    await close_redis()


# ── App instance ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Document & Multimedia Q&A API",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON error for unhandled exceptions in debug mode."""
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


# ── Routers ──────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(qa.router)


# ── Health check ─────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "version": settings.APP_VERSION}


# ── __init__ shims ────────────────────────────────────────────────────────────────
# Keep the api package importable

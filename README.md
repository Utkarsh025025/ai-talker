# AI Talker 🧠

> **AI-powered Document & Multimedia Q&A Platform**
> Upload PDFs, audio, and video — get instant AI summaries, ask questions, and jump to timestamped topics.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **PDF Q&A** | Upload PDFs, extract text with PyMuPDF/pdfplumber, and ask questions using RAG |
| 🎙️ **Audio/Video Transcription** | Groq Whisper API transcribes MP3, MP4, WAV files at high speed |
| ⏱️ **Timestamped Topics** | Groq LLM extracts major topics and maps them to exact timestamps |
| 🔍 **Semantic Search** | FAISS + local sentence-transformers embeddings (no API key for embeddings) |
| 📝 **AI Summaries** | Map-reduce summarization using Groq Llama 3 models |
| 💬 **Chatbot UI** | Streaming-style Q&A with source citations |
| 🔐 **JWT Auth** | Secure register/login with access + refresh token rotation |
| ⚡ **Redis Caching** | Q&A and summary results cached; sliding-window rate limiting |
| 🐘 **PostgreSQL** | Stores users, documents, transcriptions, Q&A sessions |

---

## 🗂️ Project Structure

```
Ai Talker/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, documents, qa)
│   │   ├── core/         # DB, Redis, JWT security
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # PDF, Whisper, FAISS, LLM services
│   │   ├── config.py     # Pydantic-settings config
│   │   └── main.py       # FastAPI app entry point
│   ├── tests/            # Pytest test suite (95%+ coverage)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # DropZone, ChatBot, SummaryPanel, TimestampPanel, DocumentList
│   │   ├── contexts/     # AuthContext
│   │   ├── pages/        # AuthPage, DashboardPage
│   │   ├── services/     # Axios API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** ≥ 24 & **Docker Compose** ≥ 2
- A **Groq API key** — get one free at [console.groq.com](https://console.groq.com)
  - Used for chat completions (Llama 3) and Whisper audio transcription
  - Embeddings run **locally** via sentence-transformers — no additional API key needed

### 1. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY and JWT_SECRET (minimum required)
```

Generate a secure JWT secret:
```bash
openssl rand -hex 32
```

### 2. Launch all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (React) | http://localhost |
| Backend API docs | http://localhost:8000/api/docs |
| ReDoc | http://localhost:8000/api/redoc |

---

## 🔧 Local Development (without Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env with your values (point DATABASE_URL to local Postgres)

# Run the FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`.

---

## 🧪 Running Tests

```bash
cd backend

# Run all tests with coverage report
pytest

# Run only a specific test file
pytest tests/test_auth.py -v

# Generate HTML coverage report
pytest --cov-report=html
# Open htmlcov/index.html in your browser
```

Target: **≥ 95% coverage** (enforced by `pytest.ini`).

---

## 🗄️ Database Migrations

The app auto-creates all tables on startup via `create_tables()`.
For production schema changes, use **Alembic**:

```bash
cd backend

# Initialize Alembic (first time only)
alembic init alembic

# Generate a migration
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head
```

---

## 📡 API Reference

All endpoints are documented interactively at **`/api/docs`** (Swagger UI).

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create account → returns JWT pair |
| `POST` | `/api/auth/login` | Login → returns JWT pair |
| `POST` | `/api/auth/refresh` | Exchange refresh token → new JWT pair |
| `GET` | `/api/auth/me` | Get current user profile |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload PDF/MP3/MP4/WAV |
| `GET` | `/api/documents/` | List user's documents (paginated) |
| `GET` | `/api/documents/{id}` | Get document detail |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `GET` | `/api/documents/{id}/summary` | Get AI summary |
| `GET` | `/api/documents/{id}/timestamps` | Get topic timestamps (audio/video) |

### Q&A

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/qa/{id}/ask` | Ask a question about a document |
| `GET` | `/api/qa/{id}/history` | Get Q&A history for a document |

### Request / Response examples

**Upload a file:**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/document.pdf"
```

**Ask a question:**
```bash
curl -X POST http://localhost:8000/api/qa/1/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main theme?"}'
```

---

## 🌍 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API key |
| `JWT_SECRET` | ✅ | — | JWT signing secret (32+ random bytes) |
| `DATABASE_URL` | ✅ | — | Async PostgreSQL DSN |
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `POSTGRES_USER` | Docker only | `aitalker` | DB username |
| `POSTGRES_PASSWORD` | Docker only | `aitalker_secret` | DB password |
| `POSTGRES_DB` | Docker only | `aitalker` | Database name |
| `DEBUG` | ❌ | `false` | Enable debug logging |
| `GROQ_MODEL` | ❌ | `llama-3.3-70b-versatile` | Groq chat model |
| `GROQ_WHISPER_MODEL` | ❌ | `whisper-large-v3-turbo` | Groq Whisper model |
| `EMBEDDING_MODEL` | ❌ | `all-MiniLM-L6-v2` | Local sentence-transformers model |
| `MAX_UPLOAD_SIZE_MB` | ❌ | `100` | Max file size |
| `RETRIEVAL_TOP_K` | ❌ | `5` | Chunks retrieved per query |
| `RATE_LIMIT_REQUESTS` | ❌ | `60` | Requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | ❌ | `60` | Rate limit window |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | Refresh token TTL |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (React)                     │
│  DropZone → DocumentList → ChatBot → TimestampPanel      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / REST
┌──────────────────────────▼──────────────────────────────┐
│              FastAPI Backend (Python 3.12)               │
│  /api/auth  /api/documents  /api/qa                      │
│                                                          │
│  ┌──────────┐  ┌───────────────────────────────────┐   │
│  │PDFService│  │  WhisperService (Groq Whisper API) │   │
│  │ PyMuPDF  │  │  whisper-large-v3-turbo            │   │
│  └──────────┘  └───────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────┐  ┌──────────────────────────┐ │
│  │   LLMService (RAG)  │  │  FAISS Index (per-doc)   │ │
│  │ Groq Llama 3.3 70B  │  │  Stored on disk          │ │
│  └─────────────────────┘  └──────────────────────────┘ │
│                                                          │
│  ┌────────────────────┐  sentence-transformers           │
│  │  VectorStoreService│  all-MiniLM-L6-v2 (local CPU)   │
│  │  Local Embeddings  │  No API key required             │
│  └────────────────────┘                                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────────────────────────┐ │
│  │  PostgreSQL  │  │  Redis (cache + rate limiting)   │ │
│  │  (SQLAlchemy)│  └──────────────────────────────────┘ │
│  └──────────────┘                                        │
└──────────────────────────────────────────────────────────┘
```

---

## 🛡️ Security Notes

- All endpoints (except `/api/auth/*` and `/api/health`) require a valid JWT Bearer token.
- Passwords are bcrypt-hashed with a cost factor of 12.
- JWT tokens have a short access TTL (default 60 min) and are rotated on refresh.
- Redis sliding-window rate limiting protects login, register, upload, and Q&A endpoints.
- Files are stored under a per-user UUID directory to prevent path traversal.

---

## 📄 License

MIT — free for personal and commercial use.
#   a i - t a l k e r  
 
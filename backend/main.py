"""
Support Knowledge Claw — FastAPI Application Entry Point

An Autonomous AI Agent that handles support queries from Eko's
micro-entrepreneur retailers using RAG, intent classification,
confidence evaluation, and intelligent escalation.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings
from backend.database import init_db
from backend.knowledge.ingestion import ingest_directory
from backend.knowledge.store import get_document_count
from backend.routers import chat, admin, knowledge

# ── Logging ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("claw")


# ── Lifespan ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  Support Knowledge Claw — Starting Up")
    logger.info("=" * 60)

    # 1. Validate API key
    if not settings.groq_api_key or settings.groq_api_key.startswith("gsk_your"):
        logger.error("❌ GROQ_API_KEY is not set! Get a free key at https://console.groq.com")
        logger.error("   Copy .env.example to .env and add your key")
    else:
        logger.info("✅ Groq API key configured")

    # 2. Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # 3. Auto-ingest knowledge base if empty
    doc_count = get_document_count()
    if doc_count == 0:
        logger.info("📚 Knowledge base is empty — auto-ingesting documents...")
        result = ingest_directory()
        if result.get("status") == "success":
            logger.info(f"✅ Ingested {result['total_chunks']} chunks from {result['files_processed']} files")
        else:
            logger.warning(f"⚠️  Knowledge ingestion: {result.get('message', 'unknown issue')}")
    else:
        logger.info(f"✅ Knowledge base ready ({doc_count} chunks)")

    logger.info("=" * 60)
    logger.info(f"  🚀 Server running at http://localhost:{settings.port}")
    logger.info(f"  📖 API docs at http://localhost:{settings.port}/docs")
    logger.info(f"  💬 Chat UI at http://localhost:{settings.port}")
    logger.info(f"  📊 Admin at http://localhost:{settings.port}/admin")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down Support Knowledge Claw...")


# ── App ───────────────────────────────────────────────

app = FastAPI(
    title="Support Knowledge Claw",
    description=(
        "Autonomous AI Support Agent for Eko Micro-Entrepreneurs. "
        "Classifies queries, retrieves knowledge, generates responses, "
        "evaluates confidence, and escalates when needed."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS — Maximum Compatibility ─────────────────────
# Serves frontend from same origin to avoid CORS entirely,
# but also allows all external origins for API consumers.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Belt-and-suspenders: add CORS headers to every response
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# Handle preflight OPTIONS requests explicitly
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


# ── Routers ───────────────────────────────────────────

app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(knowledge.router)


# ── Health Check ──────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    doc_count = get_document_count()
    return {
        "status": "healthy",
        "service": "Support Knowledge Claw",
        "version": "1.0.0",
        "knowledge_base": {"chunks": doc_count, "status": "ready" if doc_count > 0 else "empty"},
        "llm": {"provider": "groq", "model": settings.groq_model},
    }


# ── Static Files & Frontend ──────────────────────────
# Serve the frontend from the same origin (no CORS issues!)

frontend_dir = Path(settings.frontend_dir)
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/admin")
async def admin_page():
    """Serve the admin dashboard."""
    admin_path = frontend_dir / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    return JSONResponse({"error": "Admin page not found"}, status_code=404)


@app.get("/")
async def root():
    """Serve the chat interface."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({
        "service": "Support Knowledge Claw",
        "docs": "/docs",
        "health": "/api/health",
    })


# ── Run ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )

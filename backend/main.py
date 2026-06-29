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
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

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
    docs_url=None,
    redoc_url=None,
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


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve customized Swagger UI."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Support Knowledge Claw - API Docs</title>
    <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        body {{ background: #121212; color: #f5f5f5; font-family: 'Outfit', sans-serif; }}
        .swagger-ui {{ font-family: 'Outfit', sans-serif; color: #f5f5f5; }}
        .swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info h3, .swagger-ui .info h4, .swagger-ui .info h5 {{ color: #D4C3A3; font-family: 'Playfair Display', serif; }}
        .swagger-ui .info .title {{ color: #D4C3A3; }}
        .swagger-ui p, .swagger-ui li, .swagger-ui table {{ color: #cccccc; }}
        .swagger-ui .info p {{ color: #cccccc; }}
        .swagger-ui .info a {{ color: #E8DCC4; }}
        .swagger-ui .scheme-container {{ background: #1a1a1a; box-shadow: none; border-bottom: 1px solid rgba(212,195,163,0.15); }}
        .swagger-ui .opblock-tag {{ color: #E8DCC4; font-family: 'Playfair Display', serif; font-size: 1.5rem; border-bottom-color: rgba(212,195,163,0.15); }}
        .swagger-ui .opblock {{ border: 1px solid rgba(212,195,163,0.15); background: rgba(26,26,26,0.7); box-shadow: none; border-radius: 12px; }}
        .swagger-ui .opblock .opblock-summary {{ border-bottom-color: rgba(212,195,163,0.15); }}
        .swagger-ui .opblock .opblock-summary-operation-id, .swagger-ui .opblock .opblock-summary-path, .swagger-ui .opblock .opblock-summary-path__deprecated {{ color: #f5f5f5; }}
        .swagger-ui .opblock .opblock-summary-description {{ color: #cccccc; }}
        .swagger-ui .opblock.opblock-post {{ border-color: rgba(212,195,163,0.4); background: rgba(212,195,163,0.05); }}
        .swagger-ui .opblock.opblock-get {{ border-color: rgba(212,195,163,0.4); background: rgba(212,195,163,0.05); }}
        .swagger-ui .opblock.opblock-post .opblock-summary-method {{ background: #D4C3A3; color: #121212; border-radius: 6px; }}
        .swagger-ui .opblock.opblock-get .opblock-summary-method {{ background: #B5A382; color: #121212; border-radius: 6px; }}
        .swagger-ui .btn {{ border-color: #D4C3A3; color: #D4C3A3; background: transparent; font-family: 'Outfit', sans-serif; border-radius: 8px; }}
        .swagger-ui .btn:hover {{ background: #D4C3A3; color: #121212; }}
        .swagger-ui .opblock-body pre.microlight {{ background: #222222 !important; color: #E8DCC4 !important; border-radius: 8px; }}
        .swagger-ui .parameter__name, .swagger-ui .parameter__type {{ color: #f5f5f5; }}
        .swagger-ui .parameter__in, .swagger-ui .parameter__extension {{ color: #888888; }}
        .swagger-ui table thead tr td, .swagger-ui table thead tr th {{ color: #D4C3A3; border-bottom: 1px solid rgba(212,195,163,0.15); }}
        .swagger-ui .response-col_status, .swagger-ui .response-col_description {{ color: #f5f5f5; }}
        .swagger-ui .responses-inner h4, .swagger-ui .responses-inner h5 {{ color: #D4C3A3; }}
        .swagger-ui .opblock-body .opblock-section .opblock-section-header {{ background: #1a1a1a; border-color: rgba(212,195,163,0.15); }}
        .swagger-ui .opblock-body .opblock-section .opblock-section-header h4 {{ color: #D4C3A3; }}
        .swagger-ui label {{ color: #f5f5f5; font-family: 'Outfit', sans-serif; }}
        .swagger-ui .tab li {{ color: #cccccc; }}
        .swagger-ui .tab li.active {{ border-color: #D4C3A3; color: #f5f5f5; }}
        .swagger-ui input[type=text], .swagger-ui input[type=password], .swagger-ui input[type=search], .swagger-ui input[type=email], .swagger-ui input[type=file], .swagger-ui textarea {{ background: #222222; border-color: rgba(212,195,163,0.3); color: #f5f5f5; border-radius: 6px; }}
        .swagger-ui select {{ background: #222222; border-color: rgba(212,195,163,0.3); color: #f5f5f5; border-radius: 6px; }}
        .swagger-ui .models {{ border-color: rgba(212,195,163,0.15); background: rgba(26,26,26,0.7); border-radius: 12px; }}
        .swagger-ui .models h4 {{ color: #D4C3A3; font-family: 'Playfair Display', serif; border-bottom-color: rgba(212,195,163,0.15); }}
        .swagger-ui .model-title {{ color: #f5f5f5; font-family: 'Outfit', sans-serif; background: transparent !important; }}
        .swagger-ui .model-box-control {{ background: transparent !important; color: #f5f5f5 !important; }}
        .swagger-ui .model-toggle {{ background: transparent !important; color: #D4C3A3 !important; }}
        .swagger-ui .model-toggle::after {{ filter: invert(1); }}
        .swagger-ui .model {{ color: #cccccc; }}
        .swagger-ui .prop-type {{ color: #E8DCC4; }}
        .swagger-ui .prop-format {{ color: #888888; }}
        .swagger-ui svg {{ fill: #E8DCC4; }}
        .swagger-ui .model-box {{ background: #1a1a1a; border-radius: 8px; }}
        .swagger-ui section.models .model-container {{ background: rgba(26,26,26,0.7); }}
        .swagger-ui .topbar {{ display: none; }}
    </style>
    </head>
    <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    window.onload = function() {{
        SwaggerUIBundle({{
            url: "{app.openapi_url}",
            dom_id: '#swagger-ui',
        }})
    }}
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


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

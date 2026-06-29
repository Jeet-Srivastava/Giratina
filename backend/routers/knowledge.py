"""
Knowledge management API endpoints.
Ingest documents, search the knowledge base, list documents.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter

from backend.models import KnowledgeSearchRequest, KnowledgeSearchResult, RetrievedContext
from backend.knowledge.ingestion import ingest_directory
from backend.knowledge.store import get_document_count, search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


@router.post("/ingest")
async def ingest_knowledge(reset: bool = False):
    """Ingest knowledge base documents from the data directory."""
    result = await asyncio.to_thread(ingest_directory, None, reset)
    return result


@router.post("/search", response_model=KnowledgeSearchResult)
async def search_knowledge(request: KnowledgeSearchRequest):
    """Search the knowledge base for testing and debugging."""
    results = await asyncio.to_thread(search, request.query, request.top_k)

    contexts = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        similarity = max(0.0, 1.0 - (dist / 2.0))
        contexts.append(RetrievedContext(
            content=doc,
            source=meta.get("source", "unknown"),
            relevance_score=round(similarity, 3),
        ))

    return KnowledgeSearchResult(
        query=request.query,
        results=contexts,
        total_documents=get_document_count(),
    )


@router.get("/status")
async def knowledge_status():
    """Get knowledge base status."""
    count = get_document_count()
    return {
        "status": "ready" if count > 0 else "empty",
        "total_chunks": count,
        "message": f"{count} document chunks indexed" if count > 0 else "No documents indexed. Run POST /api/knowledge/ingest",
    }

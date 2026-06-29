"""
RAG context retrieval node.
Queries ChromaDB for relevant knowledge base chunks.
"""

from __future__ import annotations

import time
import logging

from backend.agent.state import AgentState
from backend.knowledge.store import get_vector_store

logger = logging.getLogger(__name__)


def retrieve_context(state: AgentState) -> dict:
    """Retrieve relevant context from the knowledge base using RAG."""
    start = time.time()
    query = state["query"]
    product_area = state.get("product_area", "general")

    try:
        store = get_vector_store()

        # Query with optional metadata filtering
        where_filter = None
        if product_area and product_area not in ("general", "unknown"):
            where_filter = {"product_area": product_area}

        # Try filtered search first
        query_args = {"query_texts": [query], "n_results": 5}
        if where_filter:
            query_args["where"] = where_filter
        results = store.query(**query_args)

        # If filtered search returns too few results, do unfiltered search
        if not results or len(results.get("documents", [[]])[0]) < 2:
            results = store.query(query_texts=[query], n_results=5)

        # Parse results
        contexts = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB returns distances (lower = more similar)
            # Convert to similarity score (0-1 range)
            similarity = max(0.0, 1.0 - (dist / 2.0))
            contexts.append({
                "content": doc,
                "source": meta.get("source", "unknown"),
                "relevance_score": round(similarity, 3),
            })

        duration = int((time.time() - start) * 1000)
        logger.info(f"Retrieved {len(contexts)} contexts (filtered by {product_area})")

        return {
            "retrieved_contexts": contexts,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Knowledge Retrieval", "result": f"{len(contexts)} chunks found", "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        duration = int((time.time() - start) * 1000)
        return {
            "retrieved_contexts": [],
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Knowledge Retrieval", "result": f"failed: {str(e)[:80]}", "duration_ms": duration}
            ],
        }

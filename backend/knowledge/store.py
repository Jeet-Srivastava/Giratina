"""
ChromaDB vector store wrapper.
Manages the knowledge base vector storage for RAG retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb

from backend.config import settings

logger = logging.getLogger(__name__)

# Module-level store instance
_collection = None
_client = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB client."""
    global _client
    if _client is None:
        persist_dir = settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"ChromaDB initialized at: {persist_dir}")
    return _client


def get_vector_store():
    """Get or create the knowledge base collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name="eko_knowledge_base",
            metadata={"description": "Eko support knowledge base for micro-entrepreneurs"},
        )
        logger.info(f"Collection 'eko_knowledge_base' ready. Documents: {_collection.count()}")
    return _collection


def add_documents(
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> int:
    """Add documents to the vector store."""
    collection = get_vector_store()
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    count = collection.count()
    logger.info(f"Added {len(documents)} documents. Total: {count}")
    return count


def search(query: str, n_results: int = 5, where: dict | None = None) -> dict:
    """Search the vector store."""
    collection = get_vector_store()
    kwargs = {"query_texts": [query], "n_results": n_results}
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def get_document_count() -> int:
    """Get the total number of documents in the store."""
    collection = get_vector_store()
    return collection.count()


def reset_store() -> None:
    """Delete and recreate the collection."""
    global _collection
    client = get_chroma_client()
    try:
        client.delete_collection("eko_knowledge_base")
    except Exception:
        pass
    _collection = None
    logger.info("Vector store reset.")

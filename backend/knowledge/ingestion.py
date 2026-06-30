"""
Knowledge base document ingestion.
Loads markdown documents, chunks them, and stores in ChromaDB.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from backend.knowledge.store import add_documents, reset_store, get_document_count
from backend.config import settings

logger = logging.getLogger(__name__)

# Chunking config
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 80      # overlapping characters between chunks

# Map filenames to product areas for metadata
PRODUCT_AREA_MAP = {
    "aeps": "aeps",
    "dmt": "money_transfer",
    "money_transfer": "money_transfer",
    "bill_payment": "bill_payment",
    "recharge": "recharge",
    "commission": "commission",
    "settlement": "commission",
    "kyc": "account",
    "wallet": "account",
    "block": "account",
    "account": "account",
    "activation": "account",
    "csp": "general",
    "escalation": "general",
    "general": "general",
    "faq": "general",
    "security": "security",
}


def _detect_product_area(filename: str) -> str:
    """Detect product area from filename."""
    name_lower = filename.lower()
    for key, area in PRODUCT_AREA_MAP.items():
        if key in name_lower:
            return area
    return "general"


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    # Split by double newlines (paragraphs) first
    paragraphs = re.split(r"\n\n+", text.strip())

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph would exceed chunk_size, save current and start new
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from the end of the current chunk
            if overlap > 0:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _make_id(source: str, index: int) -> str:
    """Create a deterministic document ID."""
    raw = f"{source}:{index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_directory(directory: str | None = None, reset: bool = False) -> dict:
    """
    Ingest all markdown files from a directory into the vector store.

    Args:
        directory: Path to directory containing .md files. Defaults to settings.knowledge_base_dir.
        reset: If True, clear the existing store before ingesting.

    Returns:
        Dict with ingestion stats.
    """
    kb_dir = Path(directory or settings.knowledge_base_dir)

    if not kb_dir.exists():
        logger.warning(f"Knowledge base directory not found: {kb_dir}")
        return {"status": "error", "message": f"Directory not found: {kb_dir}"}

    if reset:
        reset_store()
        logger.info("Reset vector store before ingestion.")

    md_files = sorted(kb_dir.glob("*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in: {kb_dir}")
        return {"status": "error", "message": "No .md files found"}

    total_chunks = 0
    file_stats = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        product_area = _detect_product_area(md_file.stem)
        chunks = _chunk_text(content)

        if not chunks:
            continue

        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            doc_id = _make_id(md_file.name, i)
            documents.append(chunk)
            metadatas.append({
                "source": md_file.name,
                "product_area": product_area,
                "chunk_index": i,
            })
            ids.append(doc_id)

        add_documents(documents=documents, metadatas=metadatas, ids=ids)
        total_chunks += len(chunks)
        file_stats.append({"file": md_file.name, "chunks": len(chunks), "product_area": product_area})
        logger.info(f"Ingested {md_file.name}: {len(chunks)} chunks (area: {product_area})")

    result = {
        "status": "success",
        "files_processed": len(file_stats),
        "total_chunks": total_chunks,
        "total_documents": get_document_count(),
        "files": file_stats,
    }
    logger.info(f"Ingestion complete: {total_chunks} chunks from {len(file_stats)} files")
    return result

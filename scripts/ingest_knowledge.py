#!/usr/bin/env python3
"""
Knowledge Base Ingestion Script.
Run this to load documents into ChromaDB before starting the server.
Usage: python -m scripts.ingest_knowledge
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.knowledge.ingestion import ingest_directory


def main():
    print("=" * 50)
    print("  Support Knowledge Claw — Knowledge Ingestion")
    print("=" * 50)

    result = ingest_directory(reset=True)

    if result["status"] == "success":
        print(f"\n✅ Ingestion complete!")
        print(f"   Files processed: {result['files_processed']}")
        print(f"   Total chunks:    {result['total_chunks']}")
        print(f"\n   Files:")
        for f in result["files"]:
            print(f"     📄 {f['file']}: {f['chunks']} chunks ({f['product_area']})")
    else:
        print(f"\n❌ Error: {result.get('message', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

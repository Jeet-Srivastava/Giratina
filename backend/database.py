"""
Async SQLite database setup and operations.
Uses aiosqlite for non-blocking database access.
"""

from __future__ import annotations

import aiosqlite
from pathlib import Path

from backend.config import settings

DB_PATH = settings.database_path


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                intent TEXT NOT NULL DEFAULT 'unknown',
                urgency TEXT NOT NULL DEFAULT 'low',
                product_area TEXT DEFAULT '',
                response TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                needs_escalation INTEGER DEFAULT 0,
                escalation_reason TEXT DEFAULT '',
                escalation_priority TEXT DEFAULT '',
                assigned_team TEXT DEFAULT '',
                retailer_id TEXT DEFAULT '',
                session_id TEXT DEFAULT '',
                sources TEXT DEFAULT '',
                status TEXT DEFAULT 'resolved',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_intent ON support_logs(intent)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_urgency ON support_logs(urgency)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_escalation ON support_logs(needs_escalation)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_created ON support_logs(created_at)
        """)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

"""
Async SQLite database setup and operations.
Uses aiosqlite for non-blocking database access.
"""

from __future__ import annotations

import aiosqlite
from pathlib import Path

from backend.config import settings

DB_PATH = settings.database_path


async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing SQLite table if it is missing."""
    cursor = await db.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in await cursor.fetchall()}
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP,
                resolved_at TIMESTAMP,
                closed_at TIMESTAMP
            )
        """)
        await _ensure_column(db, "support_logs", "session_id", "TEXT DEFAULT ''")
        await _ensure_column(db, "support_logs", "status", "TEXT DEFAULT 'open'")
        await _ensure_column(db, "support_logs", "updated_at", "TIMESTAMP")
        await _ensure_column(db, "support_logs", "assigned_at", "TIMESTAMP")
        await _ensure_column(db, "support_logs", "resolved_at", "TIMESTAMP")
        await _ensure_column(db, "support_logs", "closed_at", "TIMESTAMP")
        await db.execute("""
            UPDATE support_logs
            SET status = 'assigned'
            WHERE status = 'escalated'
        """)
        await db.execute("""
            UPDATE support_logs
            SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        """)
        await db.execute("""
            UPDATE support_logs
            SET assigned_at = COALESCE(assigned_at, created_at)
            WHERE status = 'assigned' AND assigned_at IS NULL
        """)
        await db.execute("""
            UPDATE support_logs
            SET resolved_at = COALESCE(resolved_at, created_at)
            WHERE status = 'resolved' AND resolved_at IS NULL
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
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_status ON support_logs(status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_retailer ON support_logs(retailer_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_session ON support_logs(session_id)
        """)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

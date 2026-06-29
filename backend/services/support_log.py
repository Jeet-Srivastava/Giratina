"""
Support log service.
CRUD operations for support logs in SQLite.
"""

from __future__ import annotations

import json
import logging

import aiosqlite

from backend.database import DB_PATH
from backend.models import SupportLogCreate, SupportLogResponse

logger = logging.getLogger(__name__)


async def create_log(data: SupportLogCreate) -> int:
    """Create a new support log entry. Returns the log ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO support_logs
                (query, intent, urgency, product_area, response, confidence,
                 needs_escalation, escalation_reason, escalation_priority,
                 assigned_team, retailer_id, session_id, sources, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.query,
                data.intent,
                data.urgency,
                data.product_area,
                data.response,
                data.confidence,
                1 if data.needs_escalation else 0,
                data.escalation_reason,
                data.escalation_priority,
                data.assigned_team,
                data.retailer_id,
                data.session_id,
                data.sources,
                "escalated" if data.needs_escalation else "resolved",
            ),
        )
        await db.commit()
        log_id = cursor.lastrowid
        logger.info(f"Created support log #{log_id}")
        return log_id


async def get_logs(
    limit: int = 50,
    offset: int = 0,
    intent: str | None = None,
    urgency: str | None = None,
    escalated_only: bool = False,
) -> list[SupportLogResponse]:
    """Get support logs with optional filtering."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        where_clauses = []
        params = []

        if intent:
            where_clauses.append("intent = ?")
            params.append(intent)
        if urgency:
            where_clauses.append("urgency = ?")
            params.append(urgency)
        if escalated_only:
            where_clauses.append("needs_escalation = 1")

        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = f"WHERE {where_sql}"

        query = f"""
            SELECT * FROM support_logs
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        return [
            SupportLogResponse(
                id=row["id"],
                query=row["query"],
                intent=row["intent"],
                urgency=row["urgency"],
                product_area=row["product_area"],
                response=row["response"],
                confidence=row["confidence"],
                needs_escalation=bool(row["needs_escalation"]),
                escalation_reason=row["escalation_reason"],
                escalation_priority=row["escalation_priority"],
                assigned_team=row["assigned_team"],
                retailer_id=row["retailer_id"],
                sources=row["sources"],
                created_at=str(row["created_at"]),
                status=row["status"],
            )
            for row in rows
        ]


async def get_log_by_id(log_id: int) -> SupportLogResponse | None:
    """Get a single support log by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM support_logs WHERE id = ?", (log_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return SupportLogResponse(
            id=row["id"],
            query=row["query"],
            intent=row["intent"],
            urgency=row["urgency"],
            product_area=row["product_area"],
            response=row["response"],
            confidence=row["confidence"],
            needs_escalation=bool(row["needs_escalation"]),
            escalation_reason=row["escalation_reason"],
            escalation_priority=row["escalation_priority"],
            assigned_team=row["assigned_team"],
            retailer_id=row["retailer_id"],
            sources=row["sources"],
            created_at=str(row["created_at"]),
            status=row["status"],
        )

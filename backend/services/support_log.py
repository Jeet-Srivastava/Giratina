"""
Support log service.
CRUD operations for support logs in SQLite.
"""

from __future__ import annotations

import logging

import aiosqlite

from backend.database import DB_PATH
from backend.models import SupportLogCreate, SupportLogResponse, TicketStatus

logger = logging.getLogger(__name__)


def _status_value(status: TicketStatus | str) -> str:
    return status.value if isinstance(status, TicketStatus) else status


def _row_value(row: aiosqlite.Row, key: str, default: str = ""):
    return row[key] if key in row.keys() and row[key] is not None else default


def _row_to_response(row: aiosqlite.Row) -> SupportLogResponse:
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
        session_id=_row_value(row, "session_id"),
        sources=row["sources"],
        created_at=str(row["created_at"]),
        updated_at=str(_row_value(row, "updated_at")),
        assigned_at=str(_row_value(row, "assigned_at")),
        resolved_at=str(_row_value(row, "resolved_at")),
        closed_at=str(_row_value(row, "closed_at")),
        status=_row_value(row, "status", TicketStatus.OPEN.value),
    )


def _timestamp_assignments(status: str) -> tuple[str, str]:
    assignments = ["updated_at = CURRENT_TIMESTAMP"]
    if status == TicketStatus.ASSIGNED.value:
        assignments.append("assigned_at = COALESCE(assigned_at, CURRENT_TIMESTAMP)")
    elif status == TicketStatus.RESOLVED.value:
        assignments.append("resolved_at = COALESCE(resolved_at, CURRENT_TIMESTAMP)")
    elif status == TicketStatus.CLOSED.value:
        assignments.append("closed_at = COALESCE(closed_at, CURRENT_TIMESTAMP)")
    return ", ".join(assignments), status


async def create_open_ticket(query: str, retailer_id: str = "", session_id: str = "") -> int:
    """Persist the initial open lifecycle state before the agent runs."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO support_logs
                (query, intent, urgency, product_area, response, confidence,
                 needs_escalation, retailer_id, session_id, sources, status,
                 updated_at)
            VALUES (?, 'unknown', 'low', '', '', 0.0, 0, ?, ?, '[]', 'open',
                    CURRENT_TIMESTAMP)
            """,
            (query, retailer_id, session_id),
        )
        await db.commit()
        log_id = cursor.lastrowid
        logger.info(f"Created open support ticket #{log_id}")
        return log_id


async def create_log(data: SupportLogCreate) -> int:
    """Create a new support log entry. Returns the log ID."""
    status = _status_value(data.status)
    if data.needs_escalation and status == TicketStatus.RESOLVED.value:
        status = TicketStatus.ASSIGNED.value
    timestamp_sql, _ = _timestamp_assignments(status)

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
                status,
            ),
        )
        await db.execute(
            f"UPDATE support_logs SET {timestamp_sql} WHERE id = ?",
            (cursor.lastrowid,),
        )
        await db.commit()
        log_id = cursor.lastrowid
        logger.info(f"Created support log #{log_id}")
        return log_id


async def update_log_from_agent(log_id: int, data: SupportLogCreate) -> bool:
    """Update an open ticket with the final agent result and lifecycle state."""
    status = _status_value(data.status)
    timestamp_sql, _ = _timestamp_assignments(status)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"""
            UPDATE support_logs
            SET query = ?,
                intent = ?,
                urgency = ?,
                product_area = ?,
                response = ?,
                confidence = ?,
                needs_escalation = ?,
                escalation_reason = ?,
                escalation_priority = ?,
                assigned_team = ?,
                retailer_id = ?,
                session_id = ?,
                sources = ?,
                status = ?,
                {timestamp_sql}
            WHERE id = ?
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
                status,
                log_id,
            ),
        )
        await db.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Updated support ticket #{log_id} to {status}")
        return updated


async def update_ticket_status(log_id: int, status: TicketStatus | str) -> bool:
    """Move a persisted ticket to a lifecycle state."""
    status_value = _status_value(status)
    timestamp_sql, _ = _timestamp_assignments(status_value)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"""
            UPDATE support_logs
            SET status = ?,
                {timestamp_sql}
            WHERE id = ?
            """,
            (status_value, log_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_logs(
    limit: int = 50,
    offset: int = 0,
    intent: str | None = None,
    urgency: str | None = None,
    status: str | None = None,
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
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if escalated_only:
            where_clauses.append("(needs_escalation = 1 OR status = 'assigned')")

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

        return [_row_to_response(row) for row in rows]


async def get_log_by_id(log_id: int) -> SupportLogResponse | None:
    """Get a single support log by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM support_logs WHERE id = ?", (log_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_response(row)


async def get_retailer_memory(
    retailer_id: str = "",
    session_id: str = "",
    limit: int = 5,
) -> dict:
    """Load recent query and escalation history for multi-turn memory."""
    if not retailer_id and not session_id:
        return {
            "retailer_id": retailer_id,
            "session_id": session_id,
            "recent_queries": [],
            "escalation_history": [],
            "open_tickets": [],
        }

    where = []
    params: list[str | int] = []
    if retailer_id:
        where.append("retailer_id = ?")
        params.append(retailer_id)
    if session_id:
        where.append("session_id = ?")
        params.append(session_id)

    where_sql = " OR ".join(where)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT query, intent, product_area, status, needs_escalation,
                   escalation_reason, assigned_team, created_at
            FROM support_logs
            WHERE ({where_sql})
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        rows = await cursor.fetchall()

    recent_queries = [
        {
            "query": row["query"],
            "intent": row["intent"],
            "product_area": row["product_area"],
            "status": row["status"],
            "needs_escalation": bool(row["needs_escalation"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]
    escalation_history = [
        {
            "query": row["query"],
            "escalation_reason": row["escalation_reason"],
            "assigned_team": row["assigned_team"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
        }
        for row in rows
        if row["needs_escalation"] or row["status"] == TicketStatus.ASSIGNED.value
    ]
    open_tickets = [
        item
        for item in recent_queries
        if item["status"] in {TicketStatus.OPEN.value, TicketStatus.ASSIGNED.value}
    ]

    return {
        "retailer_id": retailer_id,
        "session_id": session_id,
        "recent_queries": recent_queries,
        "escalation_history": escalation_history,
        "open_tickets": open_tickets,
    }

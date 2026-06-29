"""
Analytics service.
Aggregates support log data for the admin dashboard.
"""

from __future__ import annotations

import logging

import aiosqlite

from backend.database import DB_PATH
from backend.models import AnalyticsSummary
from backend.services.support_log import get_logs

logger = logging.getLogger(__name__)


async def get_summary() -> AnalyticsSummary:
    """Get analytics summary for the dashboard."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Total queries
        cursor = await db.execute("SELECT COUNT(*) as count FROM support_logs")
        row = await cursor.fetchone()
        total_queries = row["count"] if row else 0

        # Total escalations
        cursor = await db.execute("SELECT COUNT(*) as count FROM support_logs WHERE needs_escalation = 1")
        row = await cursor.fetchone()
        total_escalations = row["count"] if row else 0

        # Average confidence
        cursor = await db.execute("SELECT AVG(confidence) as avg_conf FROM support_logs")
        row = await cursor.fetchone()
        avg_confidence = round(row["avg_conf"], 2) if row and row["avg_conf"] else 0.0

        # Escalation rate
        escalation_rate = round(total_escalations / total_queries * 100, 1) if total_queries > 0 else 0.0

        # Intent distribution
        cursor = await db.execute(
            "SELECT intent, COUNT(*) as count FROM support_logs GROUP BY intent ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
        intent_distribution = {row["intent"]: row["count"] for row in rows}

        # Urgency distribution
        cursor = await db.execute(
            "SELECT urgency, COUNT(*) as count FROM support_logs GROUP BY urgency ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
        urgency_distribution = {row["urgency"]: row["count"] for row in rows}

        # Recent queries
        recent = await get_logs(limit=10)

        return AnalyticsSummary(
            total_queries=total_queries,
            total_escalations=total_escalations,
            escalation_rate=escalation_rate,
            avg_confidence=avg_confidence,
            intent_distribution=intent_distribution,
            urgency_distribution=urgency_distribution,
            recent_queries=recent,
        )

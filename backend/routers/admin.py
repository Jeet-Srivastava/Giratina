"""
Admin API endpoints.
Support log viewer, escalation queue, analytics dashboard.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models import SupportLogResponse, AnalyticsSummary
from backend.services.support_log import get_logs, get_log_by_id
from backend.services.analytics import get_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Admin"])


@router.get("/logs", response_model=list[SupportLogResponse])
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    intent: Optional[str] = None,
    urgency: Optional[str] = None,
):
    """Get support logs with optional filtering."""
    return await get_logs(limit=limit, offset=offset, intent=intent, urgency=urgency)


@router.get("/logs/{log_id}", response_model=SupportLogResponse)
async def get_single_log(log_id: int):
    """Get a single support log by ID."""
    log = await get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.get("/escalations", response_model=list[SupportLogResponse])
async def list_escalations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get all escalated support queries."""
    return await get_logs(limit=limit, offset=offset, escalated_only=True)


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary():
    """Get dashboard analytics summary."""
    return await get_summary()

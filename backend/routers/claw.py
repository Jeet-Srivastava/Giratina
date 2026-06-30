"""
Claw runtime metadata endpoints.
Expose formal runtime mappings and per-node tool contracts for reviewers
and external runtimes.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.agent.contracts import get_claw_manifest, get_tool_contracts

router = APIRouter(prefix="/api/claw", tags=["Claw Runtime"])


@router.get("/manifest")
async def claw_manifest():
    """Return the OpenClaw/NemoClaw/NanoClaw/Hermes runtime mapping."""
    return get_claw_manifest()


@router.get("/tools")
async def claw_tool_contracts():
    """Return explicit input/output schemas for each Claw tool node."""
    return {"tools": get_tool_contracts()}

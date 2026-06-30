"""
Chat API endpoints.
Main entry point for the Support Knowledge Claw agent.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException

from backend.models import (
    ChatRequest,
    ChatResponse,
    AgentStep,
    EscalationNote,
    Intent,
    Urgency,
    EscalationPriority,
    SupportLogCreate,
    TicketStatus,
)
from backend.agent.graph import get_agent
from backend.services.support_log import create_log, create_open_ticket, get_retailer_memory, update_log_from_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Submit a support query and get an autonomous agent response.

    The agent will:
    1. Classify the intent
    2. Assess urgency
    3. Retrieve relevant knowledge
    4. Generate a response
    5. Evaluate confidence
    6. Escalate if needed
    7. Persist lifecycle state and support log
    """
    try:
        agent = get_agent()
        retailer_id = request.retailer_id or ""
        session_id = request.session_id or ""
        memory_context = await get_retailer_memory(retailer_id=retailer_id, session_id=session_id)
        memory_step = {
            "step": "Retailer Memory",
            "result": (
                f"{len(memory_context.get('recent_queries', []))} prior queries, "
                f"{len(memory_context.get('escalation_history', []))} escalations"
            ),
            "duration_ms": 0,
        }

        log_id = await create_open_ticket(
            query=request.query,
            retailer_id=retailer_id,
            session_id=session_id,
        )

        # Prepare initial state
        initial_state = {
            "query": request.query,
            "retailer_id": retailer_id,
            "session_id": session_id,
            "support_log_id": log_id,
            "memory_context": memory_context,
            "agent_steps": [memory_step],
            "retrieved_contexts": [],
            "sources": [],
            "needs_escalation": False,
            "escalation_reason": "",
            "escalation_note": None,
            "error": "",
        }

        # Run the agent (in a thread since LangGraph is synchronous)
        result = await asyncio.to_thread(agent.invoke, initial_state)

        # Build escalation note if needed
        escalation = None
        if result.get("needs_escalation") and result.get("escalation_note"):
            note = result["escalation_note"]
            escalation = EscalationNote(
                priority=EscalationPriority(note.get("priority", "MEDIUM")),
                reason=result.get("escalation_reason", ""),
                summary=note.get("summary", ""),
                recommended_action=note.get("recommended_action", ""),
                assigned_team=note.get("assigned_team", "General Support"),
                sla=note.get("sla"),
            )

        ticket_status = TicketStatus.ASSIGNED if result.get("needs_escalation", False) else TicketStatus.RESOLVED

        # Update support log and lifecycle state
        log_data = SupportLogCreate(
            query=request.query,
            intent=result.get("intent", "unknown"),
            urgency=result.get("urgency", "medium"),
            product_area=result.get("product_area", ""),
            response=result.get("response", ""),
            confidence=result.get("confidence", 0.0),
            needs_escalation=result.get("needs_escalation", False),
            escalation_reason=result.get("escalation_reason", ""),
            escalation_priority=escalation.priority.value if escalation else "",
            assigned_team=escalation.assigned_team if escalation else "",
            retailer_id=retailer_id,
            session_id=session_id,
            sources=json.dumps(result.get("sources", [])),
            status=ticket_status,
        )
        updated = await update_log_from_agent(log_id, log_data)
        if not updated:
            log_id = await create_log(log_data)

        # Build response
        return ChatResponse(
            query=request.query,
            intent=Intent(result.get("intent", "unknown")),
            urgency=Urgency(result.get("urgency", "medium")),
            product_area=result.get("product_area", ""),
            response=result.get("response", ""),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            needs_escalation=result.get("needs_escalation", False),
            escalation=escalation,
            next_steps=result.get("next_steps", ""),
            support_log_id=log_id,
            ticket_status=ticket_status,
            agent_steps=[
                AgentStep(**step) for step in result.get("agent_steps", [])
            ],
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

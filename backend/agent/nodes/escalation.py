"""
Escalation engine node.
Creates structured escalation notes for human agents when the agent cannot resolve autonomously.
"""

from __future__ import annotations

import json
import time
import logging

from langchain_groq import ChatGroq
from backend.agent.state import AgentState
from backend.agent.prompts import ESCALATION_PROMPT
from backend.agent.utils import format_memory_context, parse_llm_json
from backend.config import settings

logger = logging.getLogger(__name__)

# Team assignment rules based on product area and intent
TEAM_ASSIGNMENT = {
    "security": "Security & Fraud",
    "commission": "Finance Operations",
    "account": "Account Management",
    "aeps": "Technical Support",
    "money_transfer": "Technical Support",
    "bill_payment": "Technical Support",
    "recharge": "Technical Support",
    "general": "General Support",
}

SLA_MAP = {
    "CRITICAL": "1 hour",
    "HIGH": "4 hours",
    "MEDIUM": "24 hours",
    "LOW": "48 hours",
}

SECURITY_KEYWORDS = [
    "fraud",
    "unauthorized",
    "stolen",
    "hacked",
    "scam",
    "someone using",
    "without my permission",
    "money stolen",
]


def _assign_team(product_area: str, query: str) -> str:
    """Assign the best human queue using product area and security signals."""
    query_lower = query.lower()
    if product_area == "security" or any(keyword in query_lower for keyword in SECURITY_KEYWORDS):
        return "Security & Fraud"
    return TEAM_ASSIGNMENT.get(product_area, "General Support")


def handle_escalation(state: AgentState) -> dict:
    """Create a structured escalation note."""
    start = time.time()
    query = state["query"]
    intent = state.get("intent", "unknown")
    urgency = state.get("urgency", "medium")
    product_area = state.get("product_area", "general")
    confidence = state.get("confidence", 0.0)
    reason = state.get("escalation_reason", "Low confidence")
    response = state.get("response", "")
    memory = format_memory_context(state.get("memory_context"))

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.0,
            max_tokens=400,
        )

        prompt = ESCALATION_PROMPT.format(
            query=query,
            intent=intent,
            urgency=urgency,
            product_area=product_area,
            confidence=confidence,
            reason=reason,
            memory=memory,
            response=response,
        )
        result = llm.invoke(prompt)
        note = parse_llm_json(result.content)

        # Override team assignment with rule-based logic (more reliable)
        assigned_team = _assign_team(product_area, query)

        # Override priority based on urgency
        priority_map = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        priority = priority_map.get(urgency, note.get("priority", "MEDIUM"))

        escalation_note = {
            "priority": priority,
            "summary": note.get("summary", f"Support query requires human review: {query[:100]}"),
            "recommended_action": note.get("recommended_action", "Review and respond to the query manually"),
            "assigned_team": assigned_team,
            "sla": SLA_MAP.get(priority, "24 hours"),
        }

        duration = int((time.time() - start) * 1000)
        logger.info(f"Escalation created: priority={priority}, team={assigned_team}")

        return {
            "escalation_note": escalation_note,
            "ticket_status": "assigned",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Escalation", "result": f"{priority} → {assigned_team}", "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Escalation creation failed: {e}")
        duration = int((time.time() - start) * 1000)

        # Fallback escalation note
        assigned_team = _assign_team(product_area, query)
        priority_map = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        priority = priority_map.get(urgency, "MEDIUM")

        return {
            "escalation_note": {
                "priority": priority,
                "summary": f"Auto-escalated: {query[:150]}",
                "recommended_action": "Review and respond manually",
                "assigned_team": assigned_team,
                "sla": SLA_MAP.get(priority, "24 hours"),
            },
            "ticket_status": "assigned",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Escalation", "result": f"{priority} → {assigned_team} (fallback)", "duration_ms": duration}
            ],
        }

"""
Urgency assessment node.
Uses a rules-based + LLM hybrid approach to assess query urgency.
"""

from __future__ import annotations

import json
import re
import time
import logging

from langchain_groq import ChatGroq
from backend.agent.state import AgentState
from backend.agent.prompts import URGENCY_PROMPT
from backend.agent.utils import parse_llm_json
from backend.config import settings

logger = logging.getLogger(__name__)

# Keywords that immediately trigger specific urgency levels
CRITICAL_KEYWORDS = [
    "fraud", "unauthorized", "stolen", "hacked", "blocked account",
    "money lost", "money gone", "someone using my", "police", "legal",
    "scam", "cheat",
]

HIGH_KEYWORDS = [
    "money deducted", "failed transaction", "stuck", "not received",
    "settlement delay", "commission wrong", "double charge", "service down",
    "not working at all", "cannot login",
]


def _check_keyword_urgency(query: str) -> str | None:
    """Rule-based urgency check using keywords."""
    query_lower = query.lower()
    for kw in CRITICAL_KEYWORDS:
        if kw in query_lower:
            return "critical"
    for kw in HIGH_KEYWORDS:
        if kw in query_lower:
            return "high"
    return None


def assess_urgency(state: AgentState) -> dict:
    """Assess the urgency of the support query."""
    start = time.time()
    query = state["query"]
    intent = state.get("intent", "unknown")
    product_area = state.get("product_area", "general")

    # Step 1: Rules-based check (fast, reliable)
    keyword_urgency = _check_keyword_urgency(query)

    if keyword_urgency == "critical":
        # Don't even ask the LLM — critical is critical
        duration = int((time.time() - start) * 1000)
        logger.info(f"Urgency: CRITICAL (keyword match)")
        return {
            "urgency": "critical",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Urgency Assessment", "result": "critical (keyword match)", "duration_ms": duration}
            ],
        }

    # Step 2: LLM assessment
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.0,
            max_tokens=150,
        )

        prompt = URGENCY_PROMPT.format(query=query, intent=intent, product_area=product_area)
        response = llm.invoke(prompt)
        result = parse_llm_json(response.content)
        urgency = result.get("urgency", "medium")

        # Validate urgency
        valid = {"low", "medium", "high", "critical"}
        if urgency not in valid:
            urgency = "medium"

        # If keyword check found high but LLM says low/medium, use high (conservative)
        if keyword_urgency == "high" and urgency in ("low", "medium"):
            urgency = "high"

        duration = int((time.time() - start) * 1000)
        logger.info(f"Urgency: {urgency}")

        return {
            "urgency": urgency,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Urgency Assessment", "result": urgency, "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Urgency assessment failed: {e}")
        duration = int((time.time() - start) * 1000)
        # Default to keyword result or medium
        fallback = keyword_urgency or "medium"
        return {
            "urgency": fallback,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Urgency Assessment", "result": f"{fallback} (fallback)", "duration_ms": duration}
            ],
        }

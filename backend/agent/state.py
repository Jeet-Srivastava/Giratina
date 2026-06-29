"""
Agent state definition for the LangGraph workflow.
This TypedDict defines what the agent 'knows' at each step.
"""

from __future__ import annotations

from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    """State carried through the LangGraph agent workflow."""

    # Input
    query: str
    retailer_id: str
    session_id: str

    # Classification
    intent: str
    product_area: str

    # Urgency
    urgency: str

    # Retrieval
    retrieved_contexts: list[dict]  # [{content, source, score}]

    # Generation
    response: str
    sources: list[str]
    next_steps: str

    # Evaluation
    confidence: float

    # Escalation
    needs_escalation: bool
    escalation_reason: str
    escalation_note: Optional[dict]

    # Logging
    support_log_id: Optional[int]

    # Metadata
    agent_steps: list[dict]  # [{step, result, duration_ms}]
    error: str

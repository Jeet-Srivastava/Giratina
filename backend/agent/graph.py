"""
LangGraph workflow definition.
Wires all agent nodes into a directed graph with conditional edges.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from backend.agent.state import AgentState
from backend.agent.nodes.classifier import classify_intent
from backend.agent.nodes.urgency import assess_urgency
from backend.agent.nodes.retriever import retrieve_context
from backend.agent.nodes.generator import generate_response
from backend.agent.nodes.evaluator import evaluate_confidence
from backend.agent.nodes.escalation import handle_escalation

logger = logging.getLogger(__name__)


def should_escalate(state: AgentState) -> str:
    """Conditional edge: decide whether to escalate or respond directly."""
    if state.get("needs_escalation", False):
        return "escalate"
    return "respond"


def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph agent workflow."""

    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("assess_urgency", assess_urgency)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_response", generate_response)
    graph.add_node("evaluate_confidence", evaluate_confidence)
    graph.add_node("handle_escalation", handle_escalation)

    # Define the flow
    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "assess_urgency")
    graph.add_edge("assess_urgency", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", "evaluate_confidence")

    # Conditional edge: escalate or respond
    graph.add_conditional_edges(
        "evaluate_confidence",
        should_escalate,
        {
            "escalate": "handle_escalation",
            "respond": END,
        },
    )

    # Escalation always ends after creating the note
    graph.add_edge("handle_escalation", END)

    return graph.compile()


# Compiled agent (singleton)
_agent = None


def get_agent():
    """Get or create the compiled agent."""
    global _agent
    if _agent is None:
        logger.info("Building agent graph...")
        _agent = build_agent_graph()
        logger.info("Agent graph ready.")
    return _agent

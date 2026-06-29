"""
Confidence evaluation node.
Self-evaluates the quality of the generated response on relevance, completeness, groundedness.
"""

from __future__ import annotations

import json
import time
import logging

from langchain_groq import ChatGroq
from backend.agent.state import AgentState
from backend.agent.prompts import EVALUATOR_PROMPT
from backend.agent.utils import parse_llm_json
from backend.config import settings

logger = logging.getLogger(__name__)


def evaluate_confidence(state: AgentState) -> dict:
    """Evaluate the confidence of the generated response."""
    start = time.time()
    query = state["query"]
    intent = state.get("intent", "unknown")
    response = state.get("response", "")
    contexts = state.get("retrieved_contexts", [])

    # If no contexts were retrieved, confidence is automatically low
    if not contexts:
        duration = int((time.time() - start) * 1000)
        logger.info("Confidence: 0.3 (no context retrieved)")
        return {
            "confidence": 0.3,
            "needs_escalation": True,
            "escalation_reason": "No relevant documents found in knowledge base",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Confidence Evaluation", "result": "0.30 (no context)", "duration_ms": duration}
            ],
        }

    context_str = "\n\n".join(
        f"[Source: {c['source']}]\n{c['content']}"
        for c in contexts[:3]  # Only send top 3 for evaluation
    )

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.0,
            max_tokens=300,
        )

        prompt = EVALUATOR_PROMPT.format(
            query=query,
            intent=intent,
            context=context_str,
            response=response,
        )
        result = llm.invoke(prompt)
        scores = parse_llm_json(result.content)
        relevance = float(scores.get("relevance", 0.5))
        completeness = float(scores.get("completeness", 0.5))
        groundedness = float(scores.get("groundedness", 0.5))

        # Composite confidence: weighted average
        # Groundedness is weighted highest (to prevent hallucination)
        confidence = round(
            0.3 * relevance + 0.3 * completeness + 0.4 * groundedness,
            2,
        )

        # Determine if escalation is needed
        threshold = settings.confidence_threshold
        urgency = state.get("urgency", "medium")
        needs_escalation = confidence < threshold or urgency == "critical"

        escalation_reason = ""
        if confidence < threshold:
            escalation_reason = f"Low confidence ({confidence:.2f} < {threshold})"
        elif urgency == "critical":
            escalation_reason = "Critical urgency — auto-escalated regardless of confidence"

        duration = int((time.time() - start) * 1000)
        logger.info(f"Confidence: {confidence} (R:{relevance} C:{completeness} G:{groundedness})")

        return {
            "confidence": confidence,
            "needs_escalation": needs_escalation,
            "escalation_reason": escalation_reason,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Confidence Evaluation", "result": f"{confidence:.2f} (R:{relevance} C:{completeness} G:{groundedness})", "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        duration = int((time.time() - start) * 1000)
        # Conservative: assume low confidence on failure
        return {
            "confidence": 0.5,
            "needs_escalation": True,
            "escalation_reason": f"Confidence evaluation failed: {str(e)[:80]}",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Confidence Evaluation", "result": f"0.50 (fallback)", "duration_ms": duration}
            ],
        }

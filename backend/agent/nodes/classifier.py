"""
Intent classification node.
Classifies user query into one of: faq, technical_issue, transaction_problem, account_issue, feature_request.
Also identifies the product area (aeps, money_transfer, etc.).
"""

from __future__ import annotations

import json
import time
import logging

from langchain_groq import ChatGroq
from backend.agent.state import AgentState
from backend.agent.prompts import CLASSIFIER_PROMPT
from backend.agent.utils import parse_llm_json
from backend.config import settings

logger = logging.getLogger(__name__)


def classify_intent(state: AgentState) -> dict:
    """Classify the intent and product area of a support query."""
    start = time.time()
    query = state["query"]

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.0,
            max_tokens=200,
        )

        prompt = CLASSIFIER_PROMPT.format(query=query)
        response = llm.invoke(prompt)
        result = parse_llm_json(response.content)
        intent = result.get("intent", "unknown")
        product_area = result.get("product_area", "general")

        # Validate intent
        valid_intents = {"faq", "technical_issue", "transaction_problem", "account_issue", "feature_request"}
        if intent not in valid_intents:
            intent = "unknown"

        duration = int((time.time() - start) * 1000)
        logger.info(f"Classified query as intent={intent}, product_area={product_area}")

        return {
            "intent": intent,
            "product_area": product_area,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Intent Classification", "result": f"{intent} ({product_area})", "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        duration = int((time.time() - start) * 1000)
        return {
            "intent": "unknown",
            "product_area": "general",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Intent Classification", "result": f"fallback (error: {str(e)[:80]})", "duration_ms": duration}
            ],
        }

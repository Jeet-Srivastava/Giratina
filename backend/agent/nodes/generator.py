"""
Response generation node.
Generates structured, actionable responses using RAG context.
"""

from __future__ import annotations

import json
import time
import logging

from langchain_groq import ChatGroq
from backend.agent.state import AgentState
from backend.agent.prompts import GENERATOR_PROMPT
from backend.agent.utils import format_memory_context, parse_llm_json
from backend.config import settings

logger = logging.getLogger(__name__)


def generate_response(state: AgentState) -> dict:
    """Generate a structured response using retrieved context."""
    start = time.time()
    query = state["query"]
    intent = state.get("intent", "unknown")
    urgency = state.get("urgency", "medium")
    product_area = state.get("product_area", "general")
    contexts = state.get("retrieved_contexts", [])
    memory = format_memory_context(state.get("memory_context"))

    # Build context string from retrieved chunks
    if contexts:
        context_str = "\n\n".join(
            f"[Source: {c['source']}]\n{c['content']}"
            for c in contexts
        )
    else:
        context_str = "No relevant documents found in the knowledge base."

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.3,
            max_tokens=1000,
        )

        prompt = GENERATOR_PROMPT.format(
            query=query,
            intent=intent,
            urgency=urgency,
            product_area=product_area,
            memory=memory,
            context=context_str,
        )
        response = llm.invoke(prompt)
        result = parse_llm_json(response.content)
        answer = result.get("answer", "I'm unable to generate a response at this time.")
        sources = result.get("sources_used", [])
        next_steps = result.get("next_steps", "")

        duration = int((time.time() - start) * 1000)
        logger.info(f"Generated response ({len(answer)} chars, {len(sources)} sources)")

        return {
            "response": answer,
            "sources": sources,
            "next_steps": next_steps,
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Response Generation", "result": f"{len(answer)} chars", "duration_ms": duration}
            ],
        }

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        duration = int((time.time() - start) * 1000)

        # Fallback: return raw context if generation fails
        fallback = "I apologize, but I'm having trouble generating a response. "
        if contexts:
            fallback += "Here's what I found in our knowledge base:\n\n"
            fallback += contexts[0]["content"][:500]
        else:
            fallback += "Please contact Eko support at cs@eko.co.in or call our helpline."

        return {
            "response": fallback,
            "sources": [],
            "next_steps": "Contact cs@eko.co.in for assistance.",
            "agent_steps": state.get("agent_steps", []) + [
                {"step": "Response Generation", "result": f"fallback (error: {str(e)[:60]})", "duration_ms": duration}
            ],
        }

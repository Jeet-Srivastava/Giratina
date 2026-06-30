"""
Tests for the agent workflow and individual nodes.
"""

import pytest
from backend.agent.nodes.urgency import _check_keyword_urgency
from backend.agent.nodes.classifier import classify_intent
from backend.agent.nodes.evaluator import evaluate_confidence
from backend.agent.nodes.escalation import handle_escalation
from backend.agent.nodes.generator import generate_response
from backend.agent.nodes.retriever import retrieve_context
from backend.agent.utils import parse_llm_json
from backend.knowledge.ingestion import _chunk_text, _detect_product_area


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class TestKeywordUrgency:
    """Test the rules-based urgency detection."""

    def test_critical_fraud(self):
        assert _check_keyword_urgency("There is fraud on my account") == "critical"

    def test_critical_unauthorized(self):
        assert _check_keyword_urgency("Someone unauthorized is using my ID") == "critical"

    def test_critical_stolen(self):
        assert _check_keyword_urgency("My money was stolen from my account") == "critical"

    def test_high_money_deducted(self):
        assert _check_keyword_urgency("Transaction failed but money deducted") == "high"

    def test_high_not_working(self):
        assert _check_keyword_urgency("App is not working at all") == "high"

    def test_none_for_general(self):
        assert _check_keyword_urgency("How do I register?") is None

    def test_none_for_feature(self):
        assert _check_keyword_urgency("Can you add Hindi language support?") is None


class TestChunking:
    """Test the document chunking logic."""

    def test_basic_chunking(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = _chunk_text(text, chunk_size=50, overlap=0)
        assert len(chunks) >= 1
        assert all(len(c) <= 60 for c in chunks)  # allow small overflow

    def test_single_paragraph(self):
        text = "This is a short paragraph."
        chunks = _chunk_text(text, chunk_size=500, overlap=0)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        chunks = _chunk_text("", chunk_size=500, overlap=0)
        assert len(chunks) == 0

    def test_overlap_produces_more_chunks(self):
        text = "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100
        no_overlap = _chunk_text(text, chunk_size=120, overlap=0)
        with_overlap = _chunk_text(text, chunk_size=120, overlap=30)
        # Overlap may produce same or more chunks
        assert len(with_overlap) >= len(no_overlap)


class TestProductAreaDetection:
    """Test product area detection from filenames."""

    def test_aeps(self):
        assert _detect_product_area("aeps_troubleshooting") == "aeps"

    def test_money_transfer(self):
        assert _detect_product_area("money_transfer_sop") == "money_transfer"

    def test_commission(self):
        assert _detect_product_area("commission_settlement") == "commission"

    def test_account(self):
        assert _detect_product_area("account_activation") == "account"

    def test_general_faq(self):
        assert _detect_product_area("eko_general_faq") == "general"

    def test_unknown(self):
        assert _detect_product_area("random_document") == "general"


class TestFailureModes:
    """Reviewer-requested failure-mode coverage."""

    def test_low_confidence_escalates(self, monkeypatch):
        class LowConfidenceLLM:
            def __init__(self, **kwargs):
                pass

            def invoke(self, prompt):
                return FakeResponse('{"relevance": 0.4, "completeness": 0.5, "groundedness": 0.4}')

        monkeypatch.setattr("backend.agent.nodes.evaluator.ChatGroq", LowConfidenceLLM)

        result = evaluate_confidence({
            "query": "My DMT transfer is pending",
            "intent": "transaction_problem",
            "urgency": "medium",
            "response": "Please check Transaction Inquiry.",
            "retrieved_contexts": [
                {"source": "money_transfer_sop.md", "content": "Check Transaction Inquiry.", "relevance_score": 0.9}
            ],
            "agent_steps": [],
        })

        assert result["confidence"] < 0.75
        assert result["needs_escalation"] is True
        assert "Low confidence" in result["escalation_reason"]

    def test_llm_generation_failure_returns_safe_fallback(self, monkeypatch):
        class FailingLLM:
            def __init__(self, **kwargs):
                pass

            def invoke(self, prompt):
                raise RuntimeError("llm unavailable")

        monkeypatch.setattr("backend.agent.nodes.generator.ChatGroq", FailingLLM)

        result = generate_response({
            "query": "My AePS transaction failed",
            "intent": "transaction_problem",
            "urgency": "high",
            "product_area": "aeps",
            "retrieved_contexts": [
                {"source": "aeps_troubleshooting.md", "content": "Use Transaction Inquiry first.", "relevance_score": 0.9}
            ],
            "agent_steps": [],
        })

        assert "trouble generating" in result["response"]
        assert result["next_steps"] == "Contact cs@eko.co.in for assistance."

    def test_json_parsing_failure_uses_classifier_fallback(self, monkeypatch):
        class InvalidJsonLLM:
            def __init__(self, **kwargs):
                pass

            def invoke(self, prompt):
                return FakeResponse("intent is probably faq")

        monkeypatch.setattr("backend.agent.nodes.classifier.ChatGroq", InvalidJsonLLM)

        result = classify_intent({
            "query": "What is Eko?",
            "agent_steps": [],
        })

        assert result["intent"] == "unknown"
        assert result["product_area"] == "general"
        with pytest.raises(ValueError):
            parse_llm_json("intent is probably faq")

    def test_retrieval_failure_leads_to_escalation_path(self, monkeypatch):
        def failing_store():
            raise RuntimeError("vector store unavailable")

        monkeypatch.setattr("backend.agent.nodes.retriever.get_vector_store", failing_store)

        retrieval = retrieve_context({
            "query": "Need settlement help",
            "product_area": "commission",
            "agent_steps": [],
        })
        evaluation = evaluate_confidence({
            "query": "Need settlement help",
            "intent": "transaction_problem",
            "urgency": "medium",
            "response": "Fallback response",
            "retrieved_contexts": retrieval["retrieved_contexts"],
            "agent_steps": retrieval["agent_steps"],
        })

        assert retrieval["retrieved_contexts"] == []
        assert evaluation["needs_escalation"] is True
        assert evaluation["confidence"] == 0.3
        assert "No relevant documents" in evaluation["escalation_reason"]

    def test_critical_fraud_routes_to_security_escalation(self, monkeypatch):
        class EscalationLLM:
            def __init__(self, **kwargs):
                pass

            def invoke(self, prompt):
                return FakeResponse(
                    '{"priority": "HIGH", "summary": "Account takeover risk", '
                    '"recommended_action": "Freeze and audit account", '
                    '"assigned_team": "Account Management", "sla": "24 hours"}'
                )

        monkeypatch.setattr("backend.agent.nodes.escalation.ChatGroq", EscalationLLM)

        note = handle_escalation({
            "query": "There is fraud and someone is using my wallet without my permission",
            "intent": "account_issue",
            "urgency": "critical",
            "product_area": "account",
            "confidence": 0.95,
            "escalation_reason": "Critical urgency",
            "response": "This has been escalated.",
            "agent_steps": [],
        })

        assert _check_keyword_urgency("Fraud on my retailer wallet") == "critical"
        assert note["escalation_note"]["priority"] == "CRITICAL"
        assert note["escalation_note"]["assigned_team"] == "Security & Fraud"
        assert note["ticket_status"] == "assigned"

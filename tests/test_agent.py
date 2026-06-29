"""
Tests for the agent workflow and individual nodes.
"""

import pytest
from backend.agent.nodes.urgency import _check_keyword_urgency
from backend.knowledge.ingestion import _chunk_text, _detect_product_area


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

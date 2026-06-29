#!/usr/bin/env python3
"""
Accuracy Benchmark Script.
Tests the agent against a suite of predefined queries with expected outcomes.
Usage: python -m scripts.benchmark_accuracy
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.graph import get_agent
from backend.knowledge.ingestion import ingest_directory
from backend.knowledge.store import get_document_count

# ── Test Cases ─────────────────────────────────────

TEST_CASES = [
    {
        "query": "What is Eko and how does it work?",
        "expected_intent": "faq",
        "expected_urgency": "low",
        "should_escalate": False,
        "min_confidence": 0.6,
    },
    {
        "query": "My AePS transaction failed but customer's money was deducted. What should I do?",
        "expected_intent": "transaction_problem",
        "expected_urgency": "high",
        "should_escalate": False,
        "min_confidence": 0.6,
    },
    {
        "query": "How do I register as a new Eko retailer?",
        "expected_intent": "faq",
        "expected_urgency": "low",
        "should_escalate": False,
        "min_confidence": 0.6,
    },
    {
        "query": "My biometric device is not being detected by the Eko app",
        "expected_intent": "technical_issue",
        "expected_urgency": "medium",
        "should_escalate": False,
        "min_confidence": 0.5,
    },
    {
        "query": "Someone is using my retailer account without my permission",
        "expected_intent": "account_issue",
        "expected_urgency": "critical",
        "should_escalate": True,
        "min_confidence": 0.3,
    },
    {
        "query": "How much commission do I earn on AePS transactions?",
        "expected_intent": "faq",
        "expected_urgency": "low",
        "should_escalate": False,
        "min_confidence": 0.6,
    },
    {
        "query": "My settlement has not been credited for the last 2 weeks",
        "expected_intent": "transaction_problem",
        "expected_urgency": "high",
        "should_escalate": False,
        "min_confidence": 0.4,
    },
    {
        "query": "I transferred money to the wrong bank account, can it be reversed?",
        "expected_intent": "transaction_problem",
        "expected_urgency": "high",
        "should_escalate": False,
        "min_confidence": 0.5,
    },
    {
        "query": "My account has been blocked and I cannot do any transactions",
        "expected_intent": "account_issue",
        "expected_urgency": "high",
        "should_escalate": False,
        "min_confidence": 0.5,
    },
    {
        "query": "It would be great if the app supported Hindi language",
        "expected_intent": "feature_request",
        "expected_urgency": "low",
        "should_escalate": False,
        "min_confidence": 0.4,
    },
    {
        "query": "I was charged double commission on yesterday's settlement",
        "expected_intent": "transaction_problem",
        "expected_urgency": "high",
        "should_escalate": False,
        "min_confidence": 0.4,
    },
    {
        "query": "There is fraud happening on my account, money is being stolen",
        "expected_intent": "account_issue",
        "expected_urgency": "critical",
        "should_escalate": True,
        "min_confidence": 0.3,
    },
]


def run_benchmark():
    """Run all test cases and compute accuracy metrics."""
    print("=" * 60)
    print("  Support Knowledge Claw — Accuracy Benchmark")
    print("=" * 60)

    # Ensure knowledge base is loaded
    if get_document_count() == 0:
        print("\n📚 Loading knowledge base...")
        ingest_directory(reset=True)

    agent = get_agent()
    results = []
    total = len(TEST_CASES)

    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{total}] Testing: {tc['query'][:60]}...")
        start = time.time()

        try:
            state = agent.invoke({
                "query": tc["query"],
                "retailer_id": "benchmark",
                "session_id": "benchmark",
                "agent_steps": [],
                "retrieved_contexts": [],
                "sources": [],
                "needs_escalation": False,
                "escalation_reason": "",
                "escalation_note": None,
                "error": "",
            })

            duration = time.time() - start
            intent_correct = state.get("intent") == tc["expected_intent"]
            urgency_correct = state.get("urgency") == tc["expected_urgency"]
            escalation_correct = state.get("needs_escalation", False) == tc["should_escalate"]
            confidence_ok = state.get("confidence", 0) >= tc["min_confidence"]

            result = {
                "query": tc["query"],
                "intent": {"expected": tc["expected_intent"], "actual": state.get("intent"), "correct": intent_correct},
                "urgency": {"expected": tc["expected_urgency"], "actual": state.get("urgency"), "correct": urgency_correct},
                "escalation": {"expected": tc["should_escalate"], "actual": state.get("needs_escalation"), "correct": escalation_correct},
                "confidence": {"value": state.get("confidence", 0), "min": tc["min_confidence"], "ok": confidence_ok},
                "duration_s": round(duration, 2),
                "passed": intent_correct and urgency_correct and escalation_correct and confidence_ok,
            }

            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  {status} | intent={state.get('intent')} urgency={state.get('urgency')} conf={state.get('confidence', 0):.2f} esc={state.get('needs_escalation')} [{duration:.1f}s]")

            if not result["passed"]:
                if not intent_correct:
                    print(f"    ↳ Intent: expected {tc['expected_intent']}, got {state.get('intent')}")
                if not urgency_correct:
                    print(f"    ↳ Urgency: expected {tc['expected_urgency']}, got {state.get('urgency')}")
                if not escalation_correct:
                    print(f"    ↳ Escalation: expected {tc['should_escalate']}, got {state.get('needs_escalation')}")
                if not confidence_ok:
                    print(f"    ↳ Confidence: {state.get('confidence', 0):.2f} < {tc['min_confidence']}")

            results.append(result)

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({"query": tc["query"], "passed": False, "error": str(e)})

    # Summary
    passed = sum(1 for r in results if r.get("passed"))
    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed}/{total} passed ({passed/total*100:.0f}% accuracy)")
    print("=" * 60)

    # Detailed breakdown
    intent_acc = sum(1 for r in results if r.get("intent", {}).get("correct")) / total * 100
    urgency_acc = sum(1 for r in results if r.get("urgency", {}).get("correct")) / total * 100
    esc_acc = sum(1 for r in results if r.get("escalation", {}).get("correct")) / total * 100

    print(f"  Intent accuracy:     {intent_acc:.0f}%")
    print(f"  Urgency accuracy:    {urgency_acc:.0f}%")
    print(f"  Escalation accuracy: {esc_acc:.0f}%")

    return results


if __name__ == "__main__":
    run_benchmark()

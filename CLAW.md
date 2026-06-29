# CLAW.md — Support Knowledge Claw Specification

## Claw Identity

| Field | Value |
|---|---|
| **Name** | Support Knowledge Claw |
| **Track** | Forward Deployed AI Accelerator |
| **Version** | 1.0.0 |
| **Author** | Jeet Srivastava |
| **Framework** | LangGraph + FastAPI |
| **LLM** | Groq (Llama 3.3 70B Versatile) |

## Mission

Transform Eko's micro-entrepreneur support workflow into an autonomous AI agent that can handle retailer queries end-to-end — from understanding the problem to delivering actionable solutions or intelligently escalating to human agents.

## Workflow Definition

```
START
  │
  ▼
[1. CLASSIFY INTENT]
  │  Input:  User query (text)
  │  Output: intent (faq | technical_issue | transaction_problem | account_issue | feature_request)
  │          product_area (aeps | money_transfer | commission | account | general | security)
  │  Method: Groq LLM with structured JSON output
  │
  ▼
[2. ASSESS URGENCY]
  │  Input:  Query + intent + product_area
  │  Output: urgency (low | medium | high | critical)
  │  Method: Rules-based keyword matching + LLM assessment (hybrid)
  │  Rules:  "fraud", "unauthorized", "stolen" → CRITICAL (no LLM needed)
  │          "money deducted", "failed transaction" → HIGH (no LLM needed)
  │
  ▼
[3. RETRIEVE CONTEXT (RAG)]
  │  Input:  Query + product_area
  │  Output: Top 5 relevant knowledge base chunks with similarity scores
  │  Method: ChromaDB vector search with metadata filtering by product_area
  │  Fallback: If filtered search returns < 2 results, retry unfiltered
  │
  ▼
[4. GENERATE RESPONSE]
  │  Input:  Query + intent + urgency + product_area + retrieved contexts
  │  Output: Structured answer with sources and next steps
  │  Method: Groq LLM with context-grounded generation
  │  Style:  Simple language, numbered steps, empathetic tone (for tier-2/3 retailers)
  │
  ▼
[5. EVALUATE CONFIDENCE]
  │  Input:  Query + response + retrieved contexts
  │  Output: Confidence score (0.0 – 1.0), needs_escalation (bool)
  │  Method: LLM self-evaluation on 3 axes:
  │          - Relevance (30%): Does it address the query?
  │          - Completeness (30%): Does it cover all aspects?
  │          - Groundedness (40%): Is it based on retrieved context?
  │  Decision: confidence < 0.75 → ESCALATE
  │            urgency == critical → ALWAYS ESCALATE
  │
  ▼
[DECISION: ESCALATE?]
  │
  ├─── NO ──→ [DIRECT RESPONSE] → [CREATE LOG] → END
  │
  └─── YES ─→ [6. CREATE ESCALATION NOTE]
                │  Output: Priority, summary, recommended_action, assigned_team, SLA
                │  Team:   Rules-based assignment (security→"Security & Fraud", etc.)
                │  SLA:    CRITICAL=1hr, HIGH=4hr, MEDIUM=24hr, LOW=48hr
                │
                ▼
              [CREATE LOG] → END
```

## Tools & APIs Used

| Tool | Purpose | Free? |
|---|---|---|
| Groq API (Llama 3.3 70B) | LLM inference for classification, generation, evaluation | ✅ Free tier |
| ChromaDB | Vector storage + similarity search (RAG) | ✅ Open source |
| SQLite | Support log storage + analytics | ✅ Built-in |
| FastAPI | REST API server | ✅ Open source |
| LangGraph | Agent workflow orchestration | ✅ Open source |

## Input / Output Examples

### Input
```json
{"query": "My AePS transaction failed but customer's money was deducted. What should I do?"}
```

### Output (High Confidence → Direct Response)
```json
{
  "intent": "transaction_problem",
  "urgency": "high",
  "confidence": 0.92,
  "needs_escalation": false,
  "response": "If your AePS transaction failed but the customer's account was debited, follow these steps:\n1. Don't retry immediately — wait 15 minutes for auto-reversal\n2. Check transaction status using Transaction Inquiry in Eko Connect\n3. Note the transaction ID for records\n4. If not reversed in 24 hours — contact cs@eko.co.in\n5. Per RBI guidelines, failed AePS transactions are auto-reversed within 5 working days",
  "sources": ["aeps_troubleshooting.md"],
  "next_steps": "If auto-reversal doesn't happen in 5 days, escalate to cs@eko.co.in"
}
```

### Input
```json
{"query": "Someone is using my retailer account without my permission"}
```

### Output (Critical → Auto-Escalated)
```json
{
  "intent": "account_issue",
  "urgency": "critical",
  "confidence": 0.85,
  "needs_escalation": true,
  "response": "⚠️ This is a CRITICAL security issue. Immediate steps:\n1. Do NOT share your credentials with anyone\n2. Change your password immediately via Eko Connect\n3. This has been auto-escalated to Security team",
  "escalation": {
    "priority": "CRITICAL",
    "summary": "Retailer reports unauthorized transactions on their account",
    "recommended_action": "IMMEDIATE: Freeze retailer account, audit recent transactions",
    "assigned_team": "Security & Fraud",
    "sla": "1 hour"
  }
}
```

## Exception Handling

| Condition | Action |
|---|---|
| LLM API failure | Return cached/fallback response + log error |
| No relevant docs found | Set confidence to 0.3 + auto-escalate |
| JSON parsing error | Retry once, then use fallback classification |
| Confidence < 0.75 | Escalate with partial response + context |
| Urgency == critical | Always escalate, even if confident |
| Money/fraud/legal keywords | Auto-set urgency to CRITICAL |
| Database error | Continue without logging (response still delivered) |

## Autonomy Assessment

### What It Does Autonomously (v1.0)
- ✅ Classifies query intent and product area
- ✅ Assesses urgency (hybrid rules + LLM)
- ✅ Retrieves relevant knowledge via RAG
- ✅ Generates structured, actionable responses
- ✅ Self-evaluates response confidence
- ✅ Decides to respond or escalate
- ✅ Creates structured escalation notes
- ✅ Logs all interactions with full metadata

### What v2.0 Would Add
- Multi-turn conversation memory
- Learning from resolved escalations (feedback loop)
- Multi-language support (Hindi, Tamil, Telugu)
- Voice input processing
- Direct Eko API integration (real transaction status checks)
- Proactive monitoring (detect issue spikes before they escalate)
- Auto-resolution tracking and follow-up

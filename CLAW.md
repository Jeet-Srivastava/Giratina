# CLAW.md — Support Knowledge Claw Specification

## Claw Identity

| Field | Value |
|---|---|
| **Name** | Support Knowledge Claw |
| **Track** | Forward Deployed AI Accelerator |
| **Version** | 2.0.0 |
| **Author** | Jeet Srivastava |
| **Framework** | LangGraph + FastAPI + Claw tool contracts |
| **LLM** | Groq (Llama 3.3 70B Versatile) |

## Mission

Transform Eko's micro-entrepreneur support workflow into an autonomous AI agent that can handle retailer queries end-to-end — from understanding the problem to delivering actionable solutions or intelligently escalating to human agents.

## Workflow Definition

```
START
  │
  ▼
[0. LOAD RETAILER MEMORY + OPEN TICKET]
  │  Input:  query + retailer_id/session_id
  │  Output: memory_context + persistent support_log_id
  │  Method: SQLite lookup of recent queries, prior escalations, open/assigned tickets
  │  State:  Creates ticket with status=open before agent execution
  │
  ▼
[1. CLASSIFY INTENT]
  │  Input:  User query (text) + memory_context
  │  Output: intent (faq | technical_issue | transaction_problem | account_issue | feature_request)
  │          product_area (aeps | money_transfer | commission | account | general | security)
  │  Method: Groq LLM with structured JSON output
  │
  ▼
[2. ASSESS URGENCY]
  │  Input:  Query + intent + product_area + memory_context
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
  │  Input:  Query + intent + urgency + product_area + retrieved contexts + memory_context
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

## Formal Claw Runtime Mapping

The current LangGraph workflow is mapped into the formal Claw runtime surface through `backend/agent/contracts.py` and the API endpoints `/api/claw/manifest` and `/api/claw/tools`.

| Runtime | Mapping |
|---|---|
| **OpenClaw** | The LangGraph DAG is the OpenClaw state graph. `AgentState` maps to shared runtime memory, and every node is exported as a typed tool contract. |
| **NemoClaw** | Retrieval, RAG context, and multi-turn retailer memory map to NemoClaw knowledge/memory capabilities. |
| **NanoClaw** | Classification, urgency, and confidence evaluation can run as small stateless NanoClaw tools with JSON-schema inputs/outputs. |
| **Hermes Agent** | Escalation output maps to a Hermes handoff: priority, reason, summary, recommended action, assigned team, SLA, and lifecycle state. |

## Tool Contracts

Each node has an explicit contract with input schema, output schema, runtime targets, and failure policy:

| Tool | Runtime Targets | Key Output |
|---|---|---|
| `classify_intent` | OpenClaw, NanoClaw | `intent`, `product_area` |
| `assess_urgency` | OpenClaw, NanoClaw | `urgency` |
| `retrieve_context` | OpenClaw, NemoClaw | `retrieved_contexts[]` |
| `generate_response` | OpenClaw, NemoClaw | `response`, `sources`, `next_steps` |
| `evaluate_confidence` | OpenClaw, NanoClaw | `confidence`, `needs_escalation`, `escalation_reason` |
| `handle_escalation` | OpenClaw, Hermes Agent | `escalation_note`, `ticket_status=assigned` |

## Persistent Ticket Lifecycle

Support logs now behave as tickets with these states:

| State | Meaning |
|---|---|
| `open` | Ticket created before the graph executes |
| `assigned` | Low-confidence, critical, fraud/security, or unresolved issue assigned to a human team |
| `resolved` | Agent produced a high-confidence autonomous answer |
| `closed` | Admin or downstream workflow closes the ticket |

Lifecycle timestamps are persisted as `updated_at`, `assigned_at`, `resolved_at`, and `closed_at`. Admins can update state with `PATCH /api/logs/{log_id}/status`.

## Multi-Turn Memory

Before the graph runs, the API loads memory by `retailer_id` or `session_id`:

- recent queries
- escalation history
- open or assigned tickets

This `memory_context` is passed into classification, urgency, response generation, and escalation so follow-up questions can refer to a retailer's previous query and escalation history.

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

## Test Coverage Added in v2.0

- Low-confidence escalation
- LLM generation failure fallback
- JSON parsing failure fallback
- Retrieval failure escalation
- Critical fraud/security routing to Security & Fraud
- Claw manifest/tool contract API exposure
- Ticket lifecycle state update

## Autonomy Assessment

### What It Does Autonomously (v2.0)
- ✅ Classifies query intent and product area
- ✅ Assesses urgency (hybrid rules + LLM)
- ✅ Retrieves relevant knowledge via RAG
- ✅ Generates structured, actionable responses
- ✅ Self-evaluates response confidence
- ✅ Decides to respond or escalate
- ✅ Creates structured escalation notes
- ✅ Logs all interactions with full metadata
- ✅ Exposes Claw runtime manifest and tool contracts
- ✅ Persists open, assigned, resolved, and closed lifecycle states
- ✅ Uses multi-turn retailer memory and escalation history

### What a Future Version Would Add
- Multi-language support (Hindi, Tamil, Telugu)
- Learning from resolved escalations (feedback loop)
- Voice input processing
- Direct Eko API integration (real transaction status checks)
- Proactive monitoring (detect issue spikes before they escalate)
- Auto-resolution tracking and follow-up

# Support Knowledge Claw 🦀

> **Autonomous AI Support Agent for Eko Micro-Entrepreneurs**
>
> An intelligent agent that handles support queries from Eko's 150,000+ micro-entrepreneur retailers — classifying intent, retrieving knowledge, generating actionable responses, evaluating confidence, and escalating when needed.

## 🎯 What It Does

The Support Knowledge Claw is an **Autonomous AI Agent** that transforms Eko's support workflow into an agentic system:

1. **Receives** a support query from a retailer
2. **Classifies** intent (FAQ, Technical, Transaction, Account, Feature Request)
3. **Assesses urgency** (Low → Critical) using rules + LLM hybrid
4. **Retrieves** relevant context via RAG from the knowledge base
5. **Generates** a structured, actionable response
6. **Self-evaluates** confidence (relevance, completeness, groundedness)
7. **Decides**: respond directly (high confidence) or escalate (low confidence / critical urgency)
8. **Logs** every interaction with full metadata

## 🏗️ Architecture

```
User Query → Retailer Memory → Open Ticket → Intent Classifier → Urgency Assessor → RAG Retriever
    → Response Generator → Confidence Evaluator → [Respond / Escalate]
    → Lifecycle Update → Support Log → Analytics
```

## Claw Runtime Mapping

This version exposes the LangGraph implementation as a formal Claw runtime manifest:

| Runtime | Mapping |
|---|---|
| OpenClaw | Stateful DAG orchestration. Each LangGraph node is exported as a typed tool contract. |
| NemoClaw | Knowledge and memory runtime for retrieval, RAG context, and retailer history. |
| NanoClaw | Lightweight local execution for stateless tools like classification, urgency, and confidence checks. |
| Hermes Agent | Human handoff runtime for structured escalation notes, assigned team, SLA, and ticket status. |

Runtime metadata is available from the running API:

| Endpoint | Purpose |
|---|---|
| `/api/claw/manifest` | Full workflow mapping, lifecycle states, memory policy, and tool contracts |
| `/api/claw/tools` | Input/output JSON schemas for every node/tool |

Each node now has an explicit contract in `backend/agent/contracts.py`, including input schema, output schema, runtime targets, and failure policy.

## Ticket Lifecycle & Memory

Every chat request creates a persistent ticket in `open` state before the graph runs. After evaluation:

| Outcome | Ticket State |
|---|---|
| Agent resolves confidently | `resolved` |
| Low confidence or critical issue | `assigned` |
| Manual/admin closure | `closed` |

The admin API can update lifecycle state with `PATCH /api/logs/{log_id}/status`.

Multi-turn memory is loaded by `retailer_id` or `session_id` before graph execution. The agent remembers recent queries, previous escalations, and open/assigned tickets, then passes that context into classification, urgency assessment, response generation, and escalation.

**Tech Stack:**

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| Agent Engine | LangGraph |
| LLM | Groq (Llama 3.3 70B) |
| Embeddings | ChromaDB default (ONNX) |
| Vector Store | ChromaDB |
| Database | SQLite (async) |
| Frontend | Vanilla HTML/CSS/JS |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- A free Groq API key from [console.groq.com](https://console.groq.com)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/support-knowledge-claw.git
cd support-knowledge-claw

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Run the server (auto-ingests knowledge base on first run)
python -m backend.main
```

### Access

| URL | Description |
|---|---|
| http://localhost:8000 | 💬 Chat Interface |
| http://localhost:8000/admin | 📊 Admin Dashboard |
| http://localhost:8000/docs | 📖 API Documentation |

## 🧪 Testing

```bash
# Run unit tests (no API key needed)
pytest tests/test_agent.py -v

# Run API tests (no API key needed)
pytest tests/test_api.py -v

# Run full accuracy benchmark (needs API key)
python -m scripts.benchmark_accuracy

# Test a single query via curl
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "My AePS transaction failed but money was deducted"}'
```

The test suite includes coverage for low-confidence escalation, LLM failure fallback, JSON parsing fallback, retrieval failure escalation, critical fraud/security escalation, Claw manifest exposure, and ticket lifecycle updates.

## 🐳 Docker

```bash
# Build and run
docker-compose up --build

# Or without compose
docker build -t support-claw .
docker run -p 8000:8000 --env-file .env support-claw
```

## 📁 Project Structure

```
claw/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings
│   ├── database.py           # SQLite setup
│   ├── models.py             # Pydantic models
│   ├── agent/
│   │   ├── graph.py          # LangGraph workflow
│   │   ├── state.py          # Agent state
│   │   ├── prompts.py        # Prompt templates
│   │   └── nodes/            # Agent nodes
│   │       ├── classifier.py # Intent classification
│   │       ├── urgency.py    # Urgency assessment
│   │       ├── retriever.py  # RAG retrieval
│   │       ├── generator.py  # Response generation
│   │       ├── evaluator.py  # Confidence evaluation
│   │       └── escalation.py # Escalation engine
│   ├── knowledge/
│   │   ├── ingestion.py      # Document loader
│   │   └── store.py          # ChromaDB wrapper
│   ├── services/
│   │   ├── support_log.py    # Log CRUD
│   │   └── analytics.py      # Dashboard stats
│   └── routers/
│       ├── chat.py           # Chat endpoint
│       ├── admin.py          # Admin endpoints
│       └── knowledge.py      # Knowledge management
├── frontend/
│   ├── index.html            # Chat UI
│   ├── admin.html            # Admin dashboard
│   ├── css/styles.css        # Premium dark theme
│   └── js/
│       ├── chat.js           # Chat logic
│       └── admin.js          # Dashboard logic
├── data/knowledge_base/      # Support documents
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── CLAW.md                   # Claw specification
├── Dockerfile                # Docker build
└── docker-compose.yml        # Docker orchestration
```

The knowledge base includes Eko-specific scenarios for CSP/retailer operations, AePS, DMT, settlement delays, KYC, wallet block, commission disputes, fraud, and escalation policy.

## 📄 License

MIT

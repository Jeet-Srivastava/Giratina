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
User Query → Intent Classifier → Urgency Assessor → RAG Retriever
    → Response Generator → Confidence Evaluator → [Respond / Escalate]
    → Support Log → Analytics
```

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

## 📄 License

MIT

"""
Formal Claw runtime contracts for the support agent nodes.

The production implementation still executes through LangGraph, but each
node is described here as an explicit tool with JSON schemas so it can be
registered in OpenClaw, NemoClaw, NanoClaw, or Hermes Agent runtimes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryTurn(BaseModel):
    query: str = ""
    intent: str = "unknown"
    product_area: str = "general"
    status: str = "open"
    needs_escalation: bool = False
    created_at: str = ""


class MemoryEscalation(BaseModel):
    query: str = ""
    escalation_reason: str = ""
    assigned_team: str = ""
    status: str = "assigned"
    created_at: str = ""


class RetailerMemoryContext(BaseModel):
    retailer_id: str = ""
    session_id: str = ""
    recent_queries: list[MemoryTurn] = Field(default_factory=list)
    escalation_history: list[MemoryEscalation] = Field(default_factory=list)
    open_tickets: list[MemoryTurn] = Field(default_factory=list)


class AgentToolInput(BaseModel):
    query: str
    retailer_id: str = ""
    session_id: str = ""
    memory_context: RetailerMemoryContext = Field(default_factory=RetailerMemoryContext)


class ClassifyIntentInput(AgentToolInput):
    pass


class ClassifyIntentOutput(BaseModel):
    intent: str
    product_area: str
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class AssessUrgencyInput(AgentToolInput):
    intent: str = "unknown"
    product_area: str = "general"


class AssessUrgencyOutput(BaseModel):
    urgency: str
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class RetrievedContextContract(BaseModel):
    content: str
    source: str
    relevance_score: float


class RetrieveContextInput(AgentToolInput):
    product_area: str = "general"


class RetrieveContextOutput(BaseModel):
    retrieved_contexts: list[RetrievedContextContract] = Field(default_factory=list)
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class GenerateResponseInput(AgentToolInput):
    intent: str = "unknown"
    urgency: str = "medium"
    product_area: str = "general"
    retrieved_contexts: list[RetrievedContextContract] = Field(default_factory=list)


class GenerateResponseOutput(BaseModel):
    response: str
    sources: list[str] = Field(default_factory=list)
    next_steps: str = ""
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class EvaluateConfidenceInput(AgentToolInput):
    intent: str = "unknown"
    urgency: str = "medium"
    response: str = ""
    retrieved_contexts: list[RetrievedContextContract] = Field(default_factory=list)


class EvaluateConfidenceOutput(BaseModel):
    confidence: float
    needs_escalation: bool
    escalation_reason: str = ""
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class HandleEscalationInput(AgentToolInput):
    intent: str = "unknown"
    urgency: str = "medium"
    product_area: str = "general"
    confidence: float = 0.0
    escalation_reason: str = ""
    response: str = ""


class EscalationNoteContract(BaseModel):
    priority: str
    summary: str
    recommended_action: str
    assigned_team: str
    sla: str = ""


class HandleEscalationOutput(BaseModel):
    escalation_note: EscalationNoteContract
    ticket_status: str = "assigned"
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)


class ToolContract(BaseModel):
    name: str
    description: str
    langgraph_node: str
    runtime_targets: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    failure_policy: str


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()


def get_tool_contracts() -> list[dict[str, Any]]:
    """Return explicit input/output schemas for each agent node."""
    contracts = [
        ToolContract(
            name="classify_intent",
            description="Classify retailer query intent and Eko product area.",
            langgraph_node="classify_intent",
            runtime_targets=["OpenClaw", "NanoClaw"],
            input_schema=_schema(ClassifyIntentInput),
            output_schema=_schema(ClassifyIntentOutput),
            failure_policy="Fallback to intent=unknown and product_area=general on LLM or JSON parsing failure.",
        ),
        ToolContract(
            name="assess_urgency",
            description="Assign urgency using deterministic security/money rules plus LLM assessment.",
            langgraph_node="assess_urgency",
            runtime_targets=["OpenClaw", "NanoClaw"],
            input_schema=_schema(AssessUrgencyInput),
            output_schema=_schema(AssessUrgencyOutput),
            failure_policy="Use keyword urgency if present, otherwise default to medium.",
        ),
        ToolContract(
            name="retrieve_context",
            description="Retrieve product-specific Eko knowledge base context from ChromaDB.",
            langgraph_node="retrieve_context",
            runtime_targets=["OpenClaw", "NemoClaw"],
            input_schema=_schema(RetrieveContextInput),
            output_schema=_schema(RetrieveContextOutput),
            failure_policy="Return zero contexts; confidence evaluator must escalate retrieval failures.",
        ),
        ToolContract(
            name="generate_response",
            description="Generate a grounded support answer using RAG context and retailer memory.",
            langgraph_node="generate_response",
            runtime_targets=["OpenClaw", "NemoClaw"],
            input_schema=_schema(GenerateResponseInput),
            output_schema=_schema(GenerateResponseOutput),
            failure_policy="Return a safe support-channel fallback and preserve escalation path.",
        ),
        ToolContract(
            name="evaluate_confidence",
            description="Score relevance, completeness, and groundedness to decide escalation.",
            langgraph_node="evaluate_confidence",
            runtime_targets=["OpenClaw", "NanoClaw"],
            input_schema=_schema(EvaluateConfidenceInput),
            output_schema=_schema(EvaluateConfidenceOutput),
            failure_policy="Escalate conservatively at confidence=0.50 on evaluator failure.",
        ),
        ToolContract(
            name="handle_escalation",
            description="Create Hermes-compatible handoff note and assign the owning support team.",
            langgraph_node="handle_escalation",
            runtime_targets=["OpenClaw", "Hermes Agent"],
            input_schema=_schema(HandleEscalationInput),
            output_schema=_schema(HandleEscalationOutput),
            failure_policy="Use rules-based priority, team assignment, and SLA if LLM handoff writing fails.",
        ),
    ]
    return [contract.model_dump() for contract in contracts]


def get_claw_manifest() -> dict[str, Any]:
    """Return the formal runtime mapping for the current LangGraph workflow."""
    return {
        "name": "Support Knowledge Claw",
        "version": "2.0.0",
        "implementation": "LangGraph + FastAPI",
        "workflow": [
            "classify_intent",
            "assess_urgency",
            "retrieve_context",
            "generate_response",
            "evaluate_confidence",
            "handle_escalation",
        ],
        "runtime_mapping": {
            "OpenClaw": "Stateful DAG orchestration. The LangGraph state maps 1:1 to OpenClaw shared memory, and each graph node is exported as a typed tool contract.",
            "NemoClaw": "Knowledge and memory runtime. retrieve_context reads the Eko KB, generate_response consumes retrieved contexts plus retailer memory.",
            "NanoClaw": "Lightweight local tool runtime. classify_intent, assess_urgency, and evaluate_confidence can run as independent stateless tools with the schemas below.",
            "Hermes Agent": "Human handoff runtime. handle_escalation emits a structured ticket note, assigned team, SLA, and assigned lifecycle status.",
        },
        "state_model": {
            "input": ["query", "retailer_id", "session_id", "memory_context"],
            "persistent_ticket_states": ["open", "assigned", "resolved", "closed"],
            "memory_policy": "Recent queries, prior escalations, and open/assigned tickets are loaded by retailer_id or session_id before graph execution.",
        },
        "tool_contracts": get_tool_contracts(),
    }

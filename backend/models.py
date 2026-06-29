"""
Pydantic models for API requests, responses, and internal data structures.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────

class Intent(str, Enum):
    FAQ = "faq"
    TECHNICAL_ISSUE = "technical_issue"
    TRANSACTION_PROBLEM = "transaction_problem"
    ACCOUNT_ISSUE = "account_issue"
    FEATURE_REQUEST = "feature_request"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── API Request / Response ────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat request from a retailer."""
    query: str = Field(..., min_length=1, max_length=2000, description="Support query text")
    retailer_id: Optional[str] = Field(None, description="Optional retailer identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


class RetrievedContext(BaseModel):
    """A single retrieved knowledge base chunk."""
    content: str
    source: str
    relevance_score: float


class EscalationNote(BaseModel):
    """Structured escalation details."""
    priority: EscalationPriority
    reason: str
    summary: str
    recommended_action: str
    assigned_team: str
    sla: Optional[str] = None


class AgentStep(BaseModel):
    """A single step in the agent's reasoning chain."""
    step: str
    result: str
    duration_ms: Optional[int] = None


class ChatResponse(BaseModel):
    """Full response from the agent."""
    query: str
    intent: Intent
    urgency: Urgency
    product_area: str = ""
    response: str
    sources: list[str] = []
    confidence: float
    needs_escalation: bool
    escalation: Optional[EscalationNote] = None
    next_steps: str = ""
    support_log_id: Optional[int] = None
    agent_steps: list[AgentStep] = []


# ── Database Models ───────────────────────────────────

class SupportLogCreate(BaseModel):
    """Data needed to create a support log."""
    query: str
    intent: str
    urgency: str
    product_area: str = ""
    response: str
    confidence: float
    needs_escalation: bool
    escalation_reason: str = ""
    escalation_priority: str = ""
    assigned_team: str = ""
    retailer_id: str = ""
    session_id: str = ""
    sources: str = ""


class SupportLogResponse(BaseModel):
    """Support log response for the admin API."""
    id: int
    query: str
    intent: str
    urgency: str
    product_area: str
    response: str
    confidence: float
    needs_escalation: bool
    escalation_reason: str
    escalation_priority: str
    assigned_team: str
    retailer_id: str
    sources: str
    created_at: str
    status: str


class AnalyticsSummary(BaseModel):
    """Dashboard analytics summary."""
    total_queries: int = 0
    total_escalations: int = 0
    escalation_rate: float = 0.0
    avg_confidence: float = 0.0
    intent_distribution: dict[str, int] = {}
    urgency_distribution: dict[str, int] = {}
    recent_queries: list[SupportLogResponse] = []


class KnowledgeSearchRequest(BaseModel):
    """Search the knowledge base."""
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    """Knowledge base search results."""
    query: str
    results: list[RetrievedContext]
    total_documents: int = 0

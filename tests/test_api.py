"""
Tests for the FastAPI endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database import init_db
from backend.services.support_log import create_open_ticket, get_log_by_id, get_retailer_memory


@pytest_asyncio.fixture
async def client():
    """Create a test client."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    """Test the health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Support Knowledge Claw"
    assert "knowledge_base" in data


@pytest.mark.asyncio
async def test_knowledge_status(client):
    """Test knowledge base status endpoint."""
    response = await client.get("/api/knowledge/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_chunks" in data


@pytest.mark.asyncio
async def test_logs_empty(client):
    """Test logs endpoint when empty."""
    response = await client.get("/api/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_escalations_empty(client):
    """Test escalations endpoint when empty."""
    response = await client.get("/api/escalations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_analytics_empty(client):
    """Test analytics endpoint when empty."""
    response = await client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "escalation_rate" in data


@pytest.mark.asyncio
async def test_chat_validation(client):
    """Test chat endpoint validates input."""
    response = await client.post("/api/chat", json={"query": ""})
    assert response.status_code == 422  # Validation error for empty query


@pytest.mark.asyncio
async def test_cors_headers(client):
    """Test CORS headers are present."""
    response = await client.get("/api/health")
    assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_claw_manifest_exposes_tool_contracts(client):
    """Test formal Claw runtime metadata is available."""
    response = await client.get("/api/claw/manifest")
    assert response.status_code == 200
    data = response.json()
    assert "runtime_mapping" in data
    assert "OpenClaw" in data["runtime_mapping"]
    assert {tool["name"] for tool in data["tool_contracts"]} >= {
        "classify_intent",
        "assess_urgency",
        "retrieve_context",
        "generate_response",
        "evaluate_confidence",
        "handle_escalation",
    }


@pytest.mark.asyncio
async def test_ticket_lifecycle_status_update(client):
    """Test persisted ticket lifecycle states can move to closed."""
    log_id = await create_open_ticket(
        query="Wallet is blocked",
        retailer_id="retailer-test",
        session_id="session-test",
    )
    open_log = await get_log_by_id(log_id)
    assert open_log.status == "open"
    memory = await get_retailer_memory(retailer_id="retailer-test", session_id="session-test")
    assert any(item["query"] == "Wallet is blocked" for item in memory["recent_queries"])
    assert any(item["status"] == "open" for item in memory["open_tickets"])

    response = await client.patch(f"/api/logs/{log_id}/status", json={"status": "closed"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_at"]

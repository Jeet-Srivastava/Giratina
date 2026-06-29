"""
Tests for the FastAPI endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database import init_db


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

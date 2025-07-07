"""Tests for health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Test health check endpoint returns valid response."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "search_engine" in data
    assert "cache_hit_rate" in data
    assert "uptime_seconds" in data
    
    # Validate data types
    assert isinstance(data["status"], str)
    assert isinstance(data["database"], str)
    assert isinstance(data["search_engine"], str)
    assert isinstance(data["cache_hit_rate"], (int, float))
    assert isinstance(data["uptime_seconds"], int)
    
    # Validate ranges
    assert 0.0 <= data["cache_hit_rate"] <= 1.0
    assert data["uptime_seconds"] >= 0


def test_health_response_headers(client: TestClient) -> None:
    """Test health endpoint includes proper response headers."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    assert "X-Request-ID" in response.headers
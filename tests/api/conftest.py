"""Test configuration and fixtures for API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.floridify.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_word() -> str:
    """Sample word for testing."""
    return "test"


@pytest.fixture
def sample_search_query() -> str:
    """Sample search query for testing."""
    return "cogn"
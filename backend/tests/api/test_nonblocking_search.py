"""Tests for non-blocking search engine initialization and per-corpus semantic search.

Tests:
1. Health endpoint is non-blocking during search engine init
2. Semantic status endpoint is non-blocking
3. SEMANTIC_SEARCH_ENABLED=false disables global semantic
4. Per-corpus semantic search works even when global semantic is disabled
5. Search works during/after background init
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set SEMANTIC_SEARCH_ENABLED=false before importing the app
os.environ["SEMANTIC_SEARCH_ENABLED"] = "false"


@pytest_asyncio.fixture
async def async_client(test_db):
    """Create async HTTP client for API testing."""
    from floridify.api.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def reset_search_manager():
    """Reset SearchEngineManager state before each test."""
    from floridify.core.search_pipeline import get_search_engine_manager

    manager = get_search_engine_manager()
    await manager.reset()
    yield manager
    await manager.reset()


class TestHealthEndpointNonBlocking:
    """Health endpoint should return immediately without triggering search init."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy_before_search_init(
        self, async_client, reset_search_manager
    ):
        """Health endpoint returns healthy even when search engine is uninitialized."""
        manager = reset_search_manager
        # Ensure engine is not initialized
        assert manager._engine is None

        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["search_engine"] in ("uninitialized", "initializing")
        # Engine should still be None — health check didn't trigger init
        assert manager._engine is None

    @pytest.mark.asyncio
    async def test_health_shows_initializing_during_background_init(
        self, async_client, reset_search_manager
    ):
        """Health shows 'initializing' when background init is running."""
        manager = reset_search_manager
        # Simulate initializing state
        manager._initializing = True

        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["search_engine"] == "initializing"

        # Clean up
        manager._initializing = False

    @pytest.mark.asyncio
    async def test_health_shows_error_on_init_failure(
        self, async_client, reset_search_manager
    ):
        """Health shows 'error' and 'degraded' when init failed."""
        manager = reset_search_manager
        manager._init_error = "Test error: model load failed"

        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["search_engine"] == "error"

        # Clean up
        manager._init_error = None


class TestSemanticStatusEndpointNonBlocking:
    """Semantic status endpoint should not trigger search engine init."""

    @pytest.mark.asyncio
    async def test_semantic_status_returns_without_init(
        self, async_client, reset_search_manager
    ):
        """Semantic status returns immediately without triggering init."""
        manager = reset_search_manager
        assert manager._engine is None

        response = await async_client.get("/api/v1/search/semantic/status")
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] is False  # SEMANTIC_SEARCH_ENABLED=false
        assert data["ready"] is False
        assert data["building"] is False
        # Engine should still be None
        assert manager._engine is None

    @pytest.mark.asyncio
    async def test_semantic_status_shows_building_during_init(
        self, async_client, reset_search_manager
    ):
        """Semantic status shows building=True during background init."""
        manager = reset_search_manager
        manager._initializing = True

        response = await async_client.get("/api/v1/search/semantic/status")
        assert response.status_code == 200

        data = response.json()
        assert data["building"] is True
        assert "initializing" in data["message"].lower()

        # Clean up
        manager._initializing = False


class TestSemanticSearchEnabled:
    """SEMANTIC_SEARCH_ENABLED env var controls global semantic search."""

    @pytest.mark.asyncio
    async def test_semantic_disabled_by_env(self):
        """_semantic_search_enabled() returns False when env var is false."""
        from floridify.search.language import _semantic_search_enabled

        with patch.dict(os.environ, {"SEMANTIC_SEARCH_ENABLED": "false"}):
            assert _semantic_search_enabled() is False

    @pytest.mark.asyncio
    async def test_semantic_enabled_by_env(self):
        """_semantic_search_enabled() returns True when env var is true."""
        from floridify.search.language import _semantic_search_enabled

        with patch.dict(os.environ, {"SEMANTIC_SEARCH_ENABLED": "true"}):
            assert _semantic_search_enabled() is True

    @pytest.mark.asyncio
    async def test_semantic_enabled_by_default(self):
        """_semantic_search_enabled() returns True when env var is unset."""
        from floridify.search.language import _semantic_search_enabled

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEMANTIC_SEARCH_ENABLED", None)
            assert _semantic_search_enabled() is True

    @pytest.mark.asyncio
    async def test_manager_uses_env_var(self):
        """SearchEngineManager defaults semantic from env var."""
        from floridify.core.search_pipeline import SearchEngineManager

        with patch.dict(os.environ, {"SEMANTIC_SEARCH_ENABLED": "false"}):
            manager = SearchEngineManager()
            assert manager._semantic is False

        with patch.dict(os.environ, {"SEMANTIC_SEARCH_ENABLED": "true"}):
            manager = SearchEngineManager()
            assert manager._semantic is True


class TestPerCorpusSemantic:
    """Per-corpus semantic search works independently of global setting."""

    @pytest.mark.asyncio
    async def test_create_corpus_with_semantic(self, async_client, test_db):
        """Create a corpus with enable_semantic=True even when global is disabled."""
        response = await async_client.post(
            "/api/v1/corpus",
            json={
                "name": "test-semantic-corpus",
                "language": "en",
                "source_type": "custom",
                "vocabulary": [
                    "happy",
                    "joyful",
                    "elated",
                    "sad",
                    "gloomy",
                    "melancholy",
                    "angry",
                    "furious",
                    "calm",
                    "serene",
                ],
                "enable_semantic": True,
                "ttl_hours": 1.0,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "test-semantic-corpus"
        assert data["vocabulary_size"] == 10
        corpus_id = data["id"]

        # Search within this corpus using exact mode (should work regardless of semantic)
        search_response = await async_client.get(
            "/api/v1/search",
            params={
                "q": "happy",
                "corpus_name": "test-semantic-corpus",
                "mode": "exact",
            },
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_found"] >= 1
        assert any(r["word"] == "happy" for r in search_data["results"])

    @pytest.mark.asyncio
    async def test_search_corpus_fuzzy(self, async_client, test_db):
        """Fuzzy search works on per-corpus search."""
        # Create corpus
        create_response = await async_client.post(
            "/api/v1/corpus",
            json={
                "name": "test-fuzzy-corpus",
                "language": "en",
                "source_type": "custom",
                "vocabulary": [
                    "beautiful",
                    "gorgeous",
                    "stunning",
                    "lovely",
                    "exquisite",
                    "magnificent",
                    "splendid",
                    "wonderful",
                    "fantastic",
                    "marvelous",
                ],
                "enable_semantic": False,
                "ttl_hours": 1.0,
            },
        )
        assert create_response.status_code == 201

        # Fuzzy search
        search_response = await async_client.get(
            "/api/v1/search",
            params={
                "q": "beautful",  # typo — should fuzzy match "beautiful"
                "corpus_name": "test-fuzzy-corpus",
                "mode": "fuzzy",
                "min_score": "0.5",
            },
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_found"] >= 1
        assert any(r["word"] == "beautiful" for r in search_data["results"])


class TestBackgroundInit:
    """Background init lifecycle."""

    @pytest.mark.asyncio
    async def test_start_background_init(self, test_db, reset_search_manager):
        """start_background_init() sets initializing state and starts task."""
        manager = reset_search_manager
        assert manager._init_task is None
        assert manager._initializing is False

        await manager.start_background_init()
        assert manager._init_task is not None
        assert manager._initializing is True

        # Wait for it to complete
        await manager._init_task
        assert manager._initializing is False

    @pytest.mark.asyncio
    async def test_start_background_init_idempotent(self, test_db, reset_search_manager):
        """Calling start_background_init twice doesn't create duplicate tasks."""
        manager = reset_search_manager

        await manager.start_background_init()
        first_task = manager._init_task

        await manager.start_background_init()
        assert manager._init_task is first_task  # Same task

        # Wait for completion
        await manager._init_task

    @pytest.mark.asyncio
    async def test_get_engine_waits_for_background(self, test_db, reset_search_manager):
        """get_engine() awaits background init instead of starting new one."""
        manager = reset_search_manager

        # Start background init
        await manager.start_background_init()

        # get_engine should await the running task
        engine = await manager.get_engine()
        assert engine is not None
        assert manager._engine is not None

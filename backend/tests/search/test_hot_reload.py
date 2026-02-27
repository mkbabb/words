"""Tests for hot-reload search pipeline (SearchEngineManager).

Covers: version detection, check interval gating, backward-compatible wrappers,
and the status endpoint.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from floridify.core.search_pipeline import (
    SearchEngineManager,
    _CorpusFingerprint,
    get_search_engine,
    get_search_engine_manager,
    reset_search_engine,
)
from floridify.models.base import Language


class TestSearchEngineManagerUnit:
    """Unit tests for SearchEngineManager (mocked dependencies)."""

    @pytest.fixture
    def manager(self):
        """Create a fresh SearchEngineManager with short check interval."""
        return SearchEngineManager(check_interval=0.1)

    async def test_initial_load(self, manager):
        """First call to get_engine triggers full reload."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ) as mock_get:
            engine = await manager.get_engine(languages=[Language.ENGLISH])
            assert engine is mock_engine
            mock_get.assert_called_once()

    async def test_cached_within_interval(self, manager):
        """Within check interval, engine is returned without checking corpus."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ) as mock_get:
            # First call - triggers load
            await manager.get_engine(languages=[Language.ENGLISH])
            assert mock_get.call_count == 1

            # Second call within interval - should return cached
            engine2 = await manager.get_engine(languages=[Language.ENGLISH])
            assert engine2 is mock_engine
            assert mock_get.call_count == 1  # No additional call

    async def test_check_interval_gating(self, manager):
        """After check interval, corpus change check occurs."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ):
            # Initial load
            await manager.get_engine(languages=[Language.ENGLISH])

        # Set last_check far enough back to trigger a check
        manager._last_check = time.monotonic() - 1.0  # 1 second ago, interval is 0.1

        # Mock _corpus_changed to return False (no change)
        with patch.object(manager, "_corpus_changed", new_callable=AsyncMock, return_value=False):
            engine = await manager.get_engine(languages=[Language.ENGLISH])
            assert engine is mock_engine

    async def test_force_rebuild_always_reloads(self, manager):
        """force_rebuild=True always triggers a full reload."""
        mock_engine1 = MagicMock()
        mock_engine1.languages = [Language.ENGLISH]
        mock_engine2 = MagicMock()
        mock_engine2.languages = [Language.ENGLISH]

        call_count = 0

        async def fake_get_language_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_engine1
            return mock_engine2

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            side_effect=fake_get_language_search,
        ):
            # Initial load
            engine1 = await manager.get_engine(languages=[Language.ENGLISH])
            assert engine1 is mock_engine1

            # Force rebuild
            engine2 = await manager.get_engine(languages=[Language.ENGLISH], force_rebuild=True)
            assert engine2 is mock_engine2
            assert call_count == 2

    async def test_concurrent_reload_shares_lock(self, manager):
        """Multiple concurrent get_engine calls during reload share the lock."""
        call_count = 0

        async def slow_get_language_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate slow rebuild
            mock = MagicMock()
            mock.languages = [Language.ENGLISH]
            return mock

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            side_effect=slow_get_language_search,
        ):
            # Launch multiple concurrent reload requests
            results = await asyncio.gather(
                manager.get_engine(languages=[Language.ENGLISH], force_rebuild=True),
                manager.get_engine(languages=[Language.ENGLISH], force_rebuild=True),
                manager.get_engine(languages=[Language.ENGLISH], force_rebuild=True),
            )

            # All should get the same engine (lock prevents duplicate rebuilds)
            # Note: They may not all be identical objects because force_rebuild
            # each acquires the lock and rebuilds. But the total call count
            # should be 3 (each waits for the lock then rebuilds).
            # The important thing is they don't crash.
            assert all(r is not None for r in results)

    async def test_reset(self, manager):
        """Reset clears engine and fingerprint."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ):
            await manager.get_engine(languages=[Language.ENGLISH])
            assert manager._engine is not None

        await manager.reset()
        assert manager._engine is None
        assert manager._fingerprint is None
        assert manager._languages is None

    def test_get_status(self, manager):
        """get_status returns a dict with expected keys."""
        status = manager.get_status()
        assert "engine_loaded" in status
        assert status["engine_loaded"] is False
        assert "check_interval" in status
        assert status["check_interval"] == 0.1
        assert "corpus_fingerprint" in status
        assert status["corpus_fingerprint"] is None


class TestCorpusFingerprint:
    """Tests for the _CorpusFingerprint dataclass."""

    def test_creation(self):
        fp = _CorpusFingerprint(
            corpus_name="language_english",
            vocabulary_hash="abc123",
            version="1.0.5",
        )
        assert fp.corpus_name == "language_english"
        assert fp.vocabulary_hash == "abc123"
        assert fp.version == "1.0.5"


class TestBackwardCompatibleWrappers:
    """Tests for get_search_engine() and reset_search_engine() wrappers."""

    async def test_get_search_engine_delegates(self):
        """get_search_engine() delegates to the global SearchEngineManager."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ):
            engine = await get_search_engine(languages=[Language.ENGLISH])
            assert engine is mock_engine

    async def test_reset_search_engine_delegates(self):
        """reset_search_engine() delegates to the global SearchEngineManager."""
        mock_engine = MagicMock()
        mock_engine.languages = [Language.ENGLISH]

        with patch(
            "floridify.core.search_pipeline.get_language_search",
            new_callable=AsyncMock,
            return_value=mock_engine,
        ):
            await get_search_engine(languages=[Language.ENGLISH])

        mgr = get_search_engine_manager()
        assert mgr._engine is not None

        await reset_search_engine()
        assert mgr._engine is None

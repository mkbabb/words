"""
Comprehensive tests for CLI search commands.

Tests the search index initialization, fuzzy search, semantic search,
and all search engine functionality through the CLI.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.floridify.cli.commands.search import (
    _search_init_async,
    search_group,
)
from src.floridify.search import Language, SearchEngine, SearchMethod, SearchResult


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_search_result():
    """Create mock search result for testing."""
    return SearchResult(
        word="test", score=0.95, method=SearchMethod.EXACT, is_phrase=False, metadata=None
    )


@pytest.fixture
def mock_search_engine():
    """Create mock search engine for testing."""
    engine = AsyncMock(spec=SearchEngine)
    engine.search.return_value = []
    engine.get_search_stats.return_value = {
        "exact": {"count": 0, "total_time": 0.0, "avg_time": 0.0},
        "fuzzy": {"count": 0, "total_time": 0.0, "avg_time": 0.0},
        "semantic": {"count": 0, "total_time": 0.0, "avg_time": 0.0},
    }
    engine.lexicon_loader = None
    engine.trie_search = None
    engine.semantic_search = None
    return engine


class TestSearchInit:
    """Test search index initialization."""

    @pytest.mark.asyncio
    async def test_search_init_async_basic(self):
        """Test basic search initialization."""
        with (
            patch("src.floridify.cli.commands.search.SearchEngine") as mock_engine_class,
            patch("src.floridify.cli.commands.search.Path") as mock_path_class,
            patch("src.floridify.cli.commands.search.console") as mock_console,
        ):
            # Setup mocks
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            mock_engine = AsyncMock()
            mock_engine.lexicon_loader = None
            mock_engine.trie_search = None
            mock_engine.semantic_search = None
            mock_engine_class.return_value = mock_engine

            # Execute initialization
            await _search_init_async(
                cache_dir="data/search", languages=("en",), enable_semantic=True, force=False
            )

            # Verify calls
            mock_engine_class.assert_called_once()
            call_kwargs = mock_engine_class.call_args.kwargs
            assert str(call_kwargs["cache_dir"]) == "data/search"
            assert call_kwargs["languages"] == [Language.ENGLISH]
            assert call_kwargs["enable_semantic"] is True

            mock_engine.initialize.assert_called_once()
            mock_engine.close.assert_called_once()

    def test_search_init_command_basic(self, cli_runner):
        """Test basic search init command."""
        with patch("src.floridify.cli.commands.search._search_init_async") as mock_init:
            result = cli_runner.invoke(search_group, ["init"])

            assert result.exit_code == 0
            mock_init.assert_called_once()

    def test_search_find_command_basic(self, cli_runner):
        """Test basic search find command."""
        with patch("src.floridify.cli.commands.search._search_find_async") as mock_find:
            result = cli_runner.invoke(search_group, ["find", "hello"])

            assert result.exit_code == 0
            mock_find.assert_called_once()

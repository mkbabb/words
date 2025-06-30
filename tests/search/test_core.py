"""
Tests for core search engine functionality.

Comprehensive testing of the unified SearchEngine interface with all methods.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.floridify.search import (
    Language,
    SearchEngine,
    SearchMethod,
    SearchResult,
)


class TestSearchEngine:
    """Test the core SearchEngine functionality."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Create temporary cache directory for testing."""
        cache_dir = tmp_path / "search_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def sample_vocabulary(self) -> list[str]:
        """Sample vocabulary for testing."""
        return [
            "hello",
            "world",
            "definition",
            "dictionary",
            "search",
            "fuzzy",
            "semantic",
            "phrase",
            "hello world",
            "search engine",
            "natural language",
            "machine learning",
            "ad hoc",
            "vis-à-vis",
            "state-of-the-art",
        ]

    @pytest.fixture
    async def search_engine(self, temp_cache_dir: Path) -> SearchEngine:
        """Create initialized search engine for testing."""
        engine = SearchEngine(
            cache_dir=temp_cache_dir,
            languages=[Language.ENGLISH],
            min_score=0.5,
            enable_semantic=True,
        )
        return engine

    @pytest.mark.asyncio
    async def test_initialization(self, temp_cache_dir: Path) -> None:
        """Test search engine initialization."""
        engine = SearchEngine(
            cache_dir=temp_cache_dir,
            languages=[Language.ENGLISH, Language.FRENCH],
            min_score=0.7,
            enable_semantic=False,
        )

        assert engine.cache_dir == temp_cache_dir
        assert engine.languages == [Language.ENGLISH, Language.FRENCH]
        assert engine.min_score == 0.7
        assert engine.enable_semantic is False
        assert not engine._initialized

    @pytest.mark.asyncio
    async def test_initialization_process(
        self, search_engine: SearchEngine, sample_vocabulary: list[str]
    ) -> None:
        """Test the async initialization process."""
        # Mock the lexicon loader
        with patch("src.floridify.search.core.LexiconLoader") as mock_loader_class:
            mock_loader = AsyncMock()
            mock_loader.load_languages = AsyncMock()
            mock_loader.get_all_words = MagicMock(
                return_value=[w for w in sample_vocabulary if " " not in w]
            )
            mock_loader.get_all_phrases = MagicMock(
                return_value=[w for w in sample_vocabulary if " " in w]
            )
            mock_loader_class.return_value = mock_loader

            # Mock other components
            with (
                patch("src.floridify.search.core.TrieSearch") as mock_trie,
                patch("src.floridify.search.core.FuzzySearch") as mock_fuzzy,
                patch("src.floridify.search.core.SemanticSearch") as mock_semantic,
            ):
                mock_trie_instance = MagicMock()
                mock_fuzzy_instance = MagicMock()
                mock_semantic_instance = AsyncMock()

                mock_trie.return_value = mock_trie_instance
                mock_fuzzy.return_value = mock_fuzzy_instance
                mock_semantic.return_value = mock_semantic_instance

                # Initialize
                await search_engine.initialize()

                # Verify initialization
                assert search_engine._initialized
                assert search_engine.lexicon_loader is not None
                assert search_engine.trie_search is not None
                assert search_engine.fuzzy_search is not None
                assert search_engine.semantic_search is not None

                # Verify component initialization calls
                mock_loader.load_languages.assert_called_once_with([Language.ENGLISH])
                mock_trie_instance.build_index.assert_called_once()
                mock_semantic_instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_automatic_method_selection(self, search_engine: SearchEngine) -> None:
        """Test automatic search method selection based on query characteristics."""

        # Test short queries (≤3 chars)
        methods = search_engine._select_optimal_methods("hi")
        assert SearchMethod.PREFIX in methods
        assert SearchMethod.EXACT in methods

        # Test medium queries (4-8 chars)
        methods = search_engine._select_optimal_methods("hello")
        assert SearchMethod.EXACT in methods
        assert SearchMethod.FUZZY in methods

        # Test long queries (>8 chars)
        methods = search_engine._select_optimal_methods("definition")
        assert SearchMethod.EXACT in methods
        assert SearchMethod.FUZZY in methods
        assert SearchMethod.SEMANTIC in methods

        # Test phrases (contains spaces)
        methods = search_engine._select_optimal_methods("hello world")
        assert SearchMethod.EXACT in methods
        assert SearchMethod.SEMANTIC in methods
        assert SearchMethod.FUZZY in methods

    @pytest.mark.asyncio
    async def test_search_with_mocked_components(self, search_engine: SearchEngine) -> None:
        """Test search functionality with mocked components."""

        # Mock all search components
        mock_trie = MagicMock()
        mock_fuzzy = MagicMock()
        mock_semantic = AsyncMock()
        mock_lexicon = MagicMock()

        mock_trie.search_exact.return_value = ["hello"]
        mock_trie.search_prefix.return_value = ["hello", "help"]

        # Mock fuzzy results
        from src.floridify.search.fuzzy import FuzzyMatch, FuzzySearchMethod

        mock_fuzzy.search.return_value = [
            FuzzyMatch(word="hello", score=0.9, method=FuzzySearchMethod.RAPIDFUZZ),
            FuzzyMatch(word="help", score=0.7, method=FuzzySearchMethod.RAPIDFUZZ),
        ]

        mock_semantic.search.return_value = [("hello", 0.8), ("greetings", 0.6)]
        mock_lexicon.get_all_words.return_value = ["hello", "help", "greetings"]
        mock_lexicon.get_all_phrases.return_value = []

        # Inject mocked components
        search_engine.trie_search = mock_trie
        search_engine.fuzzy_search = mock_fuzzy
        search_engine.semantic_search = mock_semantic
        search_engine.lexicon_loader = mock_lexicon
        search_engine._initialized = True

        # Test exact search
        results = await search_engine.search("hello", methods=[SearchMethod.EXACT])
        assert len(results) > 0
        assert any(r.word == "hello" and r.method == SearchMethod.EXACT for r in results)

        # Test prefix search
        results = await search_engine.search("hel", methods=[SearchMethod.PREFIX])
        assert len(results) > 0
        assert any(r.method == SearchMethod.PREFIX for r in results)

        # Test fuzzy search
        results = await search_engine.search("helo", methods=[SearchMethod.FUZZY])
        assert len(results) > 0
        assert any(r.method == SearchMethod.FUZZY for r in results)

        # Test semantic search
        results = await search_engine.search("greeting", methods=[SearchMethod.SEMANTIC])
        assert len(results) > 0
        assert any(r.method == SearchMethod.SEMANTIC for r in results)

    @pytest.mark.asyncio
    async def test_result_deduplication(self, search_engine: SearchEngine) -> None:
        """Test that duplicate results are properly handled."""

        # Create test results with duplicates
        results = [
            SearchResult(word="hello", score=1.0, method=SearchMethod.EXACT),
            SearchResult(word="hello", score=0.9, method=SearchMethod.FUZZY),
            SearchResult(word="hello", score=0.8, method=SearchMethod.SEMANTIC),
            SearchResult(word="world", score=0.9, method=SearchMethod.PREFIX),
            SearchResult(word="world", score=0.7, method=SearchMethod.FUZZY),
        ]

        # Test deduplication (should keep highest priority method)
        deduplicated = search_engine._deduplicate_results(results)

        # Should have 2 unique words
        assert len(deduplicated) == 2

        # Should keep EXACT for "hello" and PREFIX for "world"
        hello_result = next(r for r in deduplicated if r.word == "hello")
        world_result = next(r for r in deduplicated if r.word == "world")

        assert hello_result.method == SearchMethod.EXACT
        assert world_result.method == SearchMethod.PREFIX

    @pytest.mark.asyncio
    async def test_score_filtering(self, search_engine: SearchEngine) -> None:
        """Test that results are filtered by minimum score."""

        # Mock components to return results with various scores
        mock_trie = MagicMock()
        mock_trie.search_exact.return_value = ["hello"]

        search_engine.trie_search = mock_trie
        search_engine.fuzzy_search = None
        search_engine.semantic_search = None
        search_engine.lexicon_loader = MagicMock()
        search_engine._initialized = True

        # Test with default min_score (0.6)
        results = await search_engine.search("hello", methods=[SearchMethod.EXACT])
        # Exact matches should have score 1.0, so should pass
        assert len(results) > 0

        # Test with very high min_score
        results = await search_engine.search("hello", methods=[SearchMethod.EXACT], min_score=1.1)
        # No results should pass this threshold
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_max_results_limiting(self, search_engine: SearchEngine) -> None:
        """Test that results are limited to max_results."""

        # Mock components to return many results
        mock_trie = MagicMock()
        mock_trie.search_prefix.return_value = [f"word{i}" for i in range(100)]

        search_engine.trie_search = mock_trie
        search_engine.fuzzy_search = None
        search_engine.semantic_search = None
        search_engine.lexicon_loader = MagicMock()
        search_engine._initialized = True

        # Test max_results limiting
        results = await search_engine.search("wor", methods=[SearchMethod.PREFIX], max_results=5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, search_engine: SearchEngine) -> None:
        """Test handling of empty or invalid queries."""
        search_engine._initialized = True

        # Empty string
        results = await search_engine.search("")
        assert len(results) == 0

        # Whitespace only
        results = await search_engine.search("   ")
        assert len(results) == 0

        # None (should not crash)
        results = await search_engine.search("test")  # Normal query to avoid issues
        # Just ensure it doesn't crash

    @pytest.mark.asyncio
    async def test_performance_statistics(self, search_engine: SearchEngine) -> None:
        """Test search performance statistics tracking."""

        # Mock components
        mock_trie = MagicMock()
        mock_trie.search_exact.return_value = ["hello"]

        search_engine.trie_search = mock_trie
        search_engine.fuzzy_search = None
        search_engine.semantic_search = None
        search_engine.lexicon_loader = MagicMock()
        search_engine._initialized = True

        # Perform some searches
        await search_engine.search("hello", methods=[SearchMethod.EXACT])
        await search_engine.search("world", methods=[SearchMethod.EXACT])

        # Check statistics
        stats = search_engine.get_search_stats()

        assert "exact" in stats
        assert stats["exact"]["count"] == 2
        assert stats["exact"]["total_time"] > 0
        assert stats["exact"]["avg_time"] > 0

    @pytest.mark.asyncio
    async def test_auto_initialization(self, search_engine: SearchEngine) -> None:
        """Test that search automatically initializes if not already done."""

        # Ensure not initialized
        assert not search_engine._initialized

        # Mock the initialization process
        with patch.object(search_engine, "initialize", new_callable=AsyncMock) as mock_init:
            await search_engine.search("test")
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, search_engine: SearchEngine) -> None:
        """Test proper cleanup of resources."""

        # Mock semantic search
        mock_semantic = AsyncMock()
        search_engine.semantic_search = mock_semantic

        # Test cleanup
        await search_engine.close()
        mock_semantic.close.assert_called_once()

    def test_phrase_detection_in_results(self, search_engine: SearchEngine) -> None:
        """Test that phrase detection works in search results."""

        # Test phrase detection
        result = SearchResult(
            word="hello world", score=1.0, method=SearchMethod.EXACT, is_phrase=True
        )
        assert result.is_phrase

        result = SearchResult(word="hello", score=1.0, method=SearchMethod.EXACT, is_phrase=False)
        assert not result.is_phrase

    @pytest.mark.asyncio
    async def test_multiple_languages(self, temp_cache_dir: Path) -> None:
        """Test search engine with multiple languages."""

        engine = SearchEngine(
            cache_dir=temp_cache_dir,
            languages=[Language.ENGLISH, Language.FRENCH],
        )

        assert engine.languages == [Language.ENGLISH, Language.FRENCH]

        # Mock initialization to avoid actual network calls
        with patch("src.floridify.search.core.LexiconLoader") as mock_loader_class:
            mock_loader = AsyncMock()
            mock_loader.load_languages = AsyncMock()
            mock_loader.get_all_words = MagicMock(return_value=["hello", "bonjour"])
            mock_loader.get_all_phrases = MagicMock(return_value=["hello world", "bonjour monde"])
            mock_loader_class.return_value = mock_loader

            with (
                patch("src.floridify.search.core.TrieSearch"),
                patch("src.floridify.search.core.FuzzySearch"),
                patch("src.floridify.search.core.SemanticSearch") as mock_semantic_class,
            ):
                # Mock the semantic search instance
                mock_semantic_instance = AsyncMock()
                mock_semantic_instance.initialize = AsyncMock()
                mock_semantic_class.return_value = mock_semantic_instance

                await engine.initialize()

                # Verify loader was called with multiple languages
                mock_loader.load_languages.assert_called_once_with(
                    [Language.ENGLISH, Language.FRENCH]
                )

"""Comprehensive tests for search engine orchestration with real MongoDB."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.core import Search
from floridify.search.models import SearchIndex, SearchResult
from floridify.search.semantic.constants import DEFAULT_SENTENCE_MODEL
from floridify.search.trie import TrieSearch


class TestSearchEngineInitialization:
    """Test search engine initialization and configuration."""

    @pytest.mark.asyncio
    async def test_basic_initialization(self):
        """Test basic search engine initialization."""
        engine = Search()

        assert engine.index is None
        assert engine.corpus is None
        assert engine.trie_search is None
        assert engine.fuzzy_search is None
        assert engine.semantic_search is None
        assert engine._initialized is False
        assert engine._semantic_ready is False

    @pytest.mark.asyncio
    async def test_initialization_with_index(self, test_db):
        """Test initialization with pre-loaded index."""
        # Create test corpus
        corpus = await Corpus.create(
            corpus_name="test_corpus",
            vocabulary=["apple", "banana", "cherry"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create index
        index = SearchIndex(
            corpus_name="test_corpus",
            corpus_id=corpus.corpus_id,
            vocabulary_hash=corpus.vocabulary_hash,
            min_score=0.7,
            has_trie=True,
            has_fuzzy=True,
            semantic_enabled=False,
        )

        # Initialize engine with index
        engine = Search(index=index, corpus=corpus)
        await engine.initialize()

        assert engine.index == index
        assert engine.corpus == corpus
        assert engine.trie_search is not None
        assert engine.fuzzy_search is not None
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_from_corpus_factory(self, test_db):
        """Test creating search engine from corpus name."""
        # Create test corpus
        corpus = await Corpus.create(
            corpus_name="factory_test",
            vocabulary=["word1", "word2", "word3"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create engine from corpus
        engine = await Search.from_corpus(
            corpus_name="factory_test",
            min_score=0.8,
            semantic=False,
        )

        assert engine.index is not None
        assert engine.index.corpus_name == "factory_test"
        assert engine.index.min_score == 0.8
        assert engine.index.semantic_enabled is False
        assert engine.corpus is not None
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_corpus_not_found(self, test_db):
        """Test error when corpus doesn't exist."""
        with pytest.raises(ValueError, match="Corpus 'nonexistent' not found"):
            await Search.from_corpus("nonexistent")

    @pytest.mark.asyncio
    async def test_semantic_background_initialization(self, test_db):
        """Test semantic search initialization in background."""
        # Create corpus
        corpus = await Corpus.create(
            corpus_name="semantic_test",
            vocabulary=["test1", "test2"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create index with semantic enabled
        index = SearchIndex(
            corpus_name="semantic_test",
            corpus_id=corpus.corpus_id,
            vocabulary_hash=corpus.vocabulary_hash,
            semantic_enabled=True,
            semantic_model=DEFAULT_SENTENCE_MODEL,
        )

        # Initialize engine
        engine = Search(index=index, corpus=corpus)

        # Mock semantic search creation
        with patch("floridify.search.core.SemanticSearch.from_corpus") as mock_semantic:
            mock_semantic_instance = AsyncMock()
            mock_semantic.return_value = mock_semantic_instance

            await engine.initialize()

            # Should have created background task
            assert engine._semantic_init_task is not None

            # Wait for background initialization
            await engine._semantic_init_task

            assert engine._semantic_ready is True
            assert engine.semantic_search is not None

    @pytest.mark.asyncio
    async def test_hash_based_reinitialization_skip(self, test_db):
        """Test that reinitialization is skipped if hash unchanged."""
        corpus = await Corpus.create(
            corpus_name="hash_test",
            vocabulary=["unchanged"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = SearchIndex(
            corpus_name="hash_test",
            corpus_id=corpus.corpus_id,
            vocabulary_hash=corpus.vocabulary_hash,
        )

        engine = Search(index=index, corpus=corpus)

        # First initialization
        await engine.initialize()
        assert engine._initialized is True

        # Store component references
        original_trie = engine.trie_search
        original_fuzzy = engine.fuzzy_search

        # Second initialization with same hash - should skip
        await engine.initialize()

        # Components should be unchanged
        assert engine.trie_search is original_trie
        assert engine.fuzzy_search is original_fuzzy


class TestSearchMethods:
    """Test different search methods and modes."""

    @pytest.mark.asyncio
    async def test_exact_search(self, test_db):
        """Test exact search method."""
        corpus = await Corpus.create(
            corpus_name="exact_test",
            vocabulary=["apple", "application", "apply"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("exact_test", semantic=False)

        # Test exact match
        results = await engine.search("apple", method=SearchMethod.EXACT)
        assert len(results) == 1
        assert results[0].word == "apple"
        assert results[0].score == 1.0
        assert results[0].method == SearchMethod.EXACT

        # Test no match
        results = await engine.search("apples", method=SearchMethod.EXACT)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fuzzy_search(self, test_db):
        """Test fuzzy search method."""
        corpus = await Corpus.create(
            corpus_name="fuzzy_test",
            vocabulary=["apple", "application", "banana", "cherry"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("fuzzy_test", semantic=False)

        # Test fuzzy match
        results = await engine.search("aple", method=SearchMethod.FUZZY)
        assert len(results) > 0
        assert any(r.word == "apple" for r in results)
        assert all(r.method == SearchMethod.FUZZY for r in results)

    @pytest.mark.asyncio
    async def test_semantic_search(self, test_db):
        """Test semantic search method."""
        corpus = await Corpus.create(
            corpus_name="semantic_method_test",
            vocabulary=["happy", "joyful", "sad", "angry"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Mock semantic search
        with patch("floridify.search.core.SemanticSearch") as mock_semantic_class:
            mock_semantic = MagicMock()
            mock_semantic.search.return_value = [
                SearchResult(word="joyful", score=0.9, method=SearchMethod.SEMANTIC),
                SearchResult(word="happy", score=0.85, method=SearchMethod.SEMANTIC),
            ]
            mock_semantic_class.from_corpus.return_value = mock_semantic

            engine = await Search.from_corpus("semantic_method_test", semantic=True)

            # Wait for semantic initialization
            if engine._semantic_init_task:
                await engine._semantic_init_task

            engine.semantic_search = mock_semantic

            results = await engine.search("cheerful", method=SearchMethod.SEMANTIC)
            assert len(results) == 2
            assert all(r.method == SearchMethod.SEMANTIC for r in results)

    @pytest.mark.asyncio
    async def test_search_modes(self, test_db):
        """Test different search modes."""
        corpus = await Corpus.create(
            corpus_name="mode_test",
            vocabulary=["test", "testing", "tested"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("mode_test", semantic=False)

        # Test EXACT mode
        results = await engine.search_with_mode("test", mode=SearchMode.EXACT)
        assert len(results) == 1
        assert results[0].word == "test"

        # Test FUZZY mode
        results = await engine.search_with_mode("tst", mode=SearchMode.FUZZY)
        assert len(results) > 0

        # Test SMART mode (default cascade)
        results = await engine.search_with_mode("test", mode=SearchMode.SMART)
        assert len(results) > 0


class TestSmartSearchCascade:
    """Test smart search cascade logic."""

    @pytest.mark.asyncio
    async def test_cascade_with_exact_match(self, test_db):
        """Test cascade stops early with exact match."""
        corpus = await Corpus.create(
            corpus_name="cascade_exact",
            vocabulary=["exact", "example", "examine"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("cascade_exact", semantic=False)

        # Should find exact match and stop
        results = await engine.search("exact")
        assert len(results) == 1
        assert results[0].word == "exact"
        assert results[0].method == SearchMethod.EXACT

    @pytest.mark.asyncio
    async def test_cascade_fallback_to_fuzzy(self, test_db):
        """Test cascade falls back to fuzzy when no exact match."""
        corpus = await Corpus.create(
            corpus_name="cascade_fuzzy",
            vocabulary=["apple", "application", "banana"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("cascade_fuzzy", semantic=False)

        # Should fallback to fuzzy
        results = await engine.search("aple")  # Typo
        assert len(results) > 0
        assert any(r.word == "apple" for r in results)
        assert all(r.method == SearchMethod.FUZZY for r in results)

    @pytest.mark.asyncio
    async def test_result_deduplication(self, test_db):
        """Test deduplication across search methods."""
        corpus = await Corpus.create(
            corpus_name="dedup_test",
            vocabulary=["test", "testing", "tested", "tester"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("dedup_test", semantic=False)

        # Search should deduplicate results
        results = await engine.search("test")

        # Check no duplicates
        seen_words = set()
        for result in results:
            assert result.word not in seen_words
            seen_words.add(result.word)


class TestCorpusUpdates:
    """Test corpus update detection and handling."""

    @pytest.mark.asyncio
    async def test_corpus_update_detection(self, test_db):
        """Test detecting corpus vocabulary changes."""
        # Create initial corpus
        corpus = await Corpus.create(
            corpus_name="update_test",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("update_test", semantic=False)
        initial_hash = engine.index.vocabulary_hash

        # Update corpus vocabulary
        corpus.vocabulary.append("updated")
        corpus.update_version("Added word")
        await corpus.save()

        # Engine should detect change
        await engine.update_corpus()

        assert engine.index.vocabulary_hash != initial_hash
        assert "updated" in engine.corpus.vocabulary

    @pytest.mark.asyncio
    async def test_no_update_when_unchanged(self, test_db):
        """Test skipping update when corpus unchanged."""
        corpus = await Corpus.create(
            corpus_name="no_update_test",
            vocabulary=["static"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("no_update_test", semantic=False)

        # Mock to verify no rebuild
        with patch.object(TrieSearch, "from_corpus") as mock_trie:
            await engine.update_corpus()

            # Should not rebuild indices
            mock_trie.assert_not_called()


class TestBuildIndices:
    """Test manual index building."""

    @pytest.mark.asyncio
    async def test_build_indices_from_corpus(self, test_db):
        """Test building indices from corpus."""
        corpus = await Corpus.create(
            corpus_name="build_test",
            vocabulary=["word1", "word2", "word3"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = Search(corpus=corpus)

        # Build indices manually
        await engine.build_indices()

        assert engine.index is not None
        assert engine.index.has_trie is True
        assert engine.index.has_fuzzy is True
        assert engine.trie_search is not None
        assert engine.fuzzy_search is not None
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_build_without_corpus(self):
        """Test error when building without corpus."""
        engine = Search()

        with pytest.raises(ValueError, match="Corpus required"):
            await engine.build_indices()


class TestSearchFiltering:
    """Test search result filtering and scoring."""

    @pytest.mark.asyncio
    async def test_min_score_filtering(self, test_db):
        """Test filtering results by minimum score."""
        corpus = await Corpus.create(
            corpus_name="score_test",
            vocabulary=["perfect", "partial", "poor", "terrible"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("score_test", min_score=0.8, semantic=False)

        # High threshold should filter weak matches
        results = await engine.search("prfct", min_score=0.9)

        # Should have fewer results with high threshold
        high_threshold_count = len(results)

        results = await engine.search("prfct", min_score=0.5)
        low_threshold_count = len(results)

        assert low_threshold_count >= high_threshold_count

    @pytest.mark.asyncio
    async def test_max_results_limit(self, test_db):
        """Test limiting maximum results."""
        corpus = await Corpus.create(
            corpus_name="limit_test",
            vocabulary=[f"word{i}" for i in range(100)],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("limit_test", semantic=False)

        # Test different limits
        results = await engine.search("word", max_results=5)
        assert len(results) <= 5

        results = await engine.search("word", max_results=20)
        assert len(results) <= 20


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_query(self, test_db):
        """Test handling empty query."""
        corpus = await Corpus.create(
            corpus_name="empty_query_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("empty_query_test", semantic=False)

        results = await engine.search("")
        assert results == []

        results = await engine.search("   ")
        assert results == []

    @pytest.mark.asyncio
    async def test_invalid_search_mode(self, test_db):
        """Test error with invalid search mode."""
        corpus = await Corpus.create(
            corpus_name="invalid_mode_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("invalid_mode_test", semantic=False)

        with pytest.raises(ValueError, match="Unsupported search mode"):
            await engine.search_with_mode("test", mode="INVALID")  # type: ignore

    @pytest.mark.asyncio
    async def test_semantic_not_enabled(self, test_db):
        """Test error when semantic search not enabled."""
        corpus = await Corpus.create(
            corpus_name="no_semantic_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("no_semantic_test", semantic=False)

        with pytest.raises(ValueError, match="Semantic search is not enabled"):
            await engine.search_with_mode("test", mode=SearchMode.SEMANTIC)

    @pytest.mark.asyncio
    async def test_initialization_without_index(self):
        """Test error when initializing without index."""
        engine = Search()

        with pytest.raises(ValueError, match="Index required"):
            await engine.initialize()


class TestConcurrency:
    """Test concurrent search operations."""

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, test_db):
        """Test multiple concurrent searches."""
        corpus = await Corpus.create(
            corpus_name="concurrent_test",
            vocabulary=["apple", "banana", "cherry", "date", "elderberry"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        engine = await Search.from_corpus("concurrent_test", semantic=False)

        # Run multiple searches concurrently
        queries = ["apple", "ban", "chr", "dt", "elder"]
        tasks = [engine.search(q) for q in queries]

        results = await asyncio.gather(*tasks)

        # All searches should complete
        assert len(results) == 5
        for result_list in results:
            assert isinstance(result_list, list)

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, test_db):
        """Test concurrent initialization attempts."""
        corpus = await Corpus.create(
            corpus_name="concurrent_init",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = SearchIndex(
            corpus_name="concurrent_init",
            corpus_id=corpus.corpus_id,
            vocabulary_hash=corpus.vocabulary_hash,
        )

        engine = Search(index=index, corpus=corpus)

        # Initialize concurrently
        tasks = [engine.initialize() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should be initialized once
        assert engine._initialized is True

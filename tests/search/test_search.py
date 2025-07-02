"""Unit tests for search engine components."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.floridify.constants import Language
from src.floridify.search import SearchEngine, SearchResult
from src.floridify.search.constants import FuzzySearchMethod, SearchMethod
from src.floridify.search.fuzzy import FuzzyMatch, FuzzySearch
from src.floridify.search.phrase import MultiWordExpression, PhraseNormalizer
from src.floridify.search.trie import TrieSearch


class TestFuzzySearch:
    """Test fuzzy search algorithm components."""

    def test_fuzzy_search_initialization(self):
        """Test FuzzySearch initialization."""
        search = FuzzySearch(min_score=0.7)
        assert search.min_score == 0.7

    def test_empty_query_handling(self):
        """Test fuzzy search with empty queries."""
        search = FuzzySearch()
        results = search.search("", ["test", "hello"])
        assert results == []

        results = search.search("   ", ["test", "hello"])
        assert results == []

    def test_empty_word_list_handling(self):
        """Test fuzzy search with empty word list."""
        search = FuzzySearch()
        results = search.search("test", [])
        assert results == []

    def test_automatic_method_selection(self):
        """Test automatic fuzzy method selection."""
        search = FuzzySearch()

        # Short queries should use Jaro-Winkler
        method = search._select_optimal_method("ab")
        assert method == FuzzySearchMethod.JARO_WINKLER

        # Medium queries should use RapidFuzz
        method = search._select_optimal_method("hello")
        assert method == FuzzySearchMethod.RAPIDFUZZ

        # Queries with numbers should use RapidFuzz
        method = search._select_optimal_method("test123")
        assert method == FuzzySearchMethod.RAPIDFUZZ

    def test_length_correction_logic(self):
        """Test length-aware scoring correction."""
        search = FuzzySearch()

        # No correction for perfect matches
        corrected = search._apply_length_correction("test", "test", 1.0, False)
        assert corrected == 1.0

        # Penalty for very short candidates
        corrected = search._apply_length_correction("hello world", "hi", 0.8, True)
        assert corrected < 0.8  # Should be penalized

        # Phrase matching bonus
        corrected = search._apply_length_correction("hello world", "hello earth", 0.7, True)
        assert corrected >= 0.7  # Should get phrase bonus

    def test_rapidfuzz_search(self):
        """Test RapidFuzz search functionality."""
        search = FuzzySearch(min_score=0.5)
        word_list = ["hello", "help", "world", "test"]
        
        results = search._search_rapidfuzz("helo", word_list, 5)
        
        assert len(results) > 0
        assert all(isinstance(r, FuzzyMatch) for r in results)
        assert all(r.score >= 0.5 for r in results)
        assert results[0].method == FuzzySearchMethod.RAPIDFUZZ

    def test_fuzzy_match_model(self):
        """Test FuzzyMatch model validation."""
        match = FuzzyMatch(
            word="test",
            score=0.85,
            method=FuzzySearchMethod.RAPIDFUZZ,
            edit_distance=2,
            is_phrase=False
        )
        
        assert match.word == "test"
        assert match.score == 0.85
        assert match.method == FuzzySearchMethod.RAPIDFUZZ
        assert match.edit_distance == 2
        assert not match.is_phrase


class TestTrieSearch:
    """Test trie-based exact and prefix search."""

    def test_trie_initialization(self):
        """Test TrieSearch initialization."""
        trie = TrieSearch()
        assert trie._trie == {}

    def test_trie_index_building(self):
        """Test building trie index from word list."""
        trie = TrieSearch()
        words = ["hello", "help", "world", "word"]
        
        trie.build_index(words)
        
        # Verify trie structure is built
        assert trie._trie is not None
        assert len(trie._word_list) == 4

    def test_exact_search(self):
        """Test exact string matching."""
        trie = TrieSearch()
        words = ["hello", "help", "world", "word"]
        trie.build_index(words)
        
        # Exact matches
        results = trie.search_exact("hello")
        assert "hello" in results
        
        results = trie.search_exact("missing")
        assert results == []

    def test_prefix_search(self):
        """Test prefix matching."""
        trie = TrieSearch()
        words = ["hello", "help", "world", "word"]
        trie.build_index(words)
        
        # Prefix matches
        results = trie.search_prefix("hel", 10)
        assert "hello" in results
        assert "help" in results
        assert len(results) == 2
        
        # Limit results
        results = trie.search_prefix("hel", 1)
        assert len(results) == 1

    def test_trie_statistics(self):
        """Test trie statistics calculation."""
        trie = TrieSearch()
        words = ["hello", "help", "world"]
        trie.build_index(words)
        
        stats = trie.get_statistics()
        assert "total_words" in stats
        assert "memory_nodes" in stats
        assert "average_depth" in stats
        assert stats["total_words"] == 3


class TestPhraseNormalizer:
    """Test phrase normalization and detection."""

    def test_phrase_normalizer_init(self):
        """Test PhraseNormalizer initialization."""
        normalizer = PhraseNormalizer()
        assert normalizer is not None

    def test_phrase_detection(self):
        """Test phrase vs single word detection."""
        normalizer = PhraseNormalizer()
        
        assert normalizer.is_phrase("hello world")
        assert normalizer.is_phrase("bon vivant")
        assert not normalizer.is_phrase("hello")
        assert not normalizer.is_phrase("test")

    def test_text_normalization(self):
        """Test text normalization functionality."""
        normalizer = PhraseNormalizer()
        
        # Basic normalization
        assert normalizer.normalize("  HELLO  ") == "hello"
        assert normalizer.normalize("Hello World") == "hello world"
        
        # Handle empty/whitespace
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""

    def test_multiword_expression_creation(self):
        """Test MultiWordExpression model."""
        phrase = MultiWordExpression(
            text="bon vivant",
            normalized="bon vivant",
            word_count=2,
            language="en",
            frequency=0.5,
            is_idiom=True
        )
        
        assert phrase.text == "bon vivant"
        assert phrase.word_count == 2
        assert phrase.is_idiom
        assert phrase.frequency == 0.5


class TestSearchEngine:
    """Test main SearchEngine functionality."""

    @pytest.fixture
    def mock_search_engine(self, mock_cache_dir):
        """Create SearchEngine with mocked components."""
        with patch('src.floridify.search.core.LexiconLoader') as mock_loader, \
             patch('src.floridify.search.core.TrieSearch') as mock_trie, \
             patch('src.floridify.search.core.FuzzySearch') as mock_fuzzy:
            
            # Mock lexicon loader
            mock_loader_instance = AsyncMock()
            mock_loader_instance.get_all_words.return_value = ["test", "hello", "world"]
            mock_loader_instance.get_all_phrases.return_value = ["hello world", "test phrase"]
            mock_loader.return_value = mock_loader_instance
            
            # Mock search components
            mock_trie_instance = MagicMock()
            mock_trie.return_value = mock_trie_instance
            
            mock_fuzzy_instance = MagicMock()
            mock_fuzzy.return_value = mock_fuzzy_instance
            
            engine = SearchEngine(
                cache_dir=mock_cache_dir,
                languages=[Language.ENGLISH],
                enable_semantic=False
            )
            
            return engine

    @pytest.mark.asyncio
    async def test_search_engine_initialization(self, mock_search_engine):
        """Test SearchEngine initialization."""
        engine = mock_search_engine
        
        await engine.initialize()
        
        assert engine._initialized
        assert engine.lexicon_loader is not None
        assert engine.trie_search is not None
        assert engine.fuzzy_search is not None

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, mock_search_engine):
        """Test SearchEngine handles empty queries."""
        engine = mock_search_engine
        await engine.initialize()
        
        results = await engine.search("")
        assert results == []
        
        results = await engine.search("   ")
        assert results == []

    def test_optimal_method_selection(self, mock_search_engine):
        """Test automatic search method selection."""
        engine = mock_search_engine
        
        # Short queries - prefix matching
        methods = engine._select_optimal_methods("ab")
        assert SearchMethod.PREFIX in methods
        
        # Medium queries - exact and fuzzy
        methods = engine._select_optimal_methods("hello")
        assert SearchMethod.EXACT in methods
        assert SearchMethod.FUZZY in methods
        
        # Phrases - exact, fuzzy, semantic
        methods = engine._select_optimal_methods("hello world")
        assert SearchMethod.EXACT in methods
        assert SearchMethod.FUZZY in methods

    @pytest.mark.asyncio
    async def test_exact_search_execution(self, mock_search_engine):
        """Test exact search method execution."""
        engine = mock_search_engine
        await engine.initialize()
        
        # Mock exact search results
        engine.trie_search.search_exact.return_value = ["test"]
        
        results = await engine._search_exact("test")
        
        assert len(results) == 1
        assert results[0].word == "test"
        assert results[0].score == 1.0
        assert results[0].method == SearchMethod.EXACT

    @pytest.mark.asyncio
    async def test_search_statistics(self, mock_search_engine):
        """Test search performance statistics."""
        engine = mock_search_engine
        await engine.initialize()
        
        # Perform some searches to generate stats
        await engine._search_exact("test")
        
        stats = engine.get_search_stats()
        
        assert "exact" in stats
        assert "count" in stats["exact"]
        assert "total_time" in stats["exact"]
        assert "avg_time" in stats["exact"]

    def test_result_deduplication(self, mock_search_engine):
        """Test search result deduplication logic."""
        engine = mock_search_engine
        
        # Create duplicate results with different methods
        results = [
            SearchResult(word="test", score=1.0, method=SearchMethod.EXACT, is_phrase=False),
            SearchResult(word="test", score=0.8, method=SearchMethod.FUZZY, is_phrase=False),
            SearchResult(word="hello", score=0.9, method=SearchMethod.FUZZY, is_phrase=False),
        ]
        
        deduplicated = engine._deduplicate_results(results)
        
        # Should keep higher priority method (EXACT over FUZZY)
        assert len(deduplicated) == 2
        test_result = next(r for r in deduplicated if r.word == "test")
        assert test_result.method == SearchMethod.EXACT
        assert test_result.score == 1.0


class TestSearchIntegration:
    """Test search component integration."""

    def test_search_result_model(self):
        """Test SearchResult model validation."""
        result = SearchResult(
            word="test",
            score=0.85,
            method=SearchMethod.FUZZY,
            is_phrase=False,
            metadata={"fuzzy_method": "rapidfuzz"}
        )
        
        assert result.word == "test"
        assert result.score == 0.85
        assert result.method == SearchMethod.FUZZY
        assert not result.is_phrase
        assert result.metadata["fuzzy_method"] == "rapidfuzz"

    def test_search_result_validation(self):
        """Test SearchResult validation constraints."""
        # Valid score range
        SearchResult(word="test", score=0.0, method=SearchMethod.EXACT, is_phrase=False)
        SearchResult(word="test", score=1.0, method=SearchMethod.EXACT, is_phrase=False)
        
        # Invalid scores should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchResult(word="test", score=-0.1, method=SearchMethod.EXACT, is_phrase=False)
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchResult(word="test", score=1.1, method=SearchMethod.EXACT, is_phrase=False)
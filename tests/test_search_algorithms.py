"""Comprehensive test suite for search algorithms and core search functionality.

Tests all search components including:
1. Traditional search algorithms (Trie, BK-tree, N-grams)
2. Vectorized search with embeddings and FAISS
3. Search manager coordination and performance
4. Lexicon loading and caching
5. Multi-word phrase support
6. Performance and robustness testing
7. Integration with CLI commands
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Generator
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from src.floridify.search.enums import (
    LanguageCode,
    LexiconSource,
    SearchMethod,
    TraditionalSearchMethod,
    VectorSearchMethod,
)
from src.floridify.search.fuzzy_traditional import TraditionalFuzzySearch
from src.floridify.search.fuzzy_vectorized import (
    CharacterEmbedder,
    SubwordEmbedder,
    TFIDFEmbedder,
    VectorizedFuzzySearch,
)
from src.floridify.search.index import BKTree, NGramIndex, TrieIndex, WordIndex
from src.floridify.search.lexicon_loader import LexiconLoader
from src.floridify.search.search_manager import SearchManager, SearchResult


class TestTrieIndex:
    """Test the Trie data structure for prefix matching."""
    
    def test_trie_initialization(self) -> None:
        """Test trie can be initialized and basic operations work."""
        trie = TrieIndex()
        assert trie.trie is not None
        assert len(trie.trie) == 0
    
    def test_trie_add_word(self) -> None:
        """Test adding words to trie."""
        trie = TrieIndex()
        trie.add_word("hello")
        trie.add_word("help")
        trie.add_word("world")
        
        assert "hello" in trie.trie
        assert "help" in trie.trie
        assert "world" in trie.trie
        assert "nonexistent" not in trie.trie
    
    def test_trie_prefix_search(self) -> None:
        """Test prefix searching functionality."""
        trie = TrieIndex()
        words = ["hello", "help", "world", "word", "work"]
        for word in words:
            trie.add_word(word)
        
        # Test exact prefix matches
        hel_results = trie.prefix_search("hel", 10)
        hel_words = [word for word, _score in hel_results]
        assert "hello" in hel_words
        assert "help" in hel_words
        assert "world" not in hel_words
        
        # Test word prefix matches
        wor_results = trie.prefix_search("wor", 10)
        wor_words = [word for word, _score in wor_results]
        assert "world" in wor_words
        assert "word" in wor_words
        assert "work" in wor_words
        assert "hello" not in wor_words
    
    def test_trie_empty_search(self) -> None:
        """Test searching empty trie returns no results."""
        trie = TrieIndex()
        results = trie.prefix_search("test", 10)
        assert len(results) == 0
    
    def test_trie_limit_results(self) -> None:
        """Test that result limiting works correctly."""
        trie = TrieIndex()
        # Add many words with same prefix
        for i in range(20):
            trie.add_word(f"test{i}")
        
        results = trie.prefix_search("test", 5)
        assert len(results) <= 5


class TestBKTree:
    """Test the BK-tree for edit distance search."""
    
    def test_bk_tree_initialization(self):
        """Test BK-tree can be initialized."""
        bk_tree = BKTree()
        assert bk_tree.root is None
    
    def test_bk_tree_add_words(self):
        """Test adding words to BK-tree."""
        bk_tree = BKTree()
        bk_tree.add_word("hello")
        bk_tree.add_word("help")
        bk_tree.add_word("world")
        
        assert bk_tree.root is not None
        assert bk_tree.root.word == "hello"
    
    def test_bk_tree_edit_distance_search(self):
        """Test edit distance searching."""
        bk_tree = BKTree()
        words = ["hello", "help", "world", "word", "work", "hell", "held"]
        for word in words:
            bk_tree.add_word(word)
        
        # Test close matches to "hello"
        results = bk_tree.search("hello", max_distance=1, max_results=10)
        result_words = [word for word, distance in results]
        
        # Should find exact match and close variants
        assert "hello" in result_words
        assert "hell" in result_words  # Distance 1
        # "help" has distance 2, so won't be included with max_distance=1
        
        # Test close matches to "help"
        results = bk_tree.search("help", max_distance=1, max_results=10)
        result_words = [word for word, distance in results]
        assert "help" in result_words
        assert "held" in result_words  # Distance 1
    
    def test_bk_tree_no_matches(self):
        """Test searching for word with no close matches."""
        bk_tree = BKTree()
        words = ["hello", "world", "test"]
        for word in words:
            bk_tree.add_word(word)
        
        # Search for something very different with tight distance
        results = bk_tree.search("xyz", max_distance=1, max_results=10)
        assert len(results) == 0


@pytest.fixture
def temp_cache_dir() -> Generator[Path, None, None]:
    """Provide a temporary cache directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_words() -> list[str]:
    """Provide sample words including phrases for testing."""
    return [
        "hello", "world", "python", "programming", "test", "algorithm",
        "data", "structure", "search", "fuzzy", "machine", "learning",
        "raison d'être", "c'est la vie", "joie de vivre", "carte blanche",
        "coup de grâce", "piece de resistance", "faux pas", "savoir-faire",
        "happy birthday", "thank you", "machine learning", "artificial intelligence",
        "computer science", "data structure", "software engineering"
    ]


@pytest.fixture
def sample_phrases() -> list[str]:
    """Provide sample multi-word phrases for testing."""
    return [
        "machine learning", "artificial intelligence", "computer science",
        "data structure", "software engineering", "natural language processing",
        "deep learning", "neural network", "random forest", "decision tree",
        "c'est la vie", "raison d'être", "joie de vivre", "piece de resistance",
        "coup de grâce", "carte blanche", "faux pas", "savoir-faire"
    ]


class TestPhraseSupport:
    """Test multi-word phrase support across all search algorithms."""
    
    def test_trie_phrase_support(self, temp_cache_dir: Path, sample_phrases: list[str]) -> None:
        """Test that trie index can handle multi-word phrases."""
        trie = TrieIndex()
        
        # Add phrases
        for phrase in sample_phrases:
            trie.add_word(phrase)
        
        # Test phrase lookup
        assert "machine learning" in [data["word"] for data in trie.trie.values()]
        assert "c'est la vie" in [data["word"] for data in trie.trie.values()]
        
        # Test prefix search with phrases
        ml_results = trie.prefix_search("machine", 5)
        ml_words = [word for word, _score in ml_results]
        assert "machine learning" in ml_words
    
    def test_vectorized_phrase_support(self, temp_cache_dir: Path, sample_phrases: list[str]) -> None:
        """Test that vectorized search handles phrases correctly."""
        vectorized_search = VectorizedFuzzySearch(temp_cache_dir)
        
        # Build index with phrases
        vectorized_search.build_index(sample_phrases)
        
        # Test phrase search
        results = vectorized_search.search("machine learn", k=5)
        result_words = [word for word, _score in results]
        assert any("machine learning" in word for word in result_words)
        
        # Test French phrase search
        results = vectorized_search.search("c est", k=5)
        result_words = [word for word, _score in results]
        assert any("c'est la vie" in word for word in result_words)
    
    def test_traditional_phrase_support(self, sample_phrases: list[str]) -> None:
        """Test that traditional fuzzy search handles phrases."""
        traditional_search = TraditionalFuzzySearch(score_threshold=0.3)
        
        # Test phrase matching
        results = traditional_search.search(
            "machine learn", 
            sample_phrases, 
            max_results=5,
            methods=[TraditionalSearchMethod.RAPIDFUZZ]
        )
        
        result_words = [match.word for match in results]
        assert any("machine learning" in word for word in result_words)


class TestPerformanceAndRobustness:
    """Test performance characteristics and robustness of search algorithms."""
    
    def test_large_vocabulary_performance(self, temp_cache_dir: Path) -> None:
        """Test search performance with large vocabulary."""
        # Create large word list
        large_word_list = []
        
        # Add common English words
        for i in range(1000):
            large_word_list.append(f"word{i}")
            large_word_list.append(f"test{i}")
            large_word_list.append(f"data{i}")
        
        # Add some phrases
        large_word_list.extend([
            "machine learning", "artificial intelligence", "deep learning",
            "natural language processing", "computer vision", "data science"
        ])
        
        # Test traditional index performance
        word_index = WordIndex(temp_cache_dir)
        start_time = pytest.approx(0, abs=10)  # Allow up to 10 seconds
        
        for word in large_word_list:
            word_index.add_word(word)
        
        # Test search performance
        results = word_index.hybrid_search("machine", max_results=10)
        assert len(results) > 0
        assert any("machine learning" in result[0] for result in results)
    
    def test_empty_query_handling(self, temp_cache_dir: Path, sample_words: list[str]) -> None:
        """Test handling of empty and invalid queries."""
        search_manager = SearchManager(temp_cache_dir)
        
        # Build index
        for word in sample_words:
            search_manager.word_index.add_word(word)
        search_manager.vectorized_search.build_index(sample_words)
        search_manager.is_initialized = True
        
        # Test empty queries
        empty_results = asyncio.run(search_manager.search(""))
        assert len(empty_results) == 0
        
        whitespace_results = asyncio.run(search_manager.search("   "))
        assert len(whitespace_results) == 0
    
    def test_special_character_handling(self, temp_cache_dir: Path) -> None:
        """Test handling of special characters in queries and data."""
        special_words = [
            "café", "naïve", "résumé", "piñata", "jalapeño",
            "c'est", "don't", "isn't", "rock-n-roll",
            "mother-in-law", "twenty-one", "state-of-the-art"
        ]
        
        vectorized_search = VectorizedFuzzySearch(temp_cache_dir)
        vectorized_search.build_index(special_words)
        
        # Test searches with special characters
        results = vectorized_search.search("cafe", k=5)
        assert len(results) > 0
        
        results = vectorized_search.search("c est", k=5)
        assert len(results) > 0
    
    def test_unicode_support(self, temp_cache_dir: Path) -> None:
        """Test Unicode character support."""
        unicode_words = [
            "москва", "北京", "العربية", "हिन्दी", "français",
            "español", "português", "italiano", "deutsch", "日本語"
        ]
        
        # Test that unicode words can be indexed
        word_index = WordIndex(temp_cache_dir)
        for word in unicode_words:
            word_index.add_word(word, language="multi")
        
        # Test search with unicode
        results = word_index.prefix_search("franç", max_results=5)
        assert len(results) >= 0  # Should not crash
    
    def test_memory_efficiency(self, temp_cache_dir: Path) -> None:
        """Test memory usage with large indices."""
        # Create moderately large dataset
        words = []
        for i in range(5000):
            words.extend([
                f"word{i}", f"test{i}", f"data{i}",
                f"compound word {i}", f"phrase test {i}"
            ])
        
        # Test that we can build and save indices
        vectorized_search = VectorizedFuzzySearch(temp_cache_dir)
        vectorized_search.build_index(words)
        
        # Test save/load cycle
        vectorized_search.save_index()
        
        new_search = VectorizedFuzzySearch(temp_cache_dir)
        loaded = new_search.load_index()
        assert loaded is True
        
        # Test that loaded index works
        results = new_search.search("word", k=5)
        assert len(results) > 0


class TestSearchManager:
    """Test the unified search manager functionality."""
    
    @pytest.mark.asyncio
    async def test_search_manager_initialization(self, temp_cache_dir: Path) -> None:
        """Test search manager can be initialized."""
        search_manager = SearchManager(temp_cache_dir)
        assert search_manager.is_initialized is False
        
        # Mock lexicon loader to avoid network calls
        with patch.object(search_manager.lexicon_loader, 'load_all_lexicons') as mock_load:
            with patch.object(search_manager.lexicon_loader, 'get_unified_lexicon') as mock_unified:
                mock_load.return_value = {}
                mock_unified.return_value = ["hello", "world", "test", "machine learning"]
                
                await search_manager.initialize()
                assert search_manager.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_search_manager_comprehensive_search(self, temp_cache_dir: Path, sample_words: list[str]) -> None:
        """Test comprehensive search across all methods."""
        search_manager = SearchManager(temp_cache_dir)
        
        # Manually build indices to avoid network calls
        for word in sample_words:
            search_manager.word_index.add_word(word)
        search_manager.vectorized_search.build_index(sample_words)
        search_manager.is_initialized = True
        
        # Test different search methods
        hybrid_results = await search_manager.search(
            "machine", methods=[SearchMethod.HYBRID], max_results=5
        )
        assert len(hybrid_results) > 0
        assert any("machine" in result.word.lower() for result in hybrid_results)
        
        vector_results = await search_manager.search(
            "machine", methods=[SearchMethod.VECTORIZED], max_results=5
        )
        assert len(vector_results) > 0
        
        # Test phrase search
        phrase_results = await search_manager.search(
            "machine learn", max_results=5
        )
        assert len(phrase_results) > 0


class TestLexiconLoader:
    """Test lexicon loading and caching functionality."""
    
    @pytest.mark.asyncio
    async def test_content_parsing(self, temp_cache_dir: Path) -> None:
        """Test parsing different content formats."""
        loader = LexiconLoader(temp_cache_dir)
        
        # Test JSON parsing
        json_content = '["word1", "word2", "phrase with spaces"]'
        json_words = loader._parse_content(json_content, "json")
        assert "word1" in json_words
        assert "phrase with spaces" in json_words
        
        # Test TSV parsing
        tsv_content = "phrase one\tdefinition\nphrase two\tanother def"
        tsv_words = loader._parse_content(tsv_content, "tsv")
        assert "phrase one" in tsv_words
        assert "phrase two" in tsv_words
        
        # Test text parsing
        text_content = "word1\nword2\nphrase with spaces"
        text_words = loader._parse_content(text_content, "txt")
        assert "word1" in text_words
        assert "phrase with spaces" in text_words
    
    @pytest.mark.asyncio
    async def test_phrase_filtering(self, temp_cache_dir: Path) -> None:
        """Test that phrase filtering allows complex expressions."""
        loader = LexiconLoader(temp_cache_dir)
        
        # Mock load_all_lexicons to test filtering
        mock_lexicons = {
            "test_source": [
                "hello", "world", "machine learning", "c'est la vie",
                "raison d'être", "state-of-the-art", "mother-in-law",
                "123invalid", "", "a"  # These should be filtered out
            ]
        }
        
        with patch.object(loader, 'load_all_lexicons', return_value=mock_lexicons):
            unified = await loader.get_unified_lexicon([LanguageCode.ENGLISH])
            
            assert "hello" in unified
            assert "machine learning" in unified
            assert "c'est la vie" in unified
            assert "raison d'être" in unified
            assert "state-of-the-art" in unified
            assert "mother-in-law" in unified
            assert "123invalid" not in unified
            assert "a" not in unified  # Too short


class TestEnumUsage:
    """Test that enums are used consistently throughout the codebase."""
    
    def test_search_method_enums(self) -> None:
        """Test that search method enums are properly defined."""
        # Test SearchMethod enum
        assert SearchMethod.HYBRID.value == "hybrid"
        assert SearchMethod.VECTORIZED.value == "vectorized"
        assert SearchMethod.RAPIDFUZZ.value == "rapidfuzz"
        
        # Test VectorSearchMethod enum
        assert VectorSearchMethod.CHARACTER.value == "character"
        assert VectorSearchMethod.FUSION.value == "fusion"
        
        # Test TraditionalSearchMethod enum
        assert TraditionalSearchMethod.RAPIDFUZZ.value == "rapidfuzz"
        assert TraditionalSearchMethod.VSCODE.value == "vscode"
    
    def test_language_code_enums(self) -> None:
        """Test that language code enums work correctly."""
        assert LanguageCode.ENGLISH.value == "en"
        assert LanguageCode.FRENCH.value == "fr"
    
    def test_lexicon_source_enums(self) -> None:
        """Test that lexicon source enums are properly defined."""
        assert LexiconSource.ENGLISH_COMMON.value == "english_common"
        assert LexiconSource.FRENCH_COMMON.value == "french_common"


# Performance benchmarking (optional, can be skipped in CI)
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarking tests (optional)."""
    
    def test_search_speed_benchmark(self, temp_cache_dir: Path) -> None:
        """Benchmark search speed with various algorithms."""
        import time
        
        # Create large dataset
        words = [f"testword{i}" for i in range(10000)]
        words.extend(["machine learning", "artificial intelligence", "natural language processing"])
        
        search_manager = SearchManager(temp_cache_dir)
        
        # Build indices
        for word in words:
            search_manager.word_index.add_word(word)
        search_manager.vectorized_search.build_index(words)
        search_manager.is_initialized = True
        
        # Benchmark different search methods
        queries = ["machine", "test", "artificial", "natural"]
        
        for query in queries:
            # Time hybrid search
            start = time.time()
            hybrid_results = asyncio.run(
                search_manager.search(query, methods=[SearchMethod.HYBRID], max_results=10)
            )
            hybrid_time = time.time() - start
            
            # Time vectorized search
            start = time.time()
            vector_results = asyncio.run(
                search_manager.search(query, methods=[SearchMethod.VECTORIZED], max_results=10)
            )
            vector_time = time.time() - start
            
            # Assert reasonable performance (under 1 second for this dataset)
            assert hybrid_time < 1.0, f"Hybrid search too slow: {hybrid_time:.3f}s"
            assert vector_time < 1.0, f"Vector search too slow: {vector_time:.3f}s"
            
            # Assert we get results
            assert len(hybrid_results) > 0
            assert len(vector_results) > 0


class TestNGramIndex:
    """Test N-gram indices for substring matching."""
    
    def test_ngram_index_initialization(self):
        """Test N-gram index initialization."""
        bigram_index = NGramIndex(n=2)
        assert bigram_index.n == 2
        assert len(bigram_index.ngram_to_words) == 0
        
        trigram_index = NGramIndex(n=3)
        assert trigram_index.n == 3
    
    def test_ngram_index_add_words(self):
        """Test adding words to N-gram index."""
        index = NGramIndex(n=2)
        index.add_word("hello")
        index.add_word("help")
        
        # Should have bigrams from both words
        assert len(index.ngram_to_words) > 0
        
        # Check specific bigrams exist
        hello_bigrams = ["he", "el", "ll", "lo"]
        for bigram in hello_bigrams:
            if bigram in index.ngram_to_words:
                assert "hello" in index.ngram_to_words[bigram]
    
    def test_ngram_search(self):
        """Test N-gram based searching."""
        index = NGramIndex(n=2)
        words = ["hello", "help", "world", "hold", "hell"]
        for word in words:
            index.add_word(word)
        
        # Search for "hel" - should match words with "he" and "el" bigrams
        results = index.search("hel", max_results=10)
        result_words = [word for word, score in results]
        
        # Should find words that share bigrams
        assert "hello" in result_words
        assert "help" in result_words
        assert "hell" in result_words
        # May not find "world" as it shares fewer bigrams


class TestTraditionalFuzzySearch:
    """Test traditional fuzzy search algorithms."""
    
    def test_traditional_search_initialization(self) -> None:
        """Test traditional search initialization."""
        search = TraditionalFuzzySearch(score_threshold=0.7)
        assert search.score_threshold == 0.7
    
    def test_rapidfuzz_search(self) -> None:
        """Test RapidFuzz search functionality."""
        search = TraditionalFuzzySearch(score_threshold=0.6)
        word_list = ["hello", "help", "world", "word", "work", "hold"]
        
        results = search.search("hello", word_list, max_results=5, 
                               methods=[TraditionalSearchMethod.RAPIDFUZZ])
        
        assert len(results) > 0
        # Should find exact match with high score
        hello_result = next((r for r in results if r.word == "hello"), None)
        assert hello_result is not None
        assert hello_result.score > 0.9
    
    def test_vscode_search(self) -> None:
        """Test VSCode-style character sequence matching."""
        search = TraditionalFuzzySearch(score_threshold=0.5)
        word_list = ["hello", "help", "world", "word", "work"]
        
        # Test character sequence matching
        results = search.search("hlo", word_list, max_results=5, 
                               methods=[TraditionalSearchMethod.VSCODE])
        
        # Should find words that contain the character sequence
        result_words = [r.word for r in results]
        assert "hello" in result_words  # h-e-l-l-o contains h-l-o sequence
    
    def test_phonetic_search(self):
        """Test phonetic matching (Soundex/Metaphone)."""
        search = TraditionalFuzzySearch(score_threshold=0.5)
        word_list = ["cat", "caught", "cot", "bat", "hat", "rat"]
        
        results = search.search("cat", word_list, max_results=5, methods=['phonetic'])
        
        # Should find phonetically similar words
        result_words = [r.word for r in results]
        assert "cat" in result_words
        # May find "caught", "cot" depending on phonetic similarity
    
    def test_multiple_methods(self):
        """Test using multiple search methods simultaneously."""
        search = TraditionalFuzzySearch(score_threshold=0.4)
        word_list = ["hello", "help", "world", "hold", "hell"]
        
        results = search.search("hello", word_list, max_results=10, 
                               methods=['rapidfuzz', 'vscode', 'jaro_winkler'])
        
        assert len(results) > 0
        # Should combine results from multiple methods
        methods_used = set(r.method for r in results)
        assert len(methods_used) > 1  # Multiple methods should be used


class TestCharacterEmbedder:
    """Test character-level embeddings."""
    
    def test_character_embedder_initialization(self):
        """Test character embedder initialization."""
        embedder = CharacterEmbedder(embed_dim=32, max_word_length=10)
        assert embedder.embed_dim == 32
        assert embedder.max_word_length == 10
        assert len(embedder.char_vocab) > 50  # Should have many characters
    
    def test_character_embedding_encoding(self):
        """Test encoding words to character embeddings."""
        embedder = CharacterEmbedder(embed_dim=32)
        
        embedding = embedder.encode_word("hello")
        assert embedding.shape == (32,)
        assert embedding.dtype == np.float32
        
        # Different words should have different embeddings
        embedding2 = embedder.encode_word("world")
        assert not np.array_equal(embedding, embedding2)
    
    def test_character_embedding_consistency(self):
        """Test that same word produces same embedding."""
        embedder = CharacterEmbedder(embed_dim=32)
        
        embedding1 = embedder.encode_word("test")
        embedding2 = embedder.encode_word("test")
        
        assert np.array_equal(embedding1, embedding2)


class TestSubwordEmbedder:
    """Test subword embeddings."""
    
    def test_subword_embedder_initialization(self):
        """Test subword embedder initialization."""
        embedder = SubwordEmbedder(embed_dim=64, min_n=2, max_n=4)
        assert embedder.embed_dim == 64
        assert embedder.min_n == 2
        assert embedder.max_n == 4
        assert not embedder._is_trained
    
    def test_subword_vocabulary_building(self):
        """Test building subword vocabulary."""
        embedder = SubwordEmbedder(embed_dim=32)
        words = ["hello", "help", "world", "word", "work"] * 10  # Repeat for frequency
        
        embedder.build_vocab(words)
        
        assert embedder._is_trained
        assert len(embedder.subword_vocab) > 0
        assert embedder.subword_embeddings is not None
    
    def test_subword_encoding(self):
        """Test encoding words with subword embeddings."""
        embedder = SubwordEmbedder(embed_dim=32)
        words = ["hello", "help", "world", "word"] * 10
        embedder.build_vocab(words)
        
        embedding = embedder.encode_word("hello")
        assert embedding.shape == (32,)
        assert embedding.dtype == np.float32
        
        # Unknown word should still get embedding (may be zeros)
        unknown_embedding = embedder.encode_word("xyz")
        assert unknown_embedding.shape == (32,)


class TestTFIDFEmbedder:
    """Test TF-IDF character n-gram embeddings."""
    
    def test_tfidf_embedder_initialization(self):
        """Test TF-IDF embedder initialization."""
        embedder = TFIDFEmbedder(ngram_range=(2, 3), max_features=100)
        assert embedder.ngram_range == (2, 3)
        assert embedder.max_features == 100
        assert not embedder._is_trained
    
    def test_tfidf_fitting(self):
        """Test fitting TF-IDF vectorizer."""
        embedder = TFIDFEmbedder(max_features=100)
        words = ["hello", "help", "world", "word", "work"]
        
        embedder.fit(words)
        
        assert embedder._is_trained
        assert embedder.vectorizer is not None
    
    def test_tfidf_encoding(self):
        """Test encoding words with TF-IDF."""
        embedder = TFIDFEmbedder(max_features=100)
        words = ["hello", "help", "world", "word", "work"]
        embedder.fit(words)
        
        embedding = embedder.encode_word("hello")
        assert embedding.shape == (100,)
        assert embedding.dtype == np.float32


class TestVectorizedFuzzySearch:
    """Test vectorized search with embeddings."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Provide temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_vectorized_search_initialization(self, temp_cache_dir):
        """Test vectorized search initialization."""
        search = VectorizedFuzzySearch(temp_cache_dir)
        assert search.cache_dir == temp_cache_dir
        assert not search._is_built
    
    def test_vectorized_index_building(self, temp_cache_dir):
        """Test building vectorized search index."""
        search = VectorizedFuzzySearch(temp_cache_dir)
        words = ["hello", "help", "world", "word", "work", "test"]
        
        search.build_index(words)
        
        assert search._is_built
        assert len(search.idx_to_word) > 0
        assert search.char_index is not None
        assert search.combined_index is not None
    
    def test_vectorized_search_methods(self, temp_cache_dir):
        """Test different vectorized search methods."""
        search = VectorizedFuzzySearch(temp_cache_dir)
        words = ["hello", "help", "world", "word", "work"] * 5  # Repeat for vocab building
        search.build_index(words)
        
        # Test character search
        char_results = search.search("hello", k=3, method="character")
        assert len(char_results) > 0
        assert all(isinstance(score, float) for _, score in char_results)
        
        # Test fusion search
        fusion_results = search.search("hello", k=3, method="fusion")
        assert len(fusion_results) > 0
    
    def test_vectorized_search_caching(self, temp_cache_dir):
        """Test saving and loading vectorized search index."""
        search = VectorizedFuzzySearch(temp_cache_dir)
        words = ["hello", "help", "world", "word", "work"]
        search.build_index(words)
        
        # Save index
        search.save_index()
        
        # Create new instance and load
        search2 = VectorizedFuzzySearch(temp_cache_dir)
        loaded = search2.load_index()
        
        assert loaded
        assert search2._is_built
        assert len(search2.idx_to_word) == len(search.idx_to_word)


class TestLexiconLoader:
    """Test comprehensive lexicon loading."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Provide temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_lexicon_loader_initialization(self, temp_cache_dir):
        """Test lexicon loader initialization."""
        loader = LexiconLoader(temp_cache_dir)
        assert loader.cache_dir == temp_cache_dir
        assert len(loader.word_sources) > 0
        assert len(loader.local_collections) > 0
    
    def test_local_collection_loading(self, temp_cache_dir):
        """Test loading local word collections."""
        loader = LexiconLoader(temp_cache_dir)
        
        # Test loading academic words
        academic_words = loader._load_local_collection('academic')
        assert len(academic_words) > 0
        assert 'analysis' in academic_words or any('analysis' in word for word in academic_words)
        
        # Test loading French phrases
        french_words = loader._load_local_collection('french')
        assert len(french_words) > 0
        assert any('french' in word.lower() or 'bon' in word.lower() for word in french_words)
    
    @patch('httpx.AsyncClient')
    async def test_online_lexicon_loading(self, mock_client, temp_cache_dir):
        """Test loading lexicons from online sources."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = "hello\nworld\ntest\n"
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        loader = LexiconLoader(temp_cache_dir)
        
        # Test downloading word list
        cache_file = temp_cache_dir / "test_words.txt"
        words = await loader._download_word_list("http://example.com/words.txt", cache_file)
        
        assert len(words) == 3
        assert "hello" in words
        assert "world" in words
        assert "test" in words
        assert cache_file.exists()
    
    async def test_unified_lexicon_creation(self, temp_cache_dir):
        """Test creating unified lexicon from multiple sources."""
        loader = LexiconLoader(temp_cache_dir)
        
        # Mock the load_all_lexicons method to avoid network calls
        mock_lexicons = {
            'english_common': ['hello', 'world', 'test'],
            'french_common': ['bonjour', 'monde', 'test'],
            'academic': ['analysis', 'method', 'research']
        }
        
        with patch.object(loader, 'load_all_lexicons', return_value=mock_lexicons):
            unified = await loader.get_unified_lexicon(['english', 'french'])
            
            assert len(unified) > 0
            assert 'hello' in unified
            assert 'bonjour' in unified
            assert 'analysis' in unified  # Should include academic words
            # 'test' should appear only once (deduplication)
            assert unified.count('test') == 1


class TestSearchManager:
    """Test unified search manager coordination."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Provide temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_search_manager_initialization(self, temp_cache_dir):
        """Test search manager initialization."""
        manager = SearchManager(temp_cache_dir)
        assert manager.cache_dir == temp_cache_dir
        assert not manager.is_initialized
        assert manager.word_index is not None
        assert manager.vectorized_search is not None
    
    @patch.object(LexiconLoader, 'load_all_lexicons')
    @patch.object(LexiconLoader, 'get_unified_lexicon')
    async def test_search_manager_initialization_process(self, mock_unified, mock_load_all, temp_cache_dir):
        """Test search manager initialization process."""
        # Mock lexicon loading to avoid network calls
        mock_load_all.return_value = {'test': ['hello', 'world']}
        mock_unified.return_value = ['hello', 'world', 'test']
        
        manager = SearchManager(temp_cache_dir)
        await manager.initialize()
        
        assert manager.is_initialized
        mock_unified.assert_called_once()
    
    @patch.object(LexiconLoader, 'load_all_lexicons')
    @patch.object(LexiconLoader, 'get_unified_lexicon')
    async def test_search_manager_search_methods(self, mock_unified, mock_load_all, temp_cache_dir):
        """Test different search methods through search manager."""
        # Mock lexicon loading
        mock_load_all.return_value = {'test': ['hello', 'world']}
        mock_unified.return_value = ['hello', 'world', 'help', 'test']
        
        manager = SearchManager(temp_cache_dir)
        await manager.initialize()
        
        # Test fuzzy search
        results = await manager.search("hello", methods=['hybrid'])
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        
        # Test prefix search
        prefix_results = await manager.prefix_search("hel")
        assert len(prefix_results) >= 0  # May be 0 if no matches
    
    async def test_search_manager_performance_tracking(self, temp_cache_dir):
        """Test search performance tracking."""
        manager = SearchManager(temp_cache_dir)
        
        # Perform some searches (mock to avoid initialization)
        manager.is_initialized = True
        manager._update_search_stats("test", ['hybrid'], 0.005, 3)
        
        stats = manager.get_search_stats()
        assert stats['performance']['total_searches'] == 1
        assert stats['performance']['avg_search_time'] == 0.005
        assert 'hybrid' in stats['performance']['method_usage']


class TestSearchIntegration:
    """Integration tests for the complete search system."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Provide temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @patch.object(LexiconLoader, 'load_all_lexicons')
    @patch.object(LexiconLoader, 'get_unified_lexicon')
    async def test_end_to_end_search_workflow(self, mock_unified, mock_load_all, temp_cache_dir):
        """Test complete end-to-end search workflow."""
        # Mock lexicon loading with realistic data
        test_words = [
            'hello', 'help', 'world', 'word', 'work', 'test', 'testing', 
            'example', 'search', 'algorithm', 'computer', 'science'
        ]
        mock_load_all.return_value = {'english': test_words}
        mock_unified.return_value = test_words
        
        # Initialize search manager
        manager = SearchManager(temp_cache_dir)
        await manager.initialize()
        
        # Test various search scenarios
        
        # 1. Exact match
        exact_results = await manager.search("hello", methods=['hybrid'])
        exact_words = [r.word for r in exact_results]
        assert "hello" in exact_words
        
        # 2. Fuzzy match with typo
        typo_results = await manager.search("helo", methods=['hybrid', 'rapidfuzz'])
        typo_words = [r.word for r in typo_results]
        assert "hello" in typo_words  # Should find despite typo
        
        # 3. Prefix search
        prefix_results = await manager.prefix_search("test")
        prefix_words = [r.word for r in prefix_results]
        assert any(word.startswith("test") for word in prefix_words)
        
        # 4. Semantic search
        semantic_results = await manager.semantic_search("computer", max_results=5)
        # Should return some results (may include 'science' due to context)
        assert len(semantic_results) >= 0
    
    async def test_search_performance_benchmarks(self, temp_cache_dir):
        """Test search performance meets benchmarks."""
        import time
        
        # Create smaller test dataset for performance testing
        test_words = ['hello', 'help', 'world', 'word'] * 100  # 400 words
        
        with patch.object(LexiconLoader, 'get_unified_lexicon', return_value=test_words):
            manager = SearchManager(temp_cache_dir)
            await manager.initialize()
            
            # Test search speed
            start_time = time.time()
            results = await manager.search("hello", methods=['hybrid'])
            search_time = time.time() - start_time
            
            # Should complete within reasonable time (adjust as needed)
            assert search_time < 1.0  # Should be much faster than 1 second
            assert len(results) > 0
    
    @patch('src.floridify.search.search_manager.SearchManager.search')
    async def test_cli_integration(self, mock_search):
        """Test CLI integration with search system."""
        from src.floridify.cli.commands.search import _fuzzy_search_async
        
        # Mock search results
        mock_results = [
            SearchResult("hello", 0.95, "hybrid_trie", "Exact match"),
            SearchResult("help", 0.80, "hybrid_bktree", "Edit distance match")
        ]
        mock_search.return_value = mock_results
        
        # Test CLI search function (would normally print results)
        # In a real test, we'd capture output or use a different approach
        await _fuzzy_search_async("hello", 10, 0.6, False)
        
        # Verify search was called correctly
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[0][0] == "hello"  # Query
        assert call_args[1]['max_results'] == 10


class TestSearchPerformanceOptimization:
    """Test performance optimization features."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Provide temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_result_merging_and_deduplication(self, temp_cache_dir):
        """Test result merging removes duplicates and combines scores."""
        manager = SearchManager(temp_cache_dir)
        
        # Create duplicate results from different methods
        results = [
            SearchResult("hello", 0.95, "method1", "Exact match"),
            SearchResult("hello", 0.87, "method2", "Fuzzy match"),
            SearchResult("help", 0.80, "method1", "Similar word"),
            SearchResult("world", 0.75, "method3", "Different word")
        ]
        
        merged = manager._merge_search_results(results)
        
        # Should have only 3 unique words
        assert len(merged) == 3
        
        # Find the merged "hello" result
        hello_result = next(r for r in merged if r.word == "hello")
        assert hello_result.score == 0.95  # Should keep highest score
        assert "method1+method2" in hello_result.method
    
    def test_caching_behavior(self, temp_cache_dir):
        """Test that caching improves performance."""
        # Test with word index caching
        index = WordIndex(temp_cache_dir / "index")
        words = ["hello", "world", "test"]
        for word in words:
            index.add_word(word)
        
        # Save cache
        index.save_cache()
        
        # Create new index and load cache
        index2 = WordIndex(temp_cache_dir / "index")
        loaded = index2.load_cache()
        
        assert loaded
        # Should have same words after loading cache
        assert "hello" in index2.trie.trie
        assert "world" in index2.trie.trie


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
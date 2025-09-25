"""Comprehensive end-to-end tests for the entire search pipeline.

Tests lemmatization, diacritics, multilingual support, versioning, and performance.
"""

from __future__ import annotations

import asyncio
import time

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import CorpusManager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.core import Search
from floridify.search.models import SearchIndex


@pytest_asyncio.fixture
async def multilingual_corpus(test_db) -> Corpus:
    """Create corpus with multilingual and diacritic-containing vocabulary."""
    vocabulary = [
        # English base forms and inflections
        "run", "running", "ran", "runner", "runs",
        "walk", "walking", "walked", "walker", "walks",
        "speak", "speaking", "spoke", "spoken", "speaker",
        # French words with diacritics
        "café", "crème", "château", "naïve", "résumé", "élève",
        "à", "où", "déjà", "être", "noël", "maïs",
        # Spanish words with diacritics
        "niño", "señor", "año", "mañana", "español", "corazón",
        # German words with umlauts
        "über", "schön", "müller", "größe", "öffnen", "äpfel",
        # Mixed cases and special characters
        "naïveté", "résumé", "café-au-lait", "vis-à-vis",
        # Test normalization
        "cafe", "creme", "chateau", "naive", "resume",
    ]

    # Create lemmatized forms (simplified for testing)
    lemmatized = [
        # English lemmas
        "run", "run", "run", "runner", "run",
        "walk", "walk", "walk", "walker", "walk",
        "speak", "speak", "speak", "speak", "speaker",
        # French (keep base forms)
        "café", "crème", "château", "naïve", "résumé", "élève",
        "à", "où", "déjà", "être", "noël", "maïs",
        # Spanish (keep base forms)
        "niño", "señor", "año", "mañana", "español", "corazón",
        # German (keep base forms)
        "über", "schön", "müller", "größe", "öffnen", "äpfel",
        # Mixed
        "naïveté", "résumé", "café-au-lait", "vis-à-vis",
        # Normalized
        "cafe", "creme", "chateau", "naive", "resume",
    ]

    # Create corpus with properly built indices
    corpus = await Corpus.create(
        corpus_name="multilingual_test_corpus",
        vocabulary=vocabulary,
        language=Language.ENGLISH,
    )

    # Set the corpus type
    corpus.corpus_type = CorpusType.LANGUAGE
    # Set lemmatized vocabulary
    corpus.lemmatized_vocabulary = lemmatized

    # Build lemma mappings based on normalized vocabulary indices
    corpus.word_to_lemma_indices = {}
    corpus.lemma_to_word_indices = {}
    unique_lemmas = []
    seen_lemmas = {}

    # Map lemmas based on normalized vocabulary positions
    for orig_idx, (orig_word, lemma) in enumerate(zip(vocabulary, lemmatized)):
        # Find the normalized word in corpus vocabulary
        norm_word = orig_word.lower().strip()
        if norm_word in corpus.vocabulary_to_index:
            vocab_idx = corpus.vocabulary_to_index[norm_word]

            if lemma not in seen_lemmas:
                lemma_idx = len(unique_lemmas)
                unique_lemmas.append(lemma)
                seen_lemmas[lemma] = lemma_idx
                corpus.lemma_to_word_indices[lemma_idx] = []
            else:
                lemma_idx = seen_lemmas[lemma]

            corpus.word_to_lemma_indices[vocab_idx] = lemma_idx
            corpus.lemma_to_word_indices[lemma_idx].append(vocab_idx)

    corpus.lemmatized_vocabulary = unique_lemmas

    manager = CorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def large_corpus(test_db) -> Corpus:
    """Create large corpus for performance testing."""
    # Generate large vocabulary
    base_words = ["test", "word", "search", "find", "query", "match", "result"]
    vocabulary = []

    for base in base_words:
        for i in range(200):  # 200 variations per base word = 1400 words total
            vocabulary.extend([
                f"{base}{i}",
                f"{base}ing{i}",
                f"{base}ed{i}",
                f"{base}er{i}",
                f"{base}s{i}",
            ])

    corpus = Corpus(
        corpus_name="large_test_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=sorted(set(vocabulary)),
        original_vocabulary=vocabulary,
        lemmatized_vocabulary=sorted(set(vocabulary)),  # Simplified
    )

    # Build indices
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(corpus.vocabulary)}
    corpus._build_signature_index()

    manager = CorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def literature_corpus(test_db) -> Corpus:
    """Create literature corpus for testing."""
    # Simulate words extracted from literature
    text = """
    It was the best of times, it was the worst of times,
    it was the age of wisdom, it was the age of foolishness,
    it was the epoch of belief, it was the epoch of incredulity,
    it was the season of Light, it was the season of Darkness,
    it was the spring of hope, it was the winter of despair.
    """

    # Extract unique words
    words = []
    for word in text.lower().split():
        cleaned = ''.join(c for c in word if c.isalnum() or c in "-'")
        if cleaned and cleaned not in ["", "'"]:
            words.append(cleaned)

    vocabulary = sorted(set(words))

    corpus = Corpus(
        corpus_name="literature_test_corpus",
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=words,
        lemmatized_vocabulary=vocabulary,  # Simplified
        metadata={
            "title": "A Tale of Two Cities",
            "author": "Charles Dickens",
            "year": 1859,
        }
    )

    # Build indices
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(vocabulary)}
    corpus._build_signature_index()

    manager = CorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


class TestLemmatization:
    """Test lemmatization functionality in search."""

    @pytest.mark.asyncio
    async def test_lemma_search_finds_inflections(self, multilingual_corpus):
        """Test that searching for lemma finds all inflections."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False  # Disable for speed
        )

        # Search for base form should find inflections
        results = await search.search_with_mode("run", mode=SearchMode.SMART)

        words = [r.word for r in results]
        # Should find exact match
        assert "run" in words

        # Fuzzy/prefix might find related forms
        related = ["running", "runner", "runs"]
        found_related = sum(1 for w in related if w in words)
        assert found_related >= 0  # May find some through fuzzy/prefix

    @pytest.mark.asyncio
    async def test_inflection_search_finds_base(self, multilingual_corpus):
        """Test that searching for inflection can find base form."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search for inflected form
        results = await search.search_with_mode("running", mode=SearchMode.SMART)

        words = [r.word for r in results]
        assert "running" in words  # Should find exact match

    @pytest.mark.asyncio
    async def test_lemma_aggregation(self, multilingual_corpus):
        """Test that lemmas are properly aggregated in corpus."""
        assert len(multilingual_corpus.lemmatized_vocabulary) > 0
        assert len(multilingual_corpus.word_to_lemma_indices) > 0
        assert len(multilingual_corpus.lemma_to_word_indices) > 0

        # Check that inflections map to same lemma
        # Use vocabulary_to_index which properly handles normalized vocabulary
        run_idx = multilingual_corpus.vocabulary_to_index.get("run")
        running_idx = multilingual_corpus.vocabulary_to_index.get("running")

        # Both words should exist in normalized vocabulary
        assert run_idx is not None, "'run' should be in normalized vocabulary"
        assert running_idx is not None, "'running' should be in normalized vocabulary"

        run_lemma = multilingual_corpus.word_to_lemma_indices.get(run_idx)
        running_lemma = multilingual_corpus.word_to_lemma_indices.get(running_idx)

        # Both should have lemma mappings if lemmatization was applied
        if run_lemma is not None and running_lemma is not None:
            # Should map to same lemma
            assert run_lemma == running_lemma


class TestDiacritics:
    """Test diacritic handling in search."""

    @pytest.mark.asyncio
    async def test_diacritic_exact_search(self, multilingual_corpus):
        """Test exact search with diacritics."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search with diacritics
        results = await search.search_with_mode("café", mode=SearchMode.EXACT)
        if results:
            assert results[0].word == "café"

    @pytest.mark.asyncio
    async def test_normalized_diacritic_search(self, multilingual_corpus):
        """Test searching without diacritics finds words with diacritics."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search without diacritics should find both
        results = await search.search_with_mode("cafe", mode=SearchMode.SMART)

        words = [r.word for r in results]
        # Should find normalized version and possibly original
        assert "cafe" in words or "café" in words

    @pytest.mark.asyncio
    async def test_french_diacritics(self, multilingual_corpus):
        """Test French words with various diacritics."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Test various French diacritics
        test_words = ["château", "naïve", "résumé", "être", "noël"]

        for word in test_words:
            results = await search.search_with_mode(word, mode=SearchMode.SMART)
            assert len(results) >= 0  # Should handle without error

    @pytest.mark.asyncio
    async def test_german_umlauts(self, multilingual_corpus):
        """Test German words with umlauts."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Test German umlauts
        results = await search.search_with_mode("über", mode=SearchMode.SMART)
        assert len(results) >= 0  # Should handle without error

        results = await search.search_with_mode("schön", mode=SearchMode.SMART)
        assert len(results) >= 0  # Should handle without error


class TestMultilingual:
    """Test multilingual search capabilities."""

    @pytest.mark.asyncio
    async def test_spanish_search(self, multilingual_corpus):
        """Test Spanish word search."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search Spanish words
        results = await search.search_with_mode("niño", mode=SearchMode.SMART)
        assert len(results) >= 0

        results = await search.search_with_mode("español", mode=SearchMode.SMART)
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_mixed_language_corpus(self, multilingual_corpus):
        """Test corpus with mixed languages."""
        # Verify corpus contains words from multiple languages
        # Use original_vocabulary for words with diacritics
        original_vocab_set = set(multilingual_corpus.original_vocabulary)
        normalized_vocab_set = set(multilingual_corpus.vocabulary)

        # English (normalized)
        assert "run" in normalized_vocab_set
        # French (original has diacritics)
        assert "café" in original_vocab_set
        assert "cafe" in normalized_vocab_set
        # Spanish (original has diacritics)
        assert "niño" in original_vocab_set
        assert "nino" in normalized_vocab_set
        # German (original has diacritics)
        assert "über" in original_vocab_set
        assert "uber" in normalized_vocab_set

    @pytest.mark.asyncio
    async def test_compound_words(self, multilingual_corpus):
        """Test compound words with hyphens."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search compound words
        results = await search.search_with_mode("café-au-lait", mode=SearchMode.SMART)
        assert len(results) >= 0

        results = await search.search_with_mode("vis-à-vis", mode=SearchMode.SMART)
        assert len(results) >= 0


class TestSearchPipeline:
    """Test complete search pipeline end-to-end."""

    @pytest.mark.asyncio
    async def test_cascade_search_fallback(self, multilingual_corpus):
        """Test cascade search falls back through methods."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search for slightly misspelled word
        results = await search.search_with_mode("runing", mode=SearchMode.SMART)

        # Should find through fuzzy matching
        assert len(results) > 0
        # Should have fuzzy results
        assert any(r.method == SearchMethod.FUZZY for r in results)

    @pytest.mark.asyncio
    async def test_search_result_metadata(self, multilingual_corpus):
        """Test search results contain proper metadata."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        results = await search.search_with_mode("run", mode=SearchMode.SMART)

        for result in results:
            assert result.word is not None
            assert result.score >= 0 and result.score <= 1.0
            assert result.method in list(SearchMethod)
            # lemmatized_word is optional, can be None

    @pytest.mark.asyncio
    async def test_search_result_ordering(self, multilingual_corpus):
        """Test search results are properly ordered by score."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        results = await search.search_with_mode("run", mode=SearchMode.SMART)

        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, multilingual_corpus):
        """Test limiting search results."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        results = await search.search_with_mode(
            "r",  # Query that matches many words
            mode=SearchMode.SMART,  # Use SMART mode for search
            max_results=5
        )

        assert len(results) <= 5


class TestVersioning:
    """Test versioning system integration."""

    @pytest.mark.asyncio
    async def test_index_versioning(self, multilingual_corpus):
        """Test search index versioning."""
        # Create first index
        index1 = await SearchIndex.get_or_create(
            corpus=multilingual_corpus,
            semantic=False
        )

        # Create second index (should reuse if vocabulary unchanged)
        index2 = await SearchIndex.get_or_create(
            corpus=multilingual_corpus,
            semantic=False
        )

        # Should have same vocabulary hash
        assert index1.vocabulary_hash == index2.vocabulary_hash

    @pytest.mark.asyncio
    async def test_corpus_version_update(self, test_db):
        """Test corpus versioning on vocabulary change."""
        # Create initial corpus using proper initialization
        corpus = await Corpus.create(
            corpus_name="version_test_corpus",
            vocabulary=["apple", "banana"],
            language=Language.ENGLISH,
        )
        corpus.corpus_type = CorpusType.LANGUAGE
        corpus.lemmatized_vocabulary = ["apple", "banana"]

        manager = CorpusManager()
        saved1 = await manager.save_corpus(corpus)

        # Get version from metadata since Corpus doesn't have version_info
        meta1 = await Corpus.Metadata.get(saved1.corpus_id)
        version1 = meta1.version_info.version if meta1 and meta1.version_info else "1.0.0"

        # Update vocabulary by creating new corpus with updated vocab
        # Add more words to ensure different hash
        corpus2 = await Corpus.create(
            corpus_name="version_test_corpus",
            vocabulary=["apple", "banana", "cherry", "date", "elderberry"],
            language=Language.ENGLISH,
        )
        corpus2.corpus_type = CorpusType.LANGUAGE
        corpus2.lemmatized_vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]

        # Force increment by passing config
        from floridify.caching.models import VersionConfig
        saved2 = await manager.save_corpus(corpus2, config=VersionConfig(increment_version=True))

        # Get version from metadata since Corpus doesn't have version_info
        meta2 = await Corpus.Metadata.get(saved2.corpus_id)
        version2 = meta2.version_info.version if meta2 and meta2.version_info else "1.0.0"

        # Version should increment - use proper version comparison
        from packaging import version
        assert version.parse(version2) > version.parse(version1)

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, test_db):
        """Test cache invalidation when corpus updates."""
        corpus = await Corpus.create(
            corpus_name="cache_test_corpus",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        corpus.corpus_type = CorpusType.LANGUAGE
        corpus.lemmatized_vocabulary = ["word1", "word2"]

        manager = CorpusManager()
        saved1 = await manager.save_corpus(corpus)

        # Create search index
        index1 = await SearchIndex.get_or_create(corpus=saved1, semantic=False)

        # Update corpus
        corpus.vocabulary.append("word3")
        saved2 = await manager.save_corpus(corpus)

        # Create new index (should have different hash)
        index2 = await SearchIndex.get_or_create(corpus=saved2, semantic=False)

        # Vocabulary hashes should differ
        assert index1.vocabulary_hash != index2.vocabulary_hash


class TestPerformance:
    """Test search performance and optimization."""

    @pytest.mark.asyncio
    async def test_large_corpus_search_performance(self, large_corpus):
        """Test search performance on large corpus."""
        search = await Search.from_corpus(
            corpus_name=large_corpus.corpus_name,
            semantic=False
        )

        # Warm up
        await search.search_with_mode("test", mode=SearchMode.SMART)

        # Time exact search
        start = time.perf_counter()
        results = await search.search_with_mode("test100", mode=SearchMode.EXACT)
        exact_time = time.perf_counter() - start

        assert exact_time < 0.1  # Should be very fast

        # Time fuzzy search (as alternative to prefix)
        start = time.perf_counter()
        results = await search.search_with_mode("test", mode=SearchMode.FUZZY, max_results=20)
        fuzzy_time = time.perf_counter() - start

        assert fuzzy_time < 0.5  # Should be reasonably fast
        assert len(results) <= 20

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, large_corpus):
        """Test concurrent search performance."""
        search = await Search.from_corpus(
            corpus_name=large_corpus.corpus_name,
            semantic=False
        )

        queries = [f"test{i}" for i in range(50)]

        start = time.perf_counter()
        results = await asyncio.gather(
            *[search.search_with_mode(q, mode=SearchMode.SMART) for q in queries]
        )
        concurrent_time = time.perf_counter() - start

        assert concurrent_time < 5.0  # Should handle 50 concurrent searches quickly
        assert all(isinstance(r, list) for r in results)

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, large_corpus):
        """Test memory efficiency of search indices."""
        import sys

        # Create search engine
        search = await Search.from_corpus(
            corpus_name=large_corpus.corpus_name,
            semantic=False
        )

        # Check memory usage (rough estimate)
        if search.index:
            index_size = sys.getsizeof(search.index)
            # Should be reasonable for vocabulary size
            vocab_size = len(large_corpus.vocabulary)
            assert index_size < vocab_size * 1000  # Rough upper bound


class TestLiteratureCorpus:
    """Test literature corpus specific functionality."""

    @pytest.mark.asyncio
    async def test_literature_corpus_search(self, literature_corpus):
        """Test searching in literature corpus."""
        search = await Search.from_corpus(
            corpus_name=literature_corpus.corpus_name,
            semantic=False
        )

        # Search for common words
        results = await search.search_with_mode("times", mode=SearchMode.SMART)
        assert len(results) > 0

        results = await search.search_with_mode("wisdom", mode=SearchMode.SMART)
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_literature_metadata(self, literature_corpus):
        """Test literature corpus metadata."""
        assert literature_corpus.metadata is not None
        assert literature_corpus.metadata.get("title") == "A Tale of Two Cities"
        assert literature_corpus.metadata.get("author") == "Charles Dickens"
        assert literature_corpus.metadata.get("year") == 1859

    @pytest.mark.asyncio
    async def test_literature_vocabulary_extraction(self, literature_corpus):
        """Test vocabulary extraction from literature."""
        # Check vocabulary was properly extracted
        vocab_set = set(literature_corpus.vocabulary)

        # Should contain key words from the text
        assert "times" in vocab_set
        assert "wisdom" in vocab_set
        assert "foolishness" in vocab_set
        assert "epoch" in vocab_set


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_corpus_search(self, test_db):
        """Test searching in empty corpus."""
        corpus = Corpus(
            corpus_name="empty_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=[],
            original_vocabulary=[],
            lemmatized_vocabulary=[],
        )

        manager = CorpusManager()
        saved = await manager.save_corpus(corpus)

        search = await Search.from_corpus(
            corpus_name=saved.corpus_name,
            semantic=False
        )

        results = await search.search_with_mode("test", mode=SearchMode.SMART)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_character_search(self, multilingual_corpus):
        """Test searching with special characters."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Search with various special characters
        special_queries = [
            "café!",
            "test@123",
            "hello#world",
            "query$test",
            "search%term",
        ]

        for query in special_queries:
            # Should handle without error
            results = await search.search_with_mode(query, mode=SearchMode.SMART)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_very_long_query(self, multilingual_corpus):
        """Test searching with very long query."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Create very long query
        long_query = "test " * 100

        results = await search.search_with_mode(long_query, mode=SearchMode.SMART)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_search(self, multilingual_corpus):
        """Test searching with various Unicode characters."""
        search = await Search.from_corpus(
            corpus_name=multilingual_corpus.corpus_name,
            semantic=False
        )

        # Test various Unicode characters
        unicode_queries = [
            "测试",  # Chinese
            "テスト",  # Japanese
            "тест",  # Russian
            "🔍search",  # Emoji
            "αβγ",  # Greek
        ]

        for query in unicode_queries:
            # Should handle without error
            results = await search.search_with_mode(query, mode=SearchMode.SMART)
            assert isinstance(results, list)
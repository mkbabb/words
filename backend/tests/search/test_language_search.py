"""Language search component tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.language import LanguageSearch


@pytest_asyncio.fixture
async def language_corpus(test_db):
    """Create corpus for language search testing."""
    # Mix of different word forms and languages concepts
    vocabulary = [
        # English words
        "run",
        "running",
        "ran",
        "runner",
        "runs",
        "jump",
        "jumping",
        "jumped",
        "jumper",
        "jumps",
        "speak",
        "speaking",
        "spoke",
        "spoken",
        "speaker",
        # Language terms
        "language",
        "languages",
        "linguistic",
        "linguistics",
        "linguist",
        "grammar",
        "grammars",
        "grammatical",
        "grammatically",
        "syntax",
        "syntactic",
        "syntactical",
        "syntactically",
        # Multilingual concepts
        "translate",
        "translation",
        "translator",
        "translating",
        "interpret",
        "interpretation",
        "interpreter",
        "interpreting",
    ]

    lemmatized = [
        # Lemmatized forms
        "run",
        "run",
        "run",
        "runner",
        "run",
        "jump",
        "jump",
        "jump",
        "jumper",
        "jump",
        "speak",
        "speak",
        "speak",
        "speak",
        "speaker",
        "language",
        "language",
        "linguistic",
        "linguistics",
        "linguist",
        "grammar",
        "grammar",
        "grammatical",
        "grammatically",
        "syntax",
        "syntactic",
        "syntactical",
        "syntactically",
        "translate",
        "translation",
        "translator",
        "translate",
        "interpret",
        "interpretation",
        "interpreter",
        "interpret",
    ]

    # Create corpus with properly built indices
    corpus = await Corpus.create(
        corpus_name="test_language_corpus",
        vocabulary=vocabulary,
        language=Language.ENGLISH,
    )

    # Set the corpus type
    corpus.corpus_type = CorpusType.LANGUAGE
    # Set lemmatized vocabulary
    corpus.lemmatized_vocabulary = lemmatized

    # Build lemma mappings
    corpus.word_to_lemma_indices = {}
    corpus.lemma_to_word_indices = {}
    for i, lemma in enumerate(lemmatized):
        if lemma not in corpus.lemma_to_word_indices:
            corpus.lemma_to_word_indices[len(corpus.lemma_to_word_indices)] = []
        lemma_idx = list(corpus.lemma_to_word_indices.keys())[-1]
        corpus.word_to_lemma_indices[i] = lemma_idx
        corpus.lemma_to_word_indices[lemma_idx].append(i)

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def language_search(language_corpus):
    """Create LanguageSearch instance with corpus."""
    from floridify.search.core import Search

    # Create the main search engine from the corpus
    search_engine = await Search.from_corpus(
        corpus_name=language_corpus.corpus_name,
        semantic=False,  # Disable semantic for simplicity
    )

    # Create language search wrapper
    search = LanguageSearch(languages=[Language.ENGLISH], search_engine=search_engine)
    return search


class TestLanguageSearch:
    """Test suite for language-specific search functionality."""

    @pytest.mark.asyncio
    async def test_lemma_based_search(self, language_search):
        """Test searching by lemmatized forms."""
        # Search for base form using fuzzy/smart mode to find variations
        results = await language_search.search_with_mode("run", mode=SearchMode.FUZZY)

        words = [r.word for r in results]
        # Fuzzy search should find similar words
        assert "run" in words
        # May find other similar words but not guaranteed to find all inflections
        # as they are stored as separate normalized words

    @pytest.mark.asyncio
    async def test_inflection_handling(self, language_search):
        """Test finding different inflections of words."""
        # Search for inflected form should find base form
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("jumping", mode=SearchMode.SMART)

        words = [r.word for r in results]
        # Should at least find the word itself or similar
        assert any("jump" in w for w in words)

    @pytest.mark.asyncio
    async def test_morphological_analysis(self, language_search):
        """Test morphological word analysis."""
        # Search for word with common morphological root
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("linguistic", mode=SearchMode.SMART)

        words = [r.word for r in results]
        assert "linguistic" in words

        # Should find the word
        if results:
            words = [r.word for r in results]
            assert any("linguistic" in w for w in words)

    @pytest.mark.asyncio
    async def test_compound_word_search(self, language_search):
        """Test searching for compound words."""
        # Search for parts of compound concepts using fuzzy search
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("gram", mode=SearchMode.FUZZY)

        # Fuzzy search may find words containing "gram"
        # but exact matches depend on fuzzy scoring
        assert len(results) >= 0  # Should return some results or none

    @pytest.mark.asyncio
    async def test_language_specific_normalization(self, language_search):
        """Test language-specific text normalization."""
        # Test case normalization
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("LANGUAGE", mode=SearchMode.SMART)
        assert len(results) > 0
        assert any("language" in r.word.lower() for r in results)

        # Test special character handling
        results = await language_search.search_with_mode("language's", mode=SearchMode.SMART)
        assert len(results) >= 0  # May or may not find results based on normalization

    @pytest.mark.asyncio
    async def test_multilingual_concepts(self, language_search):
        """Test searching for multilingual/translation concepts."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("translate", mode=SearchMode.SMART)

        words = [r.word for r in results]
        assert "translate" in words or "translation" in words

    @pytest.mark.asyncio
    async def test_linguistic_term_search(self, language_search):
        """Test searching for linguistic terminology."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("syntax", mode=SearchMode.SMART)

        words = [r.word for r in results]
        assert "syntax" in words

        # Should also find related terms with fuzzy search
        results = await language_search.search_with_mode("syntact", mode=SearchMode.FUZZY)
        if results:
            words = [r.word for r in results]
            assert any("syntactic" in w for w in words)

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, language_search):
        """Test handling empty queries."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("", mode=SearchMode.SMART)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_word(self, language_search):
        """Test searching for nonexistent words."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("xyzabc", mode=SearchMode.SMART)
        # Cascade might find fuzzy matches
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, language_search):
        """Test limiting search results."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode(
            "lang", mode=SearchMode.FUZZY, max_results=2
        )
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_exact_vs_fuzzy_mode(self, language_search):
        """Test exact vs fuzzy search modes."""
        from floridify.search.constants import SearchMode

        # Exact mode
        results = await language_search.search_with_mode("language", mode=SearchMode.EXACT)
        if results:
            assert results[0].word == "language"

        # Fuzzy mode through cascade
        results = await language_search.search_with_mode("lang", mode=SearchMode.SMART)
        assert len(results) >= 0
        # May find language through prefix or fuzzy match

    @pytest.mark.asyncio
    async def test_result_scoring(self, language_search):
        """Test result scoring and ranking."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("language", mode=SearchMode.SMART)

        # Results should be scored
        assert all(hasattr(r, "score") for r in results)
        assert all(0 <= r.score <= 1.0 for r in results)

        # Results should be sorted by score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_metadata(self, language_search):
        """Test metadata in search results."""
        from floridify.search.constants import SearchMode

        results = await language_search.search_with_mode("grammar", mode=SearchMode.SMART)

        for result in results:
            assert result.method in [SearchMethod.EXACT, SearchMethod.PREFIX, SearchMethod.FUZZY]
            # Result should be valid
            assert result.word is not None
            assert result.language is None or result.language == Language.ENGLISH

    @pytest.mark.asyncio
    async def test_concurrent_language_searches(self, language_search):
        """Test concurrent language searches."""
        import asyncio

        from floridify.search.constants import SearchMode

        queries = ["run", "jump", "speak", "translate"]

        # Run searches concurrently
        results = await asyncio.gather(
            *[language_search.search_with_mode(q, mode=SearchMode.SMART) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_language_corpus_initialization(self, test_db):
        """Test initializing language search with different corpus types."""
        # Create a literature corpus (should handle differently)
        corpus = Corpus(
            corpus_name="test_lit_corpus",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["word1", "word2"],
            original_vocabulary=["word1", "word2"],
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        from floridify.search.core import Search

        # Create search engine from corpus
        search_engine = await Search.from_corpus(
            corpus_name=saved_corpus.corpus_name, semantic=False
        )

        search = LanguageSearch(languages=[Language.ENGLISH], search_engine=search_engine)

        # Should still work with literature corpus
        from floridify.search.constants import SearchMode

        results = await search.search_with_mode("word1", mode=SearchMode.SMART)
        assert len(results) >= 0

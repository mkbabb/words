"""Configuration and fixtures for search tests.

Semantic Index Caching (Performance Optimization):
    The search system leverages the existing cache infrastructure for semantic indices.
    When a semantic index is built, it's automatically cached via the VersionManager:

    - L1 (Memory): In-process cache for instant access (~1ms)
    - L2 (Filesystem): Persistent cache survives test runs (~10ms)
    - L3 (MongoDB): Database-backed versioned storage (~100ms)

    This means:
    1. First test that builds a semantic index: ~1-3s (model load + embedding)
    2. Subsequent tests with same corpus: ~10-100ms (cache hit)
    3. Across test sessions: ~100ms-1s (L2/L3 cache hit)

    No special warming fixtures needed - KISS principle applies!
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import CorpusManager
from floridify.models.dictionary import Definition, DictionaryProvider, Language, Word
from floridify.search.core import Search
from floridify.search.models import SearchIndex
from floridify.search.semantic.core import SemanticSearch

@pytest_asyncio.fixture
async def search_test_words(test_db):
    """Create a comprehensive set of test words for search testing."""
    words_data = [
        # Common words
        {"text": "test", "normalized": "test", "lemma": "test"},
        {"text": "testing", "normalized": "testing", "lemma": "test"},
        {"text": "tested", "normalized": "tested", "lemma": "test"},
        {"text": "example", "normalized": "example", "lemma": "example"},
        {"text": "examples", "normalized": "examples", "lemma": "example"},
        # Words with special characters
        {"text": "hello-world", "normalized": "hello-world", "lemma": "hello-world"},
        {"text": "test_case", "normalized": "test_case", "lemma": "test_case"},
        {"text": "multi-word", "normalized": "multi-word", "lemma": "multi-word"},
        # Unicode words
        {"text": "café", "normalized": "cafe", "lemma": "cafe"},
        {"text": "naïve", "normalized": "naive", "lemma": "naive"},
        {"text": "résumé", "normalized": "resume", "lemma": "resume"},
        # Words for fuzzy matching
        {"text": "color", "normalized": "color", "lemma": "color"},
        {"text": "colour", "normalized": "colour", "lemma": "color"},
        {"text": "organize", "normalized": "organize", "lemma": "organize"},
        {"text": "organise", "normalized": "organise", "lemma": "organize"},
    ]

    created_words = []
    for word_data in words_data:
        word = Word(**word_data, language=Language.ENGLISH)
        await word.save()

        # Add a basic definition for each word
        definition = Definition(
            word_id=word.id,
            meaning=f"Definition for {word.text}",
            examples=[f"Example using {word.text}"],
            provider=DictionaryProvider.WIKTIONARY,
        )
        await definition.save()

        created_words.append(word)

    return created_words


@pytest_asyncio.fixture
async def empty_search_engine(test_db):
    """Create an empty search engine instance."""
    from beanie import PydanticObjectId

    index = SearchIndex(
        corpus_id=PydanticObjectId(),
        corpus_name="empty_test_corpus",
        vocabulary_hash="empty_test_hash_" + str(PydanticObjectId()),
        semantic_enabled=False,
    )
    engine = Search(index=index)
    return engine


@pytest_asyncio.fixture
async def populated_search_engine(search_test_words):
    """Create a search engine populated with test words."""
    from beanie import PydanticObjectId

    index = SearchIndex(
        corpus_id=PydanticObjectId(),
        corpus_name="populated_test_corpus",
        vocabulary_hash="populated_test_hash_" + str(PydanticObjectId()),
        semantic_enabled=False,
    )
    engine = Search(index=index)
    return engine


@pytest_asyncio.fixture
async def semantic_search_engine(search_test_words):
    """Create a search engine with semantic search enabled."""
    from beanie import PydanticObjectId

    index = SearchIndex(
        corpus_id=PydanticObjectId(),
        corpus_name="semantic_test_corpus",
        vocabulary_hash="semantic_test_hash_" + str(PydanticObjectId()),
        semantic_enabled=True,
    )
    engine = Search(index=index)
    return engine


@pytest.fixture
def search_test_queries():
    """Provide common test queries for search testing."""
    return {
        "exact": ["test", "example", "café"],
        "fuzzy": ["tset", "exmaple", "colo"],
        "prefix": ["test", "exam", "multi"],
        "contains": ["est", "amp", "wor"],
        "lemma": ["testing", "examples", "organized"],
        "unicode": ["café", "naïve", "résumé"],
        "special_chars": ["hello-world", "test_case", "multi-word"],
        "empty": ["", " ", None],
        "nonexistent": ["xyz123", "notaword", "qwerty9876"],
    }


@pytest.fixture
def expected_search_results():
    """Expected results for various search queries."""
    return {
        "test": ["test", "testing", "tested"],
        "exam": ["example", "examples"],
        "color": ["color", "colour"],
        "organize": ["organize", "organise"],
    }


async def await_semantic_ready(engine: Search, timeout: float = 60.0) -> None:
    """Wait for semantic search to be ready in a Search engine.

    This utility function waits for the background semantic initialization
    to complete, with a timeout to prevent hanging tests.

    Args:
        engine: Search engine with semantic search
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If semantic search doesn't become ready within timeout
    """
    if not engine.semantic_search or not hasattr(engine, "_semantic_init_task"):
        return

    start_time = asyncio.get_event_loop().time()

    while engine._semantic_init_task and not engine._semantic_init_task.done():
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(
                f"Semantic search initialization timed out after {timeout}s"
            )
        await asyncio.sleep(0.1)  # Check every 100ms


# Make await_semantic_ready available as a fixture too
@pytest_asyncio.fixture
async def semantic_ready_helper():
    """Provide helper function to wait for semantic initialization."""
    return await_semantic_ready

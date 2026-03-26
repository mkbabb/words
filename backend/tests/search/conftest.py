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
import random
import statistics
import time

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.dictionary import Definition, DictionaryProvider, Language, Word
from floridify.search.engine import Search
from floridify.search.index import SearchIndex
from floridify.search.semantic.search import SemanticSearch

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def shared_semantic_corpus(test_db_session):
    """Session-scoped corpus with pre-built semantic index.

    For tests that NEED a semantic index but don't test index creation itself.
    Builds the index once per session and shares it across all semantic tests.
    """
    vocabulary = [
        # Emotion words
        "happy",
        "joyful",
        "cheerful",
        "glad",
        "delighted",
        "sad",
        "unhappy",
        "sorrowful",
        "miserable",
        "dejected",
        "angry",
        "furious",
        "irate",
        "enraged",
        "irritated",
        "calm",
        "peaceful",
        "serene",
        "tranquil",
        "relaxed",
        # Animal words
        "dog",
        "cat",
        "elephant",
        "tiger",
        "lion",
        # Food words
        "apple",
        "banana",
        "orange",
        "bread",
        "cheese",
        # Action words
        "run",
        "walk",
        "jump",
        "swim",
        "fly",
    ]

    sorted_vocab = sorted(vocabulary)
    corpus = Corpus(
        corpus_name="shared_semantic_test",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=sorted_vocab,
        original_vocabulary=sorted_vocab,
        lemmatized_vocabulary=sorted_vocab,
    )
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted_vocab)}
    corpus._build_candidate_index()

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)

    # Pre-build semantic index so tests don't have to
    engine = await SemanticSearch.from_corpus(corpus=saved)
    await engine.initialize()

    return saved


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
        word = Word(**word_data, languages=[Language.ENGLISH])
        await word.save()

        # Add a basic definition for each word
        definition = Definition(
            word_id=word.id,
            text=f"Definition for {word.text}",
            part_of_speech="noun",
            providers=[DictionaryProvider.WIKTIONARY],
        )
        await definition.save()

        created_words.append(word)

    return created_words


@pytest_asyncio.fixture
async def empty_search_engine(test_db):
    """Create an empty search engine instance."""
    from beanie import PydanticObjectId

    index = SearchIndex(
        corpus_uuid=str(PydanticObjectId()),
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
        corpus_uuid=str(PydanticObjectId()),
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
        corpus_uuid=str(PydanticObjectId()),
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
            raise TimeoutError(f"Semantic search initialization timed out after {timeout}s")
        await asyncio.sleep(0.1)  # Check every 100ms


# Make await_semantic_ready available as a fixture too
@pytest_asyncio.fixture
async def semantic_ready_helper():
    """Provide helper function to wait for semantic initialization."""
    return await_semantic_ready


# ═══════════════════════════════════════════════════════════════════
#  Vocabulary generation (deterministic, shared across optimization tests)
# ═══════════════════════════════════════════════════════════════════

_SEED_WORDS = [
    "apple",
    "banana",
    "cherry",
    "mountain",
    "river",
    "ocean",
    "forest",
    "happy",
    "angry",
    "calm",
    "excited",
    "beautiful",
    "dangerous",
    "important",
    "run",
    "walk",
    "jump",
    "think",
    "speak",
    "write",
    "understand",
    "elephant",
    "tiger",
    "dolphin",
    "eagle",
    "butterfly",
    "penguin",
    "computer",
    "algorithm",
    "database",
    "network",
    "software",
    "hardware",
    "democracy",
    "philosophy",
    "mathematics",
    "literature",
    "psychology",
    "restaurant",
    "hospital",
    "university",
    "government",
    "environment",
    "perspective",
    "communication",
    "responsibility",
    "extraordinary",
    "acknowledgment",
    "circumstantial",
    "discrimination",
    "comprehensive",
    "perpendicular",
    "rehabilitation",
    "superintendent",
    "transformation",
]

_PREFIXES = ["un", "re", "pre", "mis", "over", "under", "out", "dis", "non", "anti"]
_SUFFIXES = [
    "ing",
    "tion",
    "ness",
    "ment",
    "able",
    "ible",
    "ous",
    "ive",
    "ful",
    "less",
    "ly",
    "er",
    "est",
    "ize",
    "ify",
    "al",
    "ial",
    "ed",
    "en",
    "ity",
]


def _generate_vocabulary(target_size: int) -> list[str]:
    """Deterministic vocabulary at *target_size*."""
    vocab: set[str] = set(_SEED_WORDS)

    for word in list(_SEED_WORDS):
        for pfx in _PREFIXES:
            vocab.add(f"{pfx}{word}")
        for sfx in _SUFFIXES:
            vocab.add(f"{word}{sfx}")
        for pfx in _PREFIXES:
            for sfx in _SUFFIXES:
                vocab.add(f"{pfx}{word}{sfx}")

    rng = random.Random(42)
    families = [
        "lex",
        "morph",
        "syn",
        "sem",
        "phon",
        "graph",
        "prag",
        "cog",
        "neur",
        "psych",
        "soci",
        "anthro",
        "bio",
        "geo",
        "astro",
    ]
    i = 0
    while len(vocab) < target_size:
        fam = families[i % len(families)]
        length = rng.randint(4, 14)
        consonants, vowels = "bcdfghjklmnpqrstvwxyz", "aeiou"
        w = fam
        for j in range(length - len(fam)):
            w += rng.choice(consonants) if j % 2 == 0 else rng.choice(vowels)
        vocab.add(w)
        i += 1

    return sorted(vocab)[:target_size]


# Pre-generate once at module load (deterministic)
VOCAB_TINY = [
    "apple",
    "application",
    "apply",
    "applied",
    "applying",
    "banana",
    "bandana",
    "balance",
    "definitely",
    "define",
    "defined",
    "definition",
    "cat",
    "car",
    "card",
    "cart",
    "care",
    "example",
    "examine",
    "excellent",
    "exercise",
    "happy",
    "happen",
    "happening",
    "happiness",
    "orange",
    "organize",
    "organic",
    "origin",
    "original",
    "test",
    "testing",
    "tested",
    "tester",
    "testimony",
    "elephant",
    "elegant",
    "element",
    "elevator",
    "elaborate",
]
VOCAB_SMALL = _generate_vocabulary(10_000)
VOCAB_MEDIUM = _generate_vocabulary(140_000)
VOCAB_LARGE = _generate_vocabulary(278_000)

# Words guaranteed in ALL vocabs (10K through 278K).
_SAFE_WORDS = sorted(set(_SEED_WORDS) & set(VOCAB_SMALL))

# Queries for every scale — ONLY words guaranteed present at 10K+
EXACT_QUERIES = _SAFE_WORDS[:10]

# Typo->target pairs — target must be in 10K+
FUZZY_QUERIES = [
    ("aple", "apple"),
    ("banna", "banana"),
    ("elefant", "elephant"),
    ("mountan", "mountain"),
    ("hapy", "happy"),
    ("computr", "computer"),
    ("algorythm", "algorithm"),
    ("filosofy", "philosophy"),
    ("beautful", "beautiful"),
    ("databse", "database"),
]
# Filter to only targets in 10K vocab
FUZZY_QUERIES = [(t, e) for t, e in FUZZY_QUERIES if e in set(VOCAB_SMALL)]

# Large-scale only queries (words only in 278K)
EXACT_QUERIES_LARGE = [
    "understand",
    "river",
    "run",
    "walk",
    "tiger",
    "software",
    "university",
    "transformation",
]
FUZZY_QUERIES_LARGE = [
    ("undrstnd", "understand"),
    ("rivr", "river"),
    ("tigr", "tiger"),
    ("softwre", "software"),
]

SMART_QUERIES = [
    w
    for w in [
        "apple",
        "happy",
        "banana",
        "elephant",
        "mountain",
        "algorithm",
        "beautiful",
        "database",
        "computer",
        "philosophy",
    ]
    if w in set(VOCAB_SMALL)
][:10]

SEMANTIC_QUERIES = ["fruit", "animal", "emotion", "technology", "nature"]

VOCAB_DIACRITICS = [
    # Diacritics
    "café",
    "naive",
    "naïve",
    "résumé",
    "resume",
    "über",
    "cliché",
    "fiancée",
    "sauté",
    "touché",
    "jalapeño",
    "piñata",
    "señor",
    # Multi-word / phrases
    "en coulisses",
    "a fond",
    "ice cream",
    "well known",
    "machine learning",
    "hot dog",
    "new york",
    "ad hoc",
    # Contraction-expanded forms (normalize expands: "don't" -> "do not")
    "do not",
    "it is",
    "can not",
    "will not",
    "should not",
    # Simple words for baseline
    "apple",
    "banana",
    "happy",
    "sad",
    "dog",
    "cat",
    "mountain",
    "river",
    "forest",
    "ocean",
    "computer",
    "algorithm",
]


# ═══════════════════════════════════════════════════════════════════
#  Corpus + engine helpers (no DB)
# ═══════════════════════════════════════════════════════════════════


async def _make_corpus(test_db, name: str, vocab: list[str]) -> Corpus:
    """Create and persist a corpus (requires active Beanie DB)."""
    corpus = await Corpus.create(
        corpus_name=name,
        vocabulary=vocab,
        language=Language.ENGLISH,
    )
    corpus.corpus_type = CorpusType.LANGUAGE
    manager = TreeCorpusManager()
    return await manager.save_corpus(corpus)


async def _make_corpus_inmemory(name: str, vocab: list[str]) -> Corpus:
    """Create a corpus in-memory only (no DB calls).

    Used for session-scoped fixtures that must not depend on Beanie global state.
    """
    import uuid

    corpus = await Corpus.create(
        corpus_name=name,
        vocabulary=vocab,
        language=Language.ENGLISH,
    )
    corpus.corpus_type = CorpusType.LANGUAGE
    # Set UUID manually since we're not saving to DB
    if not corpus.corpus_uuid:
        corpus.corpus_uuid = str(uuid.uuid4())
    return corpus


async def _make_engine(corpus: Corpus) -> Search:
    """Build a Search engine in-memory (no DB calls).

    Avoids TrieIndex.get_or_create() which hits MongoDB -- important for
    session-scoped fixtures that must not depend on Beanie global state.
    """
    from floridify.search.fuzzy.bk_tree import BKTree
    from floridify.search.fuzzy.search import FuzzySearch
    from floridify.search.fuzzy.suffix_array import SuffixArray
    from floridify.search.phonetic.index import PhoneticIndex
    from floridify.search.trie.index import TrieIndex
    from floridify.search.trie.search import TrieSearch

    engine = Search()
    engine.corpus = corpus

    # Build index metadata in-memory
    engine.index = SearchIndex(
        corpus_name=corpus.corpus_name,
        corpus_uuid=corpus.corpus_uuid or "",
        vocabulary_hash=corpus.vocabulary_hash,
        semantic_enabled=False,
    )

    # Build trie in-memory (TrieIndex.create is pure, no DB)
    trie_index = await TrieIndex.create(corpus)
    engine.trie_search = TrieSearch(index=trie_index)

    # Build fuzzy search with BK-tree and phonetic index
    engine.fuzzy_search = FuzzySearch(min_score=engine.index.min_score)

    engine.fuzzy_search.bk_tree = BKTree.build(corpus.vocabulary)
    engine.fuzzy_search.phonetic_index = PhoneticIndex(corpus.vocabulary)
    engine.suffix_array = SuffixArray(corpus.vocabulary)

    engine._initialized = True
    return engine


# ═══════════════════════════════════════════════════════════════════
#  Session-scoped corpus + engine fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def tiny_corpus() -> Corpus:
    return await _make_corpus_inmemory("opt_tiny", VOCAB_TINY)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def small_corpus() -> Corpus:
    return await _make_corpus_inmemory("opt_10k", VOCAB_SMALL)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def medium_corpus() -> Corpus:
    return await _make_corpus_inmemory("opt_140k", VOCAB_MEDIUM)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def large_corpus() -> Corpus:
    return await _make_corpus_inmemory("opt_278k", VOCAB_LARGE)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def tiny_engine(tiny_corpus) -> Search:
    return await _make_engine(tiny_corpus)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def small_engine(small_corpus) -> Search:
    return await _make_engine(small_corpus)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def medium_engine(medium_corpus) -> Search:
    return await _make_engine(medium_corpus)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def large_engine(large_corpus) -> Search:
    return await _make_engine(large_corpus)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def diacritics_corpus() -> Corpus:
    return await _make_corpus_inmemory("opt_diacritics", VOCAB_DIACRITICS)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def diacritics_engine(diacritics_corpus) -> Search:
    return await _make_engine(diacritics_corpus)


# ═══════════════════════════════════════════════════════════════════
#  Timing helpers
# ═══════════════════════════════════════════════════════════════════


def _run_timed(fn, iterations=50, warmup=5):
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }, result


async def _run_timed_async(fn, iterations=30, warmup=3):
    for _ in range(warmup):
        await fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = await fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }, result


def _fmt(stats: dict) -> str:
    return (
        f"mean={stats['mean_ms']:8.3f}ms  median={stats['median_ms']:8.3f}ms  "
        f"min={stats['min_ms']:8.3f}ms  p95={stats['p95_ms']:8.3f}ms"
    )


def _label(corpus: Corpus) -> str:
    return (
        f"{len(corpus.vocabulary) // 1000}K"
        if len(corpus.vocabulary) >= 1000
        else str(len(corpus.vocabulary))
    )



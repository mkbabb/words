"""Multi-word phrase search tests.

Verifies that the fuzzy pipeline correctly handles multi-word phrases at all
corpus sizes, including the >100K path where the full-phrase BK-tree is skipped.
Covers per-word BK-tree decomposition, suffix array substring matching, and
mixed-language phrase coverage.
"""

from __future__ import annotations

import pytest

from floridify.audit import build_corpus_fixture
from floridify.audit.fixtures import CORPUS_SIZES
from floridify.search.constants import DEFAULT_MIN_SCORE, SearchMode
from floridify.search.engine import Search
from floridify.search.fuzzy.bk_tree import BKTree
from floridify.search.fuzzy.search import FuzzySearch
from floridify.search.fuzzy.suffix_array import SuffixArray
from floridify.search.index import SearchIndex
from floridify.search.phonetic.index import PhoneticIndex
from floridify.search.trie.index import TrieIndex
from floridify.search.trie.search import TrieSearch


# Phrases injected into every test corpus to verify multi-word support.
# Deliberately does NOT include "en coulisses" (plural) — tests verify that
# fuzzy search finds "en coulisse" (singular) when the plural is queried.
PHRASE_VOCABULARY = [
    "en coulisse",
    "en masse",
    "en route",
    "mise en scene",
    "mise en place",
    "a la carte",
    "a la mode",
    "bon appetit",
    "cul de sac",
    "joie de vivre",
    "raison d etre",
    "bon voyage",
]


async def _build_phrase_engine(name: str, size: int) -> Search:
    """Build an in-memory search engine with phrase vocabulary included.

    Merges PHRASE_VOCABULARY into the generated corpus, then builds all search
    components (trie, BK-tree, phonetic, suffix array) in-memory without DB.
    """
    corpus = await build_corpus_fixture(name, size)
    # Merge phrases into vocabulary (in-memory, no DB)
    merged = sorted(set(corpus.vocabulary) | set(PHRASE_VOCABULARY))
    corpus.vocabulary = merged
    corpus.original_vocabulary = list(merged)
    corpus.vocabulary_to_index = {w: i for i, w in enumerate(merged)}
    # Rebuild normalized→original index so _get_original_word works
    corpus.normalized_to_original_indices = {i: [i] for i in range(len(merged))}
    corpus._build_candidate_index()

    # Build search components from scratch
    index = await SearchIndex.create(corpus, min_score=DEFAULT_MIN_SCORE, semantic=False)
    trie_index = await TrieIndex.create(corpus)
    index.trie_index_id = trie_index.index_id

    engine = Search(index=index, corpus=corpus)
    engine.trie_search = TrieSearch(index=trie_index)
    engine.fuzzy_search = FuzzySearch(min_score=DEFAULT_MIN_SCORE)
    engine.fuzzy_search.bk_tree = BKTree.build(merged)
    engine.fuzzy_search.phonetic_index = PhoneticIndex(merged)
    engine.suffix_array = SuffixArray(merged)
    engine._initialized = True
    engine._semantic_ready = False
    return engine


@pytest.mark.search
@pytest.mark.asyncio
@pytest.mark.parametrize("size_name", ["tiny", "small", "medium"])
async def test_fuzzy_finds_phrase_edit_distance_1(size_name: str) -> None:
    """Fuzzy search must find 'en coulisse' for query 'en coulisses' at all
    corpus sizes — including >100K where the full-phrase BK-tree is skipped.

    'en coulisses' → 'en coulisse' is edit distance 1 and should score ~96%.
    The corpus contains 'en coulisse' but NOT 'en coulisses' — so the fuzzy
    pipeline must surface it, not just rely on exact match.
    """
    engine = await _build_phrase_engine(f"phrase-ed1-{size_name}", CORPUS_SIZES[size_name])

    results = engine.search_fuzzy("en coulisses", max_results=10)
    words = [r.word for r in results]

    assert "en coulisse" in words, (
        f"[{size_name}] Expected 'en coulisse' in fuzzy results for 'en coulisses', "
        f"got: {words[:5]}"
    )
    # Should be high-ranked (edit distance 1 → ~96% by RapidFuzz)
    assert results[0].word == "en coulisse" or results[0].score > 0.9


@pytest.mark.search
@pytest.mark.asyncio
async def test_per_word_bk_tree_surfaces_phrase_candidates() -> None:
    """Per-word BK-tree search should surface phrase candidates even when
    full-phrase BK-tree is skipped (corpus >100K, simulated via medium corpus)."""
    engine = await _build_phrase_engine("phrase-perword-bk", CORPUS_SIZES["medium"])

    # Collect candidates directly to verify BK-tree per-word path
    candidates = engine.fuzzy_search._collect_candidates(
        "en coulisses", engine.corpus, 200
    )

    # Resolve candidate indices to words
    candidate_words = engine.corpus.get_words_by_indices(list(candidates.keys()))

    assert "en coulisse" in candidate_words, (
        f"Per-word decomposition should surface 'en coulisse' as a candidate, "
        f"got {len(candidate_words)} candidates: {candidate_words[:10]}"
    )


@pytest.mark.search
@pytest.mark.asyncio
async def test_phrase_substring_candidates() -> None:
    """Suffix array per-word search should find phrases containing query words."""
    engine = await _build_phrase_engine("phrase-substr", CORPUS_SIZES["small"])

    # "joie de vivr" is a typo of "joie de vivre" — missing final 'e'
    results = engine.search_fuzzy("joie de vivr", max_results=10)
    words = [r.word for r in results]

    assert "joie de vivre" in words, (
        f"Expected 'joie de vivre' for query 'joie de vivr', got: {words}"
    )


@pytest.mark.search
@pytest.mark.asyncio
async def test_mixed_language_phrase_exact() -> None:
    """French-origin phrases should be findable via exact search."""
    engine = await _build_phrase_engine("phrase-exact", CORPUS_SIZES["small"])

    for phrase in ["en coulisse", "mise en scene", "a la carte", "bon appetit", "cul de sac"]:
        exact = engine.search_exact(phrase)
        assert len(exact) > 0, f"Exact search should find '{phrase}'"


@pytest.mark.search
@pytest.mark.asyncio
async def test_mixed_language_phrase_fuzzy_plural() -> None:
    """Pluralized variants of French phrases should fuzzy-match the singular."""
    engine = await _build_phrase_engine("phrase-fuzzy-pl", CORPUS_SIZES["small"])

    # Test a few representative phrases with added 's'
    for phrase in ["en coulisse", "mise en scene", "cul de sac"]:
        typo = phrase + "s"
        results = engine.search_fuzzy(typo, max_results=10)
        found_words = [r.word for r in results]
        assert phrase in found_words, (
            f"Fuzzy search for '{typo}' should find '{phrase}', got: {found_words[:5]}"
        )


@pytest.mark.search
@pytest.mark.asyncio
async def test_smart_cascade_includes_prefix_for_phrases() -> None:
    """Smart cascade should include prefix matches for multi-word queries."""
    engine = await _build_phrase_engine("phrase-cascade", CORPUS_SIZES["small"])

    results = await engine.search_with_mode(
        "en couliss", mode=SearchMode.SMART, max_results=10
    )
    words = [r.word for r in results]

    assert any(w.startswith("en couliss") for w in words), (
        f"Smart cascade for 'en couliss' should include prefix matches, got: {words}"
    )

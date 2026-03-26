"""Reproducible microbenchmarks for the in-memory search pipeline."""

from __future__ import annotations

import pytest

from floridify.audit import (
    CORPUS_SIZES,
    benchmark_async,
    benchmark_sync,
    build_search_fixture,
    build_semantic_fixture,
    install_fake_semantic_encoder,
)
from floridify.search.trie.bloom import BloomFilter


def _assert_fast_enough(case_name: str, p95_ms: float, ceiling_ms: float) -> None:
    assert p95_ms < ceiling_ms, f"{case_name} p95 {p95_ms:.2f}ms exceeded {ceiling_ms:.2f}ms"


@pytest.mark.performance
@pytest.mark.search
@pytest.mark.asyncio
@pytest.mark.parametrize("size_name", ["tiny", "small", "medium", "large"])
async def test_search_modes_across_corpus_sizes(size_name: str) -> None:
    search = await build_search_fixture(f"audit-search-{size_name}", CORPUS_SIZES[size_name])

    # Fewer iterations for large corpus to keep runtime reasonable
    iters = 4 if size_name == "large" else 12
    warmup = 1 if size_name == "large" else 2

    exact_case, exact_results = benchmark_sync(
        "exact",
        "search",
        lambda: search.search_exact("audittrail"),
        iterations=iters,
        warmup=warmup,
        metadata={"corpus_size": size_name},
    )
    prefix_case, prefix_results = benchmark_sync(
        "prefix",
        "search",
        lambda: search.search_prefix("audit", max_results=8),
        iterations=iters,
        warmup=warmup,
        metadata={"corpus_size": size_name},
    )
    fuzzy_case, fuzzy_results = benchmark_sync(
        "fuzzy",
        "search",
        lambda: search.search_fuzzy("audittral", max_results=8, min_score=0.6),
        iterations=max(3, iters - 2),
        warmup=warmup,
        metadata={"corpus_size": size_name},
    )
    smart_case, smart_results = await benchmark_async(
        "smart-cascade",
        "search",
        lambda: search._smart_search_cascade(
            "audittrail",
            max_results=8,
            min_score=0.6,
            semantic=False,
        ),
        iterations=max(3, iters - 2),
        warmup=warmup,
        metadata={"corpus_size": size_name},
    )

    assert exact_results[-1][0].word == "audittrail"
    assert "audittrail" in prefix_results[-1]
    assert any(result.word == "audittrail" for result in fuzzy_results[-1])
    assert any(result.word == "audittrail" for result in smart_results[-1])

    # Gates scale with corpus size — fuzzy is O(n), others are O(1) or O(log n)
    fuzzy_ceiling = {"tiny": 50.0, "small": 100.0, "medium": 500.0, "large": 5000.0}
    smart_ceiling = {"tiny": 100.0, "small": 150.0, "medium": 600.0, "large": 5000.0}
    _assert_fast_enough(f"{size_name}:exact", exact_case.stats.p95_ms, 20.0)
    _assert_fast_enough(f"{size_name}:prefix", prefix_case.stats.p95_ms, 40.0)
    _assert_fast_enough(f"{size_name}:fuzzy", fuzzy_case.stats.p95_ms, fuzzy_ceiling[size_name])
    _assert_fast_enough(f"{size_name}:smart", smart_case.stats.p95_ms, smart_ceiling[size_name])


@pytest.mark.performance
@pytest.mark.search
@pytest.mark.asyncio
async def test_search_dedup_and_query_switching_remain_correct() -> None:
    search = await build_search_fixture("audit-search-dedup", CORPUS_SIZES["small"])

    smart_case, smart_results = await benchmark_async(
        "smart-dedup",
        "search",
        lambda: search._smart_search_cascade(
            "audit",
            max_results=12,
            min_score=0.55,
            semantic=False,
        ),
        iterations=8,
        warmup=1,
    )

    latest = smart_results[-1]
    lowered = [result.word.lower() for result in latest]
    assert len(lowered) == len(set(lowered))
    assert "audittrail" in lowered
    assert any(word.startswith("audit") for word in lowered)

    _assert_fast_enough("dedup-smart", smart_case.stats.p95_ms, 250.0)


@pytest.mark.performance
@pytest.mark.search
@pytest.mark.asyncio
@pytest.mark.parametrize("size_name", ["tiny", "small"])
async def test_smart_cascade_with_semantic(size_name: str) -> None:
    """Test the full cascade with semantic=True wired up."""
    search = await build_search_fixture(f"audit-semantic-cascade-{size_name}", CORPUS_SIZES[size_name])
    _, _, semantic_search = await build_semantic_fixture(
        f"audit-semantic-cascade-sem-{size_name}", CORPUS_SIZES[size_name], dimension=32
    )
    from floridify.search.semantic.builder import SemanticEmbeddingBuilder

    builder = SemanticEmbeddingBuilder(semantic_search._encoder)
    (
        semantic_search.sentence_embeddings,
        semantic_search.sentence_index,
        semantic_search._word_embeddings,
    ) = builder._build_embeddings(semantic_search.corpus, semantic_search.index)

    # Wire semantic into the search instance
    search.semantic_search = semantic_search
    search._semantic_ready = True

    case, results = await benchmark_async(
        f"smart-semantic-{size_name}",
        "search",
        lambda: search._smart_search_cascade(
            "audittrail", max_results=8, min_score=0.0, semantic=True
        ),
        iterations=6,
        warmup=1,
        metadata={"corpus_size": size_name},
    )

    assert results[-1], "Semantic cascade should return results"
    _assert_fast_enough(f"{size_name}:smart-semantic", case.stats.p95_ms, 500.0)


@pytest.mark.performance
@pytest.mark.search
@pytest.mark.asyncio
async def test_bloom_filter_accuracy() -> None:
    """Test bloom filter: zero false negatives, low false positive rate."""
    search = await build_search_fixture("audit-bloom", CORPUS_SIZES["small"])
    bloom = search.trie_search._bloom_filter
    assert bloom is not None, "Bloom filter should be built"

    # All vocabulary words must be found (zero false negatives)
    vocab = search.corpus.lemmatized_vocabulary
    for word in vocab[:200]:
        assert word in bloom, f"False negative: {word} not found in bloom filter"

    # Check false positive rate with words not in vocabulary
    fp_count = 0
    test_count = 500
    for i in range(test_count):
        fake_word = f"xyznonexistent{i:05d}zzz"
        if fake_word in bloom:
            fp_count += 1

    fp_rate = fp_count / test_count
    stats = bloom.get_stats()
    assert fp_rate < 0.05, f"False positive rate {fp_rate:.2%} exceeds 5%"
    assert stats["fill_rate"] < 0.8, f"Bloom filter overfilled: {stats['fill_rate']:.2%}"

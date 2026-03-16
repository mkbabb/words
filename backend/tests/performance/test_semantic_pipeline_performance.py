"""Reproducible microbenchmarks for semantic build and inference."""

from __future__ import annotations

from typing import Any

import pytest

from floridify.audit import (
    CORPUS_SIZES,
    benchmark_async,
    benchmark_sync,
    build_semantic_fixture,
)
from floridify.search.semantic.builder import SemanticEmbeddingBuilder
from floridify.search.semantic.persistence import (
    load_embeddings_from_binary_data,
    load_faiss_index_from_binary_data,
    save_embeddings_and_index,
)


def _disable_flushes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "floridify.search.semantic.query_cache.SemanticQueryCache._schedule_query_cache_flush",
        lambda self: None,
    )
    monkeypatch.setattr(
        "floridify.search.semantic.query_cache.SemanticQueryCache._schedule_result_cache_flush",
        lambda self: None,
    )


def _build_embeddings_sync(semantic_search: Any) -> None:
    """Build embeddings synchronously via SemanticEmbeddingBuilder."""
    builder = SemanticEmbeddingBuilder(semantic_search._encoder)
    (
        semantic_search.sentence_embeddings,
        semantic_search.sentence_index,
        semantic_search._word_embeddings,
    ) = builder._build_embeddings(semantic_search.corpus, semantic_search.index)


@pytest.mark.performance
@pytest.mark.semantic
@pytest.mark.asyncio
@pytest.mark.parametrize("size_name", ["tiny", "small", "medium", "large"])
async def test_semantic_build_and_cached_inference(
    size_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_flushes(monkeypatch)
    _, index, semantic_search = await build_semantic_fixture(
        f"audit-semantic-{size_name}",
        CORPUS_SIZES[size_name],
        dimension=32,
    )

    build_iters = 1 if size_name == "large" else 3

    build_case, _ = benchmark_sync(
        "embedding-build",
        "semantic",
        lambda: _build_embeddings_sync(semantic_search),
        iterations=build_iters,
        warmup=0,
        metadata={"corpus_size": size_name},
    )

    assert semantic_search.sentence_embeddings is not None
    assert semantic_search.sentence_index is not None
    assert index.num_embeddings == len(semantic_search.corpus.lemmatized_vocabulary)

    cold_case, cold_results = await benchmark_async(
        "semantic-cold-query",
        "semantic",
        lambda: semantic_search.search("audittrail", max_results=6, min_score=0.0),
        iterations=1,
        warmup=0,
        metadata={"corpus_size": size_name},
    )
    warm_case, warm_results = await benchmark_async(
        "semantic-warm-query",
        "semantic",
        lambda: semantic_search.search("audittrail", max_results=6, min_score=0.0),
        iterations=8,
        warmup=0,
        metadata={"corpus_size": size_name},
    )

    assert cold_results[-1]
    assert warm_results[-1]
    assert semantic_search._query_cache_manager.result_cache
    assert semantic_search._query_cache_manager.result_cache_order
    assert warm_case.stats.p95_ms <= cold_case.stats.max_ms + 1.0


@pytest.mark.performance
@pytest.mark.semantic
@pytest.mark.asyncio
async def test_semantic_persistence_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_flushes(monkeypatch)
    _, index, semantic_search = await build_semantic_fixture(
        "audit-semantic-persist",
        CORPUS_SIZES["small"],
        dimension=32,
    )
    _build_embeddings_sync(semantic_search)

    async def fake_save(
        self: Any,
        config: Any | None = None,
        corpus_uuid: str | None = None,
        binary_data: dict[str, bytes] | None = None,
    ) -> None:
        self.binary_data = binary_data
        self._audit_saved = {"config": config, "corpus_uuid": corpus_uuid}

    monkeypatch.setattr(type(index), "save", fake_save)

    save_case, _ = await benchmark_async(
        "semantic-persist",
        "semantic",
        lambda: save_embeddings_and_index(
            index=index,
            sentence_embeddings=semantic_search.sentence_embeddings,
            sentence_index=semantic_search.sentence_index,
            build_time=0.01,
            corpus_uuid=semantic_search.corpus.corpus_uuid,
        ),
        iterations=3,
        warmup=0,
    )

    binary_data = index.binary_data
    assert binary_data is not None

    load_embeddings_case, loaded_embeddings = benchmark_sync(
        "semantic-load-embeddings",
        "semantic",
        lambda: load_embeddings_from_binary_data(binary_data, index.corpus_name),
        iterations=6,
        warmup=1,
    )
    load_index_case, loaded_indices = benchmark_sync(
        "semantic-load-faiss",
        "semantic",
        lambda: load_faiss_index_from_binary_data(binary_data, index.corpus_name),
        iterations=4,
        warmup=1,
    )

    assert loaded_embeddings[-1].shape == semantic_search.sentence_embeddings.shape
    assert loaded_indices[-1].ntotal == semantic_search.sentence_index.ntotal
    assert save_case.stats.p95_ms < 200.0
    assert load_embeddings_case.stats.p95_ms < 150.0
    assert load_index_case.stats.p95_ms < 200.0


@pytest.mark.performance
@pytest.mark.semantic
def test_faiss_index_tier_selection() -> None:
    """Verify correct FAISS index type selected for different corpus sizes."""
    import faiss

    from floridify.audit import fake_encode_texts
    from floridify.search.semantic.index_builder import build_optimized_index

    tiers = [
        (500, "IndexFlatL2"),
        (5_000, "IndexFlatL2"),
        (15_000, "IndexIVFFlat"),
        (60_000, "IndexScalarQuantizer"),
        (150_000, "IndexHNSWFlat"),
    ]

    for size, expected_type in tiers:
        embeddings = fake_encode_texts([f"word{i}" for i in range(size)], dimension=32)
        index = build_optimized_index(32, size, embeddings)
        actual_type = type(index).__name__
        assert actual_type == expected_type, (
            f"Size {size}: expected {expected_type}, got {actual_type}"
        )
        assert index.ntotal == size


@pytest.mark.performance
@pytest.mark.semantic
@pytest.mark.asyncio
async def test_query_cache_effectiveness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated queries should hit cache; warm should be faster than cold."""
    _disable_flushes(monkeypatch)
    _, _, semantic_search = await build_semantic_fixture(
        "audit-cache-eff", CORPUS_SIZES["small"], dimension=32
    )
    _build_embeddings_sync(semantic_search)

    # Cold query
    cold_case, _ = await benchmark_async(
        "cache-cold",
        "semantic",
        lambda: semantic_search.search("audittrail", max_results=6, min_score=0.0),
        iterations=1,
        warmup=0,
    )

    # Warm queries (same word)
    warm_case, _ = await benchmark_async(
        "cache-warm",
        "semantic",
        lambda: semantic_search.search("audittrail", max_results=6, min_score=0.0),
        iterations=8,
        warmup=0,
    )

    # Cache should have exactly 1 entry for this query
    assert len(semantic_search._query_cache_manager.result_cache) >= 1
    # Warm should be faster than cold
    assert warm_case.stats.mean_ms <= cold_case.stats.max_ms + 1.0

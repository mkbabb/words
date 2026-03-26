"""Tests for explicit semantic search gating."""

from types import SimpleNamespace

import pytest

from floridify.search.constants import SearchMethod
from floridify.search.engine import Search
from floridify.search.result import SearchResult


class _FakeSemanticSearch:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    async def search(self, query: str, max_results: int, min_score: float) -> list[SearchResult]:
        return [result for result in self._results if result.score >= min_score][:max_results]


@pytest.mark.asyncio
async def test_explicit_semantic_search_filters_irrelevant_low_score_hits() -> None:
    engine = Search()
    engine._semantic_ready = True
    # Scores must account for three filtering layers in search_semantic:
    #   1. effective_min_score = max(min_score, 0.78) for single-word queries
    #   2. lexical sanity gate: low lexical similarity words need
    #      score >= effective_min_score + LEXICAL_GATE_SCORE_MARGIN (0.05)
    # "table" (score 0.77) should be filtered by the min score floor (0.78).
    # "acute" (score 0.85) should survive both the floor and the lexical gate (0.83).
    engine.semantic_search = _FakeSemanticSearch(
        [
            SearchResult(word="table", score=0.77, method=SearchMethod.SEMANTIC),
            SearchResult(word="acute", score=0.85, method=SearchMethod.SEMANTIC),
        ]
    )
    # Vocabulary must have >= 2000 entries to avoid the small-corpus floor
    # (which raises the min_score to 0.82, filtering out our 0.81 test hit).
    fake_vocab = [f"word_{i}" for i in range(2500)]
    engine.corpus = SimpleNamespace(
        vocabulary=fake_vocab,
        vocabulary_to_index={w: i for i, w in enumerate(fake_vocab)},
        normalized_to_original_indices={},
        original_vocabulary=fake_vocab,
        get_original_word_by_index=lambda idx: "",
    )

    results = await engine.search_semantic("undeniable", max_results=5, min_score=0.3)

    words = [result.word for result in results]
    assert "table" not in words
    assert "acute" in words
    assert all(result.score >= 0.83 for result in results)

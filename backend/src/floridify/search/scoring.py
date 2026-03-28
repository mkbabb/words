"""Search result scoring, sorting, and deduplication.

Extracted from engine.py for cohesion: these are pure functions operating
on SearchResult lists, independent of the Search class's index state.
"""

from __future__ import annotations

from .constants import SearchMethod
from .result import MatchDetail, SearchResult

# Method priority for deduplication (higher = preferred when same word appears)
METHOD_PRIORITY: dict[SearchMethod, int] = {
    SearchMethod.EXACT: 5,
    SearchMethod.PREFIX: 4,
    SearchMethod.SUBSTRING: 3,
    SearchMethod.SEMANTIC: 2,
    SearchMethod.FUZZY: 1,
}

# Small bonus added to score for sorting — tiebreaker only, never overrides score.
# A fuzzy match at 0.95 still beats a semantic match at 0.80.
METHOD_SORT_BONUS: dict[SearchMethod, float] = {
    SearchMethod.EXACT: 0.03,
    SearchMethod.PREFIX: 0.02,
    SearchMethod.SUBSTRING: 0.015,
    SearchMethod.SEMANTIC: 0.01,
    SearchMethod.FUZZY: 0.0,
}


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicates, preferring exact matches. Case-insensitive dedup keys."""
    word_to_result: dict[str, SearchResult] = {}

    for result in results:
        key = result.word.lower()
        if key not in word_to_result:
            word_to_result[key] = result
        else:
            existing = word_to_result[key]
            # Prefer higher priority methods, then higher scores
            result_priority = METHOD_PRIORITY.get(result.method, 0)
            existing_priority = METHOD_PRIORITY.get(existing.method, 0)

            if (result_priority > existing_priority) or (
                result_priority == existing_priority and result.score > existing.score
            ):
                word_to_result[key] = result

    return list(word_to_result.values())


def deduplicate_results_multi(results: list[SearchResult]) -> list[SearchResult]:
    """Deduplicate results, collecting all (method, score) pairs per word.

    Keeps the highest-priority method as primary but stores all matches.
    """
    word_to_result: dict[str, SearchResult] = {}
    word_to_matches: dict[str, dict[SearchMethod, float]] = {}

    for result in results:
        key = result.word.lower()

        # Collect match detail (keep best score per method)
        if key not in word_to_matches:
            word_to_matches[key] = {}
        method_scores = word_to_matches[key]
        if result.method not in method_scores or result.score > method_scores[result.method]:
            method_scores[result.method] = result.score

        # Track best primary result (same logic as deduplicate_results)
        if key not in word_to_result:
            word_to_result[key] = result
        else:
            existing = word_to_result[key]
            result_priority = METHOD_PRIORITY.get(result.method, 0)
            existing_priority = METHOD_PRIORITY.get(existing.method, 0)
            if (result_priority > existing_priority) or (
                result_priority == existing_priority and result.score > existing.score
            ):
                word_to_result[key] = result

    # Attach collected matches to each result
    for key, result in word_to_result.items():
        method_scores = word_to_matches[key]
        result.matches = sorted(
            [MatchDetail(method=m, score=s) for m, s in method_scores.items()],
            key=lambda md: (METHOD_PRIORITY.get(md.method, 0), md.score),
            reverse=True,
        )

    return list(word_to_result.values())


def sort_key(result: SearchResult) -> float:
    """Sort key combining score with method-based tiebreaker bonus."""
    return result.score + METHOD_SORT_BONUS.get(result.method, 0.0)

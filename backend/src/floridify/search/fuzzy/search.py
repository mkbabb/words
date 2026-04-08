"""Fuzzy search powered by the ``ffuzzy`` Rust crate.

This module is a thin Python wrapper around ``ffuzzy.Index`` — the hybrid
Rust engine that fuses SymSpell (precomputed deletes), Levenshtein
automaton (stub), bounded Damerau-Levenshtein BK-tree, 3.5-gram
positional-mask trigram index, and silent-consonant-aware Double Metaphone.

Candidate generation, signal boosting, length correction, and verification
all live in ``ffuzzy-core/src/router``. This module just converts between
``ffuzzy.SearchHit`` and ``SearchResult``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import ffuzzy

from ...corpus.core import Corpus
from ...utils.logging import get_logger
from ..constants import DEFAULT_MIN_SCORE, SearchMethod
from ..result import SearchResult

if TYPE_CHECKING:
    from .suffix_array import SuffixArray

logger = get_logger(__name__)


class FuzzySearch:
    """Thin wrapper around a loaded ``ffuzzy.Index``.

    The Rust crate handles candidate generation, signal boosting, length
    correction, and verification. This class just converts between
    ``ffuzzy.SearchHit`` and ``SearchResult``.
    """

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        self.min_score = min_score
        # The loaded ffuzzy index. Set via ``load()`` or ``for_corpus()``.
        self._ffuzzy: Any = None

    def load(self, ffuzzy_index: Any) -> None:
        """Attach a loaded ``ffuzzy.Index`` for querying."""
        self._ffuzzy = ffuzzy_index

    @classmethod
    def for_corpus(cls, corpus: Corpus, min_score: float = DEFAULT_MIN_SCORE) -> FuzzySearch:
        """Construct and immediately load a FuzzySearch from a corpus.

        Convenience for tests and one-off in-memory engines that don't go
        through the versioned `FuzzyIndex` cache. Builds the full ffuzzy
        hybrid index in Rust.
        """
        instance = cls(min_score=min_score)
        instance.load(ffuzzy.Index.build(corpus.vocabulary))
        return instance

    def search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        min_score: float | None = None,
        suffix_array: SuffixArray | None = None,  # unused; suffix array is for substring search
    ) -> list[SearchResult]:
        """Run a hybrid fuzzy search.

        Args:
            query: Normalized query string.
            corpus: Corpus for language tagging on results.
            max_results: Maximum results to return.
            min_score: Optional override for the minimum score threshold.
            suffix_array: Unused here — kept for API compatibility with
                the substring-search cascade path.

        Returns:
            List of ``SearchResult`` sorted by descending score.
        """
        if self._ffuzzy is None:
            return []
        if not query:
            return []

        threshold = min_score if min_score is not None else self.min_score

        try:
            raw_hits = self._ffuzzy.search(
                query,
                max_results=max_results,
                min_score=float(threshold),
            )
        except Exception as e:  # pragma: no cover — Rust errors are already specific
            logger.warning(f"ffuzzy search failed for {query!r}: {e}")
            return []

        results: list[SearchResult] = []
        for hit in raw_hits:
            results.append(
                SearchResult(
                    word=hit.word,
                    score=hit.score,
                    method=SearchMethod.FUZZY,
                    lemmatized_word=None,
                    language=corpus.language,
                    metadata={"engine": hit.engine} if hit.engine != "exact" else None,
                ),
            )
        return results


__all__ = ["FuzzySearch"]

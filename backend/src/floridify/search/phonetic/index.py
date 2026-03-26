"""Phonetic inverted index for multilingual sound-alike matching.

Uses PhoneticEncoder (ICU normalization + jellyfish Metaphone) to build
an inverted index mapping phonetic codes to vocabulary word indices.

Architecture:
1. Normalize: ICU CLDR transliteration (script + diacritics + cross-linguistic rules)
2. Encode: jellyfish Metaphone (Rust-backed, fast)
3. Index: composite key (per-word codes joined with |) + per-word inverted index
4. Search: exact composite → fuzzy composite → per-word intersection
"""

from __future__ import annotations

from collections import Counter

import jellyfish

from ...utils.logging import get_logger
from ..config import PHONETIC_FUZZY_COMPOSITE_LIMIT
from .encoder import PhoneticEncoder, get_phonetic_encoder

logger = get_logger(__name__)


class PhoneticIndex:
    """Multilingual phonetic inverted index.

    All entries are normalized through ICU cross-linguistic phonetic rules
    before Metaphone encoding, making the index language-agnostic.
    """

    def __init__(
        self,
        vocabulary: list[str],
        encoder: PhoneticEncoder | None = None,
    ) -> None:
        """Build phonetic index from vocabulary.

        Args:
            vocabulary: Sorted, normalized vocabulary list.
            encoder: PhoneticEncoder instance (uses singleton if not provided).
        """
        self._encoder = encoder or get_phonetic_encoder()

        # Composite key → vocabulary indices
        self._composite_index: dict[str, list[int]] = {}

        # Per-word code → vocabulary indices (for partial matching)
        self._word_index: dict[str, list[int]] = {}

        for idx, entry in enumerate(vocabulary):
            # Composite key for the full entry
            ckey = self._encoder.encode_composite(entry)
            if ckey:
                self._composite_index.setdefault(ckey, []).append(idx)

            # Per-word keys for partial matching
            normalized = self._encoder.normalize(entry)
            for word in normalized.split():
                if len(word) < 2:
                    continue
                try:
                    code = jellyfish.metaphone(word)
                    if code:
                        self._word_index.setdefault(code, []).append(idx)
                except Exception:
                    continue

        logger.info(
            f"Built phonetic index: {len(self._composite_index)} composite codes, "
            f"{len(self._word_index)} per-word codes "
            f"from {len(vocabulary)} words"
        )

    def search(self, query: str, max_results: int = 50) -> list[int]:
        """Search using multilingual phonetic matching.

        Strategy cascade:
        1. Exact composite match (strongest signal)
        2. Fuzzy composite match (Levenshtein on Metaphone codes, <10K codes)
        3. Per-word intersection (majority of query words match phonetically)
        """
        seen: set[int] = set()
        results: list[int] = []

        # Strategy 1: Exact composite match
        qkey = self._encoder.encode_composite(query)
        if qkey and qkey in self._composite_index:
            for idx in self._composite_index[qkey]:
                if idx not in seen:
                    seen.add(idx)
                    results.append(idx)

        # Strategy 2: Fuzzy composite match — Levenshtein on Metaphone codes
        if qkey and len(results) < max_results and len(self._composite_index) < PHONETIC_FUZZY_COMPOSITE_LIMIT:
            from rapidfuzz.distance import Levenshtein

            max_code_dist = max(1, len(qkey) // 4)
            for stored_code, indices in self._composite_index.items():
                if stored_code == qkey:
                    continue
                dist = Levenshtein.distance(qkey, stored_code)
                if dist <= max_code_dist:
                    for idx in indices:
                        if idx not in seen:
                            seen.add(idx)
                            results.append(idx)
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break

        # Strategy 3: Per-word intersection
        if len(results) < max_results:
            normalized_query = self._encoder.normalize(query)
            query_words = [w for w in normalized_query.split() if len(w) >= 2]
            if query_words:
                per_word_candidates: list[set[int]] = []
                for word in query_words:
                    try:
                        code = jellyfish.metaphone(word)
                        if code and code in self._word_index:
                            per_word_candidates.append(set(self._word_index[code]))
                    except Exception:
                        continue

                if per_word_candidates:
                    counts: Counter[int] = Counter()
                    for candidate_set in per_word_candidates:
                        counts.update(candidate_set)

                    threshold = max(1, len(per_word_candidates) // 2)
                    for idx, count in counts.most_common():
                        if count < threshold:
                            break
                        if idx not in seen:
                            seen.add(idx)
                            results.append(idx)
                        if len(results) >= max_results:
                            break

        return results[:max_results]


__all__ = ["PhoneticIndex"]

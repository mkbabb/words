"""Local word frequency assessment using wordfreq + WordNet sense counts.

Two levels of frequency:
  Word-level: wordfreq Zipf score (how common is this word form overall)
  Sense-level: WordNet SemCor corpus counts (how common is THIS meaning)

The combination gives per-definition frequency: a common word like "bank"
has band=4 overall, but the "financial" sense (SemCor count=20) is more
common than the "ridge/pile" sense (count=2), so their CEFR differs.
"""

from __future__ import annotations

from functools import lru_cache

from ...utils.logging import get_logger

logger = get_logger(__name__)

try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None  # type: ignore[assignment]

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None  # type: ignore[assignment]


# Zipf thresholds for each frequency band
_BAND_THRESHOLDS: list[tuple[float, int]] = [
    (6.0, 5),  # Core vocabulary
    (5.0, 4),  # Common
    (4.0, 3),  # Moderate
    (3.0, 2),  # Uncommon
]


def assess_frequency_local(
    word: str,
    lang: str = "en",
) -> int | None:
    """Assess word-level frequency band using corpus-derived Zipf scores.

    Returns:
        Frequency band 1-5, or None if wordfreq is unavailable.
    """
    if zipf_frequency is None:
        return None

    zipf = zipf_frequency(word, lang)

    # Zipf 0.0 means "not in the corpus" — return None (unknown), not band 1
    if zipf == 0.0:
        return None

    for threshold, band in _BAND_THRESHOLDS:
        if zipf >= threshold:
            return band

    return 1  # Rare


def assess_frequency_score_local(
    word: str,
    lang: str = "en",
) -> float | None:
    """Assess continuous frequency score (0.0-1.0) for temperature visualization.

    Returns:
        Float between 0.0 (extremely rare) and 1.0 (most common), or None.
    """
    if zipf_frequency is None:
        return None

    zipf = zipf_frequency(word, lang)
    if zipf == 0.0:
        return None
    return min(max(zipf / 8.0, 0.0), 1.0)


# ── Sense-level frequency ─────────────────────────────────────────────


@lru_cache(maxsize=1024)
def _word_sense_counts(word: str, pos: str | None = None) -> dict[str, int]:
    """Get SemCor tagged frequency for each sense of a word.

    Returns:
        Dict mapping synset name → count. Higher = more commonly used sense.
    """
    if wn is None:
        return {}

    pos_map = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
    wn_pos = pos_map.get(pos) if pos else None
    synsets = wn.synsets(word, pos=wn_pos)

    counts: dict[str, int] = {}
    for s in synsets:
        # Sum counts across all lemmas for this synset
        total = sum(lem.count() for lem in s.lemmas())
        counts[s.name()] = total

    return counts


async def assess_sense_frequency(
    word: str,
    pos: str,
    definition_text: str,
) -> float | None:
    """Assess how common THIS specific sense of the word is.

    Uses WordNet SemCor corpus counts. Returns a 0.0-1.0 score where:
      1.0 = dominant sense (most frequently tagged in SemCor)
      0.0 = never tagged / very rare sense

    This allows per-definition CEFR: the "financial institution" sense
    of "bank" (count=20) scores higher than the "ridge/pile" sense (count=2).
    """
    counts = _word_sense_counts(word, pos)
    if not counts:
        return None

    total_count = sum(counts.values())
    if total_count == 0:
        return None

    from ..embedding_utils import best_synset_by_embedding

    synset = await best_synset_by_embedding(word, pos, definition_text)
    if synset is None:
        return None

    sense_count = counts.get(synset.name(), 0)
    # Normalize by total count across all senses
    return sense_count / total_count if total_count > 0 else 0.0


def adjust_band_for_sense(
    word_band: int,
    sense_frequency: float | None,
) -> int:
    """Adjust word-level frequency band based on sense-level prominence.

    A rare sense of a common word should get a lower band (harder/less common).
    A dominant sense of a common word keeps the high band.

    Args:
        word_band: Word-level frequency band (1-5).
        sense_frequency: Sense prominence (0.0-1.0 from assess_sense_frequency).

    Returns:
        Adjusted frequency band (1-5).
    """
    if sense_frequency is None:
        return word_band

    # Rare senses (< 10% of total usage) drop 1-2 bands
    # Common senses (> 30% of total usage) stay at word-level band
    if sense_frequency < 0.05:
        return max(1, word_band - 2)
    elif sense_frequency < 0.15:
        return max(1, word_band - 1)
    else:
        return word_band

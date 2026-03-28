"""Hybrid synthesis helpers: local sources first, AI for the delta.

For synonyms, antonyms, and etymology, we first pull data from Wiktionary
(already in the definition) and WordNet, then only call AI to fill gaps.

Uses the shared embedding-based synset matcher for sense-accurate
synonym/antonym extraction (no cross-sense bleed for polysemous words).
"""

from __future__ import annotations

from ...models.dictionary import Definition
from ...utils.logging import get_logger
from ..embedding_utils import best_synset_by_embedding

logger = get_logger(__name__)

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None  # type: ignore[assignment]


async def get_wordnet_synonyms(
    word: str,
    pos: str | None = None,
    definition_text: str = "",
) -> list[str]:
    """Get synonyms from the best-matching WordNet synset.

    When definition_text is provided, matches to the specific sense first,
    so "bank (financial institution)" gets different synonyms than
    "bank (sloping land)".
    """
    if wn is None:
        return []

    # Match to the specific sense via embeddings
    if definition_text and pos:
        synset = await best_synset_by_embedding(word, pos, definition_text)
        synsets = [synset] if synset else []
    else:
        pos_map = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
        wn_pos = pos_map.get(pos) if pos else None
        synsets = wn.synsets(word, pos=wn_pos)

    synonyms: list[str] = []
    seen: set[str] = set()

    for synset in synsets:
        for lemma in synset.lemmas():
            name = lemma.name().replace("_", " ")
            if name.lower() != word.lower() and name.lower() not in seen:
                seen.add(name.lower())
                synonyms.append(name)

    return synonyms[:20]


async def get_wordnet_antonyms(
    word: str,
    pos: str | None = None,
    definition_text: str = "",
) -> list[str]:
    """Get antonyms from the best-matching WordNet synset.

    When definition_text is provided, matches to the specific sense first.
    """
    if wn is None:
        return []

    if definition_text and pos:
        synset = await best_synset_by_embedding(word, pos, definition_text)
        synsets = [synset] if synset else []
    else:
        pos_map = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
        wn_pos = pos_map.get(pos) if pos else None
        synsets = wn.synsets(word, pos=wn_pos)

    antonyms: list[str] = []
    seen: set[str] = set()

    for synset in synsets:
        for lemma in synset.lemmas():
            for antonym in lemma.antonyms():
                name = antonym.name().replace("_", " ")
                if name.lower() not in seen:
                    seen.add(name.lower())
                    antonyms.append(name)

    return antonyms[:15]


def merge_with_existing(
    existing: list[str],
    new_items: list[str],
    max_total: int = 20,
) -> list[str]:
    """Merge new items into existing list, preserving order and deduplicating."""
    seen: set[str] = {s.lower() for s in existing}
    merged = list(existing)

    for item in new_items:
        if item.lower() not in seen and len(merged) < max_total:
            seen.add(item.lower())
            merged.append(item)

    return merged


async def compute_synonym_delta(
    definition: Definition,
    word: str,
    target_count: int = 10,
) -> tuple[list[str], int]:
    """Compute how many synonyms still need AI generation.

    Merges Wiktionary synonyms (already on definition) with WordNet,
    returns the merged list and the remaining count for AI.
    """
    existing = list(definition.synonyms)
    wordnet_syns = await get_wordnet_synonyms(word, definition.part_of_speech, definition.text)
    merged = merge_with_existing(existing, wordnet_syns, max_total=target_count)
    ai_needed = max(0, target_count - len(merged))

    if wordnet_syns:
        logger.debug(
            f"Synonyms for '{word}': {len(existing)} from Wiktionary + "
            f"{len(wordnet_syns)} from WordNet → {len(merged)} total, "
            f"{ai_needed} needed from AI"
        )

    return merged, ai_needed


async def compute_antonym_delta(
    definition: Definition,
    word: str,
    target_count: int = 5,
) -> tuple[list[str], int]:
    """Compute how many antonyms still need AI generation."""
    existing = list(definition.antonyms)
    wordnet_ants = await get_wordnet_antonyms(word, definition.part_of_speech, definition.text)
    merged = merge_with_existing(existing, wordnet_ants, max_total=target_count)
    ai_needed = max(0, target_count - len(merged))

    if wordnet_ants:
        logger.debug(
            f"Antonyms for '{word}': {len(existing)} from Wiktionary + "
            f"{len(wordnet_ants)} from WordNet → {len(merged)} total, "
            f"{ai_needed} needed from AI"
        )

    return merged, ai_needed

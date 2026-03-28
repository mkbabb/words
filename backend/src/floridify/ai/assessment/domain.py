"""Local domain classification via WordNet hypernym chains + lexicographer files.

Uses the shared embedding-based synset matcher to find the correct WordNet
sense, then walks the hypernym chain and checks lexicographer file names
to determine the domain. No hardcoded pattern lists.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ...utils.logging import get_logger
from ..embedding_utils import best_synset_by_embedding

logger = get_logger(__name__)

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None  # type: ignore[assignment]

# ── WordNet lexicographer file → domain mapping ───────────────────────

_LEXNAME_TO_DOMAIN: dict[str, str | None] = {
    "noun.animal": "biology",
    "noun.artifact": "technology",
    "noun.attribute": None,
    "noun.body": "anatomy",
    "noun.cognition": "psychology",
    "noun.communication": "communication",
    "noun.event": None,
    "noun.feeling": "psychology",
    "noun.food": "cooking",
    "noun.group": None,
    "noun.location": "geography",
    "noun.motive": None,
    "noun.object": None,
    "noun.person": None,
    "noun.phenomenon": "science",
    "noun.plant": "botany",
    "noun.possession": "finance",
    "noun.process": None,
    "noun.quantity": "mathematics",
    "noun.relation": None,
    "noun.shape": None,
    "noun.state": None,
    "noun.substance": "chemistry",
    "noun.time": None,
    "verb.body": "anatomy",
    "verb.change": None,
    "verb.cognition": "psychology",
    "verb.communication": "communication",
    "verb.competition": "sports",
    "verb.consumption": "cooking",
    "verb.contact": None,
    "verb.creation": None,
    "verb.emotion": "psychology",
    "verb.motion": None,
    "verb.perception": None,
    "verb.possession": "finance",
    "verb.social": None,
    "verb.stative": None,
    "verb.weather": "meteorology",
    "adj.all": None,
    "adj.pert": None,
    "adv.all": None,
}

# Hypernym synsets that indicate specific domains (for when lexname is too coarse)
_HYPERNYM_DOMAIN_MAP: dict[str, str] = {
    "financial_institution.n.01": "finance",
    "depository_financial_institution.n.01": "finance",
    "medium_of_exchange.n.01": "finance",
    "geological_formation.n.01": "geography",
    "body_of_water.n.01": "geography",
    "airplane_maneuver.n.01": "aviation",
    "flight_maneuver.n.01": "aviation",
    "aircraft.n.01": "aviation",
    "game_of_chance.n.01": "gambling",
    "musical_instrument.n.01": "music",
    "musical_composition.n.01": "music",
    "legal_document.n.01": "law",
    "drug.n.01": "medicine",
    "medicine.n.02": "medicine",
    "computer.n.01": "computing",
    "program.n.07": "computing",
    "vessel.n.02": "nautical",
    "ship.n.01": "nautical",
    "weapon.n.01": "military",
    "celestial_body.n.01": "astronomy",
}


def get_all_known_domains() -> set[str]:
    """Return the set of all domain labels used in this module.

    Used by postprocess.py to derive the domain label set programmatically
    (avoids hardcoded duplicate lists).
    """
    domains = {v for v in _LEXNAME_TO_DOMAIN.values() if v is not None}
    domains |= set(_HYPERNYM_DOMAIN_MAP.values())
    return domains


@lru_cache(maxsize=2048)
def _synset_domain(synset_name: str) -> str | None:
    """Get domain for a synset via lexname + hypernym chain. Cached."""
    if wn is None:
        return None

    synset = wn.synset(synset_name)

    # First: check lexicographer file name
    lexname = synset.lexname()
    domain = _LEXNAME_TO_DOMAIN.get(lexname)
    if domain is not None:
        return domain

    # Second: walk hypernym chain (max 6 levels)
    visited: set[str] = set()
    queue = [synset]
    for _ in range(6):
        next_queue: list[Any] = []
        for s in queue:
            name = s.name()
            if name in visited:
                continue
            visited.add(name)
            if name in _HYPERNYM_DOMAIN_MAP:
                return _HYPERNYM_DOMAIN_MAP[name]
            next_queue.extend(s.hypernyms())
        queue = next_queue
        if not queue:
            break

    return None


async def classify_domain_local(
    definition_text: str,
    word: str = "",
    part_of_speech: str = "",
) -> str | None:
    """Classify the subject domain of a definition using WordNet taxonomy.

    Uses embedding-based synset matching for accurate sense disambiguation,
    then lexicographer files + hypernym chain for domain inference.

    Args:
        definition_text: The definition text to classify.
        word: The word being defined (required for WordNet lookup).
        part_of_speech: POS of the definition.

    Returns:
        Domain label string, or None if no clear domain detected.
    """
    if not word or wn is None:
        return None

    synset = await best_synset_by_embedding(word, part_of_speech, definition_text)
    if synset is None:
        return None

    return _synset_domain(synset.name())

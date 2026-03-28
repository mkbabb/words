"""WordNet provider using NLTK's WordNet corpus.

Provides definitions, synonyms, antonyms, hypernyms, hyponyms, and examples
from Princeton WordNet (BSD-like license). Zero network calls — all local.
"""

from __future__ import annotations

from typing import Any

from ....core.state_tracker import StateTracker
from ....models.dictionary import DictionaryProvider, Word
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector
from ..models import DictionaryProviderEntry

logger = get_logger(__name__)

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None  # type: ignore[assignment]

# WordNet POS tag → standard POS mapping
_WN_POS_MAP: dict[str, str] = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",  # satellite adjective
    "r": "adverb",
}


class WordNetConnector(DictionaryConnector):
    """WordNet provider via NLTK — local, no network, BSD-like license."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.LOCAL.value)
        super().__init__(provider=DictionaryProvider.WORDNET, config=config)

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
        **kwargs: Any,
    ) -> DictionaryProviderEntry | None:
        if wn is None:
            logger.warning("NLTK wordnet not available")
            return None

        synsets = wn.synsets(word)
        if not synsets:
            return None

        definitions: list[dict[str, Any]] = []
        all_hypernyms: list[str] = []
        all_hyponyms: list[str] = []

        for idx, synset in enumerate(synsets):
            pos = _WN_POS_MAP.get(synset.pos(), "noun")
            def_text = synset.definition()
            if not def_text or len(def_text) < 5:
                continue

            # Extract synonyms (lemma names, excluding the word itself)
            synonyms = [
                lemma.name().replace("_", " ")
                for lemma in synset.lemmas()
                if lemma.name().lower().replace("_", " ") != word.lower()
            ]

            # Extract antonyms from all lemmas
            antonyms = list(
                {
                    ant.name().replace("_", " ")
                    for lemma in synset.lemmas()
                    for ant in lemma.antonyms()
                }
            )

            # Extract examples
            examples = synset.examples()

            # Collect hypernyms/hyponyms (word-level, stored in provider_metadata)
            for hyper in synset.hypernyms():
                for lemma in hyper.lemmas():
                    name = lemma.name().replace("_", " ")
                    if name.lower() != word.lower():
                        all_hypernyms.append(name)

            for hypo in synset.hyponyms():
                for lemma in hypo.lemmas():
                    name = lemma.name().replace("_", " ")
                    if name.lower() != word.lower():
                        all_hyponyms.append(name)

            definitions.append(
                {
                    "part_of_speech": pos,
                    "text": def_text,
                    "sense_number": str(idx + 1),
                    "synonyms": synonyms[:15],
                    "antonyms": antonyms[:10],
                    "examples": examples[:3],
                }
            )

        if not definitions:
            return None

        # Deduplicate hypernyms/hyponyms
        seen_hyper: set[str] = set()
        unique_hypernyms = []
        for h in all_hypernyms:
            if h.lower() not in seen_hyper:
                seen_hyper.add(h.lower())
                unique_hypernyms.append(h)

        seen_hypo: set[str] = set()
        unique_hyponyms = []
        for h in all_hyponyms:
            if h.lower() not in seen_hypo:
                seen_hypo.add(h.lower())
                unique_hyponyms.append(h)

        return DictionaryProviderEntry(
            word=word,
            provider=DictionaryProvider.WORDNET.value,
            definitions=definitions,
            provider_metadata={
                "synset_count": len(synsets),
                "hypernyms": unique_hypernyms[:20],
                "hyponyms": unique_hyponyms[:20],
            },
        )

    async def _fetch_provider_entry(
        self,
        word: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        return await self._fetch_from_provider(word.text, state_tracker)

    async def close(self) -> None:
        pass  # No resources to close

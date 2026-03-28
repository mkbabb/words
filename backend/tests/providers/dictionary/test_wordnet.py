"""WordNet provider tests — local, no network, no DB required."""

from __future__ import annotations

import pytest

from floridify.providers.dictionary.local.wordnet_provider import WordNetConnector


@pytest.fixture
def connector() -> WordNetConnector:
    return WordNetConnector()


class TestWordNetConnectorBasic:
    @pytest.mark.asyncio
    async def test_fetches_common_word(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("bank")
        assert entry is not None
        assert entry.word == "bank"
        assert len(entry.definitions) > 0

    @pytest.mark.asyncio
    async def test_returns_none_for_nonsense(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("xyzzyplugh")
        assert entry is None

    @pytest.mark.asyncio
    async def test_definitions_have_pos(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("run")
        assert entry is not None
        pos_values = {d["part_of_speech"] for d in entry.definitions}
        assert "noun" in pos_values or "verb" in pos_values


class TestWordNetConnectorSynonyms:
    @pytest.mark.asyncio
    async def test_extracts_synonyms(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("happy")
        assert entry is not None
        # At least one definition should have synonyms
        all_syns = [s for d in entry.definitions for s in d.get("synonyms", [])]
        assert len(all_syns) > 0

    @pytest.mark.asyncio
    async def test_excludes_self_from_synonyms(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("happy")
        assert entry is not None
        for defn in entry.definitions:
            syns = defn.get("synonyms", [])
            assert "happy" not in [s.lower() for s in syns]


class TestWordNetConnectorAntonyms:
    @pytest.mark.asyncio
    async def test_extracts_antonyms_for_adjectives(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("good")
        assert entry is not None
        all_ants = [a for d in entry.definitions for a in d.get("antonyms", [])]
        # "good" has antonym "bad" or "evil" in WordNet
        assert len(all_ants) > 0


class TestWordNetConnectorRelationships:
    @pytest.mark.asyncio
    async def test_includes_hypernyms_in_metadata(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("dog")
        assert entry is not None
        hypernyms = entry.provider_metadata.get("hypernyms", [])
        # "dog" hypernyms include "canine" or "domestic animal"
        assert len(hypernyms) > 0

    @pytest.mark.asyncio
    async def test_includes_hyponyms_in_metadata(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("dog")
        assert entry is not None
        hyponyms = entry.provider_metadata.get("hyponyms", [])
        assert len(hyponyms) > 0

    @pytest.mark.asyncio
    async def test_synset_count_in_metadata(self, connector: WordNetConnector) -> None:
        entry = await connector._fetch_from_provider("bank")
        assert entry is not None
        assert entry.provider_metadata["synset_count"] > 5  # bank has many senses

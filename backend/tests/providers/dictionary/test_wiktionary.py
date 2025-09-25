"""WiktionaryConnector parsing tests."""

from __future__ import annotations

import pytest
import wikitextparser as wtp

from floridify.models.dictionary import Word
from floridify.providers.dictionary.scraper.wiktionary import WikitextCleaner, WiktionaryConnector

SAMPLE_WIKITEXT = """
==English==
===Pronunciation===
* {{IPA|en|/tɛst/}}
===Noun===
# {{lb|en|informal}} A {{gloss|trial}} or examination.
"""


def test_cleaner_removes_markup() -> None:
    cleaner = WikitextCleaner()
    raw = "{{lb|en|formal}} {{gloss|trial}} '''test'''"
    cleaned = cleaner.clean_text(raw)
    assert "formal" in cleaned
    assert "test" in cleaned
    assert "{{" not in cleaned


@pytest.mark.asyncio
async def test_extract_definitions_parses_section(test_db) -> None:
    connector = WiktionaryConnector()
    try:
        word = Word(text="test")
        await word.save()
        assert word.id is not None

        parsed = wtp.parse(SAMPLE_WIKITEXT)
        english_section = next(section for section in parsed.sections if section.title == "English")

        definitions = await connector._extract_definitions(english_section, word.id)

        assert len(definitions) == 1
        definition = definitions[0]
        assert definition.part_of_speech == "noun"
        assert definition.text.startswith("(informal)")
    finally:
        await connector.close()


@pytest.mark.asyncio
async def test_fetch_from_provider_returns_entry(monkeypatch: pytest.MonkeyPatch, test_db) -> None:
    connector = WiktionaryConnector()

    async def fake_cached_get(url: str, params: dict[str, str]) -> str:  # noqa: ARG001
        import json

        mock_response = {
            "query": {
                "pages": [{"revisions": [{"slots": {"main": {"content": SAMPLE_WIKITEXT}}}]}]
            },
        }
        return json.dumps(mock_response)

    monkeypatch.setattr(connector, "_cached_get", fake_cached_get)
    monkeypatch.setattr(connector, "_extract_section_synonyms", lambda section: ["trial"])
    monkeypatch.setattr(
        connector,
        "_extract_etymology",
        lambda section: "Derived from Latin testum",
    )

    # Mock pronunciation extraction
    from floridify.models.dictionary import Pronunciation

    async def fake_extract_pronunciation(section, word_id):
        return Pronunciation(word_id=word_id, phonetic="/tɛst/", ipa="/tɛst/")

    monkeypatch.setattr(
        connector,
        "_extract_pronunciation",
        lambda section, word_id: Pronunciation(word_id=word_id, phonetic="/tɛst/", ipa="/tɛst/"),
    )

    try:
        entry = await connector._fetch_from_provider("test")
    finally:
        await connector.close()

    assert entry is not None
    assert entry.word == "test"
    assert entry.pronunciation == "/tɛst/"
    assert entry.etymology == "Derived from Latin testum"
    assert entry.definitions[0]["synonyms"] == ["trial"]

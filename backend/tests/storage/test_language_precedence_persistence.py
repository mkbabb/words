"""Regression tests for canonical language precedence persistence."""

from __future__ import annotations

import pytest

from floridify.api.services.loaders import DictionaryEntryLoader
from floridify.models.dictionary import DictionaryEntry, DictionaryProvider, Word
from floridify.storage.dictionary import save_entry_versioned
from floridify.storage import mongodb as mongodb_storage


@pytest.mark.asyncio
async def test_save_entry_versioned_updates_live_entry_languages(test_db) -> None:
    """Live synthesized entry must update its languages on re-save."""
    word = Word(text="en coulisse", languages=["en"])
    await word.save()
    assert word.id is not None

    initial_entry = DictionaryEntry(
        provider=DictionaryProvider.SYNTHESIS,
        word_id=word.id,
        languages=["en"],
        definition_ids=[],
    )
    await save_entry_versioned(initial_entry, word.text)

    updated_entry = DictionaryEntry(
        provider=DictionaryProvider.SYNTHESIS,
        word_id=word.id,
        languages=["fr", "en"],
        definition_ids=[],
    )
    await save_entry_versioned(updated_entry, word.text)

    live_entry = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )
    assert live_entry is not None
    assert list(live_entry.languages) == ["fr", "en"]


@pytest.mark.asyncio
async def test_lookup_loader_uses_word_language_precedence(test_db) -> None:
    """Lookup response languages must come from canonical Word.languages."""
    word = Word(text="en coulisse", languages=["fr", "en"])
    await word.save()
    assert word.id is not None

    entry = DictionaryEntry(
        provider=DictionaryProvider.SYNTHESIS,
        word_id=word.id,
        languages=["en"],  # stale/mismatched entry metadata
        definition_ids=[],
    )
    await entry.save()

    response = await DictionaryEntryLoader.load_as_lookup_response(entry)
    assert response["languages"] == ["fr", "en"]


@pytest.mark.asyncio
async def test_get_synthesized_entry_by_word_and_provider(test_db, monkeypatch) -> None:
    """Synthesized-entry lookup should be keyed by word + provider."""
    word = Word(text="en coulisse", languages=["fr", "en"])
    await word.save()
    assert word.id is not None

    entry = DictionaryEntry(
        provider=DictionaryProvider.SYNTHESIS,
        word_id=word.id,
        languages=["fr", "en"],
        definition_ids=[],
    )
    await entry.save()

    async def _noop_init() -> None:
        return None

    # Use fixture-managed Beanie initialization instead of global app storage init.
    monkeypatch.setattr(mongodb_storage, "_ensure_initialized", _noop_init)

    cached = await mongodb_storage.get_synthesized_entry(word.text)
    assert cached is not None
    assert list(cached.languages) == ["fr", "en"]

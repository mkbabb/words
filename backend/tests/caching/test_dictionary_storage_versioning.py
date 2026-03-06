"""Integration tests for dictionary storage versioning helpers."""

from __future__ import annotations

import pytest

from floridify.caching.delta import compute_diff_between
from floridify.caching.manager import get_version_manager
from floridify.caching.models import CacheNamespace, ResourceType
from floridify.models.base import Language
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Word,
)
from floridify.storage.dictionary import save_definition_versioned, save_entry_versioned


@pytest.mark.asyncio
async def test_definition_versioning_uses_stable_resource_id(test_db):
    """Definitions should keep one version chain from first save onward."""
    manager = get_version_manager()

    word = Word(text="stable_definition_test", languages=[Language.ENGLISH])
    await word.save()

    definition = Definition(
        word_id=word.id,
        part_of_speech="noun",
        text="First definition text",
        providers=[DictionaryProvider.SYNTHESIS],
        synonyms=["alpha"],
    )

    await save_definition_versioned(definition, word.text)
    assert definition.id is not None

    definition.text = "Second definition text"
    definition.synonyms = ["alpha", "beta"]
    await save_definition_versioned(definition, word.text)

    resource_id = f"def:{word.text}:{definition.id}"
    versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)
    assert len(versions) == 2

    # Regression guard: no split history under "...:new"
    orphan_versions = await manager.list_versions(f"def:{word.text}:new", ResourceType.DICTIONARY)
    assert orphan_versions == []

    v1 = await manager.get_by_version(resource_id, ResourceType.DICTIONARY, "1.0.0", use_cache=False)
    v2 = await manager.get_latest(resource_id, ResourceType.DICTIONARY, use_cache=False)
    assert v1 is not None
    assert v2 is not None

    diff = compute_diff_between(v1.content_inline or {}, v2.content_inline or {})
    assert diff
    assert "values_changed" in diff or "iterable_item_added" in diff


@pytest.mark.asyncio
async def test_synthesized_entry_versioning_and_diff(test_db):
    """Synthesized DictionaryEntry snapshots should version and diff correctly."""
    manager = get_version_manager()

    word = Word(text="synth_entry_version_test", languages=[Language.ENGLISH])
    await word.save()

    d1 = Definition(
        word_id=word.id,
        part_of_speech="noun",
        text="Primary meaning",
        providers=[DictionaryProvider.SYNTHESIS],
    )
    d2 = Definition(
        word_id=word.id,
        part_of_speech="verb",
        text="Secondary meaning",
        providers=[DictionaryProvider.SYNTHESIS],
    )
    await d1.save()
    await d2.save()

    entry = DictionaryEntry(
        word_id=word.id,
        definition_ids=[d1.id],
        provider=DictionaryProvider.SYNTHESIS,
        languages=[Language.ENGLISH],
    )

    await save_entry_versioned(entry, word.text)

    entry.definition_ids = [d1.id, d2.id]
    entry.etymology = Etymology(text="From synthesized testing roots")
    await save_entry_versioned(entry, word.text)

    resource_id = f"{word.text}:{DictionaryProvider.SYNTHESIS.value}"
    versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)
    assert len(versions) == 2

    v1 = await manager.get_by_version(resource_id, ResourceType.DICTIONARY, "1.0.0", use_cache=False)
    latest = await manager.get_latest(resource_id, ResourceType.DICTIONARY, use_cache=False)
    assert v1 is not None
    assert latest is not None

    latest_content = latest.content_inline or {}
    assert latest_content.get("etymology", {}).get("text") == "From synthesized testing roots"
    assert len(latest_content.get("definition_ids", [])) == 2

    diff = compute_diff_between(v1.content_inline or {}, latest_content)
    assert diff
    assert "values_changed" in diff or "dictionary_item_added" in diff


@pytest.mark.asyncio
async def test_literature_versioning_and_deep_diff(test_db):
    """Literature snapshots should retain version history and deep diff output."""
    manager = get_version_manager()
    resource_id = "literature:version_diff_test"

    v1_content = {
        "title": "Versioned Work",
        "chapters": ["Chapter 1"],
        "metadata": {"edition": 1, "tags": ["classic"]},
    }
    v2_content = {
        "title": "Versioned Work",
        "chapters": ["Chapter 1", "Chapter 2"],
        "metadata": {"edition": 2, "tags": ["classic", "annotated"]},
    }

    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.LITERATURE,
        namespace=CacheNamespace.LITERATURE,
        content=v1_content,
    )
    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.LITERATURE,
        namespace=CacheNamespace.LITERATURE,
        content=v2_content,
    )

    v1 = await manager.get_by_version(resource_id, ResourceType.LITERATURE, "1.0.0", use_cache=False)
    latest = await manager.get_latest(resource_id, ResourceType.LITERATURE, use_cache=False)
    assert v1 is not None
    assert latest is not None
    assert latest.version_info.version == "1.0.1"

    diff = compute_diff_between(v1.content_inline or {}, latest.content_inline or {})
    assert diff
    assert "values_changed" in diff or "iterable_item_added" in diff

"""Versioned persistence for DictionaryEntry and Definition documents.

Canonical dual-save: L3 version snapshot (SHA-256 content-addressable)
+ live document upsert with per-resource locking.

Mirrors models/dictionary.py — storage/dictionary.py handles persistence
while models/dictionary.py defines the schemas.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from enum import Enum
from typing import Any

from ..caching.manager import get_version_manager
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..models.base import AudioMedia, ImageMedia
from ..models.dictionary import (
    Definition,
    DictionaryEntry,
    Example,
    Fact,
    Pronunciation,
    Word,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)

_entry_upsert_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_definition_upsert_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _provider_str(provider: Any) -> str:
    """Extract string value from provider (enum or str)."""
    return provider.value if isinstance(provider, Enum) else str(provider)


async def _resolve_word_text(word_id: Any) -> str:
    """Resolve word text from a word_id. Returns '<unknown>' on failure."""
    try:
        word = await Word.get(word_id)
        if word:
            return word.text
    except Exception:
        pass
    return "<unknown>"


async def _cleanup_replaced_children(
    old_entry: DictionaryEntry,
    new_entry: DictionaryEntry,
) -> None:
    """Delete child documents that are no longer referenced by the updated entry."""

    # --- Definitions (and their Examples) ---
    old_def_ids = set(old_entry.definition_ids)
    new_def_ids = set(new_entry.definition_ids)
    removed_def_ids = old_def_ids - new_def_ids

    if removed_def_ids:
        for def_id in removed_def_ids:
            definition = await Definition.get(def_id)
            if definition and definition.example_ids:
                await Example.find({"_id": {"$in": definition.example_ids}}).delete()
            if definition:
                await definition.delete()
        logger.debug(f"Cleaned up {len(removed_def_ids)} replaced definitions")

    # --- Pronunciation (and its AudioMedia) ---
    if old_entry.pronunciation_id and old_entry.pronunciation_id != new_entry.pronunciation_id:
        old_pron = await Pronunciation.get(old_entry.pronunciation_id)
        if old_pron:
            if old_pron.audio_file_ids:
                await AudioMedia.find({"_id": {"$in": old_pron.audio_file_ids}}).delete()
            await old_pron.delete()
        logger.debug(f"Cleaned up replaced pronunciation {old_entry.pronunciation_id}")

    # --- Facts ---
    old_fact_ids = set(old_entry.fact_ids)
    new_fact_ids = set(new_entry.fact_ids)
    removed_fact_ids = old_fact_ids - new_fact_ids

    if removed_fact_ids:
        await Fact.find({"_id": {"$in": list(removed_fact_ids)}}).delete()
        logger.debug(f"Cleaned up {len(removed_fact_ids)} replaced facts")

    # --- Images ---
    old_img_ids = set(old_entry.image_ids)
    new_img_ids = set(new_entry.image_ids)
    removed_img_ids = old_img_ids - new_img_ids

    if removed_img_ids:
        await ImageMedia.find({"_id": {"$in": list(removed_img_ids)}}).delete()
        logger.debug(f"Cleaned up {len(removed_img_ids)} replaced images")


async def save_entry_versioned(
    entry: DictionaryEntry,
    word: str,
    *,
    config: VersionConfig | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    """Save DictionaryEntry with version chain + live document upsert.

    Args:
        entry: DictionaryEntry to save.
        word: Word text for resource ID.
        config: Optional version config override.
        extra_metadata: Additional metadata to include in the version snapshot.

    """
    manager = get_version_manager()

    provider_value = _provider_str(entry.provider)
    resource_id = f"{word}:{provider_value}"

    entry_dict = entry.model_dump(mode="json")

    metadata: dict[str, Any] = {
        "word": word,
        "provider": provider_value,
        "word_id": str(entry.word_id) if entry.word_id else None,
    }

    if entry.model_info:
        if isinstance(entry.model_info, dict):
            metadata["model_info"] = entry.model_info
        else:
            metadata["model_info"] = entry.model_info.model_dump(mode="json")

    if entry.source_entries:
        metadata["source_entries"] = [se.model_dump(mode="json") for se in entry.source_entries]

    if extra_metadata:
        metadata.update(extra_metadata)

    # L3 version snapshot (canonical history)
    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.DICTIONARY,
        namespace=CacheNamespace.DICTIONARY,
        content=entry_dict,
        config=config or VersionConfig(),
        metadata=metadata,
    )

    # Live document upsert — per-resource lock prevents concurrent races
    async with _entry_upsert_locks[resource_id]:
        existing_live = await DictionaryEntry.find_one(
            DictionaryEntry.word_id == entry.word_id,
            DictionaryEntry.provider == entry.provider,
        )
        if existing_live:
            await _cleanup_replaced_children(existing_live, entry)
            existing_live.definition_ids = entry.definition_ids
            existing_live.pronunciation_id = entry.pronunciation_id
            existing_live.fact_ids = entry.fact_ids
            existing_live.languages = entry.languages
            existing_live.etymology = entry.etymology
            existing_live.source_entries = entry.source_entries
            existing_live.model_info = entry.model_info
            existing_live.raw_data = entry.raw_data
            await existing_live.save()
            entry.id = existing_live.id
            logger.debug(f"Updated live DictionaryEntry '{resource_id}'")
        else:
            await entry.save()
            logger.debug(f"Created live DictionaryEntry '{resource_id}'")

    logger.debug(f"Saved dictionary entry '{resource_id}' with version history")


async def save_definition_versioned(
    definition: Definition,
    word_text: str,
    *,
    config: VersionConfig | None = None,
) -> None:
    """Save Definition with version chain + live document upsert.

    Args:
        definition: Definition to save.
        word_text: Word text for resource ID.
        config: Optional version config override.

    """
    manager = get_version_manager()

    # Ensure a stable identifier before creating version snapshots.
    # Without this, first save uses "...:new" and later saves use "...:<id>",
    # splitting history across different resource IDs.
    if not definition.id:
        await definition.save()

    resource_id = f"def:{word_text}:{definition.id}"

    def_dict = definition.model_dump(mode="json")

    metadata: dict[str, Any] = {
        "word": word_text,
        "definition_id": str(definition.id),
        "part_of_speech": definition.part_of_speech,
    }

    # L3 version snapshot
    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.DICTIONARY,
        namespace=CacheNamespace.DICTIONARY,
        content=def_dict,
        config=config or VersionConfig(),
        metadata=metadata,
    )

    # Live document upsert
    async with _definition_upsert_locks[resource_id]:
        await definition.save()
        logger.debug(f"Saved live Definition '{resource_id}'")


async def save_definitions_batch_versioned(
    definitions: list[Definition],
    word_text: str,
) -> None:
    """Parallel versioned save for multiple definitions.

    Args:
        definitions: List of definitions to save.
        word_text: Word text for resource ID context.

    """
    async with asyncio.TaskGroup() as tg:
        for d in definitions:
            tg.create_task(save_definition_versioned(d, word_text))


async def save_pronunciation_versioned(
    pronunciation: Pronunciation,
    word: str,
    config: VersionConfig | None = None,
) -> None:
    """Save pronunciation with L3 version history."""
    manager = get_version_manager()
    resource_id = f"pron:{word}:{pronunciation.id}"
    pron_dict = pronunciation.model_dump(mode="json")

    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.DICTIONARY,
        namespace=CacheNamespace.DICTIONARY,
        content=pron_dict,
        config=config or VersionConfig(),
        metadata={"word": word, "type": "pronunciation"},
    )


async def save_fact_versioned(
    fact: Fact,
    word: str,
    config: VersionConfig | None = None,
) -> None:
    """Save fact with L3 version history."""
    manager = get_version_manager()
    resource_id = f"fact:{word}:{fact.id}"
    fact_dict = fact.model_dump(mode="json")

    await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.DICTIONARY,
        namespace=CacheNamespace.DICTIONARY,
        content=fact_dict,
        config=config or VersionConfig(),
        metadata={"word": word, "type": "fact"},
    )

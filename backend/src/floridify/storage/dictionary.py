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
from ..models.dictionary import Definition, DictionaryEntry, Word
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
            existing_live.definition_ids = entry.definition_ids
            existing_live.pronunciation_id = entry.pronunciation_id
            existing_live.fact_ids = entry.fact_ids
            existing_live.etymology = entry.etymology
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

    resource_id = f"def:{word_text}:{definition.id or 'new'}"

    def_dict = definition.model_dump(mode="json")

    metadata: dict[str, Any] = {
        "word": word_text,
        "definition_id": str(definition.id) if definition.id else None,
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
        if definition.id:
            # Already persisted — just save updates
            await definition.save()
            logger.debug(f"Updated live Definition '{resource_id}'")
        else:
            # New definition — create
            await definition.save()
            logger.debug(f"Created live Definition '{resource_id}'")


async def save_definitions_batch_versioned(
    definitions: list[Definition],
    word_text: str,
) -> None:
    """Parallel versioned save for multiple definitions.

    Args:
        definitions: List of definitions to save.
        word_text: Word text for resource ID context.

    """
    await asyncio.gather(
        *[save_definition_versioned(d, word_text) for d in definitions],
    )

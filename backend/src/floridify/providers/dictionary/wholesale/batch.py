"""Batch save strategies for wholesale Wiktionary imports.

Two paths:
- `flush_batch_insert`: Fast `insert_many` for initial bulk import (INSERT mode).
- `flush_batch_upsert`: Versioned per-entry save for updates/hydration (UPDATE/HYDRATE modes).
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any

from ....models.base import PydanticObjectId
from ....models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Pronunciation,
    Word,
)
from ....storage.dictionary import save_definition_versioned, save_entry_versioned
from ....utils.logging import get_logger

logger = get_logger(__name__)


class ImportMode(str, Enum):
    """Controls how the wholesale import handles existing entries."""

    INSERT = "insert"  # Skip existing entries (fast insert_many)
    UPDATE = "update"  # Re-parse all, save via versioned upsert
    HYDRATE = "hydrate"  # Only re-parse incomplete entries


# ── Shared helpers ────────────────────────────────────────────────────


def _build_etymology(etym: Any) -> Etymology | None:
    """Build Etymology object from parsed entry data."""
    if isinstance(etym, str) and etym:
        return Etymology(text=etym)
    if isinstance(etym, dict) and etym.get("text"):
        return Etymology(
            text=etym["text"],
            origin_language=etym.get("origin_language"),
            root_words=etym.get("root_words", []),
            first_known_use=etym.get("first_known_use"),
        )
    return None


def _build_raw_data(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Extract structured data fields into raw_data dict."""
    raw: dict[str, Any] = {}
    for key in (
        "derived_terms",
        "related_terms",
        "hypernyms",
        "hyponyms",
        "coordinate_terms",
        "alternative_forms",
    ):
        if entry.get(key):
            raw[key] = entry[key]
    return raw or None


# ── INSERT mode: fast bulk insert ─────────────────────────────────────


async def flush_batch_insert(
    batch: list[dict[str, Any]],
    word_index: dict[str, Word],
    lang_code: str,
) -> int:
    """Save batch via insert_many (fast, no versioning).

    Pre-assigns IDs so all collections can be inserted in parallel.
    Used for initial bulk import (INSERT mode).
    """
    word_docs: list[Word] = []
    def_docs: list[Definition] = []
    pron_docs: list[Pronunciation] = []
    dict_entries: list[DictionaryEntry] = []

    for entry in batch:
        try:
            title = entry["title"]

            word_obj = word_index.get(title)
            if not word_obj:
                word_obj = Word(
                    id=PydanticObjectId(),
                    text=title,
                    languages=[lang_code],
                )
                word_docs.append(word_obj)
                word_index[title] = word_obj

            if not word_obj.id:
                continue

            defs_for_entry: list[Definition] = []
            for def_data in entry["definitions"]:
                defs_for_entry.append(
                    Definition(
                        id=PydanticObjectId(),
                        word_id=word_obj.id,
                        part_of_speech=def_data["part_of_speech"],
                        text=def_data["text"],
                        synonyms=def_data.get("synonyms", [])[:20],
                        antonyms=def_data.get("antonyms", [])[:20],
                        providers=[DictionaryProvider.WIKTIONARY],
                    )
                )
            if not defs_for_entry:
                continue
            def_docs.extend(defs_for_entry)

            pron = entry.get("pronunciation")
            pron_doc = None
            if pron and hasattr(pron, "phonetic"):
                pron_doc = Pronunciation(
                    id=PydanticObjectId(),
                    word_id=word_obj.id,
                    phonetic=pron.phonetic,
                    ipa=pron.ipa,
                    syllables=getattr(pron, "syllables", []),
                )
                pron_docs.append(pron_doc)

            etymology_obj = _build_etymology(entry.get("etymology"))
            raw_data = _build_raw_data(entry)

            dict_entries.append(
                DictionaryEntry(
                    word_id=word_obj.id,
                    definition_ids=[d.id for d in defs_for_entry if d.id],
                    pronunciation_id=pron_doc.id if pron_doc and pron_doc.id else None,
                    provider=DictionaryProvider.WIKTIONARY,
                    languages=[lang_code],
                    etymology=etymology_obj,
                    raw_data=raw_data,
                )
            )

        except Exception as e:
            logger.debug(f"Build error for '{entry.get('title')}': {e}")

    try:
        insert_tasks = []
        if word_docs:
            insert_tasks.append(Word.insert_many(word_docs))
        if def_docs:
            insert_tasks.append(Definition.insert_many(def_docs))
        if pron_docs:
            insert_tasks.append(Pronunciation.insert_many(pron_docs))
        if dict_entries:
            insert_tasks.append(DictionaryEntry.insert_many(dict_entries))

        if insert_tasks:
            await asyncio.gather(*insert_tasks)

        return len(dict_entries)
    except Exception as e:
        logger.warning(f"Batch insert error: {e}")
        return 0


# ── UPDATE/HYDRATE mode: versioned per-entry upsert ──────────────────


async def flush_batch_upsert(
    batch: list[dict[str, Any]],
    word_index: dict[str, Word],
    lang_code: str,
) -> int:
    """Save batch via versioned upsert (correct versioning, slower).

    Uses save_entry_versioned / save_definition_versioned for:
    - Version chains with SHA-256 dedup
    - Delta compression of old versions
    - Automatic orphan cleanup
    """
    imported = 0

    for entry in batch:
        try:
            title = entry["title"]

            # Get or create Word
            word_obj = word_index.get(title)
            if not word_obj:
                word_obj = Word(text=title, languages=[lang_code])
                await word_obj.save()
                word_index[title] = word_obj

            if not word_obj.id:
                continue

            # Build and save definitions (versioned)
            defs: list[Definition] = []
            for def_data in entry["definitions"]:
                d = Definition(
                    word_id=word_obj.id,
                    part_of_speech=def_data["part_of_speech"],
                    text=def_data["text"],
                    synonyms=def_data.get("synonyms", [])[:20],
                    antonyms=def_data.get("antonyms", [])[:20],
                    providers=[DictionaryProvider.WIKTIONARY],
                )
                await save_definition_versioned(d, title)
                defs.append(d)

            if not defs:
                continue

            # Pronunciation
            pron = entry.get("pronunciation")
            pron_doc = None
            if pron and hasattr(pron, "phonetic"):
                pron_doc = Pronunciation(
                    word_id=word_obj.id,
                    phonetic=pron.phonetic,
                    ipa=pron.ipa,
                    syllables=getattr(pron, "syllables", []),
                )
                await pron_doc.save()

            etymology_obj = _build_etymology(entry.get("etymology"))
            raw_data = _build_raw_data(entry)

            # Build DictionaryEntry and save versioned
            dict_entry = DictionaryEntry(
                word_id=word_obj.id,
                definition_ids=[d.id for d in defs if d.id],
                pronunciation_id=pron_doc.id if pron_doc and pron_doc.id else None,
                provider=DictionaryProvider.WIKTIONARY,
                languages=[lang_code],
                etymology=etymology_obj,
                raw_data=raw_data,
            )

            await save_entry_versioned(dict_entry, title)
            imported += 1

        except Exception as e:
            logger.debug(f"Upsert error for '{entry.get('title')}': {e}")

    return imported


# ── Hydrate: find incomplete entries ──────────────────────────────────


async def find_complete_entries(word_index: dict[str, Word]) -> set[str]:
    """Find words with complete Wiktionary entries.

    An entry is "complete" if it has etymology AND at least one definition.
    Complete entries are skipped in HYDRATE mode.
    """
    complete_word_ids: set[PydanticObjectId] = set()
    async for entry in DictionaryEntry.find(
        {
            "provider": DictionaryProvider.WIKTIONARY.value,
            "etymology": {"$ne": None},
            "definition_ids.0": {"$exists": True},
        }
    ):
        complete_word_ids.add(entry.word_id)

    word_id_to_text = {w.id: text for text, w in word_index.items()}
    return {
        word_id_to_text[wid]
        for wid in complete_word_ids
        if wid in word_id_to_text
    }

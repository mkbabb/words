"""Manual migration for strict multi-language word model.

Run this script manually after deploying the `languages`-only schema.
It performs:
1) `Word.language` -> `Word.languages`
2) `DictionaryEntry.language` -> `DictionaryEntry.languages`
3) Ensures `Word.corpus_ids` exists
4) Deduplicates Word documents by text and rewires FK references
"""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from beanie import PydanticObjectId
from bson import ObjectId
from bson import json_util
from pymongo import IndexModel

from floridify.caching.models import BaseVersionedData
from floridify.caching.models import VersionConfig
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.corpus.semantic_policy import recompute_semantic_effective_subtree
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    Fact,
    Pronunciation,
    Word,
)
from floridify.models.relationships import WordRelationship
from floridify.storage.mongodb import get_database, get_storage
from floridify.utils.language_precedence import merge_language_precedence
from floridify.utils.config import Config
from floridify.wordlist.models import WordList


@dataclass
class MigrationStats:
    words_language_migrated: int = 0
    entries_language_migrated: int = 0
    words_corpus_ids_initialized: int = 0
    word_duplicates_merged: int = 0
    definitions_rewired: int = 0
    pronunciations_rewired: int = 0
    facts_rewired: int = 0
    dictionary_entries_rewired: int = 0
    relationships_rewired: int = 0
    wordlists_rewired: int = 0
    duplicate_words_deleted: int = 0
    indexes_created: int = 0
    indexes_dropped: int = 0
    search_linkages_repaired: int = 0
    semantic_policy_backfilled: int = 0
    semantic_policy_recomputed: int = 0
    index_verification_passed: bool = False
    metadata_backup_path: str = ""


def _sort_key(word: Word) -> tuple[datetime, str]:
    created_at = word.created_at if isinstance(word.created_at, datetime) else datetime.min
    word_id = str(word.id) if word.id else ""
    return created_at, word_id


async def _migrate_legacy_language_fields(stats: MigrationStats) -> None:
    word_collection = Word.get_pymongo_collection()
    entry_collection = DictionaryEntry.get_pymongo_collection()

    word_cursor = word_collection.find({"language": {"$exists": True}})
    async for word_doc in word_cursor:
        legacy_language = word_doc.get("language")
        if not isinstance(legacy_language, str) or not legacy_language:
            continue

        await word_collection.update_one(
            {"_id": word_doc["_id"]},
            {
                "$set": {"languages": [legacy_language]},
                "$unset": {"language": ""},
            },
        )
        stats.words_language_migrated += 1

    entry_cursor = entry_collection.find({"language": {"$exists": True}})
    async for entry_doc in entry_cursor:
        legacy_language = entry_doc.get("language")
        if not isinstance(legacy_language, str) or not legacy_language:
            continue

        await entry_collection.update_one(
            {"_id": entry_doc["_id"]},
            {
                "$set": {"languages": [legacy_language]},
                "$unset": {"language": ""},
            },
        )
        stats.entries_language_migrated += 1

    init_result = await word_collection.update_many(
        {"corpus_ids": {"$exists": False}},
        {"$set": {"corpus_ids": []}},
    )
    stats.words_corpus_ids_initialized = init_result.modified_count


def _merge_word_languages(words: list[Word]) -> list[str]:
    merged: list[str] = []
    for word in words:
        merged = merge_language_precedence(merged, list(word.languages))
    return merged


def _merge_word_corpus_ids(words: list[Word]) -> list[PydanticObjectId]:
    merged: list[PydanticObjectId] = []
    for word in words:
        for corpus_id in word.corpus_ids:
            if corpus_id not in merged:
                merged.append(corpus_id)
    return merged


async def _rewire_duplicate_word(
    primary_word: Word,
    duplicate_word: Word,
    stats: MigrationStats,
) -> None:
    assert primary_word.id is not None
    assert duplicate_word.id is not None

    definitions_result = await Definition.find(Definition.word_id == duplicate_word.id).update(
        {"$set": {"word_id": primary_word.id}}
    )
    pronunciations_result = await Pronunciation.find(
        Pronunciation.word_id == duplicate_word.id
    ).update({"$set": {"word_id": primary_word.id}})
    facts_result = await Fact.find(Fact.word_id == duplicate_word.id).update(
        {"$set": {"word_id": primary_word.id}}
    )
    dictionary_entries_result = await DictionaryEntry.find(
        DictionaryEntry.word_id == duplicate_word.id
    ).update({"$set": {"word_id": primary_word.id}})
    relationships_from_result = await WordRelationship.find(
        WordRelationship.from_word_id == duplicate_word.id
    ).update({"$set": {"from_word_id": primary_word.id}})
    relationships_to_result = await WordRelationship.find(
        WordRelationship.to_word_id == duplicate_word.id
    ).update({"$set": {"to_word_id": primary_word.id}})

    wordlist_collection = WordList.get_pymongo_collection()
    wordlists_result = await wordlist_collection.update_many(
        {"words.word_id": duplicate_word.id},
        {"$set": {"words.$[wordref].word_id": primary_word.id}},
        array_filters=[{"wordref.word_id": duplicate_word.id}],
    )

    stats.definitions_rewired += definitions_result.modified_count
    stats.pronunciations_rewired += pronunciations_result.modified_count
    stats.facts_rewired += facts_result.modified_count
    stats.dictionary_entries_rewired += dictionary_entries_result.modified_count
    stats.relationships_rewired += (
        relationships_from_result.modified_count + relationships_to_result.modified_count
    )
    stats.wordlists_rewired += wordlists_result.modified_count

    await duplicate_word.delete()
    stats.duplicate_words_deleted += 1


async def _deduplicate_words(stats: MigrationStats) -> None:
    all_words = await Word.find_all().to_list()
    words_by_text: dict[str, list[Word]] = defaultdict(list)

    for word in all_words:
        words_by_text[word.text].append(word)

    for grouped_words in words_by_text.values():
        if len(grouped_words) < 2:
            continue

        ordered_words = sorted(grouped_words, key=_sort_key)
        primary_word = ordered_words[0]
        duplicate_words = ordered_words[1:]

        merged_languages = _merge_word_languages(ordered_words)
        merged_corpus_ids = _merge_word_corpus_ids(ordered_words)

        primary_changed = False
        if merged_languages != list(primary_word.languages):
            primary_word.languages = merged_languages
            primary_changed = True
        if merged_corpus_ids != list(primary_word.corpus_ids):
            primary_word.corpus_ids = merged_corpus_ids
            primary_changed = True
        if primary_changed:
            await primary_word.save()

        for duplicate_word in duplicate_words:
            await _rewire_duplicate_word(primary_word, duplicate_word, stats)
            stats.word_duplicates_merged += 1


async def _drop_index_if_exists(
    *,
    collection: Any,
    index_name: str,
    stats: MigrationStats,
) -> None:
    index_info = await collection.index_information()
    if index_name in index_info:
        await collection.drop_index(index_name)
        stats.indexes_dropped += 1


async def _ensure_index(
    *,
    collection: Any,
    index_model: IndexModel,
    stats: MigrationStats,
) -> None:
    index_name = index_model.document.get("name")
    if not index_name:
        raise ValueError("IndexModel must include an explicit name")

    index_info = await collection.index_information()
    if index_name in index_info:
        return

    await collection.create_indexes([index_model])
    stats.indexes_created += 1


async def _migrate_indexes(stats: MigrationStats) -> None:
    word_collection = Word.get_pymongo_collection()
    entry_collection = DictionaryEntry.get_pymongo_collection()
    versioned_collection = BaseVersionedData.get_pymongo_collection()

    # Drop legacy single-language indexes removed by the strict schema migration.
    await _drop_index_if_exists(
        collection=word_collection,
        index_name="text_1_language_1",
        stats=stats,
    )
    await _drop_index_if_exists(
        collection=entry_collection,
        index_name="language_1",
        stats=stats,
    )

    # Ensure canonical multi-language indexes exist.
    await _ensure_index(
        collection=word_collection,
        index_model=IndexModel([("text", 1), ("languages", 1)], name="text_1_languages_1"),
        stats=stats,
    )
    await _ensure_index(
        collection=entry_collection,
        index_model=IndexModel([("languages", 1)], name="languages_1"),
        stats=stats,
    )

    # Versioned data: drop non-type-qualified resource indexes and old corpus_id sparse index.
    await _drop_index_if_exists(
        collection=versioned_collection,
        index_name="resource_id_1_version_info.is_latest_1__id_-1",
        stats=stats,
    )
    await _drop_index_if_exists(
        collection=versioned_collection,
        index_name="resource_id_1_version_info.version_1",
        stats=stats,
    )
    await _drop_index_if_exists(
        collection=versioned_collection,
        index_name="resource_id_1_version_info.data_hash_1",
        stats=stats,
    )
    await _drop_index_if_exists(
        collection=versioned_collection,
        index_name="corpus_id_sparse",
        stats=stats,
    )
    await _drop_index_if_exists(
        collection=versioned_collection,
        index_name="parent_corpus_id_sparse",
        stats=stats,
    )

    # Ensure canonical versioned metadata indexes for semantic/search/trie persistence.
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel(
            [("resource_type", 1), ("resource_id", 1), ("version_info.is_latest", 1), ("_id", -1)],
            name="resource_type_id_latest_idx",
        ),
        stats=stats,
    )
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel(
            [("resource_type", 1), ("resource_id", 1), ("version_info.version", 1)],
            name="resource_type_id_version_idx",
        ),
        stats=stats,
    )
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel(
            [("resource_type", 1), ("resource_id", 1), ("version_info.data_hash", 1)],
            name="resource_type_id_hash_idx",
        ),
        stats=stats,
    )
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel([("corpus_uuid", 1)], sparse=True, name="corpus_uuid_sparse"),
        stats=stats,
    )
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel([("parent_uuid", 1)], sparse=True, name="parent_uuid_sparse"),
        stats=stats,
    )
    await _ensure_index(
        collection=versioned_collection,
        index_model=IndexModel([("model_name", 1)], sparse=True, name="model_name_sparse"),
        stats=stats,
    )


async def _backfill_and_recompute_semantic_policy(stats: MigrationStats) -> None:
    """Backfill typed semantic policy fields and recompute effective state tree-wide."""
    versioned_collection = BaseVersionedData.get_pymongo_collection()

    corpus_cursor = versioned_collection.find(
        {
            "resource_type": "corpus",
            "version_info.is_latest": True,
        }
    )
    async for corpus_doc in corpus_cursor:
        updates: dict[str, Any] = {}
        explicit = corpus_doc.get("semantic_enabled_explicit")
        if explicit is None and "semantic_enabled_explicit" not in corpus_doc:
            legacy_explicit = corpus_doc.get("semantic_enabled")
            if not isinstance(legacy_explicit, bool):
                legacy_meta = corpus_doc.get("metadata", {})
                if isinstance(legacy_meta, dict):
                    legacy_meta_value = legacy_meta.get("semantic_enabled")
                    legacy_explicit = (
                        legacy_meta_value if isinstance(legacy_meta_value, bool) else None
                    )
                else:
                    legacy_explicit = None
            updates["semantic_enabled_explicit"] = legacy_explicit
            explicit = legacy_explicit

        if "semantic_enabled_effective" not in corpus_doc:
            updates["semantic_enabled_effective"] = bool(explicit is True)
        if "semantic_model" not in corpus_doc:
            legacy_model = corpus_doc.get("semantic_model")
            updates["semantic_model"] = legacy_model if isinstance(legacy_model, str) else None

        if updates:
            await versioned_collection.update_one({"_id": corpus_doc["_id"]}, {"$set": updates})
            stats.semantic_policy_backfilled += 1

    manager = get_tree_corpus_manager()
    roots = await versioned_collection.find(
        {
            "resource_type": "corpus",
            "version_info.is_latest": True,
            "$or": [{"parent_uuid": None}, {"parent_uuid": {"$exists": False}}],
        }
    ).to_list()

    for root_doc in roots:
        root_uuid = root_doc.get("uuid")
        if not isinstance(root_uuid, str) or not root_uuid:
            continue
        await recompute_semantic_effective_subtree(
            root_corpus_uuid=root_uuid,
            get_corpus_fn=manager.get_corpus,
            save_corpus_fn=manager.save_corpus,
            config=VersionConfig(use_cache=False),
        )
        stats.semantic_policy_recomputed += 1


async def _verify_versioned_index_convergence(stats: MigrationStats) -> None:
    """Verify canonical versioned_data index set exists after migration."""
    required_index_names = {
        "resource_type_id_latest_idx",
        "resource_type_id_version_idx",
        "resource_type_id_hash_idx",
        "corpus_uuid_sparse",
        "parent_uuid_sparse",
        "model_name_sparse",
    }
    versioned_collection = BaseVersionedData.get_pymongo_collection()
    index_info = await versioned_collection.index_information()
    missing = sorted(name for name in required_index_names if name not in index_info)
    if missing:
        raise RuntimeError(f"Missing required versioned_data indexes after migration: {missing}")
    stats.index_verification_passed = True


def _database_name_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.path.lstrip("/")


def _host_signature(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.netloc.rsplit("@", 1)[-1].lower()


def _preflight_validate_database_targets() -> None:
    config = Config.from_file()
    runtime_url = config.database.get_url("runtime")
    test_url = config.database.get_url("test")

    runtime_db = _database_name_from_uri(runtime_url)
    test_db = _database_name_from_uri(test_url)
    if not runtime_db:
        raise RuntimeError("database.runtime_url must include a database name")
    if not test_db or not test_db.startswith("test_"):
        raise RuntimeError(
            f"database.test_url must include a test_ database name (got '{test_db or '<empty>'}')"
        )
    if _host_signature(runtime_url) == _host_signature(test_url) and runtime_db == test_db:
        raise RuntimeError("Runtime/test database targets resolve to the same DB; aborting migration")


async def _backup_versioned_metadata(stats: MigrationStats) -> None:
    """Snapshot current metadata docs before mutation."""
    db = await get_database()
    backup_dir = Path("migration_backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"versioned_metadata_backup_{timestamp}.json"

    query = {"resource_type": {"$in": ["corpus", "search", "trie", "semantic"]}}
    docs = await db["versioned_data"].find(query).to_list(length=None)
    with backup_path.open("w", encoding="utf-8") as handle:
        handle.write(json_util.dumps(docs, indent=2))
    stats.metadata_backup_path = str(backup_path)


async def _repair_search_index_linkages(stats: MigrationStats) -> None:
    """Repair search->trie/semantic metadata links for existing latest docs."""
    versioned_collection = BaseVersionedData.get_pymongo_collection()
    search_cursor = versioned_collection.find(
        {
            "resource_type": "search",
            "version_info.is_latest": True,
        }
    )

    async for search_doc in search_cursor:
        resource_id = search_doc.get("resource_id", "")
        corpus_uuid = search_doc.get("corpus_uuid")
        if not corpus_uuid and isinstance(resource_id, str) and resource_id.endswith(":search"):
            corpus_uuid = resource_id[: -len(":search")]
        if not isinstance(corpus_uuid, str) or not corpus_uuid:
            continue

        content_inline = search_doc.get("content_inline") or {}
        updates: dict[str, Any] = {}
        expected_trie = await versioned_collection.find_one(
            {
                "resource_type": "trie",
                "resource_id": f"{corpus_uuid}:trie",
                "version_info.is_latest": True,
            }
        )
        current_trie_id = _coerce_object_id(content_inline.get("trie_index_id"))
        trie_is_valid = False
        if current_trie_id:
            current_trie_doc = await versioned_collection.find_one(
                {
                    "_id": current_trie_id,
                    "resource_type": "trie",
                    "version_info.is_latest": True,
                }
            )
            trie_is_valid = (
                bool(current_trie_doc)
                and current_trie_doc.get("resource_id") == f"{corpus_uuid}:trie"
            )

        if expected_trie and (
            not trie_is_valid or current_trie_id != expected_trie.get("_id")
        ):
            updates["content_inline.trie_index_id"] = expected_trie["_id"]

        semantic_candidates = await versioned_collection.find(
            {
                "resource_type": "semantic",
                "version_info.is_latest": True,
                "resource_id": {"$regex": f"^{re.escape(corpus_uuid)}:semantic:"},
            }
        ).to_list()

        selected_semantic = None
        search_vocabulary_hash = (
            content_inline.get("vocabulary_hash") or search_doc.get("vocabulary_hash") or ""
        )
        if search_vocabulary_hash:
            short_hash = str(search_vocabulary_hash)[:8]
            selected_semantic = next(
                (
                    candidate
                    for candidate in semantic_candidates
                    if str(candidate.get("resource_id", "")).endswith(f":{short_hash}")
                ),
                None,
            )
        if not selected_semantic and semantic_candidates:
            selected_semantic = semantic_candidates[0]

        current_semantic_id = _coerce_object_id(content_inline.get("semantic_index_id"))
        semantic_is_valid = False
        if current_semantic_id:
            current_semantic_doc = await versioned_collection.find_one(
                {
                    "_id": current_semantic_id,
                    "resource_type": "semantic",
                    "version_info.is_latest": True,
                }
            )
            semantic_is_valid = bool(current_semantic_doc) and str(
                current_semantic_doc.get("resource_id", "")
            ).startswith(f"{corpus_uuid}:semantic:")

        if selected_semantic and (
            not semantic_is_valid or current_semantic_id != selected_semantic.get("_id")
        ):
            updates["content_inline.semantic_index_id"] = selected_semantic["_id"]
            if content_inline.get("semantic_enabled") is not True:
                updates["content_inline.semantic_enabled"] = True
        elif not selected_semantic:
            # Canonical consistency: semantic cannot be "enabled" without a valid semantic index.
            if content_inline.get("semantic_enabled") is True:
                updates["content_inline.semantic_enabled"] = False
            if content_inline.get("semantic_index_id") is not None:
                updates["content_inline.semantic_index_id"] = None

        if updates:
            await versioned_collection.update_one(
                {"_id": search_doc["_id"]},
                {"$set": updates},
            )
            stats.search_linkages_repaired += 1


def _coerce_object_id(value: Any) -> ObjectId | None:
    """Convert mixed ID values (ObjectId/PydanticObjectId/str) to ObjectId."""
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, PydanticObjectId):
        return ObjectId(str(value))
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except Exception:
            return None
    return None


async def main() -> None:
    _preflight_validate_database_targets()
    await get_storage()
    stats = MigrationStats()
    await _backup_versioned_metadata(stats)

    await _migrate_legacy_language_fields(stats)
    await _deduplicate_words(stats)
    await _migrate_indexes(stats)
    await _repair_search_index_linkages(stats)
    await _backfill_and_recompute_semantic_policy(stats)
    await _verify_versioned_index_convergence(stats)

    print("✅ Migration complete")
    print(f"  Word.language -> languages: {stats.words_language_migrated}")
    print(f"  DictionaryEntry.language -> languages: {stats.entries_language_migrated}")
    print(f"  Word.corpus_ids initialized: {stats.words_corpus_ids_initialized}")
    print(f"  Duplicate words merged: {stats.word_duplicates_merged}")
    print(f"  Definitions rewired: {stats.definitions_rewired}")
    print(f"  Pronunciations rewired: {stats.pronunciations_rewired}")
    print(f"  Facts rewired: {stats.facts_rewired}")
    print(f"  Dictionary entries rewired: {stats.dictionary_entries_rewired}")
    print(f"  Relationships rewired: {stats.relationships_rewired}")
    print(f"  Wordlists rewired: {stats.wordlists_rewired}")
    print(f"  Duplicate words deleted: {stats.duplicate_words_deleted}")
    print(f"  Indexes created: {stats.indexes_created}")
    print(f"  Indexes dropped: {stats.indexes_dropped}")
    print(f"  Search index linkages repaired: {stats.search_linkages_repaired}")
    print(f"  Semantic policy docs backfilled: {stats.semantic_policy_backfilled}")
    print(f"  Semantic policy roots recomputed: {stats.semantic_policy_recomputed}")
    print(f"  Versioned index verification passed: {stats.index_verification_passed}")
    print(f"  Metadata backup path: {stats.metadata_backup_path}")


if __name__ == "__main__":
    asyncio.run(main())

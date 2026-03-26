"""Corpus CRUD operations: save, get, batch retrieval, and stats.

Standalone async functions that receive needed parameters (db objects,
version manager) from the TreeCorpusManager caller. This is delegation,
not method-binding.
"""

from __future__ import annotations

from typing import Any

import coolname
from beanie import PydanticObjectId

from ..caching.core import get_versioned_content
from ..caching.manager import VersionedDataManager
from ..caching.models import BaseVersionedData, CacheNamespace, ResourceType, VersionConfig
from ..models.base import Language
from ..utils.logging import get_logger
from .core import Corpus
from .models import CorpusType
from .semantic_policy import recompute_semantic_effective_upward

logger = get_logger(__name__)


def remove_self_references(
    child_uuids: list[str] | None,
    corpus_uuid: str | None = None,
) -> list[str]:
    """Remove self-references from child_uuids list.

    CRITICAL FIX: Extracted helper to prevent corpus cycles and data corruption.
    Self-references occur when a corpus appears in its own child list,
    which breaks tree traversal and aggregation logic.

    Args:
        child_uuids: List of child UUIDs (strings)
        corpus_uuid: The corpus UUID (string) for self-reference comparison

    Returns:
        Filtered list with self-reference removed, or original list if no self-reference

    """
    if not child_uuids:
        return []

    if corpus_uuid and corpus_uuid in child_uuids:
        logger.warning(f"Removing self-reference from child_uuids: {corpus_uuid}")
        return [cid for cid in child_uuids if cid != corpus_uuid]

    return child_uuids


async def save_corpus_simple(
    vm: VersionedDataManager,
    corpus: Corpus,
    config: VersionConfig | None = None,
) -> Corpus | None:
    """Simplified save that focuses on tree structure.

    Args:
        vm: Version manager instance
        corpus: Corpus object to save
        config: Version configuration

    Returns:
        Saved Corpus instance or None

    """
    # Get or create metadata
    if corpus.corpus_id:
        metadata = await Corpus.Metadata.get(corpus.corpus_id)
    else:
        metadata = None

    if not metadata:
        metadata = Corpus.Metadata(
            resource_id=corpus.corpus_name,
            resource_type=ResourceType.CORPUS.value,
        )

    # Update all fields directly
    metadata.corpus_type = (
        corpus.corpus_type.value
        if isinstance(corpus.corpus_type, CorpusType)
        else corpus.corpus_type
    )
    metadata.language = (
        corpus.language.value if isinstance(corpus.language, Language) else corpus.language
    )
    metadata.parent_uuid = corpus.parent_uuid
    metadata.child_uuids = corpus.child_uuids or []
    metadata.is_master = corpus.is_master
    metadata.semantic_enabled_explicit = corpus.semantic_enabled_explicit
    metadata.semantic_enabled_effective = corpus.semantic_enabled_effective
    metadata.semantic_model = corpus.semantic_model

    # Store content
    content = corpus.model_dump(mode="json")
    metadata.content = content

    # Save to MongoDB
    await metadata.save()
    corpus.corpus_id = metadata.id

    return corpus


async def save_metadata(
    metadata: Corpus.Metadata,
) -> Corpus.Metadata:
    """Save a Corpus.Metadata object directly to MongoDB.

    This bypasses all corpus logic and directly saves the metadata.
    Used for low-level operations and tests.

    Args:
        metadata: Corpus.Metadata object to save

    Returns:
        Saved metadata object

    """
    # Clean self-references before saving using extracted helper
    # Use UUID for comparison since child_uuids contains UUID strings
    metadata.child_uuids = remove_self_references(metadata.child_uuids, corpus_uuid=metadata.uuid)

    await metadata.save()
    return metadata


async def save_corpus(
    vm: VersionedDataManager,
    corpus: Corpus | None = None,
    corpus_id: PydanticObjectId | None = None,
    corpus_name: str | None = None,
    content: dict[str, Any] | None = None,
    corpus_type: CorpusType = CorpusType.LEXICON,
    language: Language = Language.ENGLISH,
    parent_uuid: str | None = None,
    child_uuids: list[str] | None = None,
    is_master: bool | None = None,
    semantic_enabled_explicit: bool | None = None,
    semantic_enabled_effective: bool | None = None,
    semantic_model: str | None = None,
    config: VersionConfig | None = None,
    metadata: dict[str, Any] | None = None,
    get_corpus_fn: Any = None,
    skip_parent_update: bool = False,
) -> Corpus | None:
    """Save a corpus - ONLY saves data, does NOT manage relationships.

    This is a pure data persistence operation. Use update_parent() to manage
    parent-child relationships separately.

    Args:
        vm: Version manager instance
        corpus: Corpus object to save (MUST be Corpus, not Metadata)
        corpus_id: Existing corpus ID for updates
        corpus_name: Corpus name (optional, will be generated if not provided)
        content: Corpus content (vocabulary, etc.)
        corpus_type: Type of corpus
        language: Language of the corpus
        parent_uuid: Parent corpus uuid (saved as data only)
        child_uuids: Child corpus uuids (saved as data only)
        is_master: Whether this is a master corpus
        semantic_enabled_explicit: Explicit semantic toggle for this corpus
        semantic_enabled_effective: Effective semantic state computed over descendants
        semantic_model: Preferred semantic model for this corpus
        config: Version configuration
        metadata: Additional metadata
        get_corpus_fn: Callable to get a corpus (for auto-update parent logic)

    Returns:
        Saved Corpus instance

    """
    # save_corpus should NOT accept Metadata objects
    # Check if corpus is a Metadata object by type

    if corpus and isinstance(corpus, BaseVersionedData):
        logger.error(
            "save_corpus called with Metadata object - use save_metadata() or get_corpus() first"
        )
        return None

    # If corpus object provided, extract parameters from it
    # IMPORTANT: Explicit parameters take precedence over corpus object values
    if corpus:
        corpus_id = corpus_id if corpus_id is not None else corpus.corpus_id
        corpus_name = corpus_name or corpus.corpus_name

        # Ensure indices are built if we have vocabulary but no indices
        if corpus.vocabulary and not corpus.vocabulary_to_index:
            await corpus._rebuild_indices()

        content = content if content is not None else corpus.model_dump(mode="json")
        corpus_type = corpus_type if corpus_type != CorpusType.LEXICON else corpus.corpus_type
        language = language if language != Language.ENGLISH else corpus.language
        parent_uuid = parent_uuid if parent_uuid is not None else corpus.parent_uuid
        child_uuids = child_uuids if child_uuids is not None else corpus.child_uuids
        semantic_enabled_explicit = (
            semantic_enabled_explicit
            if semantic_enabled_explicit is not None
            else corpus.semantic_enabled_explicit
        )
        semantic_enabled_effective = (
            semantic_enabled_effective
            if semantic_enabled_effective is not None
            else corpus.semantic_enabled_effective
        )
        semantic_model = semantic_model if semantic_model is not None else corpus.semantic_model
        logger.debug(
            f"save_corpus: corpus has {len(corpus.child_uuids) if corpus.child_uuids else 0} children, using {len(child_uuids) if child_uuids else 0} children"
        )
        # Preserve is_master flag: use explicit value if provided, otherwise get from corpus
        # PATHOLOGICAL REMOVAL: No getattr - direct attribute access only
        is_master = is_master if is_master is not None else (corpus.is_master if corpus else False)

        # Clean self-references from child_uuids immediately using extracted helper
        # PATHOLOGICAL FIX: Use corpus_uuid if available from existing corpus
        corpus_uuid_for_clean = None
        if corpus and corpus.corpus_uuid:
            corpus_uuid_for_clean = corpus.corpus_uuid
        # NO FALLBACK - removed reference to undefined 'existing'

        child_uuids = remove_self_references(child_uuids, corpus_uuid=corpus_uuid_for_clean)

    # Generate name if not provided
    if not corpus_name and not corpus_id:
        corpus_name = coolname.generate_slug(2)

    # If we have a corpus_id, try to get the existing corpus first
    existing = None
    if corpus_id:
        existing = await Corpus.Metadata.get(corpus_id)
        if existing and not corpus_name:
            corpus_name = existing.resource_id  # Use existing name
        if existing:
            if semantic_enabled_explicit is None:
                semantic_enabled_explicit = existing.semantic_enabled_explicit
            if semantic_enabled_effective is None:
                semantic_enabled_effective = existing.semantic_enabled_effective
            if semantic_model is None:
                semantic_model = existing.semantic_model

    # Use corpus_name as resource_id, or fallback to corpus_id, or generate
    if corpus_name:
        resource_id = corpus_name
    elif corpus_id:
        resource_id = str(corpus_id)
    else:
        resource_id = coolname.generate_slug(2)

    # Prepare metadata - handle enum values properly
    corpus_type_value = corpus_type.value if isinstance(corpus_type, CorpusType) else corpus_type
    language_value = language.value if isinstance(language, Language) else language

    default_semantic_effective = (
        semantic_enabled_effective
        if semantic_enabled_effective is not None
        else bool(semantic_enabled_explicit is True)
    )

    full_metadata = {
        "corpus_name": corpus_name or "",
        "corpus_type": corpus_type_value,
        "language": language_value,
        "parent_uuid": parent_uuid,  # Stable UUID string
        "child_uuids": child_uuids
        if child_uuids is not None
        else [],  # List of stable UUID strings
        "is_master": is_master if is_master is not None else False,  # Default to False if None
        "semantic_enabled_explicit": semantic_enabled_explicit,
        "semantic_enabled_effective": default_semantic_effective,
        "semantic_model": semantic_model,
        **(metadata or {}),
    }

    # Save using version manager
    saved = await vm.save(
        resource_id=resource_id,
        resource_type=ResourceType.CORPUS,  # Registry maps this to Corpus.Metadata
        namespace=CacheNamespace.CORPUS,
        content=content or {},
        config=config or VersionConfig(),
        metadata=full_metadata,
    )

    # Self-references already cleaned at line 171-174 before save
    # No need for redundant post-save cleanup that causes double-save race condition

    # Auto-update parent's child_uuids if parent_uuid is provided
    # BUT ONLY if we're creating a NEW corpus (not updating existing)
    # AND we're not explicitly managing child_uuids
    # AND caller hasn't opted out (skip_parent_update=True means caller manages parent-child links)
    if parent_uuid and saved and not corpus_id and not skip_parent_update and (child_uuids is None or not child_uuids):
        child_uuid = saved.uuid  # Use UUID string, not ObjectId
        if child_uuid and get_corpus_fn:
            # Get the full parent corpus via versioned path (not raw Beanie save)
            parent_corpus = await get_corpus_fn(
                corpus_uuid=parent_uuid,
                config=VersionConfig(use_cache=False),  # Fresh from DB
            )
            if parent_corpus and child_uuid not in parent_corpus.child_uuids:
                updated_children = parent_corpus.child_uuids.copy()
                updated_children.append(child_uuid)
                await save_corpus(
                    vm=vm,
                    corpus_id=parent_corpus.corpus_id,
                    corpus_name=parent_corpus.corpus_name,
                    content=parent_corpus.model_dump(mode="json"),
                    corpus_type=parent_corpus.corpus_type,
                    language=parent_corpus.language,
                    parent_uuid=parent_corpus.parent_uuid,
                    child_uuids=updated_children,
                    is_master=parent_corpus.is_master,
                    semantic_enabled_explicit=parent_corpus.semantic_enabled_explicit,
                    semantic_enabled_effective=parent_corpus.semantic_enabled_effective,
                    semantic_model=parent_corpus.semantic_model,
                )

                async def _save_for_semantic(**kwargs: Any) -> Corpus | None:
                    return await save_corpus(
                        vm=vm,
                        get_corpus_fn=get_corpus_fn,
                        **kwargs,
                    )

                await recompute_semantic_effective_upward(
                    start_corpus_uuid=parent_uuid,
                    get_corpus_fn=get_corpus_fn,
                    get_corpora_by_uuids_fn=None,
                    save_corpus_fn=_save_for_semantic,
                    config=VersionConfig(use_cache=False),
                )
                logger.debug(f"Auto-added new child UUID {child_uuid} to parent {parent_uuid}")

    # If we saved metadata, convert back to Corpus
    if saved:
        saved_content = await get_versioned_content(saved)
        if saved_content:
            # Merge metadata into content - use ENUM OBJECTS, not string values
            # This ensures Pydantic doesn't need to convert them
            saved_content.update(
                {
                    "corpus_name": corpus_name or "",
                    "corpus_type": corpus_type,  # Pass enum object, not string
                    "language": language,  # Pass enum object, not string
                    "parent_uuid": parent_uuid,
                    "child_uuids": child_uuids if child_uuids is not None else [],
                    "is_master": is_master if is_master is not None else False,
                    "semantic_enabled_explicit": saved.semantic_enabled_explicit,
                    "semantic_enabled_effective": saved.semantic_enabled_effective,
                    "semantic_model": saved.semantic_model,
                }
            )
            # Preserve original corpus_id if updating, otherwise use new ID
            if corpus_id:
                # We're updating an existing corpus, preserve its ID
                saved_content["corpus_id"] = corpus_id
            else:
                # New corpus, use the metadata document's ID
                saved_content["corpus_id"] = saved.id
            # CRITICAL: Copy uuid from metadata to content (guaranteed to exist via Pydantic validator)
            saved_content["corpus_uuid"] = saved.uuid
            # PATHOLOGICAL REMOVAL: No try/except - let validation errors propagate
            result = Corpus.model_validate(saved_content)
            logger.info(f"✅ Saved corpus '{resource_id}' with {len(result.vocabulary):,} words")
            return result
    logger.warning("save_corpus: saved_content is None, returning None")
    return None


async def get_corpus_metadata(corpus_name: str) -> Corpus.Metadata | None:
    """Retrieve corpus metadata by resource id.

    Args:
        corpus_name: Name of the corpus

    Returns:
        Corpus.Metadata or None

    """
    return await Corpus.Metadata.find_one({"resource_id": corpus_name})


async def get_stats() -> dict[str, Any]:
    """Return lightweight corpus statistics.

    Returns:
        Dictionary with total count and corpus names

    """
    metadatas = await Corpus.Metadata.find_all().to_list()
    return {
        "total": len(metadatas),
        "corpus_names": [meta.resource_id for meta in metadatas],
    }


async def get_corpus(
    vm: VersionedDataManager,
    corpus_id: PydanticObjectId | None = None,
    corpus_uuid: str | None = None,
    corpus_name: str | None = None,
    config: VersionConfig | None = None,
) -> Corpus | None:
    """Simple corpus retrieval by ID, uuid, or name - always returns latest version.

    Args:
        vm: Version manager instance
        corpus_id: Corpus MongoDB ObjectId
        corpus_uuid: Corpus stable UUID string
        corpus_name: Corpus name string
        config: Version configuration

    Returns:
        Corpus instance or None

    """
    # force_rebuild means bypass cache, not return None
    # The config will be passed down to version manager methods

    if corpus_id:
        # Get metadata to find resource_id, then get LATEST version
        temp_meta = await Corpus.Metadata.get(corpus_id)
        if not temp_meta:
            return None
        # Get the latest version using the resource_id
        metadata = await vm.get_latest(
            resource_id=temp_meta.resource_id,
            resource_type=ResourceType.CORPUS,
            use_cache=config.use_cache if config else False,
        )
    elif corpus_uuid:
        # When retrieving by uuid, find the metadata with that uuid
        metadata = await Corpus.Metadata.find_one(
            {"uuid": corpus_uuid, "version_info.is_latest": True}
        )
    elif corpus_name:
        # When retrieving by name, use version manager for latest
        metadata = await vm.get_latest(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
            use_cache=config.use_cache if config else False,
        )
    else:
        return None

    if not metadata:
        return None

    # Get content from versioned storage, respecting config.use_cache
    content = await get_versioned_content(metadata, config=config)
    if not content:
        content = {}

    # Ensure all required fields from metadata
    # Corpus-specific fields should come from metadata attributes, not content
    # Let Pydantic v2 handle enum conversion automatically during model_validate()
    content.update(
        {
            "corpus_id": metadata.id,
            "corpus_uuid": metadata.uuid,  # CRITICAL: Copy UUID (guaranteed to exist)
            "corpus_name": metadata.resource_id,
            "corpus_type": metadata.corpus_type,  # Pydantic v2 handles enum conversion
            "language": metadata.language,  # Pydantic v2 handles enum conversion
            "parent_uuid": metadata.parent_uuid,
            "child_uuids": metadata.child_uuids or [],
            "is_master": metadata.is_master,
            "semantic_enabled_explicit": metadata.semantic_enabled_explicit,
            "semantic_enabled_effective": metadata.semantic_enabled_effective,
            "semantic_model": metadata.semantic_model,
        }
    )

    # Clean self-references even when reading using extracted helper
    content["child_uuids"] = remove_self_references(
        content.get("child_uuids"), corpus_uuid=content.get("corpus_uuid")
    )

    # Handle vocabulary
    if "vocabulary" not in content:
        content["vocabulary"] = []

    logger.info(
        f"get_corpus: loaded corpus {corpus_id or corpus_name}, vocabulary size: {len(content.get('vocabulary', []))}"
    )

    # Ensure vocabulary_to_index is built if we have vocabulary
    if content.get("vocabulary") and not content.get("vocabulary_to_index"):
        content["vocabulary_to_index"] = {
            word: idx for idx, word in enumerate(content["vocabulary"])
        }

    # Ensure lemmatization indices exist (needed for semantic search)
    if content.get("vocabulary") and not content.get("lemmatized_vocabulary"):
        logger.info(f"Rebuilding lemmatization for loaded corpus {corpus_name or corpus_id}")
        # Pydantic v2 model_validate() handles both enum objects and strings automatically
        corpus_obj = Corpus.model_validate(content)
        await corpus_obj._create_unified_indices()
        # Update content with rebuilt indices
        content["lemmatized_vocabulary"] = corpus_obj.lemmatized_vocabulary
        content["word_to_lemma_indices"] = corpus_obj.word_to_lemma_indices
        content["lemma_to_word_indices"] = corpus_obj.lemma_to_word_indices

    # Ensure version info - convert to dict for Pydantic validation
    if metadata.version_info:
        content["version_info"] = metadata.version_info.model_dump(mode="json")

    # Create and return the Corpus
    return Corpus.model_validate(content)


async def get_corpora_by_ids(
    vm: VersionedDataManager,
    corpus_ids: list[PydanticObjectId],
    config: VersionConfig | None = None,
) -> list[Corpus]:
    """Get multiple corpora by their IDs in batch.

    Args:
        vm: Version manager instance
        corpus_ids: List of corpus IDs to retrieve
        config: Version configuration

    Returns:
        List of Corpus instances (may be shorter than input if some IDs don't exist)

    """
    if not corpus_ids:
        return []

    # Get metadata for all corpus IDs
    metadatas = await Corpus.Metadata.find_many(
        {"_id": {"$in": corpus_ids}},
    ).to_list()

    if not metadatas:
        return []

    # Convert each metadata to Corpus
    # PATHOLOGICAL REMOVAL: No try/except - let errors propagate
    corpora = []
    for metadata in metadatas:
        # Get versioned content for each metadata, respecting config.use_cache
        content = await get_versioned_content(metadata, config=config)
        if content:
            # Add the ID from metadata
            content["corpus_id"] = metadata.id
            # Extract corpus-specific fields from metadata object
            # Let Pydantic v2 handle enum conversion automatically
            content["child_uuids"] = metadata.child_uuids
            content["parent_uuid"] = metadata.parent_uuid
            content["is_master"] = metadata.is_master
            content["corpus_name"] = metadata.corpus_name
            content["corpus_type"] = metadata.corpus_type  # Pydantic v2 handles enum conversion
            content["language"] = metadata.language  # Pydantic v2 handles enum conversion
            content["semantic_enabled_explicit"] = metadata.semantic_enabled_explicit
            content["semantic_enabled_effective"] = metadata.semantic_enabled_effective
            content["semantic_model"] = metadata.semantic_model
            # Add version information
            if metadata.version_info:
                content["version_info"] = metadata.version_info
                content["_metadata_id"] = metadata.id

            corpus_obj = Corpus.model_validate(content)
            # Rebuild indices if needed
            if corpus_obj.vocabulary and not corpus_obj.vocabulary_to_index:
                await corpus_obj._rebuild_indices()
            corpora.append(corpus_obj)

    return corpora


async def get_corpora_by_uuids(
    vm: VersionedDataManager,
    corpus_uuids: list[str],
    config: VersionConfig | None = None,
) -> list[Corpus]:
    """Get multiple corpora by their UUIDs in batch (CRITICAL N+1 FIX).

    This method eliminates N+1 query anti-pattern by batch-fetching all
    child corpora in a single MongoDB query instead of one query per child.

    Args:
        vm: Version manager instance
        corpus_uuids: List of corpus UUIDs to retrieve
        config: Version configuration

    Returns:
        List of Corpus instances (may be shorter than input if some UUIDs don't exist)

    """
    if not corpus_uuids:
        return []

    # CRITICAL FIX: Single batch query for all UUIDs instead of N separate queries
    metadatas = await Corpus.Metadata.find(
        {"uuid": {"$in": corpus_uuids}, "version_info.is_latest": True}
    ).to_list()

    if not metadatas:
        return []

    # Convert each metadata to Corpus using the same logic as get_corpora_by_ids
    # PATHOLOGICAL REMOVAL: No try/except - let errors propagate
    corpora = []
    for metadata in metadatas:
        # Get versioned content, respecting config.use_cache
        content = await get_versioned_content(metadata, config=config)
        if content:
            content["corpus_id"] = metadata.id
            content["corpus_uuid"] = metadata.uuid
            content["child_uuids"] = metadata.child_uuids
            content["parent_uuid"] = metadata.parent_uuid
            content["is_master"] = metadata.is_master
            content["corpus_name"] = metadata.corpus_name
            content["corpus_type"] = metadata.corpus_type
            content["language"] = metadata.language
            content["semantic_enabled_explicit"] = metadata.semantic_enabled_explicit
            content["semantic_enabled_effective"] = metadata.semantic_enabled_effective
            content["semantic_model"] = metadata.semantic_model

            if metadata.version_info:
                content["version_info"] = metadata.version_info
                content["_metadata_id"] = metadata.id

            corpus_obj = Corpus.model_validate(content)
            if corpus_obj.vocabulary and not corpus_obj.vocabulary_to_index:
                await corpus_obj._rebuild_indices()
            corpora.append(corpus_obj)

    return corpora


__all__ = [
    "get_corpora_by_ids",
    "get_corpora_by_uuids",
    "get_corpus",
    "get_corpus_metadata",
    "get_stats",
    "remove_self_references",
    "save_corpus",
    "save_corpus_simple",
    "save_metadata",
]

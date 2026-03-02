"""Corpus tree structure operations: create, get, update parent, add/remove child, delete, invalidate.

Standalone async functions for managing hierarchical corpus trees.
Receives needed parameters from the TreeCorpusManager caller.
"""

from __future__ import annotations

import asyncio
from typing import Any

import coolname
from beanie import PydanticObjectId

from ..caching.core import get_global_cache
from ..caching.manager import VersionedDataManager
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..models.base import Language
from ..utils.logging import get_logger
from .core import Corpus
from .models import CorpusType

logger = get_logger(__name__)


async def create_tree(
    vm: VersionedDataManager,
    master_id: PydanticObjectId | None = None,
    master_name: str | None = None,
    children: list[dict[str, Any]] | None = None,
    config: VersionConfig | None = None,
    save_corpus_fn: Any = None,
) -> Corpus | None:
    """Create a hierarchical corpus tree.

    Args:
        vm: Version manager instance
        master_id: Master corpus ID (preferred)
        master_name: Master corpus name (will generate if not provided)
        children: List of child corpus definitions
        config: Version configuration
        save_corpus_fn: Callable to save a corpus

    Returns:
        Master Corpus instance

    """
    # Generate name if not provided
    if not master_name and not master_id:
        master_name = coolname.generate_slug(2) + "_master"

    # Create master corpus
    master = await save_corpus_fn(
        corpus_id=master_id,
        corpus_name=master_name,
        content={
            "corpus_name": master_name or "",
            "vocabulary": [],
            "is_master": True,
        },
        is_master=True,
        config=config,
    )

    if not master or not master.corpus_id:
        return None

    # Create child corpora
    child_ids = []
    for child_def in children or []:
        child_name = child_def.get("name", "")
        if not child_name:
            child_name = coolname.generate_slug(2) + "_child"

        child = await save_corpus_fn(
            corpus_name=child_name,
            content=child_def.get("content", {}),
            corpus_type=child_def.get("corpus_type", CorpusType.LEXICON),
            language=child_def.get("language", Language.ENGLISH),
            parent_uuid=master.corpus_uuid,
            config=config,
            metadata=child_def.get("metadata"),
        )
        if child and child.corpus_uuid:
            child_ids.append(child.corpus_uuid)

    # Update master with child references
    if child_ids:
        # Master is now a Corpus object, use model_dump to get content
        master_content = master.model_dump(mode="json") if master else {}
        master_content["child_uuids"] = child_ids

        await save_corpus_fn(
            corpus_id=master.corpus_id,
            corpus_name=master.corpus_name,
            content=master_content,
            child_uuids=child_ids,
            is_master=True,
            config=config,
        )

    return master


async def get_tree(
    vm: VersionedDataManager,
    corpus_id: PydanticObjectId,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
) -> dict[str, Any] | None:
    """Get the tree structure of a corpus and its descendants.

    Args:
        vm: Version manager instance
        corpus_id: Corpus ID
        config: Version configuration
        get_corpus_fn: Callable to get a corpus

    Returns:
        Dictionary representation of the tree

    """
    corpus = await get_corpus_fn(corpus_id=corpus_id, config=config)
    if not corpus:
        return None

    tree = corpus.model_dump(mode="json")
    tree["children"] = []

    # Safely iterate over children, handling potential None values
    if corpus.child_uuids:
        for child_uuid in corpus.child_uuids:
            # For uuids, need to get corpus first to get its corpus_id
            child = await get_corpus_fn(corpus_uuid=child_uuid, config=config)
            if child and child.corpus_id:
                child_tree = await get_tree(
                    vm=vm,
                    corpus_id=child.corpus_id,
                    config=config,
                    get_corpus_fn=get_corpus_fn,
                )
                if child_tree:
                    tree["children"].append(child_tree)

    return tree


async def update_parent(
    vm: VersionedDataManager,
    parent_id: PydanticObjectId | Any,
    child_id: PydanticObjectId | Any,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    save_corpus_fn: Any = None,
    would_create_cycle_fn: Any = None,
) -> bool | None:
    """Simple tree operation: add child to parent.

    Args:
        vm: Version manager instance
        parent_id: Parent corpus ID or object with 'id' or 'corpus_id' attribute
        child_id: Child corpus ID or object with 'id' or 'corpus_id' attribute
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        save_corpus_fn: Callable to save a corpus
        would_create_cycle_fn: Callable to check for cycles

    Returns:
        True if successful, False if prevented, None if invalid

    """
    # Extract IDs from objects if needed (common pattern when passing Corpus objects)
    if isinstance(parent_id, Corpus):
        parent_id = parent_id.corpus_id or parent_id.corpus_uuid
    if isinstance(child_id, Corpus):
        child_id = child_id.corpus_id or child_id.corpus_uuid

    # Convert to PydanticObjectId if needed
    if not isinstance(parent_id, PydanticObjectId):
        parent_id = PydanticObjectId(str(parent_id))
    if not isinstance(child_id, PydanticObjectId):
        child_id = PydanticObjectId(str(child_id))

    # Prevent self-reference
    if parent_id == child_id:
        logger.warning(f"Cannot add corpus as its own child: {parent_id}")
        return False

    # Check for cycles
    if await would_create_cycle_fn(parent_id, child_id, config):
        logger.warning(f"Would create cycle: {child_id} -> {parent_id}")
        return False

    # Get both corpora using get_corpus for consistency
    parent = await get_corpus_fn(corpus_id=parent_id, config=config)
    child = await get_corpus_fn(corpus_id=child_id, config=config)

    logger.info(f"update_parent: parent={parent is not None}, child={child is not None}")

    if not parent or not child:
        logger.warning("update_parent failed: parent or child not found")
        return False

    # Update parent's children list via save_corpus to maintain versioning
    parent_updated = False
    if child.corpus_uuid not in parent.child_uuids:
        logger.info(f"Adding child UUID {child.corpus_uuid} (ID: {child_id}) to parent {parent_id}")
        # Add child's UUID to parent's list (NOT the corpus_id!)
        updated_children = parent.child_uuids.copy()
        updated_children.append(child.corpus_uuid)
        # Save through save_corpus to create new version - MUST preserve all corpus fields!
        await save_corpus_fn(
            corpus_id=parent_id,
            corpus_name=parent.corpus_name,
            content=parent.model_dump(mode="json"),
            corpus_type=parent.corpus_type,  # CRITICAL: preserve corpus type
            language=parent.language,  # CRITICAL: preserve language
            parent_uuid=parent.parent_uuid,  # preserve parent
            child_uuids=updated_children,
            is_master=parent.is_master,  # preserve master status
            config=config,
        )
        parent_updated = True
        logger.info(f"Parent updated with children: {updated_children}")
    else:
        logger.info(f"Child {child_id} already in parent {parent_id}")

    # Update child's parent reference via save_corpus to maintain versioning
    child_updated = False
    # BUG FIX: Compare UUID strings, not UUID with ObjectId
    # child.parent_uuid is str, parent.corpus_uuid is str (compatible types)
    if child.parent_uuid != parent.corpus_uuid:
        logger.info(
            f"Setting parent UUID {parent.corpus_uuid} (ID: {parent_id}) for child {child_id}"
        )
        # Save through save_corpus to create new version - MUST preserve all corpus fields!
        await save_corpus_fn(
            corpus_id=child_id,
            corpus_name=child.corpus_name,
            content=child.model_dump(mode="json"),
            corpus_type=child.corpus_type,  # CRITICAL: preserve corpus type
            language=child.language,  # CRITICAL: preserve language
            parent_uuid=parent.corpus_uuid,  # Use UUID, not corpus_id!
            child_uuids=child.child_uuids,  # preserve children
            is_master=child.is_master,  # preserve master status
            config=config,
        )
        child_updated = True
        logger.info(f"Child updated with parent UUID: {parent.corpus_uuid}")
    else:
        logger.info(f"Child already has parent UUID {parent.corpus_uuid}")

    return parent_updated or child_updated


async def add_child(
    vm: VersionedDataManager,
    parent: Corpus,
    child: Corpus,
    config: VersionConfig | None = None,
    update_parent_fn: Any = None,
) -> bool:
    """Add a child to a parent corpus.

    Args:
        vm: Version manager instance
        parent: Parent corpus
        child: Child corpus to add
        config: Version configuration
        update_parent_fn: Callable for the update_parent operation

    Returns:
        True if added successfully

    """
    if parent.corpus_id and child.corpus_id:
        result = await update_parent_fn(parent.corpus_id, child.corpus_id, config)
        return result if result is not None else False
    return False


async def delete_corpus(
    vm: VersionedDataManager,
    corpus_id: PydanticObjectId | None = None,
    corpus_uuid: str | None = None,
    corpus_name: str | None = None,
    cascade: bool = False,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    remove_child_fn: Any = None,
) -> bool:
    """Delete a corpus and optionally its children.

    Args:
        vm: Version manager instance
        corpus_id: Corpus ID (preferred)
        corpus_uuid: Corpus UUID (stable identifier)
        corpus_name: Corpus name (fallback)
        cascade: Whether to delete child corpora
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        remove_child_fn: Callable to remove a child from parent

    Returns:
        True if deleted successfully

    """
    corpus = await get_corpus_fn(
        corpus_id=corpus_id, corpus_uuid=corpus_uuid, corpus_name=corpus_name, config=config
    )
    if not corpus or not corpus.corpus_id:
        return False

    # Handle cascade deletion
    if cascade and corpus.child_uuids:
        # Make a copy to avoid modification during iteration and handle potential None values
        children_to_delete = list(corpus.child_uuids) if corpus.child_uuids else []
        for child_uuid_str in children_to_delete:
            # child_uuids contains UUID strings, need to use corpus_uuid parameter
            await delete_corpus(
                vm=vm,
                corpus_uuid=child_uuid_str,
                cascade=True,
                config=config,
                get_corpus_fn=get_corpus_fn,
                remove_child_fn=remove_child_fn,
            )

    # Remove from parent if it has one
    if corpus.parent_uuid and corpus.corpus_id:
        # Get parent corpus to get its corpus_id
        parent = await get_corpus_fn(corpus_uuid=corpus.parent_uuid, config=config)
        if parent and parent.corpus_id:
            await remove_child_fn(
                parent_id=parent.corpus_id,
                child_id=corpus.corpus_id,
                delete_child=False,
                config=config,
            )

    # Store the corpus name and id before deletion
    corpus_name_to_clear = corpus.corpus_name
    corpus_id_to_delete = corpus.corpus_id

    # Delete associated search indices
    if corpus_id_to_delete:
        from ..search.search_index import SearchIndex
        from ..search.semantic.models import SemanticIndex
        from ..search.trie_index import TrieIndex

        # Delete all versioned metadata for this corpus
        # These are stored in BaseVersionedData collection
        await asyncio.gather(
            # Delete TrieIndex metadata
            TrieIndex.Metadata.find({"corpus_id": corpus_id_to_delete}).delete(),
            # Delete SearchIndex metadata
            SearchIndex.Metadata.find({"corpus_id": corpus_id_to_delete}).delete(),
            # Delete SemanticIndex metadata
            SemanticIndex.Metadata.find({"corpus_id": corpus_id_to_delete}).delete(),
            return_exceptions=True,
        )
        logger.info(f"Deleted search indices for corpus {corpus_name_to_clear}")

    # Delete ALL metadata documents with the same UUID from MongoDB
    # Versioning creates multiple documents per corpus, so we delete all versions
    if corpus.corpus_uuid:
        # Delete all documents with this UUID (all versions)
        result = await Corpus.Metadata.find({"uuid": corpus.corpus_uuid}).delete()
        logger.info(
            f"Deleted all versions of corpus {corpus_name_to_clear} (UUID: {corpus.corpus_uuid}, {result.deleted_count if result else 0} documents)"
        )

    # Note: corpus.delete() would fail because Corpus is not a Document
    # The metadata deletion above handles the actual removal

    # Clear cache entries for this corpus
    if corpus_name_to_clear:
        cache = await get_global_cache()

        # Clear the general cache key for this resource
        general_cache_key = f"{ResourceType.CORPUS.value}:{corpus_name_to_clear}"
        await cache.delete(CacheNamespace.CORPUS, general_cache_key)

    return True


async def invalidate_corpus(
    vm: VersionedDataManager,
    corpus_name: str,
) -> bool:
    """Invalidate a specific corpus and all related caches.

    Args:
        vm: Version manager instance
        corpus_name: Name of the corpus to invalidate

    Returns:
        True if invalidation succeeded

    """
    # PATHOLOGICAL REMOVAL: No try/except - let errors propagate
    # Clear cache entries for this corpus

    cache = await get_global_cache()

    # Clear the main corpus cache key
    cache_key = f"{ResourceType.CORPUS.value}:{corpus_name}"
    await cache.delete(CacheNamespace.CORPUS, cache_key)

    # Clear any versioned cache entries
    # Find all versions and clear their cache entries
    latest = await vm.get_latest(
        resource_id=corpus_name,
        resource_type=ResourceType.CORPUS,
    )

    if latest and latest.version_info:
        versioned_key = f"{ResourceType.CORPUS.value}:{corpus_name}:v{latest.version_info.version}"
        await cache.delete(CacheNamespace.CORPUS, versioned_key)

    # Note: Search indexes are not stored as Documents in MongoDB,
    # they are cached in memory or as serialized files.
    # For now, we just clear the corpus cache.

    return True


async def invalidate_all_corpora(
    vm: VersionedDataManager,
) -> int:
    """Invalidate all corpora and related caches.

    Args:
        vm: Version manager instance

    Returns:
        Number of corpora invalidated

    """
    # PATHOLOGICAL REMOVAL: No try/except - let errors propagate
    # Get all corpus metadata
    all_corpora = await Corpus.Metadata.find_all().to_list()

    count = 0
    for corpus_meta in all_corpora:
        if await invalidate_corpus(vm=vm, corpus_name=corpus_meta.resource_id):
            count += 1

    # Clear the entire corpus namespace as well

    cache = await get_global_cache()
    await cache.clear_namespace(CacheNamespace.CORPUS)

    return count


async def would_create_cycle(
    vm: VersionedDataManager,
    parent_id: PydanticObjectId,
    child_id: PydanticObjectId,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
) -> bool:
    """Simple cycle detection: walk up from parent to see if we hit child.

    Args:
        vm: Version manager instance
        parent_id: Parent corpus ID
        child_id: Child corpus ID being added
        config: Version configuration
        get_corpus_fn: Callable to get a corpus

    Returns:
        True if adding child would create a cycle

    """
    current: PydanticObjectId | None = parent_id
    visited = set()

    while current:
        if current == child_id:
            return True  # Found cycle

        if current in visited:
            break  # Existing cycle, stop

        visited.add(current)

        # Get parent of current
        corpus = await get_corpus_fn(corpus_id=current, config=config)
        # Get parent UUID and convert to corpus_id for next iteration
        if corpus and corpus.parent_uuid:
            parent_corpus = await get_corpus_fn(corpus_uuid=corpus.parent_uuid, config=config)
            current = parent_corpus.corpus_id if parent_corpus else None
        else:
            current = None

    return False


async def get_children(
    vm: VersionedDataManager,
    parent_id: PydanticObjectId,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    get_corpora_by_uuids_fn: Any = None,
) -> list[Corpus]:
    """Get all child corpora of a parent (N+1 QUERY FIX).

    Args:
        vm: Version manager instance
        parent_id: Parent corpus ID
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        get_corpora_by_uuids_fn: Callable to batch-fetch corpora by UUIDs

    Returns:
        List of child Corpus objects

    """
    parent = await get_corpus_fn(corpus_id=parent_id, config=config)
    if not parent:
        return []

    # CRITICAL FIX: Batch-fetch all children in single query instead of N separate queries
    if parent.child_uuids:
        return await get_corpora_by_uuids_fn(parent.child_uuids, config)

    return []


async def remove_child(
    vm: VersionedDataManager,
    parent_id: PydanticObjectId,
    child_id: PydanticObjectId,
    delete_child: bool = False,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    save_corpus_fn: Any = None,
    delete_corpus_fn: Any = None,
) -> bool:
    """Simple tree operation: remove child from parent.

    Args:
        vm: Version manager instance
        parent_id: Parent corpus ID
        child_id: Child corpus ID to remove
        delete_child: Whether to delete the child corpus
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        save_corpus_fn: Callable to save a corpus
        delete_corpus_fn: Callable to delete a corpus

    Returns:
        True if removal succeeded

    """
    # Force fresh read to avoid stale data
    fresh_config = config or VersionConfig()
    fresh_config.use_cache = False

    # Get parent using get_corpus for consistency with version manager
    parent = await get_corpus_fn(corpus_id=parent_id, config=fresh_config)
    if not parent:
        logger.warning(f"Parent {parent_id} not found in remove_child")
        return False

    # Log current state
    logger.info(f"Parent {parent_id} currently has children: {parent.child_uuids}")

    # Get child corpus to get its UUID
    child = await get_corpus_fn(corpus_id=child_id, config=fresh_config)
    if not child or not child.corpus_uuid:
        logger.warning(f"Child {child_id} not found or missing UUID")
        return False

    # Remove from parent's children list (compare UUIDs)
    removed = False
    if child.corpus_uuid in parent.child_uuids:
        logger.info(
            f"Removing child UUID {child.corpus_uuid} (ID: {child_id}) from parent {parent_id} children list"
        )
        parent.child_uuids.remove(child.corpus_uuid)
        removed = True
    else:
        logger.warning(f"Child UUID {child.corpus_uuid} not in parent's children list")

    # Save parent with updated children list via save_corpus for versioning
    if removed or delete_child:
        logger.info(f"Updating parent with children: {parent.child_uuids}")
        # Save through save_corpus to create new version
        saved_parent = await save_corpus_fn(
            corpus_id=parent.corpus_id,
            corpus_name=parent.corpus_name,
            content=parent.model_dump(mode="json"),
            child_uuids=parent.child_uuids,
            parent_uuid=parent.parent_uuid,
            is_master=parent.is_master,
            corpus_type=parent.corpus_type,
            language=parent.language,
            config=fresh_config,
        )
        logger.info(
            f"Parent saved with updated children: saved has {len(saved_parent.child_uuids) if saved_parent else 'None'} children"
        )

    # Clear child's parent reference via save_corpus for versioning (unless deleting)
    if not delete_child:
        # child was already fetched above, check if it has parent reference
        if child and child.parent_uuid == parent.corpus_uuid:
            child.parent_uuid = None
            await save_corpus_fn(
                corpus_id=child.corpus_id,
                corpus_name=child.corpus_name,
                content=child.model_dump(mode="json"),
                child_uuids=child.child_uuids,
                parent_uuid=None,
                is_master=child.is_master,
                corpus_type=child.corpus_type,
                language=child.language,
                config=fresh_config,
            )
            logger.info(f"Cleared parent reference from child {child_id}")
    elif delete_child:
        logger.info(f"Deleting child corpus {child_id}")
        # Delete the child corpus
        await delete_corpus_fn(corpus_id=child_id, cascade=False, config=fresh_config)

    return True


__all__ = [
    "add_child",
    "create_tree",
    "delete_corpus",
    "get_children",
    "get_tree",
    "invalidate_all_corpora",
    "invalidate_corpus",
    "remove_child",
    "update_parent",
    "would_create_cycle",
]

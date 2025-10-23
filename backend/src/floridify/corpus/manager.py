from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import coolname
from beanie import PydanticObjectId

from ..caching.core import get_global_cache, get_versioned_content
from ..caching.manager import get_version_manager
from ..caching.models import BaseVersionedData, CacheNamespace, ResourceType, VersionConfig
from ..models.base import Language
from ..utils.logging import get_logger
from .core import Corpus
from .models import CorpusType

logger = get_logger(__name__)

if TYPE_CHECKING:
    from ..caching.manager import VersionedDataManager


class TreeCorpusManager:
    """Manager for hierarchical corpus structures with vocabulary aggregation."""

    def __init__(self, vm: VersionedDataManager | None = None) -> None:
        """Initialize with optional version manager.

        Args:
            vm: Version manager instance or None to use default

        """
        if vm is not None:
            self.vm = vm
        else:
            self.vm = get_version_manager()

    @staticmethod
    def _remove_self_references(
        corpus_id: PydanticObjectId | str | None,
        child_uuids: list[str] | None,
        corpus_uuid: str | None = None,
    ) -> list[str]:
        """Remove self-references from child_uuids list.

        CRITICAL FIX: Extracted helper to prevent corpus cycles and data corruption.
        Self-references occur when a corpus appears in its own child list,
        which breaks tree traversal and aggregation logic.

        Args:
            corpus_id: The corpus ID (ObjectId) - DEPRECATED, use corpus_uuid
            child_uuids: List of child UUIDs (strings)
            corpus_uuid: The corpus UUID (string) - PREFERRED for comparison

        Returns:
            Filtered list with self-reference removed, or original list if no self-reference

        """
        if not child_uuids:
            return []

        # PATHOLOGICAL REMOVAL: No fallbacks - only use corpus_uuid
        # corpus_id is ObjectId which will NEVER match UUID strings
        if corpus_uuid and corpus_uuid in child_uuids:
            logger.warning(f"Removing self-reference from child_uuids: {corpus_uuid}")
            return [cid for cid in child_uuids if cid != corpus_uuid]

        # NO FALLBACK - if no corpus_uuid provided, don't try to guess
        return child_uuids

    async def save_corpus_simple(
        self,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Simplified save that focuses on tree structure."""
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

        # Store content
        content = corpus.model_dump(mode="json")
        metadata.content = content

        # Save to MongoDB
        await metadata.save()
        corpus.corpus_id = metadata.id

        return corpus

    async def save_metadata(self, metadata: Corpus.Metadata) -> Corpus.Metadata:
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
        metadata.child_uuids = self._remove_self_references(metadata.uuid, metadata.child_uuids)

        await metadata.save()
        return metadata

    async def save_corpus(
        self,
        corpus: Corpus | None = None,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        content: dict[str, Any] | None = None,
        corpus_type: CorpusType = CorpusType.LEXICON,
        language: Language = Language.ENGLISH,
        parent_uuid: str | None = None,
        child_uuids: list[str] | None = None,
        is_master: bool | None = None,
        config: VersionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Corpus | None:
        """Save a corpus - ONLY saves data, does NOT manage relationships.

        This is a pure data persistence operation. Use update_parent() to manage
        parent-child relationships separately.

        Args:
            corpus: Corpus object to save (MUST be Corpus, not Metadata)
            corpus_id: Existing corpus ID for updates
            corpus_name: Corpus name (optional, will be generated if not provided)
            content: Corpus content (vocabulary, etc.)
            corpus_type: Type of corpus
            language: Language of the corpus
            parent_uuid: Parent corpus uuid (saved as data only)
            child_uuids: Child corpus uuids (saved as data only)
            is_master: Whether this is a master corpus
            config: Version configuration
            metadata: Additional metadata

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
            logger.debug(
                f"save_corpus: corpus has {len(corpus.child_uuids) if corpus.child_uuids else 0} children, using {len(child_uuids) if child_uuids else 0} children"
            )
            # Preserve is_master flag: use explicit value if provided, otherwise get from corpus
            # PATHOLOGICAL REMOVAL: No getattr - direct attribute access only
            is_master = (
                is_master
                if is_master is not None
                else (corpus.is_master if corpus else False)
            )

            # Clean self-references from child_uuids immediately using extracted helper
            # PATHOLOGICAL FIX: Use corpus_uuid if available from existing corpus
            corpus_uuid_for_clean = None
            if corpus and corpus.corpus_uuid:
                corpus_uuid_for_clean = corpus.corpus_uuid
            # NO FALLBACK - removed reference to undefined 'existing'

            child_uuids = self._remove_self_references(
                corpus_id, child_uuids, corpus_uuid=corpus_uuid_for_clean
            )

        # Generate name if not provided
        if not corpus_name and not corpus_id:
            corpus_name = coolname.generate_slug(2)

        # If we have a corpus_id, try to get the existing corpus first
        existing = None
        if corpus_id:
            existing = await Corpus.Metadata.get(corpus_id)
            if existing and not corpus_name:
                corpus_name = existing.resource_id  # Use existing name

        # Use corpus_name as resource_id, or fallback to corpus_id, or generate
        if corpus_name:
            resource_id = corpus_name
        elif corpus_id:
            resource_id = str(corpus_id)
        else:
            resource_id = coolname.generate_slug(2)

        # Prepare metadata - handle enum values properly
        corpus_type_value = (
            corpus_type.value if isinstance(corpus_type, CorpusType) else corpus_type
        )
        language_value = language.value if isinstance(language, Language) else language

        full_metadata = {
            "corpus_name": corpus_name or "",
            "corpus_type": corpus_type_value,
            "language": language_value,
            "parent_uuid": parent_uuid,  # Stable UUID string
            "child_uuids": child_uuids
            if child_uuids is not None
            else [],  # List of stable UUID strings
            "is_master": is_master if is_master is not None else False,  # Default to False if None
            **(metadata or {}),
        }

        # Save using version manager
        saved = await self.vm.save(
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
        if parent_uuid and saved and not corpus_id and (child_uuids is None or not child_uuids):
            child_uuid = saved.uuid  # Use UUID string, not ObjectId
            if child_uuid:
                # Get the parent using UUID (correct way)
                parent_meta = await Corpus.Metadata.find_one({"uuid": parent_uuid})
                if parent_meta and child_uuid not in parent_meta.child_uuids:
                    # This is a new child being created with a parent reference
                    # child_uuids contains UUID strings, not ObjectIds
                    parent_meta.child_uuids.append(child_uuid)
                    await parent_meta.save()
                    logger.debug(f"Auto-added new child UUID {child_uuid} to parent {parent_uuid}")

        # If we saved metadata, convert back to Corpus
        if saved:
            saved_content = await get_versioned_content(saved)
            if saved_content:
                # Merge metadata into content - use ENUM OBJECTS, not string values
                # This ensures Pydantic doesn't need to convert them
                saved_content.update({
                    "corpus_name": corpus_name or "",
                    "corpus_type": corpus_type,  # Pass enum object, not string
                    "language": language,  # Pass enum object, not string
                    "parent_uuid": parent_uuid,
                    "child_uuids": child_uuids if child_uuids is not None else [],
                    "is_master": is_master if is_master is not None else False,
                })
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

    async def create_corpus(
        self,
        corpus_name: str,
        vocabulary: list[str],
        *,
        language: Language = Language.ENGLISH,
        config: VersionConfig | None = None,
    ) -> Corpus:
        """Backwards compatible corpus creation helper."""
        corpus = await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            language=language,
        )
        saved = await self.save_corpus(corpus=corpus, config=config)
        if not saved:
            raise ValueError(f"Failed to save corpus '{corpus_name}'")
        return saved

    async def get_corpus_metadata(self, corpus_name: str) -> Corpus.Metadata | None:
        """Retrieve corpus metadata by resource id."""
        return await Corpus.Metadata.find_one({"resource_id": corpus_name})

    async def get_stats(self) -> dict[str, Any]:
        """Return lightweight corpus statistics for compatibility."""
        metadatas = await Corpus.Metadata.find_all().to_list()
        return {
            "total": len(metadatas),
            "corpus_names": [meta.resource_id for meta in metadatas],
        }

    async def get_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Simple corpus retrieval by ID, uuid, or name - always returns latest version."""
        # force_rebuild means bypass cache, not return None
        # The config will be passed down to version manager methods

        if corpus_id:
            # Get metadata to find resource_id, then get LATEST version
            temp_meta = await Corpus.Metadata.get(corpus_id)
            if not temp_meta:
                return None
            # Get the latest version using the resource_id
            metadata = await self.vm.get_latest(
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
            metadata = await self.vm.get_latest(
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
            }
        )

        # Clean self-references even when reading using extracted helper
        # PATHOLOGICAL FIX: Use corpus_uuid (which we just set above), not corpus_id
        content["child_uuids"] = self._remove_self_references(
            content.get("corpus_id"), content.get("child_uuids"), corpus_uuid=content.get("corpus_uuid")
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
            corpus = Corpus.model_validate(content)
            await corpus._create_unified_indices()
            # Update content with rebuilt indices
            content["lemmatized_vocabulary"] = corpus.lemmatized_vocabulary
            content["word_to_lemma_indices"] = corpus.word_to_lemma_indices
            content["lemma_to_word_indices"] = corpus.lemma_to_word_indices

        # Ensure version info - convert to dict for Pydantic validation
        if metadata.version_info:
            content["version_info"] = metadata.version_info.model_dump(mode="json")

        # Create and return the Corpus
        return Corpus.model_validate(content)

    async def get_corpora_by_ids(
        self,
        corpus_ids: list[PydanticObjectId],
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get multiple corpora by their IDs in batch.

        Args:
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
                # Add version information
                if metadata.version_info:
                    content["version_info"] = metadata.version_info
                    content["_metadata_id"] = metadata.id

                corpus = Corpus.model_validate(content)
                # Rebuild indices if needed
                if corpus.vocabulary and not corpus.vocabulary_to_index:
                    await corpus._rebuild_indices()
                corpora.append(corpus)

        return corpora

    async def get_corpora_by_uuids(
        self,
        corpus_uuids: list[str],
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get multiple corpora by their UUIDs in batch (CRITICAL N+1 FIX).

        This method eliminates N+1 query anti-pattern by batch-fetching all
        child corpora in a single MongoDB query instead of one query per child.

        Args:
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

                if metadata.version_info:
                    content["version_info"] = metadata.version_info
                    content["_metadata_id"] = metadata.id

                corpus = Corpus.model_validate(content)
                if corpus.vocabulary and not corpus.vocabulary_to_index:
                    await corpus._rebuild_indices()
                corpora.append(corpus)

        return corpora

    async def create_tree(
        self,
        master_id: PydanticObjectId | None = None,
        master_name: str | None = None,
        children: list[dict[str, Any]] | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Create a hierarchical corpus tree.

        Args:
            master_id: Master corpus ID (preferred)
            master_name: Master corpus name (will generate if not provided)
            children: List of child corpus definitions
            config: Version configuration

        Returns:
            Master Corpus instance

        """
        # Generate name if not provided
        if not master_name and not master_id:
            master_name = coolname.generate_slug(2) + "_master"

        # Create master corpus
        master = await self.save_corpus(
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

            child = await self.save_corpus(
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

            await self.save_corpus(
                corpus_id=master.corpus_id,
                corpus_name=master.corpus_name,
                content=master_content,
                child_uuids=child_ids,
                is_master=True,
                config=config,
            )

        return master

    async def aggregate_vocabularies(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        config: VersionConfig | None = None,
        update_parent: bool = True,
    ) -> list[str]:
        """Aggregate vocabularies from a corpus and its children.

        Args:
            corpus_id: Corpus MongoDB ID to aggregate from (deprecated, use corpus_uuid)
            corpus_uuid: Corpus stable UUID to aggregate from (preferred)
            config: Version configuration
            update_parent: Whether to update the parent corpus with aggregated vocabulary

        Returns:
            Aggregated vocabulary list

        """
        logger.info(
            f"aggregate_vocabularies: ENTER with corpus_id={corpus_id}, corpus_uuid={corpus_uuid}"
        )
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_uuid=corpus_uuid, config=config)
        logger.info(
            f"aggregate_vocabularies: get_corpus returned corpus: {corpus is not None}, uuid={corpus.corpus_uuid if corpus else None}"
        )
        if not corpus:
            logger.warning("aggregate_vocabularies: corpus is None, returning empty list")
            return []

        # For master corpora, only aggregate children's vocabularies
        # Don't include the parent's own vocabulary since it's just an aggregate container
        vocabulary: set[str] = set()

        # Get child vocabularies recursively in parallel
        child_ids = corpus.child_uuids or []
        if child_ids:

            # Fetch all child vocabularies concurrently
            child_vocabs = await asyncio.gather(
                *[
                    self.aggregate_vocabularies(corpus_uuid=cid, config=config, update_parent=False)
                    for cid in child_ids
                ],
                return_exceptions=True,
            )
            # Merge successful vocabularies
            for i, child_vocab in enumerate(child_vocabs):
                if isinstance(child_vocab, Exception):
                    logger.error(
                        f"Failed to aggregate vocabulary for child {child_ids[i]}: {child_vocab}"
                    )
                elif child_vocab:  # Ensure we have a valid vocabulary list
                    vocabulary.update(child_vocab)

        # Determine whether to include the corpus's own vocabulary
        if corpus.is_master:
            # Master corpora never include their own vocabulary, only children's
            logger.info(f"Master corpus {corpus_id} - using only children's vocabulary")
        # Non-master corpora always include their own vocabulary
        elif corpus.vocabulary:
            vocabulary.update(corpus.vocabulary)

        aggregated = sorted(vocabulary)
        logger.info(
            f"aggregate_vocabularies: corpus_uuid={corpus.corpus_uuid}, is_master={corpus.is_master}, child_ids={child_ids}, aggregated={aggregated}, update_parent={update_parent}"
        )

        # Update the parent corpus with aggregated vocabulary if requested
        if update_parent and aggregated != corpus.vocabulary:
            corpus.vocabulary = aggregated
            corpus.unique_word_count = len(aggregated)
            corpus.total_word_count = len(aggregated)

            # Update vocabulary stats and indices
            corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(aggregated)}
            corpus.vocabulary_stats["unique_words"] = len(aggregated)
            corpus.vocabulary_stats["total_words"] = len(aggregated)

            # Rebuild unified indices (lemmatization, etc.) for the aggregated vocabulary
            logger.info(f"Rebuilding indices for aggregated corpus {corpus_id}")
            await corpus._create_unified_indices()
            corpus._build_signature_index()

            # Save the entire corpus with all rebuilt indices
            # This ensures lemmatization, signatures, etc. are persisted
            logger.info(f"Saving aggregated corpus {corpus_id} with all indices")
            await self.save_corpus(
                corpus=corpus,
                config=config,
            )
            logger.info(f"Saved corpus {corpus_id} with vocabulary of size {len(aggregated)}")

        return aggregated

    async def get_vocabulary(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        aggregate: bool = False,
        config: VersionConfig | None = None,
    ) -> list[str] | None:
        """Get vocabulary from a corpus.

        Args:
            corpus_id: Corpus ID (preferred)
            corpus_name: Corpus name (fallback)
            aggregate: Whether to aggregate from children
            config: Version configuration

        Returns:
            Vocabulary list or None

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name, config=config)
        if not corpus:
            return None

        if aggregate and corpus.corpus_id:
            return await self.aggregate_vocabularies(corpus.corpus_id, config)

        # Corpus is now a Corpus object, not metadata
        return corpus.vocabulary if corpus else []

    async def update_parent(
        self,
        parent_id: PydanticObjectId | Any,
        child_id: PydanticObjectId | Any,
        config: VersionConfig | None = None,
    ) -> bool | None:
        """Simple tree operation: add child to parent.

        Args:
            parent_id: Parent corpus ID or object with 'id' or 'corpus_id' attribute
            child_id: Child corpus ID or object with 'id' or 'corpus_id' attribute
            config: Version configuration

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
        if await self._would_create_cycle(parent_id, child_id, config):
            logger.warning(f"Would create cycle: {child_id} -> {parent_id}")
            return False

        # Get both corpora using get_corpus for consistency
        parent = await self.get_corpus(corpus_id=parent_id, config=config)
        child = await self.get_corpus(corpus_id=child_id, config=config)

        logger.info(f"update_parent: parent={parent is not None}, child={child is not None}")

        if not parent or not child:
            logger.warning("update_parent failed: parent or child not found")
            return False

        # Update parent's children list via save_corpus to maintain versioning
        parent_updated = False
        if child.corpus_uuid not in parent.child_uuids:
            logger.info(
                f"Adding child UUID {child.corpus_uuid} (ID: {child_id}) to parent {parent_id}"
            )
            # Add child's UUID to parent's list (NOT the corpus_id!)
            updated_children = parent.child_uuids.copy()
            updated_children.append(child.corpus_uuid)
            # Save through save_corpus to create new version - MUST preserve all corpus fields!
            await self.save_corpus(
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
            logger.info(f"Setting parent UUID {parent.corpus_uuid} (ID: {parent_id}) for child {child_id}")
            # Save through save_corpus to create new version - MUST preserve all corpus fields!
            await self.save_corpus(
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

    async def update_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        content: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Update an existing corpus.

        Args:
            corpus_id: Corpus ID (preferred)
            corpus_name: Corpus name (fallback)
            content: New content to merge
            metadata: New metadata to merge
            config: Version configuration

        Returns:
            Updated Corpus or None

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name, config=config)
        if not corpus:
            return None

        # Merge content into the corpus object
        existing_content = corpus.model_dump()
        if content:
            logger.info(f"update_corpus: updating content with {list(content.keys())}")
            existing_content.update(content)

        # Extract corpus-specific fields from content for metadata
        existing_metadata = {}
        corpus_specific_fields = {}

        if metadata:
            # Extract corpus-specific fields from metadata
            for field in [
                "parent_uuid",
                "child_uuids",
                "is_master",
                "corpus_type",
                "language",
            ]:
                if field in metadata:
                    corpus_specific_fields[field] = metadata.pop(field)

            # Update remaining generic metadata
            existing_metadata.update(metadata)

        # Preserve existing child_uuids if not explicitly provided
        if "child_uuids" not in corpus_specific_fields:
            corpus_specific_fields["child_uuids"] = corpus.child_uuids

        # Preserve existing is_master if not explicitly provided
        if "is_master" not in corpus_specific_fields:
            corpus_specific_fields["is_master"] = corpus.is_master

        # Save updated corpus with corpus-specific fields
        logger.info(
            f"update_corpus: saving corpus {corpus.corpus_id} with vocabulary size {len(existing_content.get('vocabulary', []))}, is_master={corpus_specific_fields.get('is_master')}"
        )
        result = await self.save_corpus(
            corpus_id=corpus.corpus_id,
            corpus_name=corpus.corpus_name,
            content=existing_content,
            metadata=existing_metadata,
            **corpus_specific_fields,  # Pass corpus-specific fields directly
            config=config or VersionConfig(increment_version=True, use_cache=False),
        )
        logger.info(
            f"update_corpus: save result {result.corpus_id if result else None}, vocabulary size {len(result.vocabulary) if result else 'None'}, is_master={result.is_master if result else None}"
        )
        return result

    async def delete_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        cascade: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Delete a corpus and optionally its children.

        Args:
            corpus_id: Corpus ID (preferred)
            corpus_uuid: Corpus UUID (stable identifier)
            corpus_name: Corpus name (fallback)
            cascade: Whether to delete child corpora
            config: Version configuration

        Returns:
            True if deleted successfully

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_uuid=corpus_uuid, corpus_name=corpus_name, config=config)
        if not corpus or not corpus.corpus_id:
            return False

        # Handle cascade deletion
        if cascade and corpus.child_uuids:
            # Make a copy to avoid modification during iteration and handle potential None values
            children_to_delete = list(corpus.child_uuids) if corpus.child_uuids else []
            for child_uuid in children_to_delete:
                # child_uuids contains UUID strings, need to use corpus_uuid parameter
                await self.delete_corpus(corpus_uuid=child_uuid, cascade=True, config=config)

        # Remove from parent if it has one
        if corpus.parent_uuid and corpus.corpus_id:
            # Get parent corpus to get its corpus_id
            parent = await self.get_corpus(corpus_uuid=corpus.parent_uuid, config=config)
            if parent and parent.corpus_id:
                await self.remove_child(
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
            from ..search.models import SearchIndex, TrieIndex
            from ..search.semantic.models import SemanticIndex

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

    async def invalidate_corpus(self, corpus_name: str) -> bool:
        """Invalidate a specific corpus and all related caches.

        Args:
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
        latest = await self.vm.get_latest(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
        )

        if latest and latest.version_info:
            versioned_key = (
                f"{ResourceType.CORPUS.value}:{corpus_name}:v{latest.version_info.version}"
            )
            await cache.delete(CacheNamespace.CORPUS, versioned_key)

        # Note: Search indexes are not stored as Documents in MongoDB,
        # they are cached in memory or as serialized files.
        # For now, we just clear the corpus cache.

        return True

    async def invalidate_all_corpora(self) -> int:
        """Invalidate all corpora and related caches.

        Returns:
            Number of corpora invalidated

        """
        # PATHOLOGICAL REMOVAL: No try/except - let errors propagate
        # Get all corpus metadata
        all_corpora = await Corpus.Metadata.find_all().to_list()

        count = 0
        for corpus_meta in all_corpora:
            if await self.invalidate_corpus(corpus_meta.resource_id):
                count += 1

        # Clear the entire corpus namespace as well

        cache = await get_global_cache()
        await cache.clear_namespace(CacheNamespace.CORPUS)

        return count

    async def get_tree(
        self,
        corpus_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get the tree structure of a corpus and its descendants.

        Args:
            corpus_id: Corpus ID
            config: Version configuration

        Returns:
            Dictionary representation of the tree

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, config=config)
        if not corpus:
            return None

        tree = corpus.model_dump(mode="json")
        tree["children"] = []

        # Safely iterate over children, handling potential None values
        if corpus.child_uuids:
            for child_uuid in corpus.child_uuids:
                # For uuids, need to get corpus first to get its corpus_id
                child = await self.get_corpus(corpus_uuid=child_uuid, config=config)
                if child and child.corpus_id:
                    child_tree = await self.get_tree(child.corpus_id, config)
                    if child_tree:
                        tree["children"].append(child_tree)

        return tree

    async def aggregate_vocabulary(
        self,
        corpus_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> bool:
        """Aggregate vocabulary from children and update parent.

        Args:
            corpus_id: Corpus ID
            config: Version configuration

        Returns:
            True if aggregation succeeded

        """
        aggregated = await self.aggregate_vocabularies(corpus_id, config)
        return len(aggregated) > 0

    async def aggregate_from_children(
        self,
        parent_corpus_id: PydanticObjectId | None = None,
        parent_corpus_uuid: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Aggregate vocabularies from parent and all children into a new corpus.

        Args:
            parent_corpus_id: Parent corpus ID to aggregate from (deprecated, use parent_corpus_uuid)
            parent_corpus_uuid: Parent corpus UUID to aggregate from (preferred)
            config: Version configuration

        Returns:
            Corpus object with aggregated vocabulary from parent and children

        """
        # Get the parent corpus
        parent = await self.get_corpus(corpus_id=parent_corpus_id, corpus_uuid=parent_corpus_uuid, config=config)
        if not parent:
            return None

        # Collect vocabularies from parent and children
        vocabulary = set()

        # Add parent's vocabulary if it exists
        if parent.vocabulary:
            vocabulary.update(parent.vocabulary)

        # Get child vocabularies recursively using existing aggregate_vocabularies method
        child_ids = parent.child_uuids or []
        for child_id in child_ids:
            child_vocab = await self.aggregate_vocabularies(
                corpus_uuid=child_id, config=config, update_parent=False
            )
            vocabulary.update(child_vocab)

        # Create a new corpus with the aggregated vocabulary
        aggregated_vocab = sorted(vocabulary)

        # Create a copy of the parent corpus with the aggregated vocabulary
        aggregated_corpus_data = parent.model_dump()
        aggregated_corpus_data["vocabulary"] = aggregated_vocab
        aggregated_corpus_data["unique_word_count"] = len(aggregated_vocab)
        aggregated_corpus_data["total_word_count"] = len(aggregated_vocab)

        # Rebuild vocabulary index
        aggregated_corpus_data["vocabulary_to_index"] = {
            word: idx for idx, word in enumerate(aggregated_vocab)
        }

        # Update vocabulary stats
        if "vocabulary_stats" not in aggregated_corpus_data:
            aggregated_corpus_data["vocabulary_stats"] = {}
        aggregated_corpus_data["vocabulary_stats"]["unique_words"] = len(aggregated_vocab)
        aggregated_corpus_data["vocabulary_stats"]["total_words"] = len(aggregated_vocab)

        return Corpus.model_validate(aggregated_corpus_data)

    async def _would_create_cycle(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> bool:
        """Simple cycle detection: walk up from parent to see if we hit child."""
        current: PydanticObjectId | None = parent_id
        visited = set()

        while current:
            if current == child_id:
                return True  # Found cycle

            if current in visited:
                break  # Existing cycle, stop

            visited.add(current)

            # Get parent of current
            corpus = await self.get_corpus(corpus_id=current, config=config)
            # Get parent UUID and convert to corpus_id for next iteration
            if corpus and corpus.parent_uuid:
                parent_corpus = await self.get_corpus(corpus_uuid=corpus.parent_uuid, config=config)
                current = parent_corpus.corpus_id if parent_corpus else None
            else:
                current = None

        return False

    async def add_child(
        self,
        parent: Corpus,
        child: Corpus,
        config: VersionConfig | None = None,
    ) -> bool:
        """Add a child to a parent corpus.

        Args:
            parent: Parent corpus
            child: Child corpus to add
            config: Version configuration

        Returns:
            True if added successfully

        """
        if parent.corpus_id and child.corpus_id:
            result = await self.update_parent(parent.corpus_id, child.corpus_id, config)
            return result if result is not None else False
        return False

    async def get_children(
        self,
        parent_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get all child corpora of a parent (N+1 QUERY FIX).

        Args:
            parent_id: Parent corpus ID
            config: Version configuration

        Returns:
            List of child Corpus objects

        """
        parent = await self.get_corpus(corpus_id=parent_id, config=config)
        if not parent:
            return []

        # CRITICAL FIX: Batch-fetch all children in single query instead of N separate queries
        if parent.child_uuids:
            return await self.get_corpora_by_uuids(parent.child_uuids, config)

        return []

    async def remove_child(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        delete_child: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Simple tree operation: remove child from parent."""
        # Force fresh read to avoid stale data
        fresh_config = config or VersionConfig()
        fresh_config.use_cache = False

        # Get parent using get_corpus for consistency with version manager
        parent = await self.get_corpus(corpus_id=parent_id, config=fresh_config)
        if not parent:
            logger.warning(f"Parent {parent_id} not found in remove_child")
            return False

        # Log current state
        logger.info(f"Parent {parent_id} currently has children: {parent.child_uuids}")

        # Get child corpus to get its UUID
        child = await self.get_corpus(corpus_id=child_id, config=fresh_config)
        if not child or not child.corpus_uuid:
            logger.warning(f"Child {child_id} not found or missing UUID")
            return False

        # Remove from parent's children list (compare UUIDs)
        removed = False
        if child.corpus_uuid in parent.child_uuids:
            logger.info(f"Removing child UUID {child.corpus_uuid} (ID: {child_id}) from parent {parent_id} children list")
            parent.child_uuids.remove(child.corpus_uuid)
            removed = True
        else:
            logger.warning(f"Child UUID {child.corpus_uuid} not in parent's children list")

        # Save parent with updated children list via save_corpus for versioning
        if removed or delete_child:
            logger.info(f"Updating parent with children: {parent.child_uuids}")
            # Save through save_corpus to create new version
            saved_parent = await self.save_corpus(
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
                await self.save_corpus(
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
            await self.delete_corpus(corpus_id=child_id, cascade=False, config=fresh_config)

        return True


# Global tree corpus manager instance
_tree_corpus_manager: TreeCorpusManager | None = None


def get_tree_corpus_manager() -> TreeCorpusManager:
    """Get the global tree corpus manager instance.

    Returns:
        TreeCorpusManager singleton

    """
    global _tree_corpus_manager
    if _tree_corpus_manager is None:
        _tree_corpus_manager = TreeCorpusManager()
    return _tree_corpus_manager


# Backwards compatibility aliases for legacy imports
CorpusManager = TreeCorpusManager


def get_corpus_manager() -> TreeCorpusManager:
    """Legacy alias that returns the tree corpus manager."""
    return get_tree_corpus_manager()

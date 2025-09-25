from __future__ import annotations

from typing import TYPE_CHECKING, Any

import coolname
from beanie import PydanticObjectId
from pydantic import BaseModel

from ..caching.core import get_versioned_content
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
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
            from ..caching.manager import get_version_manager

            self.vm = get_version_manager()

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
        metadata.parent_corpus_id = corpus.parent_corpus_id
        metadata.child_corpus_ids = corpus.child_corpus_ids or []
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
        # Clean self-references before saving
        if metadata.id and metadata.child_corpus_ids and metadata.id in metadata.child_corpus_ids:
            logger.warning(f"Removing self-reference from metadata.child_corpus_ids: {metadata.id}")
            metadata.child_corpus_ids = [
                cid for cid in metadata.child_corpus_ids if cid != metadata.id
            ]

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
        parent_corpus_id: PydanticObjectId | None = None,
        child_corpus_ids: list[PydanticObjectId] | None = None,
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
            parent_corpus_id: Parent corpus ID (saved as data only)
            child_corpus_ids: Child corpus IDs (saved as data only)
            is_master: Whether this is a master corpus
            config: Version configuration
            metadata: Additional metadata

        Returns:
            Saved Corpus instance

        """
        # save_corpus should NOT accept Metadata objects
        # Check if corpus is a Metadata object by type
        from ..caching.models import BaseVersionedData
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
            content = content if content is not None else corpus.model_dump(mode="json")
            corpus_type = corpus_type if corpus_type != CorpusType.LEXICON else corpus.corpus_type
            language = language if language != Language.ENGLISH else corpus.language
            parent_corpus_id = (
                parent_corpus_id if parent_corpus_id is not None else corpus.parent_corpus_id
            )
            child_corpus_ids = (
                child_corpus_ids if child_corpus_ids is not None else corpus.child_corpus_ids
            )
            logger.debug(
                f"save_corpus: corpus has {len(corpus.child_corpus_ids) if corpus.child_corpus_ids else 0} children, using {len(child_corpus_ids) if child_corpus_ids else 0} children"
            )
            # Preserve is_master flag: use explicit value if provided, otherwise get from corpus
            is_master = (
                is_master
                if is_master is not None
                else (getattr(corpus, "is_master", False) if corpus else False)
            )

            # Clean self-references from child_corpus_ids immediately
            if corpus_id and child_corpus_ids and corpus_id in child_corpus_ids:
                logger.warning(f"Removing self-reference from child_corpus_ids: {corpus_id}")
                child_corpus_ids = [cid for cid in child_corpus_ids if cid != corpus_id]

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
            "parent_corpus_id": parent_corpus_id,
            "child_corpus_ids": child_corpus_ids if child_corpus_ids is not None else [],
            "is_master": is_master if is_master is not None else False,  # Default to False if None
            **(metadata or {}),
        }

        logger.debug(
            f"save_corpus: saving with child_corpus_ids={full_metadata['child_corpus_ids']}"
        )

        # Save using version manager
        logger.info(
            f"save_corpus: calling vm.save with resource_id={resource_id}, child_corpus_ids={full_metadata.get('child_corpus_ids', [])}"
        )
        saved = await self.vm.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content or {},
            config=config or VersionConfig(),
            metadata=full_metadata,
        )
        logger.info(f"save_corpus: vm.save returned ID={saved.id if saved else None}")

        # Clean up self-references in child_corpus_ids AFTER getting the ID
        actual_id = corpus_id if corpus_id else (saved.id if saved else None)
        if actual_id and child_corpus_ids and actual_id in child_corpus_ids:
            logger.warning(f"Removing self-reference from child_corpus_ids: {actual_id}")
            child_corpus_ids = [cid for cid in child_corpus_ids if cid != actual_id]
            # Update the metadata in version manager
            full_metadata["child_corpus_ids"] = child_corpus_ids
            # Re-save with cleaned child_corpus_ids
            if saved:
                saved = await self.vm.save(
                    resource_id=resource_id,
                    resource_type=ResourceType.CORPUS,
                    namespace=CacheNamespace.CORPUS,
                    content=content or {},
                    config=config or VersionConfig(),
                    metadata=full_metadata,
                )

        # Auto-update parent's child_corpus_ids if parent_corpus_id is provided
        # BUT ONLY if we're creating a NEW corpus (not updating existing)
        # AND we're not explicitly managing child_corpus_ids
        if parent_corpus_id and saved and not corpus_id and child_corpus_ids is None:
            child_id = saved.id
            if child_id:
                # Get the parent
                parent_meta = await Corpus.Metadata.get(parent_corpus_id)
                if parent_meta and child_id not in parent_meta.child_corpus_ids:
                    # This is a new child being created with a parent reference
                    parent_meta.child_corpus_ids.append(child_id)
                    await parent_meta.save()
                    logger.debug(f"Auto-added new child {child_id} to parent {parent_corpus_id}")

        # If we saved metadata, convert back to Corpus
        if saved:
            saved_content = await get_versioned_content(saved)
            if saved_content:
                # Merge metadata into content for proper Corpus creation
                saved_content.update(full_metadata)
                # Preserve original corpus_id if updating, otherwise use new ID
                if corpus_id:
                    # We're updating an existing corpus, preserve its ID
                    saved_content["corpus_id"] = corpus_id
                else:
                    # New corpus, use the metadata document's ID
                    saved_content["corpus_id"] = saved.id
                # IMPORTANT: Always use the cleaned child_corpus_ids if we have them
                saved_content["child_corpus_ids"] = (
                    child_corpus_ids if child_corpus_ids is not None else []
                )
                return Corpus.model_validate(saved_content)
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
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Simple corpus retrieval by ID or name - always returns latest version."""
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

        # Get content from versioned storage
        content = await get_versioned_content(metadata)
        if not content:
            content = {}

        logger.info(
            f"get_corpus: metadata.id={metadata.id if metadata else None}, content has vocabulary: {len(content.get('vocabulary', []))}, metadata.child_corpus_ids={metadata.child_corpus_ids}"
        )

        # Ensure all required fields from metadata
        # Corpus-specific fields should come from metadata attributes, not content
        content.update(
            {
                "corpus_id": metadata.id,
                "corpus_name": metadata.resource_id,
                "corpus_type": metadata.corpus_type,
                "language": metadata.language,
                "parent_corpus_id": metadata.parent_corpus_id,
                "child_corpus_ids": metadata.child_corpus_ids or [],
                "is_master": metadata.is_master,
            }
        )

        # Clean self-references even when reading
        if content.get("corpus_id") and content.get("child_corpus_ids"):
            self_id = content["corpus_id"]
            if self_id in content["child_corpus_ids"]:
                logger.warning(f"Cleaning self-reference found in loaded corpus {self_id}")
                content["child_corpus_ids"] = [
                    cid for cid in content["child_corpus_ids"] if cid != self_id
                ]

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

        # Ensure version info
        if metadata.version_info:
            content["version_info"] = metadata.version_info

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
        corpora = []
        for metadata in metadatas:
            # Get versioned content for each metadata
            try:
                content = await get_versioned_content(metadata)
                if content:
                    # Add the ID from metadata
                    content["corpus_id"] = metadata.id
                    # Extract corpus-specific fields from metadata object
                    content["child_corpus_ids"] = metadata.child_corpus_ids
                    content["parent_corpus_id"] = metadata.parent_corpus_id
                    content["is_master"] = metadata.is_master
                    content["corpus_name"] = metadata.corpus_name
                    content["corpus_type"] = metadata.corpus_type
                    content["language"] = metadata.language
                    # Add version information
                    if metadata.version_info:
                        content["version_info"] = metadata.version_info
                        content["_metadata_id"] = metadata.id

                    corpus = Corpus.model_validate(content)
                    # Rebuild indices if needed
                    if corpus.vocabulary and not corpus.vocabulary_to_index:
                        await corpus._rebuild_indices()
                    corpora.append(corpus)
            except Exception as e:
                logger.warning(f"Failed to convert metadata {metadata.id} to corpus: {e}")
                continue

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
                parent_corpus_id=master.corpus_id,
                config=config,
                metadata=child_def.get("metadata"),
            )
            if child and child.corpus_id:
                child_ids.append(child.corpus_id)

        # Update master with child references
        if child_ids:
            # Master is now a Corpus object, use model_dump to get content
            master_content = master.model_dump(mode="json") if master else {}
            master_content["child_corpus_ids"] = child_ids

            await self.save_corpus(
                corpus_id=master.corpus_id,
                corpus_name=master.corpus_name,
                content=master_content,
                child_corpus_ids=child_ids,
                is_master=True,
                config=config,
            )

        return master

    async def aggregate_vocabularies(
        self,
        corpus_id: PydanticObjectId,
        config: VersionConfig | None = None,
        update_parent: bool = True,
    ) -> list[str]:
        """Aggregate vocabularies from a corpus and its children.

        Args:
            corpus_id: Corpus ID to aggregate from
            config: Version configuration
            update_parent: Whether to update the parent corpus with aggregated vocabulary

        Returns:
            Aggregated vocabulary list

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, config=config)
        if not corpus:
            return []

        # For master corpora, only aggregate children's vocabularies
        # Don't include the parent's own vocabulary since it's just an aggregate container
        vocabulary = set()

        # Get child vocabularies recursively
        child_ids = corpus.child_corpus_ids or []
        for child_id in child_ids:
            child_vocab = await self.aggregate_vocabularies(child_id, config, update_parent=False)
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
            f"aggregate_vocabularies: corpus_id={corpus_id}, is_master={corpus.is_master}, child_ids={child_ids}, aggregated={aggregated}, update_parent={update_parent}"
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

            # Update the corpus without creating a new version
            # This preserves child_corpus_ids relationships
            updated = await self.update_corpus(
                corpus_id=corpus_id,
                content={"vocabulary": aggregated},
                metadata={"vocabulary_size": len(aggregated)},
                config=config,
            )
            logger.info(
                f"Updated corpus {corpus_id} with vocabulary of size {len(aggregated)}, result: {updated is not None}"
            )

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
        # Extract IDs from objects if needed (KISS - handle both cases)
        # Convert to ID if it's an object
        if isinstance(parent_id, BaseModel) and hasattr(parent_id, "id"):
            parent_id = parent_id.id
        elif isinstance(parent_id, dict) and "corpus_id" in parent_id:
            parent_id = parent_id["corpus_id"]

        # Convert to ID if it's an object
        if isinstance(child_id, BaseModel) and hasattr(child_id, "id"):
            child_id = child_id.id
        elif isinstance(child_id, dict) and "corpus_id" in child_id:
            child_id = child_id["corpus_id"]

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
        if child_id not in parent.child_corpus_ids:
            logger.info(f"Adding child {child_id} to parent {parent_id}")
            # Add child to parent's list
            updated_children = parent.child_corpus_ids.copy()
            updated_children.append(child_id)
            # Save through save_corpus to create new version - MUST preserve all corpus fields!
            await self.save_corpus(
                corpus_id=parent_id,
                corpus_name=parent.corpus_name,
                content=parent.model_dump(),
                corpus_type=parent.corpus_type,  # CRITICAL: preserve corpus type
                language=parent.language,  # CRITICAL: preserve language
                parent_corpus_id=parent.parent_corpus_id,  # preserve parent
                child_corpus_ids=updated_children,
                is_master=parent.is_master,  # preserve master status
                config=config,
            )
            parent_updated = True
            logger.info(f"Parent updated with children: {updated_children}")
        else:
            logger.info(f"Child {child_id} already in parent {parent_id}")

        # Update child's parent reference via save_corpus to maintain versioning
        child_updated = False
        if child.parent_corpus_id != parent_id:
            logger.info(f"Setting parent {parent_id} for child {child_id}")
            # Save through save_corpus to create new version - MUST preserve all corpus fields!
            await self.save_corpus(
                corpus_id=child_id,
                corpus_name=child.corpus_name,
                content=child.model_dump(),
                corpus_type=child.corpus_type,  # CRITICAL: preserve corpus type
                language=child.language,  # CRITICAL: preserve language
                parent_corpus_id=parent_id,
                child_corpus_ids=child.child_corpus_ids,  # preserve children
                is_master=child.is_master,  # preserve master status
                config=config,
            )
            child_updated = True
            logger.info(f"Child updated with parent: {parent_id}")
        else:
            logger.info(f"Child already has parent {parent_id}")

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
                "parent_corpus_id",
                "child_corpus_ids",
                "is_master",
                "corpus_type",
                "language",
            ]:
                if field in metadata:
                    corpus_specific_fields[field] = metadata.pop(field)

            # Update remaining generic metadata
            existing_metadata.update(metadata)

        # Preserve existing child_corpus_ids if not explicitly provided
        if "child_corpus_ids" not in corpus_specific_fields:
            corpus_specific_fields["child_corpus_ids"] = corpus.child_corpus_ids

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
        corpus_name: str | None = None,
        cascade: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Delete a corpus and optionally its children.

        Args:
            corpus_id: Corpus ID (preferred)
            corpus_name: Corpus name (fallback)
            cascade: Whether to delete child corpora
            config: Version configuration

        Returns:
            True if deleted successfully

        """
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name, config=config)
        if not corpus or not corpus.corpus_id:
            return False

        # Handle cascade deletion
        if cascade:
            for child_id in corpus.child_corpus_ids:
                await self.delete_corpus(corpus_id=child_id, cascade=True, config=config)

        # Remove from parent if it has one
        if corpus.parent_corpus_id and corpus.corpus_id:
            await self.remove_child(
                parent_id=corpus.parent_corpus_id,
                child_id=corpus.corpus_id,
                delete_child=False,
                config=config,
            )

        # Store the corpus name and id before deletion
        corpus_name_to_clear = corpus.corpus_name
        corpus_id_to_delete = corpus.corpus_id

        # Delete the metadata document directly from MongoDB
        # This prevents get_corpus from finding it
        if corpus_id_to_delete:
            metadata_to_delete = await Corpus.Metadata.get(corpus_id_to_delete)
            if metadata_to_delete:
                await metadata_to_delete.delete()
                logger.info(
                    f"Deleted corpus metadata for {corpus_name_to_clear} (ID: {corpus_id_to_delete})"
                )

        # Note: corpus.delete() would fail because Corpus is not a Document
        # The metadata deletion above handles the actual removal

        # Clear cache entries for this corpus
        if corpus_name_to_clear:
            from ..caching.core import get_global_cache

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
        try:
            # Clear cache entries for this corpus
            from ..caching.core import get_global_cache

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
        except Exception:
            return False

    async def invalidate_all_corpora(self) -> int:
        """Invalidate all corpora and related caches.

        Returns:
            Number of corpora invalidated

        """
        try:
            # Get all corpus metadata
            all_corpora = await Corpus.Metadata.find_all().to_list()

            count = 0
            for corpus_meta in all_corpora:
                if await self.invalidate_corpus(corpus_meta.resource_id):
                    count += 1

            # Clear the entire corpus namespace as well
            from ..caching.core import get_global_cache

            cache = await get_global_cache()
            await cache.clear_namespace(CacheNamespace.CORPUS)

            return count
        except Exception:
            return 0

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

        for child_id in corpus.child_corpus_ids:
            child_tree = await self.get_tree(child_id, config)
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
            current = corpus.parent_corpus_id if corpus else None

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
        """Get all child corpora of a parent.

        Args:
            parent_id: Parent corpus ID
            config: Version configuration

        Returns:
            List of child Corpus objects

        """
        parent = await self.get_corpus(corpus_id=parent_id, config=config)
        if not parent:
            return []

        children = []
        for child_id in parent.child_corpus_ids:
            child = await self.get_corpus(corpus_id=child_id, config=config)
            if child:
                children.append(child)

        return children

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
        logger.info(f"Parent {parent_id} currently has children: {parent.child_corpus_ids}")

        # Remove from parent's children list
        removed = False
        if child_id in parent.child_corpus_ids:
            logger.info(f"Removing child {child_id} from parent {parent_id} children list")
            parent.child_corpus_ids.remove(child_id)
            removed = True
        else:
            logger.warning(f"Child {child_id} not in parent's children list")

        # Save parent with updated children list via save_corpus for versioning
        if removed or delete_child:
            logger.info(f"Updating parent with children: {parent.child_corpus_ids}")
            # Save through save_corpus to create new version
            saved_parent = await self.save_corpus(
                corpus_id=parent.corpus_id,
                corpus_name=parent.corpus_name,
                content=parent.model_dump(),
                child_corpus_ids=parent.child_corpus_ids,
                parent_corpus_id=parent.parent_corpus_id,
                is_master=parent.is_master,
                corpus_type=parent.corpus_type,
                language=parent.language,
                config=fresh_config,
            )
            logger.info(
                f"Parent saved with updated children: saved has {len(saved_parent.child_corpus_ids) if saved_parent else 'None'} children"
            )

        # Clear child's parent reference via save_corpus for versioning (unless deleting)
        if not delete_child:
            child = await self.get_corpus(corpus_id=child_id, config=fresh_config)
            if child and child.parent_corpus_id == parent_id:
                child.parent_corpus_id = None
                await self.save_corpus(
                    corpus_id=child.corpus_id,
                    corpus_name=child.corpus_name,
                    content=child.model_dump(),
                    child_corpus_ids=child.child_corpus_ids,
                    parent_corpus_id=None,
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

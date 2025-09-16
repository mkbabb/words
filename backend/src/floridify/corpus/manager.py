from typing import Any

import coolname
from beanie import PydanticObjectId

from ..caching.core import get_versioned_content
from ..caching.manager import VersionedDataManager, get_version_manager
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..models.base import Language
from .core import Corpus
from .models import CorpusType


class TreeCorpusManager:
    """Manager for hierarchical corpus structures with vocabulary aggregation."""

    def __init__(self, vm: VersionedDataManager | None = None) -> None:
        """Initialize with optional version manager.

        Args:
            vm: Version manager instance or None to use default
        """
        self.vm = vm or get_version_manager()

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
        is_master: bool = False,
        config: VersionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Corpus | None:
        """Save a corpus with ID-based primary key support.

        Args:
            corpus: Corpus object to save (if provided, overrides other params)
            corpus_id: Existing corpus ID for updates
            corpus_name: Corpus name (optional, will be generated if not provided)
            content: Corpus content (vocabulary, etc.)
            corpus_type: Type of corpus
            language: Language of the corpus
            parent_corpus_id: Parent corpus ID if part of tree
            child_corpus_ids: Child corpus IDs
            is_master: Whether this is a master corpus
            config: Version configuration
            metadata: Additional metadata

        Returns:
            Saved Corpus instance
        """
        # If corpus object provided, extract parameters from it
        if corpus:
            corpus_id = corpus.corpus_id if corpus.corpus_id else corpus_id
            corpus_name = corpus.corpus_name or corpus_name
            content = corpus.model_dump(mode="json") if not content else content
            corpus_type = corpus.corpus_type or corpus_type
            language = corpus.language or language
            parent_corpus_id = corpus.parent_corpus_id or parent_corpus_id
            child_corpus_ids = corpus.child_corpus_ids or child_corpus_ids
            is_master = corpus.is_master if hasattr(corpus, "is_master") else is_master

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

        # Prepare metadata
        full_metadata = {
            "corpus_name": corpus_name or "",
            "corpus_type": corpus_type.value if hasattr(corpus_type, "value") else corpus_type,
            "language": language.value if hasattr(language, "value") else language,
            "parent_corpus_id": parent_corpus_id,
            "child_corpus_ids": child_corpus_ids or [],
            "is_master": is_master,
            **(metadata or {}),
        }

        # Save using version manager
        saved = await self.vm.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content or {},
            config=config or VersionConfig(),
            metadata=full_metadata,
        )

        # Handle tree structures
        if parent_corpus_id and saved and saved.id:
            await self.update_parent(parent_corpus_id, saved.id)

        # If we saved metadata, convert back to Corpus
        if saved:
            saved_content = await get_versioned_content(saved)
            if saved_content:
                # Merge metadata into content for proper Corpus creation
                saved_content.update(full_metadata)
                # Add the ID from the saved metadata
                saved_content["corpus_id"] = saved.id
                # Ensure child_corpus_ids are properly included
                if "child_corpus_ids" not in saved_content and child_corpus_ids:
                    saved_content["child_corpus_ids"] = child_corpus_ids
                return Corpus.model_validate(saved_content)
        return None

    async def get_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Get a corpus by ID or name.

        Args:
            corpus_id: ObjectId of the corpus (preferred)
            corpus_name: Name of the corpus (fallback)
            config: Version configuration

        Returns:
            Corpus instance or None
        """
        metadata = None

        # Direct ID lookup - but we need to get the resource_id first
        if corpus_id:
            # First get the metadata to find the resource_id
            temp_metadata = await Corpus.Metadata.get(corpus_id)
            if temp_metadata:
                # Now use version manager with the resource_id to respect config
                metadata = await self.vm.get_latest(
                    resource_id=temp_metadata.resource_id,
                    resource_type=ResourceType.CORPUS,
                    use_cache=config.use_cache if config else True,
                    config=config or VersionConfig(),
                )

        # Fallback to name-based lookup
        if not metadata and corpus_name:
            metadata = await self.vm.get_latest(
                resource_id=corpus_name,
                resource_type=ResourceType.CORPUS,
                use_cache=config.use_cache if config else True,
                config=config or VersionConfig(),
            )

        # Convert metadata to Corpus
        if metadata:
            content = await get_versioned_content(metadata)
            if content:
                # Add the ID from metadata
                content["corpus_id"] = metadata.id
                # Extract corpus-specific fields from metadata object
                # These are stored as fields on the Metadata model, not in content
                if hasattr(metadata, "child_corpus_ids"):
                    content["child_corpus_ids"] = metadata.child_corpus_ids
                if hasattr(metadata, "parent_corpus_id"):
                    content["parent_corpus_id"] = metadata.parent_corpus_id
                if hasattr(metadata, "is_master"):
                    content["is_master"] = metadata.is_master
                if hasattr(metadata, "corpus_name"):
                    content["corpus_name"] = metadata.corpus_name
                if hasattr(metadata, "corpus_type"):
                    content["corpus_type"] = metadata.corpus_type
                if hasattr(metadata, "language"):
                    content["language"] = metadata.language
                corpus = Corpus.model_validate(content)
                # Rebuild indices if needed
                if corpus.vocabulary and not corpus.vocabulary_to_index:
                    await corpus._rebuild_indices()
                return corpus

        return None

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

        # Get corpus vocabulary
        vocabulary = set(corpus.vocabulary) if corpus.vocabulary else set()

        # Get child vocabularies recursively
        child_ids = corpus.child_corpus_ids or []
        for child_id in child_ids:
            child_vocab = await self.aggregate_vocabularies(child_id, config, update_parent=False)
            vocabulary.update(child_vocab)

        aggregated = sorted(vocabulary)

        # Update the parent corpus with aggregated vocabulary if requested
        if update_parent and aggregated != corpus.vocabulary:
            corpus.vocabulary = aggregated
            corpus.unique_word_count = len(aggregated)
            corpus.total_word_count = len(aggregated)

            # Update vocabulary stats and indices
            corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(aggregated)}
            corpus.vocabulary_stats["unique_words"] = len(aggregated)
            corpus.vocabulary_stats["total_words"] = len(aggregated)

            # Save the updated corpus
            await self.save_corpus(corpus=corpus, config=config)

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
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> bool:
        """Update parent corpus with child reference.

        Args:
            parent_id: Parent corpus ID
            child_id: Child corpus ID to add
            config: Version configuration

        Returns:
            True if updated successfully
        """
        parent = await self.get_corpus(corpus_id=parent_id, config=config)
        if not parent:
            return False

        # Parent is now a Corpus object
        if child_id not in parent.child_corpus_ids:
            parent.child_corpus_ids.append(child_id)

            saved = await self.save_corpus(
                corpus=parent,
                config=config,
            )
            return bool(saved)

        return True

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

        # Save updated corpus with corpus-specific fields
        return await self.save_corpus(
            corpus_id=corpus.corpus_id,
            corpus_name=corpus.corpus_name,
            content=existing_content,
            metadata=existing_metadata,
            **corpus_specific_fields,  # Pass corpus-specific fields directly
            config=config,
        )

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

        # Delete the corpus
        await corpus.delete()

        # Also delete from versioned storage to clear cache
        if corpus.corpus_name:
            # Get the latest version to delete
            latest = await self.vm.get_latest(
                resource_id=corpus.corpus_name, resource_type=ResourceType.CORPUS
            )
            if latest and latest.version_info:
                await self.vm.delete_version(
                    resource_id=corpus.corpus_name,
                    resource_type=ResourceType.CORPUS,
                    version=latest.version_info.version,
                )

        return True

    async def invalidate_corpus(self, corpus_name: str) -> bool:
        """Invalidate a specific corpus and all related caches.

        Args:
            corpus_name: Name of the corpus to invalidate

        Returns:
            True if invalidation succeeded
        """
        try:
            # Invalidate the corpus itself - get latest version
            latest = await self.vm.get_latest(
                resource_id=corpus_name, resource_type=ResourceType.CORPUS
            )
            deleted = False
            if latest and latest.version_info:
                deleted = await self.vm.delete_version(
                    resource_id=corpus_name,
                    resource_type=ResourceType.CORPUS,
                    version=latest.version_info.version,
                )

            # Also clear any search indexes that depend on this corpus
            from ..search.models import SearchIndex, TrieIndex
            from ..search.semantic.models import SemanticIndex

            # Clear search indexes related to this corpus
            await SearchIndex.Metadata.find({"corpus_id": corpus_name}).delete()

            await TrieIndex.Metadata.find({"corpus_id": corpus_name}).delete()

            await SemanticIndex.Metadata.find({"corpus_id": corpus_name}).delete()

            return bool(deleted)
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

    async def remove_child(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        delete_child: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Remove a child from a parent corpus.

        Args:
            parent_id: Parent corpus ID
            child_id: Child corpus ID to remove
            delete_child: Whether to also delete the child corpus
            config: Version configuration

        Returns:
            True if removed successfully
        """
        parent = await self.get_corpus(corpus_id=parent_id, config=config)
        if not parent:
            return False

        # Parent is now a Corpus object, access child_corpus_ids directly
        child_ids = list(parent.child_corpus_ids)  # Make a copy

        if child_id in child_ids:
            child_ids.remove(child_id)
            parent.child_corpus_ids = child_ids

            saved = await self.save_corpus(
                corpus=parent,
                child_corpus_ids=child_ids,
                config=config,
            )

            if not saved:
                return False

        # Delete the child if requested
        if delete_child:
            await self.delete_corpus(corpus_id=child_id, cascade=False, config=config)

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

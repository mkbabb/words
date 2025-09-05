from typing import Any, cast

import coolname  # type: ignore
from beanie import PydanticObjectId

from ..caching.core import load_external_content, store_external_content
from ..caching.manager import VersionedDataManager, get_version_manager
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..corpus.utils import get_vocabulary_hash
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
    ) -> Corpus.Metadata | None:
        """Save a corpus with ID-based primary key support.

        Args:
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
            Saved Corpus.Metadata instance
        """
        # Generate name if not provided
        if not corpus_name and not corpus_id:
            corpus_name = coolname.generate_slug(2)
            
        # If we have a corpus_id, try to get the existing corpus first
        existing = None
        if corpus_id:
            existing = await Corpus.Metadata.get(corpus_id)
            if existing and not corpus_name:
                corpus_name = existing.resource_id  # Use existing name
                
        # Use corpus_id string as resource_id if no name
        resource_id = corpus_name or str(corpus_id) if corpus_id else None
        if not resource_id:
            resource_id = coolname.generate_slug(2)

        # Prepare metadata
        full_metadata = {
            "corpus_name": corpus_name or "",
            "corpus_type": corpus_type.value,
            "language": language.value,
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

        return saved

    async def get_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus.Metadata | None:
        """Get a corpus by ID or name.

        Args:
            corpus_id: ObjectId of the corpus (preferred)
            corpus_name: Name of the corpus (fallback)
            config: Version configuration

        Returns:
            Corpus.Metadata instance or None
        """
        # Direct ID lookup is most efficient
        if corpus_id:
            corpus = await Corpus.Metadata.get(corpus_id)
            if corpus:
                return corpus
                
        # Fallback to name-based lookup
        if corpus_name:
            return await self.vm.get_latest(
                resource_id=corpus_name,
                resource_type=ResourceType.CORPUS,
                use_cache=config.use_cache if config else True,
                config=config or VersionConfig(),
            )
            
        return None

    async def create_tree(
        self,
        master_id: PydanticObjectId | None = None,
        master_name: str | None = None,
        children: list[dict[str, Any]] | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus.Metadata | None:
        """Create a hierarchical corpus tree.

        Args:
            master_id: Master corpus ID (preferred)
            master_name: Master corpus name (will generate if not provided)
            children: List of child corpus definitions
            config: Version configuration

        Returns:
            Master Corpus.Metadata instance
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

        if not master or not master.id:
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
                parent_corpus_id=master.id,
                config=config,
                metadata=child_def.get("metadata"),
            )
            if child and child.id:
                child_ids.append(child.id)

        # Update master with child references
        if child_ids:
            master_content = await master.get_content() or {}
            master_content["child_corpus_ids"] = child_ids
            
            await self.save_corpus(
                corpus_id=master.id,
                corpus_name=master.resource_id,
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
    ) -> list[str]:
        """Aggregate vocabularies from a corpus and its children.

        Args:
            corpus_id: Corpus ID to aggregate from
            config: Version configuration

        Returns:
            Aggregated vocabulary list
        """
        corpus = await self.get_corpus(corpus_id=corpus_id, config=config)
        if not corpus:
            return []

        # Get corpus vocabulary
        content = await corpus.get_content() or {}
        vocabulary = set(content.get("vocabulary", []))

        # Get child vocabularies
        child_ids = content.get("child_corpus_ids", [])
        for child_id in child_ids:
            child_vocab = await self.aggregate_vocabularies(child_id, config)
            vocabulary.update(child_vocab)

        return sorted(vocabulary)

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
        corpus = await self.get_corpus(
            corpus_id=corpus_id,
            corpus_name=corpus_name,
            config=config
        )
        if not corpus:
            return None

        if aggregate and corpus.id:
            return await self.aggregate_vocabularies(corpus.id, config)

        content = await corpus.get_content() or {}
        vocab = content.get("vocabulary", [])
        
        # Handle external storage (TODO: implement when FileManager is available)
        # if content_location := content.get("content_location"):
        #     external_content = await read_external_content(content_location)
        #     if external_content:
        #         vocab = external_content.get("vocabulary", vocab)
        
        return cast(list[str], vocab)

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

        content = await parent.get_content() or {}
        child_ids = content.get("child_corpus_ids", [])
        
        if child_id not in child_ids:
            child_ids.append(child_id)
            content["child_corpus_ids"] = child_ids
            
            saved = await self.save_corpus(
                corpus_id=parent.id,
                corpus_name=parent.resource_id,
                content=content,
                child_corpus_ids=child_ids,
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
    ) -> Corpus.Metadata | None:
        """Update an existing corpus.

        Args:
            corpus_id: Corpus ID (preferred)
            corpus_name: Corpus name (fallback)
            content: New content to merge
            metadata: New metadata to merge
            config: Version configuration

        Returns:
            Updated Corpus.Metadata or None
        """
        corpus = await self.get_corpus(
            corpus_id=corpus_id,
            corpus_name=corpus_name,
            config=config
        )
        if not corpus:
            return None

        # Merge content
        existing_content = await corpus.get_content() or {}
        if content:
            existing_content.update(content)

        # Merge metadata
        existing_metadata = corpus.metadata or {}
        if metadata:
            existing_metadata.update(metadata)

        # Save updated corpus
        return await self.save_corpus(
            corpus_id=corpus.id,
            corpus_name=corpus.resource_id,
            content=existing_content,
            metadata=existing_metadata,
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
        corpus = await self.get_corpus(
            corpus_id=corpus_id,
            corpus_name=corpus_name,
            config=config
        )
        if not corpus or not corpus.id:
            return False

        # Handle cascade deletion
        if cascade:
            content = await corpus.get_content() or {}
            child_ids = content.get("child_corpus_ids", [])
            for child_id in child_ids:
                await self.delete_corpus(
                    corpus_id=child_id,
                    cascade=True,
                    config=config
                )

        # Remove from parent if it has one
        if parent_id := corpus.metadata.get("parent_corpus_id"):
            await self.remove_child(
                parent_id=parent_id,
                child_id=corpus.id,
                delete_child=False,
                config=config
            )

        # Delete the corpus
        await corpus.delete()
        return True

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

        content = await parent.get_content() or {}
        child_ids = content.get("child_corpus_ids", [])
        
        if child_id in child_ids:
            child_ids.remove(child_id)
            content["child_corpus_ids"] = child_ids
            
            saved = await self.save_corpus(
                corpus_id=parent.id,
                corpus_name=parent.resource_id,
                content=content,
                child_corpus_ids=child_ids,
                config=config,
            )
            
            if not saved:
                return False

        # Delete the child if requested
        if delete_child:
            await self.delete_corpus(
                corpus_id=child_id,
                cascade=False,
                config=config
            )

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

from typing import Any

from beanie import PydanticObjectId

from ..caching.core import load_external_content, store_external_content
from ..corpus.utils import get_vocabulary_hash

from ..caching.manager import VersionedDataManager, get_version_manager
from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..models.base import Language
from .models import (
    CorpusMetadata,
    CorpusType,
)


class TreeCorpusManager:
    """Manages corpus trees with automatic vocabulary aggregation."""

    def __init__(self, version_manager: VersionedDataManager | None = None):
        """Initialize with version manager.

        Args:
            version_manager: VersionedDataManager instance (defaults to global)
        """
        self.vm = version_manager or get_version_manager()

    async def save_corpus(
        self,
        corpus_name: str,
        content: dict[str, Any],
        corpus_type: CorpusType = CorpusType.LEXICON,
        language: Language = Language.ENGLISH,
        parent_id: PydanticObjectId | None = None,
        config: VersionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CorpusMetadata:
        """Save a corpus with versioning and tree support.

        Args:
            corpus_name: Name/ID of the corpus
            content: Corpus content (vocabulary, etc.)
            corpus_type: Type of corpus
            language: Language of the corpus
            parent_id: Parent corpus ID if part of tree
            config: Version configuration
            metadata: Additional metadata

        Returns:
            Saved CorpusMetadata instance
        """
        # Prepare metadata
        full_metadata = {
            "corpus_type": corpus_type.value,
            "language": language.value,
            **(metadata or {}),
        }

        # Save using version manager
        saved = await self.vm.save(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
            config=config or VersionConfig(),
            metadata=full_metadata,
        )

        # Handle tree structures
        if parent_id and saved.id:
            await self.update_parent(parent_id, saved.id)

        return saved

    async def get_corpus(
        self,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> CorpusMetadata | None:
        """Get a corpus by name.

        Args:
            corpus_name: Name/ID of the corpus
            config: Version configuration

        Returns:
            CorpusMetadata instance or None
        """
        return await self.vm.get_latest(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

    async def create_tree(
        self,
        master_name: str,
        language: Language,
        children: list[dict[str, Any]],
        config: VersionConfig = VersionConfig(),
    ) -> CorpusMetadata:
        """Create corpus tree with master and children.

        Args:
            master_name: Name for the master corpus
            language: Language of the corpus
            children: List of child corpus configurations
            config: Version configuration

        Returns:
            Master corpus with aggregated vocabulary
        """
        from ..models.dictionary import CorpusType

        child_ids: list[PydanticObjectId] = []

        # Create children
        for child_config in children:
            child = await self.vm.save(
                resource_id=child_config["id"],
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content=child_config["content"],
                config=config,
                metadata=child_config.get("metadata", {}),
            )
            if child.id:
                child_ids.append(child.id)

        # Create master
        master = await self.vm.save(
            resource_id=master_name,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": []},  # Will be aggregated
            config=config,
            metadata={
                "corpus_type": CorpusType.LANGUAGE.value,
                "is_master": True,
                "language": language.value,
            },
            dependencies=child_ids,
        )

        if master.id is None:
            raise ValueError("Failed to create master corpus")

        # Aggregate vocabularies
        await self.aggregate_vocabularies(master.id, child_ids)

        return master

    async def aggregate_vocabularies(
        self, master_id: PydanticObjectId, child_ids: list[PydanticObjectId]
    ) -> None:
        """Aggregate child vocabularies into master via set union.

        Args:
            master_id: ID of the master corpus
            child_ids: IDs of child corpora
        """
        master = await CorpusMetadata.get(master_id)
        if not master or not master.is_master:
            return

        all_vocab: set[str] = set()

        for child_id in child_ids:
            child = await CorpusMetadata.get(child_id)
            if child:
                vocab = await self.get_vocabulary(child)
                all_vocab.update(vocab)

        # Update master
        master.vocabulary_size = len(all_vocab)
        master.vocabulary_hash = get_vocabulary_hash(all_vocab)

        # Store vocabulary externally if large
        if len(all_vocab) > 10_000:
            master.vocabulary = await store_external_content(
                sorted(list(all_vocab)),
                master.namespace,
                f"corpus:{master.resource_id}:vocab",
            )
        else:
            master.content_inline = {"vocabulary": sorted(list(all_vocab))}

        await master.save()

    async def get_vocabulary(self, corpus: CorpusMetadata) -> list[str]:
        """Get vocabulary from a corpus, handling inline and external storage.

        Args:
            corpus: CorpusMetadata instance

        Returns:
            List of vocabulary words
        """
        # Try inline content first
        if corpus.content_inline and "vocabulary" in corpus.content_inline:
            return corpus.content_inline["vocabulary"]

        # Try external vocabulary storage
        if corpus.vocabulary:
            vocab = await load_external_content(corpus.vocabulary)
            if vocab:
                return vocab

        # Try general content retrieval
        content = await corpus.get_content()
        if content and isinstance(content, dict) and "vocabulary" in content:
            return content["vocabulary"]

        # Return empty list if no vocabulary found
        return []

    async def update_parent(
        self, parent_id: PydanticObjectId, child_id: PydanticObjectId
    ) -> None:
        """Update parent when child is added.

        Args:
            parent_id: ID of parent corpus
            child_id: ID of child corpus to add
        """
        parent = await CorpusMetadata.get(parent_id)
        child = await CorpusMetadata.get(child_id)

        if parent and child:
            if child_id not in parent.child_corpus_ids:
                parent.child_corpus_ids.append(child_id)

            child.parent_corpus_id = parent_id

            await parent.save()
            await child.save()

            if parent.is_master:
                await self.aggregate_vocabularies(parent_id, parent.child_corpus_ids)


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

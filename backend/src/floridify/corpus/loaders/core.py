"""Base loader class for corpus management.

Provides abstract interface for language and literature corpus loaders
with deep integration of VersionManager and TreeCorpusManager for
hierarchical, versioned corpus management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from ...caching.manager import (
    TreeCorpusManager,
    VersionedDataManager,
    get_tree_corpus_manager,
    get_version_manager,
)
from ...models.dictionary import CorpusType, Language
from ...models.versioned import CorpusMetadata, VersionConfig
from ...utils.logging import get_logger
from ..core import Corpus

logger = get_logger(__name__)

# Type variable for corpus models
CorpusModel = TypeVar("CorpusModel", bound=Corpus)


class BaseCorpusLoader[CorpusModel](ABC):
    """Abstract base class for corpus loaders.

    Provides hierarchical corpus management with source-level granularity,
    automatic propagation of updates through the tree structure, and
    deep integration with VersionManager for versioned storage.

    Key Features:
    - Source-level granularity for incremental updates
    - Hierarchical tree structure with automatic aggregation
    - Versioned storage with content deduplication
    - Unified interface for language and literature corpora
    """

    def __init__(
        self,
        corpus_type: CorpusType,
        default_language: Language = Language.ENGLISH,
    ) -> None:
        """Initialize base corpus loader with managers.

        Args:
            corpus_type: Type of corpus (LANGUAGE or LITERATURE)
            default_language: Default language for corpora
        """
        self.corpus_type = corpus_type
        self.default_language = default_language

        # Deep integration with managers
        self.tree_manager: TreeCorpusManager = get_tree_corpus_manager()
        self.version_manager: VersionedDataManager = get_version_manager()

        # In-memory cache of corpus models
        self._corpus_cache: dict[str, CorpusModel] = {}

    @abstractmethod
    async def build_corpus(
        self,
        corpus_name: str,
        sources: list[dict[str, Any]],
        config: VersionConfig | None = None,
    ) -> CorpusModel:
        """Build a complete corpus from multiple sources.

        This method should:
        1. Create individual source corpora
        2. Aggregate vocabularies
        3. Create master corpus with tree structure
        4. Save with versioning

        Args:
            corpus_name: Name for the corpus
            sources: List of source configurations
            config: Version configuration

        Returns:
            Built corpus model (LanguageCorpus or LiteratureCorpus)
        """

    @abstractmethod
    async def rebuild_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> CorpusModel:
        """Rebuild a specific source within a corpus.

        This method should:
        1. Load existing corpus
        2. Rebuild only the specified source
        3. Update aggregated vocabulary
        4. Propagate changes through tree
        5. Save new version

        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the source to rebuild
            config: Version configuration

        Returns:
            Updated corpus model with propagated changes
        """

    @abstractmethod
    async def add_source(
        self,
        corpus_name: str,
        source_name: str,
        source_data: dict[str, Any],
        config: VersionConfig | None = None,
    ) -> CorpusModel:
        """Add a new source to an existing corpus.

        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the new source
            source_data: Configuration for the new source
            config: Version configuration

        Returns:
            Updated corpus model with new source
        """

    @abstractmethod
    async def remove_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> CorpusModel:
        """Remove a source from a corpus.

        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the source to remove
            config: Version configuration

        Returns:
            Updated corpus model without the source
        """

    @abstractmethod
    async def list_sources(
        self,
        corpus_name: str,
    ) -> list[str]:
        """List all sources in a corpus.

        Args:
            corpus_name: Name of the corpus

        Returns:
            List of source names
        """

    @abstractmethod
    def _create_corpus_model(
        self,
        corpus_name: str,
        vocabulary: list[str],
        sources: list[str],
        metadata: dict[str, Any],
    ) -> CorpusModel:
        """Create the appropriate corpus model (LanguageCorpus or LiteratureCorpus).

        Must be implemented by subclasses to return the correct model type.

        Args:
            corpus_name: Name of the corpus
            vocabulary: Aggregated vocabulary
            sources: List of source names
            metadata: Additional metadata

        Returns:
            Corpus model instance
        """

    async def get_corpus(
        self,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> CorpusModel | None:
        """Get an existing corpus by name with versioning support.

        Args:
            corpus_name: Name of the corpus
            config: Version configuration

        Returns:
            Corpus model or None if not found
        """
        # Check in-memory cache first
        if corpus_name in self._corpus_cache and not (config and config.force_rebuild):
            return self._corpus_cache[corpus_name]

        # Load from versioned storage via tree manager
        corpus_metadata = await self.tree_manager.get_corpus(
            corpus_name=corpus_name,
            config=config or VersionConfig(),
        )

        if not corpus_metadata:
            return None

        # Load content and create model
        content = await corpus_metadata.get_content()
        if not content:
            return None

        # Create appropriate model from content
        model = self._create_corpus_model(
            corpus_name=corpus_name,
            vocabulary=content.get("vocabulary", []),
            sources=content.get("sources", []),
            metadata=corpus_metadata.metadata,
        )

        # Cache the model
        self._corpus_cache[corpus_name] = model

        return model

    async def save_corpus(
        self,
        corpus: CorpusModel,
        config: VersionConfig | None = None,
    ) -> CorpusMetadata:
        """Save a corpus with versioning and tree support.

        Args:
            corpus: Corpus model to save
            config: Version configuration

        Returns:
            Saved CorpusMetadata with version info
        """
        # Update in-memory cache
        corpus_name = getattr(corpus, "corpus_name")
        self._corpus_cache[corpus_name] = corpus

        # Prepare content for storage
        content = {
            "vocabulary": getattr(corpus, "vocabulary", []),
            "normalized_vocabulary": getattr(corpus, "normalized_vocabulary", []),
            "lemmatized_vocabulary": getattr(corpus, "lemmatized_vocabulary", []),
            "sources": corpus.sources if hasattr(corpus, "sources") else [],
            "metadata": corpus.metadata if hasattr(corpus, "metadata") else {},
        }

        # Add source vocabularies for LanguageCorpus
        if hasattr(corpus, "source_vocabularies"):
            content["source_vocabularies"] = corpus.source_vocabularies

        # Add work vocabularies for LiteratureCorpus
        if hasattr(corpus, "work_vocabularies"):
            content["work_vocabularies"] = corpus.work_vocabularies
        if hasattr(corpus, "author_vocabularies"):
            content["author_vocabularies"] = corpus.author_vocabularies

        # Save via tree manager with versioning
        vocabulary = getattr(corpus, "vocabulary", [])
        corpus_metadata = getattr(corpus, "metadata", {})
        metadata = await self.tree_manager.save_corpus(
            corpus_name=corpus_name,
            content=content,
            corpus_type=self.corpus_type,
            language=getattr(corpus, "language", self.default_language),
            config=config or VersionConfig(increment_version=True),
            metadata={
                "vocabulary_size": len(vocabulary),
                "unique_words": getattr(corpus, "unique_words", len(set(vocabulary))),
                "vocabulary_hash": getattr(corpus, "vocabulary_hash", ""),
                **corpus_metadata,
            },
        )

        logger.info(
            f"Saved {self.corpus_type.value} corpus '{corpus_name}' "
            f"version {metadata.version_info.version} with {len(vocabulary)} words"
        )

        return metadata

    async def delete_corpus(
        self,
        corpus_name: str,
        delete_children: bool = True,
    ) -> bool:
        """Delete a corpus and optionally its children.

        Args:
            corpus_name: Name of the corpus to delete
            delete_children: Whether to delete child corpora

        Returns:
            True if deleted, False if not found
        """
        # Remove from cache
        if corpus_name in self._corpus_cache:
            del self._corpus_cache[corpus_name]

        # Get corpus metadata
        corpus_metadata = await self.tree_manager.get_corpus(corpus_name)

        if not corpus_metadata:
            return False

        # Delete children if requested
        if delete_children and corpus_metadata.child_corpus_ids:
            for child_id in corpus_metadata.child_corpus_ids:
                child = await CorpusMetadata.get(child_id)
                if child:
                    await self.delete_corpus(child.resource_id, delete_children=True)

        # Delete the corpus itself
        await corpus_metadata.delete()

        action = "its children" if delete_children else "kept children"
        logger.info(f"Deleted corpus '{corpus_name}' and {action}")
        return True

    async def create_corpus_tree(
        self,
        master_name: str,
        source_configs: list[dict[str, Any]],
        config: VersionConfig | None = None,
    ) -> CorpusModel:
        """Create a hierarchical corpus tree with automatic aggregation.

        This method creates:
        1. Individual source corpora as children
        2. Master corpus that aggregates all children
        3. Tree relationships for automatic updates

        Args:
            master_name: Name for the master corpus
            source_configs: List of source configurations
            config: Version configuration

        Returns:
            Master corpus with aggregated vocabulary
        """
        config = config or VersionConfig()

        # Build individual source corpora
        source_corpora: list[CorpusModel] = []
        for source_config in source_configs:
            source_corpus = await self.build_corpus(
                corpus_name=source_config["name"],
                sources=[source_config],
                config=config,
            )
            source_corpora.append(source_corpus)

        # Aggregate vocabularies
        all_vocabulary: set[str] = set()
        all_sources: list[str] = []

        for source_corpus in source_corpora:
            all_vocabulary.update(getattr(source_corpus, "vocabulary", []))
            all_sources.extend(
                getattr(source_corpus, "sources", [getattr(source_corpus, "corpus_name")])
            )

        # Create master corpus
        master_corpus = self._create_corpus_model(
            corpus_name=master_name,
            vocabulary=sorted(list(all_vocabulary)),
            sources=all_sources,
            metadata={
                "is_master": True,
                "child_count": len(source_corpora),
                "source_count": len(all_sources),
            },
        )

        # Save master with tree relationships
        master_metadata = await self.save_corpus(master_corpus, config)

        # Update children to point to parent
        if master_metadata.id:
            for source_corpus in source_corpora:
                child_name = getattr(source_corpus, "corpus_name")
                child_metadata = await self.tree_manager.get_corpus(child_name)
                if child_metadata and child_metadata.id:
                    await self.tree_manager.update_parent(master_metadata.id, child_metadata.id)

        logger.info(
            f"Created corpus tree '{master_name}' with {len(source_corpora)} children "
            f"and {len(all_vocabulary)} total words"
        )

        return master_corpus

    async def update_corpus_tree(
        self,
        master_name: str,
        source_name: str,
        operation: str,
        config: VersionConfig | None = None,
        **kwargs: Any,
    ) -> CorpusModel:
        """Update a corpus tree with automatic propagation.

        Operations:
        - "rebuild": Rebuild a specific source
        - "add": Add a new source
        - "remove": Remove a source

        Changes automatically propagate through the tree structure.

        Args:
            master_name: Name of the master corpus
            source_name: Name of the source to update
            operation: Operation to perform
            config: Version configuration
            **kwargs: Operation-specific parameters

        Returns:
            Updated master corpus
        """
        config = config or VersionConfig(increment_version=True)

        # Get master corpus
        master = await self.get_corpus(master_name, config)
        if not master:
            raise ValueError(f"Master corpus '{master_name}' not found")

        # Perform operation
        if operation == "rebuild":
            await self.rebuild_source(master_name, source_name, config)
        elif operation == "add":
            source_data = kwargs.get("source_data", {})
            await self.add_source(master_name, source_name, source_data, config)
        elif operation == "remove":
            await self.remove_source(master_name, source_name, config)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Reload master with updated vocabulary
        updated_master = await self.get_corpus(master_name, VersionConfig(force_rebuild=True))
        if not updated_master:
            raise ValueError(f"Failed to reload master corpus '{master_name}'")

        # Tree manager handles automatic aggregation via aggregate_vocabularies

        return updated_master

    def _calculate_metrics(self, vocabulary: list[str]) -> dict[str, float]:
        """Calculate vocabulary metrics.

        Args:
            vocabulary: List of words

        Returns:
            Dictionary of calculated metrics
        """
        if not vocabulary:
            return {
                "vocabulary_diversity": 0.0,
                "average_word_length": 0.0,
                "unique_ratio": 0.0,
                "total_words": 0,
                "unique_words": 0,
            }

        # Calculate unique words
        unique_words = set(vocabulary)
        unique_ratio = len(unique_words) / len(vocabulary) if vocabulary else 0.0

        # Calculate vocabulary diversity (type-token ratio)
        vocabulary_diversity = len(unique_words) / len(vocabulary) if vocabulary else 0.0

        # Calculate average word length
        total_length = sum(len(word) for word in unique_words)
        average_word_length = total_length / len(unique_words) if unique_words else 0.0

        return {
            "vocabulary_diversity": vocabulary_diversity,
            "average_word_length": average_word_length,
            "unique_ratio": unique_ratio,
            "total_words": len(vocabulary),
            "unique_words": len(unique_words),
        }

    async def get_corpus_versions(
        self,
        corpus_name: str,
    ) -> list[str]:
        """List all versions of a corpus.

        Args:
            corpus_name: Name of the corpus

        Returns:
            List of version strings
        """
        from ...models.versioned import ResourceType

        return await self.version_manager.list_versions(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
        )

    async def get_corpus_by_version(
        self,
        corpus_name: str,
        version: str,
    ) -> CorpusModel | None:
        """Get a specific version of a corpus.

        Args:
            corpus_name: Name of the corpus
            version: Version string (e.g., "1.0.0")

        Returns:
            Corpus model or None if not found
        """
        config = VersionConfig(version=version)
        return await self.get_corpus(corpus_name, config)

"""Versioned data manager for unified caching and content management."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, TypeVar

from beanie import PydanticObjectId

from ..models.dictionary import CorpusType, Language
from ..models.versioned import (
    BaseVersionedData,
    CorpusMetadata,
    DictionaryEntryMetadata,
    LiteratureEntryMetadata,
    ResourceType,
    SearchIndexMetadata,
    SemanticIndexMetadata,
    TrieIndexMetadata,
    VersionConfig,
    VersionInfo,
)
from ..utils.logging import get_logger
from .core import GlobalCacheManager, get_global_cache
from .models import CacheNamespace

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseVersionedData)


class VersionedDataManager:
    """Manages versioned data with proper typing and performance optimization."""

    def __init__(self) -> None:
        """Initialize with cache integration."""
        self.cache: GlobalCacheManager | None = (
            None  # Will be initialized lazily (GlobalCacheManager)
        )
        self.lock = asyncio.Lock()

    async def save(
        self,
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig = VersionConfig(),
        metadata: dict[str, Any] | None = None,
        dependencies: list[PydanticObjectId] | None = None,
    ) -> BaseVersionedData:
        """Save with versioning and optimal serialization."""
        # Single serialization with sorted keys
        content_str = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Check for duplicate
        if not config.force_rebuild:
            existing = await self._find_by_hash(resource_id, content_hash)
            if existing:
                logger.debug(
                    f"Found existing version for {resource_id} with same content"
                )
                return existing

        # Get latest for version increment
        latest = None
        if config.increment_version:
            latest = await self.get_latest(
                resource_id, resource_type, use_cache=not config.force_rebuild
            )

        new_version = config.version or (
            self._increment_version(latest.version_info.version)
            if latest and config.increment_version
            else "1.0.0"
        )

        # Create versioned instance
        model_class = self._get_model_class(resource_type)
        versioned = model_class(
            resource_id=resource_id,
            resource_type=resource_type,
            namespace=namespace,
            version_info=VersionInfo(
                version=new_version,
                data_hash=content_hash,
                is_latest=True,
                supersedes=latest.id if latest else None,
                dependencies=dependencies or [],
            ),
            metadata={**config.metadata, **(metadata or {})},
            ttl=config.ttl,
        )

        # Set content with automatic storage strategy
        await versioned.set_content(content)

        # Atomic save with version chain update
        async with self.lock:
            if latest and config.increment_version:
                latest.version_info.is_latest = False
                latest.version_info.superseded_by = versioned.id
                await latest.save()

            await versioned.save()

            # Tree structures handled by TreeCorpusManager for corpus types

        # Cache if enabled
        if config.use_cache:
            if self.cache is None:
                self.cache = await get_global_cache()
            cache_key = f"{resource_type.value}:{resource_id}"
            await self.cache.set(namespace, cache_key, versioned, config.ttl)

        logger.info(
            f"Saved {resource_type.value} '{resource_id}' version {new_version}"
        )
        return versioned

    async def get_latest(
        self,
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool = True,
        config: VersionConfig = VersionConfig(),
    ) -> BaseVersionedData | None:
        """Get latest version with proper typing."""
        namespace = self._get_namespace(resource_type)

        # Check cache unless forced
        if use_cache and not config.force_rebuild:
            cache_key = f"{resource_type.value}:{resource_id}"

            # Handle specific version request
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"

            if self.cache is None:
                self.cache = await get_global_cache()
            cached = await self.cache.get(namespace, cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached  # type: ignore[no-any-return]

        # Query database
        model_class = self._get_model_class(resource_type)

        if config.version:
            # Get specific version
            result = await model_class.find_one(
                model_class.resource_id == resource_id,
                model_class.version_info.version == config.version,
            )
        else:
            # Get latest
            result = await model_class.find_one(
                model_class.resource_id == resource_id,
                model_class.version_info.is_latest,
            )

        # Cache result
        if result and use_cache:
            cache_key = f"{resource_type.value}:{resource_id}"
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"
            if self.cache is None:
                self.cache = await get_global_cache()
            await self.cache.set(namespace, cache_key, result, result.ttl)

        return result

    async def get_by_version(
        self,
        resource_id: str,
        resource_type: ResourceType,
        version: str,
        use_cache: bool = True,
    ) -> BaseVersionedData | None:
        """Get specific version of a resource."""
        config = VersionConfig(version=version, use_cache=use_cache)
        return await self.get_latest(resource_id, resource_type, use_cache, config)

    async def list_versions(
        self, resource_id: str, resource_type: ResourceType
    ) -> list[str]:
        """List all versions of a resource."""
        model_class = self._get_model_class(resource_type)
        results = await model_class.find(
            model_class.resource_id == resource_id
        ).to_list()
        return [r.version_info.version for r in results]

    async def delete_version(
        self, resource_id: str, resource_type: ResourceType, version: str
    ) -> bool:
        """Delete a specific version."""
        model_class = self._get_model_class(resource_type)
        result = await model_class.find_one(
            model_class.resource_id == resource_id,
            model_class.version_info.version == version,
        )

        if result:
            # Update version chain
            if result.version_info.superseded_by:
                next_version = await model_class.get(result.version_info.superseded_by)
                if next_version:
                    next_version.version_info.supersedes = (
                        result.version_info.supersedes
                    )
                    await next_version.save()

            if result.version_info.supersedes:
                prev_version = await model_class.get(result.version_info.supersedes)
                if prev_version:
                    prev_version.version_info.superseded_by = (
                        result.version_info.superseded_by
                    )
                    if result.version_info.is_latest:
                        prev_version.version_info.is_latest = True
                    await prev_version.save()

            await result.delete()

            # Clear cache
            namespace = self._get_namespace(resource_type)
            cache_key = f"{resource_type.value}:{resource_id}:v{version}"
            if self.cache is None:
                self.cache = await get_global_cache()
            await self.cache.delete(namespace, cache_key)

            logger.info(f"Deleted {resource_type.value} '{resource_id}' v{version}")
            return True

        return False

    async def _find_by_hash(
        self, resource_id: str, content_hash: str
    ) -> BaseVersionedData | None:
        """Find existing version with same content hash."""
        # Check all resource types for deduplication
        for resource_type in ResourceType:
            model_class = self._get_model_class(resource_type)
            result = await model_class.find_one(
                model_class.resource_id == resource_id,
                model_class.version_info.data_hash == content_hash,
            )
            if result:
                return result
        return None

    def _get_model_class(self, resource_type: ResourceType) -> type[BaseVersionedData]:
        """Map resource type enum to model class."""
        mapping = {
            ResourceType.DICTIONARY: DictionaryEntryMetadata,
            ResourceType.CORPUS: CorpusMetadata,
            ResourceType.SEMANTIC: SemanticIndexMetadata,
            ResourceType.LITERATURE: LiteratureEntryMetadata,
            ResourceType.TRIE: TrieIndexMetadata,
            ResourceType.SEARCH: SearchIndexMetadata,
        }
        return mapping[resource_type]

    def _get_namespace(self, resource_type: ResourceType) -> CacheNamespace:
        """Map resource type enum to namespace."""
        mapping = {
            ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
            ResourceType.CORPUS: CacheNamespace.CORPUS,
            ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
            ResourceType.LITERATURE: CacheNamespace.LITERATURE,
            ResourceType.TRIE: CacheNamespace.TRIE,
            ResourceType.SEARCH: CacheNamespace.SEARCH,
        }
        return mapping[resource_type]

    def _increment_version(self, version: str) -> str:
        """Increment patch version."""
        major, minor, patch = version.split(".")
        return f"{major}.{minor}.{int(patch) + 1}"


# Global singleton instance
_version_manager: VersionedDataManager | None = None


def get_version_manager() -> VersionedDataManager:
    """Get the global version manager instance.

    Returns:
        VersionedDataManager singleton
    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionedDataManager()
    return _version_manager


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
        master.vocabulary_hash = hashlib.sha256(
            "".join(sorted(all_vocab)).encode()
        ).hexdigest()

        # Store vocabulary externally if large
        if len(all_vocab) > 10_000:
            from ..caching.core import store_external_content

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
            from ..caching.core import load_external_content
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

"""Unified corpus manager with versioning support."""

from __future__ import annotations

from datetime import timedelta

from ..caching.models import CacheNamespace, CacheTTL
from ..caching.manager import BaseManager
from ..core.constants import ResourceType
from ..caching.versioned import (
    VersionConfig,
    VersionedDataManager,
    get_corpus_version_manager,
)
from ..models.dictionary import Language
from ..models.versioned import CorpusVersionedData
from ..providers.literature.manager import get_literature_manager
from ..utils.logging import get_logger
from .core import Corpus
from .loaders.language import CorpusLanguageLoader
from .loaders.literature import LiteratureCorpusLoader
from .models import CorpusMetadata, LexiconData

logger = get_logger(__name__)


class CorpusManager(BaseManager[Corpus, CorpusMetadata]):
    """Base manager for corpus operations with versioning."""

    def __init__(self) -> None:
        """Initialize the corpus manager."""
        super().__init__()

    @property
    def cache_namespace(self) -> CacheNamespace:
        """Get the resource type this manager handles."""
        return CacheNamespace.CORPUS

    def _get_version_manager(self) -> VersionedDataManager[CorpusVersionedData]:
        """Get the version manager for corpus data."""
        return get_corpus_version_manager()

    async def _reconstruct_resource(
        self, versioned_data: CorpusVersionedData
    ) -> Corpus | None:
        """Reconstruct corpus from versioned data."""
        try:
            # Load inline content if available
            if versioned_data.content_inline:
                lexicon_data = LexiconData(**versioned_data.content_inline)
                corpus = Corpus(corpus_name=versioned_data.resource_id)
                corpus.vocabulary = lexicon_data.vocabulary
                corpus.original_vocabulary = lexicon_data.vocabulary.copy()
                return corpus
            if versioned_data.content_location:
                # Load content from storage
                version_manager = self._get_version_manager()
                content = await version_manager.load_content(
                    versioned_data.content_location
                )
                if content:
                    lexicon_data = LexiconData(**content)
                    corpus = Corpus(corpus_name=versioned_data.resource_id)
                    corpus.vocabulary = lexicon_data.vocabulary
                    corpus.original_vocabulary = lexicon_data.vocabulary.copy()
                    return corpus
            return None
        except Exception:
            return None

    async def create_corpus(
        self,
        name: str,
        vocabulary: list[str],
        sources: list[str] | None = None,
        language: Language = Language.ENGLISH,
        use_ttl: bool = True,
    ) -> CorpusMetadata:
        """Create a new corpus from vocabulary.

        Args:
            name: Corpus name
            vocabulary: List of words/phrases for the corpus
            sources: Optional list of source identifiers
            language: Corpus language
            use_ttl: Whether to use TTL for caching

        Returns:
            Corpus metadata

        """
        # Build corpus from vocabulary
        corpus = Corpus(corpus_name=name)
        corpus.vocabulary = vocabulary
        corpus.original_vocabulary = vocabulary.copy()

        # Create metadata with cache information
        metadata = CorpusMetadata(
            corpus_id=name,
            name=name,
            language=language,
            total_entries=len(corpus.vocabulary),
            unique_entries=len(set(corpus.vocabulary)),
        )
        metadata.generate_cache_key("corpus", name, "1.0.0", corpus.vocabulary_hash)
        metadata.set_ttl(CacheTTL.CORPUS if use_ttl else None)
        metadata.cache_tags = ["corpus", language.value]

        # Configure versioning
        config = VersionConfig(
            save_versions=True,
            ttl=CacheTTL.CORPUS if use_ttl else None,
        )

        # Save to versioned storage
        lexicon_data = LexiconData(
            vocabulary=list(corpus.vocabulary),
            sources=sources or [],
            metadata={"language": language.value},
        )

        version_manager = self._get_version_manager()
        await version_manager.save(
            resource_id=name,
            content=lexicon_data.model_dump(),
            resource_type=self.resource_type.value,
            metadata=metadata.model_dump(),
            tags=["corpus", language.value],
            config=config,
            corpus_name=name,
            language=language.value,
            corpus_type="custom",
            unique_word_count=len(set(corpus.vocabulary)),
            total_sources=len(sources) if sources else 0,
        )

        # Cache the corpus
        self._cache[name] = corpus

        # Save metadata to MongoDB
        await metadata.save()

        return metadata

    async def get_corpus(
        self,
        name: str,
        use_ttl: bool = True,
    ) -> Corpus | None:
        """Get a corpus by name.

        Args:
            name: Corpus name
            use_ttl: Whether to use TTL for caching

        Returns:
            Corpus instance or None

        """
        return await self.get(name, use_ttl)

    async def get_or_create_corpus(
        self,
        name: str,
        vocabulary: list[str] | None = None,
        sources: list[str] | None = None,
        language: Language = Language.ENGLISH,
        use_ttl: bool = True,
    ) -> tuple[Corpus, CorpusMetadata]:
        """Get existing corpus or create new one.

        Args:
            name: Corpus name
            vocabulary: List of words/phrases (required for creation)
            sources: Optional list of source identifiers
            language: Corpus language
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (corpus, metadata)

        """
        # Try to get existing corpus
        corpus = await self.get_corpus(name, use_ttl)
        if corpus:
            metadata = await CorpusMetadata.find_one({"corpus_id": name})
            if metadata:
                return corpus, metadata

        # Create new corpus if vocabulary provided
        if vocabulary is None:
            raise ValueError(f"Vocabulary required to create corpus '{name}'")

        metadata = await self.create_corpus(
            name=name,
            vocabulary=vocabulary,
            sources=sources,
            language=language,
            use_ttl=use_ttl,
        )
        corpus = self._cache[name]
        return corpus, metadata

    async def get_or_create(
        self,
        name: str,
        vocabulary: list[str] | None = None,
        sources: list[str] | None = None,
        language: Language = Language.ENGLISH,
        use_ttl: bool = True,
    ) -> tuple[Corpus, CorpusMetadata]:
        """Simplified get or create method.

        Args:
            name: Corpus name
            vocabulary: List of words/phrases (required for creation)
            sources: Optional list of source identifiers
            language: Corpus language
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (corpus, metadata)

        """
        return await self.get_or_create_corpus(
            name, vocabulary, sources, language, use_ttl
        )

    async def update_corpus(
        self,
        name: str,
        new_vocabulary: list[str],
        new_sources: list[str] | None = None,
        use_ttl: bool = True,
    ) -> CorpusMetadata | None:
        """Update an existing corpus with new vocabulary.

        Args:
            name: Corpus name
            new_vocabulary: Additional vocabulary to add
            new_sources: Optional new sources
            use_ttl: Whether to use TTL for caching

        Returns:
            Updated metadata or None

        """
        corpus = await self.get_corpus(name, use_ttl)
        if not corpus:
            return None

        # Add new vocabulary
        corpus.vocabulary.extend(new_vocabulary)
        corpus.original_vocabulary.extend(new_vocabulary)

        # Update metadata with new version
        metadata = await CorpusMetadata.find_one({"corpus_id": name})
        if metadata:
            # Update cache key with new version
            version_manager = self._get_version_manager()
            next_version = await version_manager._get_next_version(name)
            metadata.generate_cache_key(
                "corpus", name, next_version, corpus.vocabulary_hash
            )
            metadata.total_entries = len(corpus.vocabulary)
            metadata.unique_entries = len(set(corpus.vocabulary))

            # Configure versioning
            config = VersionConfig(
                save_versions=True,
                ttl=CacheTTL.CORPUS if use_ttl else None,
            )

            # Save new version
            lexicon_data = LexiconData(
                vocabulary=list(corpus.vocabulary),
                sources=new_sources or [],
                metadata={"updated": True},
            )

            await version_manager.save(
                resource_id=name,
                content=lexicon_data.model_dump(),
                resource_type=self.resource_type.value,
                metadata=metadata.model_dump(),
                config=config,
            )

            await metadata.save()

        return metadata


class LanguageCorpusManager(CorpusManager):
    """Manager for language-specific corpora."""

    def __init__(self) -> None:
        """Initialize the language corpus manager."""
        super().__init__()
        self.language_loaders: dict[Language, CorpusLanguageLoader] = {}

    async def load_language_corpus(
        self,
        language: Language,
        use_ttl: bool = True,
    ) -> CorpusMetadata:
        """Load a language corpus from sources.

        Args:
            language: Language to load
            use_ttl: Whether to use TTL for caching

        Returns:
            Language corpus metadata

        """
        corpus_name = f"language_{language.value}"

        # Create language loader if needed
        if language not in self.language_loaders:
            self.language_loaders[language] = CorpusLanguageLoader()

        loader = self.language_loaders[language]

        # Load vocabulary for language
        vocabulary = loader.get_vocabulary_for_language(language)

        # Create corpus with vocabulary
        return await self.create_corpus(
            name=corpus_name,
            vocabulary=vocabulary,
            sources=["language_sources"],
            language=language,
            use_ttl=use_ttl,
        )

    async def get_or_create_language_corpus(
        self,
        language: Language,
        use_ttl: bool = True,
    ) -> tuple[Corpus, CorpusMetadata]:
        """Get or create a language corpus.

        Args:
            language: Language to load
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (corpus, metadata)

        """
        corpus_name = f"language_{language.value}"

        # Try to get existing
        corpus = await self.get_corpus(corpus_name, use_ttl)
        if corpus:
            metadata = await CorpusMetadata.find_one({"corpus_id": corpus_name})
            if metadata:
                return corpus, metadata

        # Create new
        metadata = await self.load_language_corpus(language, use_ttl)
        corpus = self._cache[corpus_name]
        return corpus, metadata


class LiteratureCorpusManager(CorpusManager):
    """Manager for literature-based corpora."""

    def __init__(self) -> None:
        """Initialize the literature corpus manager."""
        super().__init__()
        self.literature_manager = get_literature_manager()
        self.literature_loader = LiteratureCorpusLoader()

    async def create_author_corpus(
        self,
        author_name: str,
        max_works: int = 10,
        use_ttl: bool = True,
    ) -> CorpusMetadata:
        """Create a corpus from an author's works.

        Args:
            author_name: Author name
            max_works: Maximum works to include
            use_ttl: Whether to use TTL for caching

        Returns:
            Author corpus metadata

        """
        corpus_name = f"author_{author_name.lower().replace(' ', '_')}"

        # Load vocabulary from author works
        # For now, create a simple placeholder vocabulary
        # TODO: Implement actual author vocabulary loading
        vocabulary = [f"word_{i}" for i in range(100)]

        # Create corpus with vocabulary
        return await self.create_corpus(
            name=corpus_name,
            vocabulary=vocabulary,
            sources=[f"author:{author_name}"],
            language=Language.ENGLISH,
            use_ttl=use_ttl,
        )

    async def get_or_create_author_corpus(
        self,
        author_name: str,
        max_works: int = 10,
        use_ttl: bool = True,
    ) -> tuple[Corpus, CorpusMetadata]:
        """Get or create an author corpus.

        Args:
            author_name: Author name
            max_works: Maximum works to include
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (corpus, metadata)

        """
        corpus_name = f"author_{author_name.lower().replace(' ', '_')}"

        # Try to get existing
        corpus = await self.get_corpus(corpus_name, use_ttl)
        if corpus:
            metadata = await CorpusMetadata.find_one({"corpus_id": corpus_name})
            if metadata:
                return corpus, metadata

        # Create new
        metadata = await self.create_author_corpus(
            author_name=author_name,
            max_works=max_works,
            use_ttl=use_ttl,
        )
        corpus = self._cache[corpus_name]
        return corpus, metadata

    async def create_period_corpus(
        self,
        period: str,
        max_works: int = 50,
        use_ttl: bool = True,
    ) -> CorpusMetadata:
        """Create a corpus from a literary period.

        Args:
            period: Period name (e.g., "Victorian", "Romantic")
            max_works: Maximum works to include
            use_ttl: Whether to use TTL for caching

        Returns:
            Period corpus metadata

        """
        corpus_name = f"period_{period.lower()}"

        # Load vocabulary from period works
        # For now, create a simple placeholder vocabulary
        # TODO: Implement actual period vocabulary loading
        vocabulary = [f"period_word_{i}" for i in range(100)]

        # Create corpus with vocabulary
        return await self.create_corpus(
            name=corpus_name,
            vocabulary=vocabulary,
            sources=[f"period:{period}"],
            language=Language.ENGLISH,
            use_ttl=use_ttl,
        )

    async def get_or_create_period_corpus(
        self,
        period: str,
        max_works: int = 50,
        use_ttl: bool = True,
    ) -> tuple[Corpus, CorpusMetadata]:
        """Get or create a period corpus.

        Args:
            period: Period name
            max_works: Maximum works to include
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (corpus, metadata)

        """
        corpus_name = f"period_{period.lower()}"

        # Try to get existing
        corpus = await self.get_corpus(corpus_name, use_ttl)
        if corpus:
            metadata = await CorpusMetadata.find_one({"corpus_id": corpus_name})
            if metadata:
                return corpus, metadata

        # Create new
        metadata = await self.create_period_corpus(
            period=period,
            max_works=max_works,
            use_ttl=use_ttl,
        )
        corpus = self._cache[corpus_name]
        return corpus, metadata


# Global manager instances
_corpus_manager: CorpusManager | None = None
_language_corpus_manager: LanguageCorpusManager | None = None
_literature_corpus_manager: LiteratureCorpusManager | None = None


def get_corpus_manager() -> CorpusManager:
    """Get the global corpus manager instance."""
    global _corpus_manager
    if _corpus_manager is None:
        _corpus_manager = CorpusManager()
    return _corpus_manager


def get_language_corpus_manager() -> LanguageCorpusManager:
    """Get the global language corpus manager instance."""
    global _language_corpus_manager
    if _language_corpus_manager is None:
        _language_corpus_manager = LanguageCorpusManager()
    return _language_corpus_manager


def get_literature_corpus_manager() -> LiteratureCorpusManager:
    """Get the global literature corpus manager instance."""
    global _literature_corpus_manager
    if _literature_corpus_manager is None:
        _literature_corpus_manager = LiteratureCorpusManager()
    return _literature_corpus_manager

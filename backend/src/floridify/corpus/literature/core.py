"""Literature corpus implementation with provider pattern and enhanced metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ...caching.models import BaseVersionedData, ResourceType, VersionConfig
from ...models.base import Language
from ...models.literature import (
    AuthorInfo,
    Genre,
    LiteratureEntry,
    LiteratureProvider,
    Period,
)
from ...models.versioned import register_model
from ...providers.literature.core import LiteratureConnector
from ...utils.logging import get_logger
from ..core import MultisourceCorpus
from ..models import CorpusType

logger = get_logger(__name__)


class LiteratureEntryMetadata(BaseModel):
    """Enhanced metadata for literature entries."""
    
    title: str
    author: AuthorInfo
    provider: LiteratureProvider
    source_url: str | None = None
    gutenberg_id: str | None = None
    year: int | None = None
    genre: Genre | None = None
    period: Period | None = None
    language: Language = Language.ENGLISH
    query: str | None = None
    file_path: str | None = None  # For LOCAL_FILE provider
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnhancedLiteratureEntry(LiteratureEntry):
    """Enhanced literature entry with provider information and metadata."""
    
    provider: LiteratureProvider
    source_url: str | None = None
    query: str | None = None
    file_path: str | None = None
    extracted_vocabulary: list[str] = Field(default_factory=list)
    metadata: LiteratureEntryMetadata | None = None


@register_model(ResourceType.LITERATURE)
class LiteratureCorpusMetadata(BaseVersionedData, Document):
    """MongoDB metadata for literature corpus with versioning."""
    
    corpus_name: str
    corpus_type: CorpusType = CorpusType.LITERATURE
    language: Language
    providers: list[LiteratureProvider] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    
    # Tree structure
    parent_id: PydanticObjectId | None = None
    child_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False
    
    # Statistics
    total_works: int = 0
    total_vocabulary: int = 0
    unique_vocabulary: int = 0
    provider_counts: dict[str, int] = Field(default_factory=dict)
    
    class Settings:
        """Beanie document settings."""
        
        name = "literature_corpora"
        indexes = [
            "corpus_name",
            "language",
            "providers",
            "authors",
            "genres",
            "periods",
            "is_latest",
        ]


class FileSystemConnector(LiteratureConnector):
    """Connector for local file system literature sources."""
    
    provider = LiteratureProvider.LOCAL_FILE
    
    def __init__(self, file_path: str | Path) -> None:
        """Initialize with file path.
        
        Args:
            file_path: Path to the literature file
        """
        from ...providers.core import ConnectorConfig
        
        super().__init__(
            source=LiteratureProvider.LOCAL_FILE,
            config=ConnectorConfig(),
        )
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
    async def _fetch_from_provider(self, identifier: str) -> str:
        """Fetch content from local file.
        
        Args:
            identifier: File identifier (can be relative path)
            
        Returns:
            File contents as string
        """
        # If identifier is provided, use it as additional path
        if identifier and identifier != str(self.file_path):
            target_path = self.file_path.parent / identifier
        else:
            target_path = self.file_path
            
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")
            
        return target_path.read_text(encoding="utf-8")
        
    async def list_files(self, pattern: str = "*.txt") -> list[Path]:
        """List files matching pattern.
        
        Args:
            pattern: Glob pattern for file matching
            
        Returns:
            List of matching file paths
        """
        if self.file_path.is_dir():
            return list(self.file_path.glob(pattern))
        return [self.file_path] if self.file_path.match(pattern) else []


class LiteratureCorpus(MultisourceCorpus):
    """Literature-specific corpus with enhanced metadata and provider support."""
    
    # Literature-specific fields
    corpus_type: CorpusType = CorpusType.LITERATURE
    providers: list[LiteratureProvider] = Field(default_factory=list)
    literature_entries: dict[str, EnhancedLiteratureEntry] = Field(default_factory=dict)
    provider_works: dict[LiteratureProvider, list[str]] = Field(default_factory=dict)
    
    # Metadata collections
    authors: dict[str, AuthorInfo] = Field(default_factory=dict)
    genres: set[Genre] = Field(default_factory=set)
    periods: set[Period] = Field(default_factory=set)
    
    async def add_literature_work(
        self,
        work: LiteratureEntry | EnhancedLiteratureEntry,
        provider: LiteratureProvider,
        vocabulary: list[str] | None = None,
        source_url: str | None = None,
        file_path: str | None = None,
    ) -> None:
        """Add a literature work to the corpus.
        
        Args:
            work: Literature work entry
            provider: Provider of the work
            vocabulary: Extracted vocabulary from the work
            source_url: Source URL if from web
            file_path: File path if from local file
        """
        # Create enhanced entry
        if isinstance(work, EnhancedLiteratureEntry):
            enhanced_work = work
        else:
            enhanced_work = EnhancedLiteratureEntry(
                **work.model_dump(),
                provider=provider,
                source_url=source_url,
                file_path=file_path,
                extracted_vocabulary=vocabulary or [],
                metadata=LiteratureEntryMetadata(
                    title=work.title,
                    author=work.author,
                    provider=provider,
                    source_url=source_url,
                    gutenberg_id=work.gutenberg_id,
                    year=work.year,
                    genre=work.genre,
                    period=work.period,
                    language=work.language,
                    file_path=file_path,
                ),
            )
            
        # Store work
        work_id = f"{provider.value}_{work.title}_{work.author.name}".replace(" ", "_")
        self.literature_entries[work_id] = enhanced_work
        
        # Update provider tracking
        if provider not in self.providers:
            self.providers.append(provider)
        if provider not in self.provider_works:
            self.provider_works[provider] = []
        if work_id not in self.provider_works[provider]:
            self.provider_works[provider].append(work_id)
            
        # Update metadata collections
        self.authors[work.author.name] = work.author
        if work.genre:
            self.genres.add(work.genre)
        if work.period:
            self.periods.add(work.period)
            
        # Add vocabulary as source
        if vocabulary:
            await self.add_source(
                source_name=work_id,
                vocabulary=vocabulary,
                metadata={
                    "title": work.title,
                    "author": work.author.name,
                    "provider": provider.value,
                    "genre": work.genre.value if work.genre else None,
                    "period": work.period.value if work.period else None,
                },
            )
            
    async def add_file_system_work(
        self,
        file_path: str | Path,
        metadata: dict[str, Any] | None = None,
        extract_vocabulary: bool = True,
    ) -> None:
        """Add a work from the local file system.
        
        Args:
            file_path: Path to the literature file
            metadata: Optional metadata for the work
            extract_vocabulary: Whether to extract vocabulary
        """
        file_path = Path(file_path)
        
        # Create connector
        connector = FileSystemConnector(file_path)
        
        # Fetch content
        content = await connector._fetch_from_provider(str(file_path))
        
        # Extract vocabulary if requested
        vocabulary = []
        if extract_vocabulary:
            # Simple word extraction (can be enhanced)
            import re
            words = re.findall(r'\b[a-zA-Z]+\b', content if isinstance(content, str) else str(content))
            vocabulary = list(set(words))
            
        # Create work entry
        work_metadata = metadata or {}
        work = LiteratureEntry(
            title=work_metadata.get("title", file_path.stem),
            author=AuthorInfo(
                name=work_metadata.get("author", "Unknown"),
                period=Period(work_metadata.get("period", Period.CONTEMPORARY)),
                primary_genre=Genre(work_metadata.get("genre", Genre.NOVEL)),
                language=Language(work_metadata.get("language", Language.ENGLISH)),
            ),
            genre=Genre(work_metadata.get("genre", Genre.NOVEL)),
            period=Period(work_metadata.get("period", Period.CONTEMPORARY)),
            language=Language(work_metadata.get("language", Language.ENGLISH)),
            text="",  # Empty text for now
        )
        
        # Add to corpus
        await self.add_literature_work(
            work=work,
            provider=LiteratureProvider.LOCAL_FILE,
            vocabulary=vocabulary,
            file_path=str(file_path),
        )
        
        logger.info(f"Added local file: {file_path.name} with {len(vocabulary)} words")
        
    async def add_directory(
        self,
        directory_path: str | Path,
        pattern: str = "*.txt",
        metadata_func: Any = None,
    ) -> None:
        """Add all matching files from a directory.
        
        Args:
            directory_path: Path to the directory
            pattern: Glob pattern for file matching
            metadata_func: Function to extract metadata from filename
        """
        directory_path = Path(directory_path)
        if not directory_path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")
            
        connector = FileSystemConnector(directory_path)
        files = await connector.list_files(pattern)
        
        for file_path in files:
            metadata = metadata_func(file_path) if metadata_func else None
            await self.add_file_system_work(file_path, metadata)
            
        logger.info(f"Added {len(files)} files from {directory_path}")
        
    async def get_works_by_author(self, author_name: str) -> list[EnhancedLiteratureEntry]:
        """Get all works by a specific author.
        
        Args:
            author_name: Name of the author
            
        Returns:
            List of works by the author
        """
        return [
            work
            for work in self.literature_entries.values()
            if work.author.name == author_name
        ]
        
    async def get_works_by_genre(self, genre: Genre) -> list[EnhancedLiteratureEntry]:
        """Get all works of a specific genre.
        
        Args:
            genre: Genre to filter by
            
        Returns:
            List of works in the genre
        """
        return [
            work
            for work in self.literature_entries.values()
            if work.genre == genre
        ]
        
    async def get_works_by_period(self, period: Period) -> list[EnhancedLiteratureEntry]:
        """Get all works from a specific period.
        
        Args:
            period: Period to filter by
            
        Returns:
            List of works from the period
        """
        return [
            work
            for work in self.literature_entries.values()
            if work.period == period
        ]
        
    async def save(self, config: VersionConfig | None = None) -> None:
        """Save literature corpus with enhanced metadata."""
        # Create metadata document
        metadata = LiteratureCorpusMetadata(
            corpus_name=self.corpus_name,
            corpus_type=self.corpus_type,
            language=self.language,
            providers=self.providers,
            authors=list(self.authors.keys()),
            genres=list(self.genres),
            periods=list(self.periods),
            parent_id=self.parent_corpus_id,
            child_ids=self.child_corpus_ids,
            is_master=self.is_master,
            total_works=len(self.literature_entries),
            total_vocabulary=self.total_word_count,
            unique_vocabulary=self.unique_word_count,
            provider_counts={
                provider.value: len(self.provider_works.get(provider, []))
                for provider in self.providers
            },
        )
        
        # Set content
        content = self.model_dump()
        await metadata.set_content(content)
        
        # Save metadata
        await metadata.save_version(config)
        
        # Update corpus_id
        if metadata.id and not self.corpus_id:
            self.corpus_id = metadata.id
            
    @classmethod
    async def create_from_providers(
        cls,
        corpus_name: str,
        language: Language,
        providers: dict[LiteratureProvider, list[LiteratureEntry]],
        semantic: bool = False,
        model_name: str | None = None,
    ) -> LiteratureCorpus:
        """Create literature corpus from multiple providers.
        
        Args:
            corpus_name: Name for the corpus
            language: Language of the corpus
            providers: Dict mapping providers to lists of works
            semantic: Enable semantic search
            model_name: Embedding model name
            
        Returns:
            Configured LiteratureCorpus instance
        """
        corpus = cls(
            corpus_name=corpus_name,
            corpus_type=CorpusType.LITERATURE,
            language=language,
            is_master=True,
        )
        
        corpus.metadata = {
            "semantic_enabled": semantic,
            "model_name": model_name,
        }
        
        # Add all works
        for provider, works in providers.items():
            for work in works:
                await corpus.add_literature_work(work, provider)
                
        return corpus
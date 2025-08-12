"""Literature metadata models with disk-based content storage.

This module provides metadata models for literature storage that integrate
with the versioned data system while keeping large text content on disk.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field

from ...models.base import BaseMetadata
from ...models.definition import Language
from ..models import ContentLocation


class LiteratureSource(str, Enum):
    """Literature download sources."""

    GUTENBERG = "gutenberg"
    INTERNET_ARCHIVE = "internet_archive"
    WIKISOURCE = "wikisource"
    HATHI_TRUST = "hathi_trust"
    STANDARD_EBOOKS = "standard_ebooks"
    LOCAL_FILE = "local_file"


class Genre(str, Enum):
    """Literary genres."""

    EPIC = "epic"
    DRAMA = "drama"
    POETRY = "poetry"
    NOVEL = "novel"
    SHORT_STORY = "short_story"
    ESSAY = "essay"
    PHILOSOPHY = "philosophy"
    BIOGRAPHY = "biography"
    HISTORY = "history"
    ROMANCE = "romance"
    SATIRE = "satire"
    TRAGEDY = "tragedy"
    COMEDY = "comedy"


class Period(str, Enum):
    """Historical literary periods."""

    ANCIENT = "ancient"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    BAROQUE = "baroque"
    ENLIGHTENMENT = "enlightenment"
    ROMANTIC = "romantic"
    VICTORIAN = "victorian"
    MODERNIST = "modernist"
    CONTEMPORARY = "contemporary"


class AuthorInfo(BaseModel):
    """Author information."""

    name: str
    birth_year: int | None = None
    death_year: int | None = None
    nationality: str | None = None
    period: Period
    primary_genre: Genre
    language: Language = Language.ENGLISH

    # External IDs
    gutenberg_author_id: str | None = None
    wikipedia_url: str | None = None
    wikidata_id: str | None = None

    def get_semantic_era_index(self) -> int:
        """Map period to semantic era index for WOTD training."""
        period_to_era = {
            Period.ANCIENT: 0,
            Period.MEDIEVAL: 1,
            Period.RENAISSANCE: 2,
            Period.BAROQUE: 3,
            Period.ENLIGHTENMENT: 4,
            Period.ROMANTIC: 5,
            Period.VICTORIAN: 5,
            Period.MODERNIST: 6,
            Period.CONTEMPORARY: 7,
        }
        return period_to_era.get(self.period, 7)

    def get_semantic_style_index(self) -> int:
        """Map genre to semantic style index for WOTD training."""
        genre_to_style = {
            Genre.EPIC: 4,
            Genre.DRAMA: 3,
            Genre.POETRY: 2,
            Genre.NOVEL: 2,
            Genre.SHORT_STORY: 1,
            Genre.ESSAY: 0,
            Genre.PHILOSOPHY: 0,
            Genre.BIOGRAPHY: 1,
            Genre.HISTORY: 0,
            Genre.ROMANCE: 2,
            Genre.SATIRE: 1,
            Genre.TRAGEDY: 3,
            Genre.COMEDY: 3,
        }
        return genre_to_style.get(self.primary_genre, 2)


# Alias for backward compatibility and clarity
Author = AuthorInfo
AuthorMetadata = AuthorInfo


class TextQualityMetrics(BaseModel):
    """Quality metrics for literary text content."""

    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    sentence_count: int = 0
    average_sentence_length: float = 0.0
    readability_score: float | None = None
    completeness_score: float = 1.0
    quality_score: float = 1.0


class LiteratureMetadata(Document, BaseMetadata):
    """Metadata for literature storage with disk-based content.

    Similar to SemanticMetadata, this stores only metadata in MongoDB
    while the actual text content is stored on disk and managed through
    the versioned data system.
    """

    # Work identification
    source_id: str = Field(description="Provider-specific source ID")
    title: str
    author: AuthorInfo

    # Source information
    source: LiteratureSource
    source_url: str | None = None
    language: Language = Language.ENGLISH

    # Content metadata
    text_hash: str = Field(description="SHA256 hash of content for deduplication")
    quality_metrics: TextQualityMetrics = Field(default_factory=TextQualityMetrics)

    # Content location
    content_location: ContentLocation

    # Processing information
    processing_version: str = "1.0.0"
    last_processed: datetime = Field(default_factory=datetime.now)

    # Classification
    genre: Genre | None = None
    period: Period | None = None
    estimated_reading_time_minutes: int | None = None

    # Additional metadata
    publication_year: int | None = None
    isbn: str | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    class Settings:
        name = "literature_metadata"
        indexes = [
            [("source_id", 1), ("source", 1)],  # Unique per source
            [("text_hash", 1)],  # Deduplication
            [("author.name", 1)],
            [("title", 1)],
            [("source", 1)],
            [("language", 1)],
            [("processing_version", 1)],
        ]

    @property
    def cache_key(self) -> str:
        """Generate cache key for content retrieval."""
        return f"{self.source.value}_{self.source_id}_{self.processing_version}"

    async def get_text_content(self) -> str | None:
        """Retrieve the full text content from storage."""
        from ..versioned import versioned_manager

        return await versioned_manager.load_content(self.content_location)

    async def update_text_content(self, text: str) -> None:
        """Update the text content and recalculate metrics."""
        from ..versioned import versioned_manager

        # Calculate new hash
        new_hash = hashlib.sha256(text.encode()).hexdigest()

        # Update quality metrics
        self.quality_metrics = self._calculate_quality_metrics(text)
        self.text_hash = new_hash
        self.last_processed = datetime.now()

        # Save new content
        self.content_location = await versioned_manager.save_content(
            content=text,
            content_type="text",
            use_disk=True,
            namespace=f"literature_{self.source.value}",
        )

        await self.save()

    def _calculate_quality_metrics(self, text: str) -> TextQualityMetrics:
        """Calculate quality metrics for text content."""
        import re

        words = text.split()
        sentences = re.split(r"[.!?]+", text)
        paragraphs = text.split("\n\n")

        return TextQualityMetrics(
            word_count=len(words),
            character_count=len(text),
            paragraph_count=len([p for p in paragraphs if p.strip()]),
            sentence_count=len([s for s in sentences if s.strip()]),
            average_sentence_length=len(words) / max(1, len([s for s in sentences if s.strip()])),
            completeness_score=min(1.0, len(words) / 1000),  # Assume 1000+ words is "complete"
            quality_score=self._calculate_text_quality(text),
        )

    def _calculate_text_quality(self, text: str) -> float:
        """Calculate overall text quality score."""
        if not text or len(text.strip()) < 100:
            return 0.0

        # Check printable character ratio
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)

        # Check for reasonable word distribution
        words = text.split()
        if not words:
            return 0.0

        avg_word_length = sum(len(w) for w in words) / len(words)
        word_length_score = min(1.0, avg_word_length / 5.0)  # Expect ~5 char average

        return min(1.0, (printable_ratio + word_length_score) / 2.0)

    @classmethod
    async def find_by_author(cls, author_name: str) -> list[LiteratureMetadata]:
        """Find all works by an author."""
        return await cls.find({"author.name": {"$regex": author_name, "$options": "i"}}).to_list()

    @classmethod
    async def find_by_source(cls, source: LiteratureSource) -> list[LiteratureMetadata]:
        """Find all works from a source."""
        return await cls.find({"source": source}).to_list()

    @classmethod
    async def find_by_hash(cls, text_hash: str) -> LiteratureMetadata | None:
        """Find work by content hash (for deduplication)."""
        return await cls.find_one({"text_hash": text_hash})


class LiteratureCorpusMetadata(Document, BaseMetadata):
    """Metadata for literature-based corpora."""

    corpus_id: str = Field(unique=True)
    name: str
    description: str | None = None

    # Literature-specific metadata
    authors: list[AuthorInfo] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    # Source information
    works: list[str] = Field(default_factory=list)  # LiteratureMetadata IDs
    total_works: int = 0
    total_unique_words: int = 0
    total_word_occurrences: int = 0

    # Processing metadata
    processing_config: dict[str, Any] = Field(default_factory=dict)
    ai_analysis: dict[str, Any] | None = None
    semantic_classification: dict[str, Any] | None = None

    # Quality metrics
    vocabulary_diversity: float | None = None
    average_word_length: float | None = None
    readability_score: float | None = None

    class Settings:
        name = "literature_corpus_metadata"
        indexes = [
            [("corpus_id", 1)],
            [("name", 1)],
        ]

    def add_work(self, work_metadata: LiteratureMetadata) -> None:
        """Add a literary work to this corpus."""
        work_id = str(work_metadata.id)
        if work_id not in self.works:
            self.works.append(work_id)
            self.total_works += 1

            # Update aggregate metadata
            if work_metadata.author not in self.authors:
                self.authors.append(work_metadata.author)
            if work_metadata.period and work_metadata.period not in self.periods:
                self.periods.append(work_metadata.period)
            if work_metadata.genre and work_metadata.genre not in self.genres:
                self.genres.append(work_metadata.genre)
            if work_metadata.language not in self.languages:
                self.languages.append(work_metadata.language)


class LiteraryWork(BaseModel):
    """Represents a single literary work with metadata.
    
    Migrated from wotd/literature/models.py.
    """
    
    title: str
    author: AuthorInfo
    gutenberg_id: str
    year: int | None = None
    genre: Genre | None = None
    period: Period | None = None
    language: Language = Language.ENGLISH
    url: str | None = None
    
    def __post_init__(self):
        """Generate Gutenberg URL if not provided."""
        if not self.url and self.gutenberg_id:
            # Handle both numeric IDs and full URLs
            if self.gutenberg_id.startswith("http"):
                self.url = self.gutenberg_id
            else:
                self.url = f"https://www.gutenberg.org/files/{self.gutenberg_id}/{self.gutenberg_id}-0.txt"


class LiteraryWord(BaseModel):
    """A word extracted from literature with context."""

    word: str
    frequency: int
    works: list[str] = Field(default_factory=list)

    # Author context
    author_name: str
    period: Period

    # Linguistic information
    pos_tag: str | None = None
    lemma: str | None = None

    # Context examples
    context_examples: list[str] = Field(default_factory=list, max_length=5)

    # Usage metadata
    first_occurrence_year: int | None = None
    semantic_domains: list[str] = Field(default_factory=list)

    def to_search_word(self) -> str:
        """Convert to format suitable for search corpus."""
        return self.word.lower().strip()


class VersionedLiteratureData(BaseMetadata):
    """Versioned literature data with work reference.
    
    Import from providers.models instead of defining here.
    This is just a placeholder for backward compatibility.
    """
    pass

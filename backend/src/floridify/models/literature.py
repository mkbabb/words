"""Literature metadata models for versioned storage.

This module contains metadata models for literature that integrate with the
versioned data system for proper storage and retrieval.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .dictionary import Language


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


class LiteratureMetrics(BaseModel):
    """Literature metrics and statistics."""
    
    word_count: int
    unique_words: int
    sentence_count: int
    paragraph_count: int
    chapter_count: int
    readability_score: float | None = None
    average_sentence_length: float | None = None
    lexical_diversity: float | None = None


class LiteraryWork(BaseModel):
    """Literary work metadata."""
    
    title: str
    author: AuthorInfo
    gutenberg_id: str | None = None
    year: int | None = None
    genre: Genre
    period: Period
    language: Language = Language.ENGLISH
    
    # Additional metadata
    subtitle: str | None = None
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)


class LiteratureEntry(BaseModel):
    """In-memory representation of a literary work.
    
    Contains the full text content and associated metadata for a literary work.
    """
    
    # Identification
    literature_id: str | None = None
    
    # Metadata
    title: str
    authors: list[str]
    publication_year: int | None = None
    language: Language
    source: LiteratureSource
    
    # Content (loaded from external storage)
    full_text: str
    
    # Computed metrics
    text_hash: str
    text_size_bytes: int
    word_count: int
    unique_words: int
    readability_score: float | None = None
    
    # Extracted features
    chapters: list[str] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LiteratureEntry:
        """Create LiteratureEntry from dictionary representation."""
        return cls.model_validate(data)
    
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Export model to dictionary for storage."""
        return super().model_dump(exclude_none=True, **kwargs)


class LiteratureContent(BaseModel):
    """Literature content structure."""
    
    chapters: list[str] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    extracted_vocabulary: list[str] = Field(default_factory=list)
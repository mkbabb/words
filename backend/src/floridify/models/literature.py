from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .base import Language


class LiteratureProvider(str, Enum):
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


class LiteratureEntry(BaseModel):
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

    # Data
    text: str | None = None  # Full text content (loaded separately)

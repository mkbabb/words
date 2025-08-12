"""Data models for literature corpus processing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..core import Author


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


class Period(str, Enum):
    """Literary periods."""
    ANCIENT = "ancient"  # Pre-500 CE
    MEDIEVAL = "medieval"  # 500-1400
    RENAISSANCE = "renaissance"  # 1400-1600
    BAROQUE = "baroque"  # 1600-1750
    ENLIGHTENMENT = "enlightenment"  # 1700-1800
    ROMANTIC = "romantic"  # 1800-1850
    VICTORIAN = "victorian"  # 1837-1901
    MODERNIST = "modernist"  # 1900-1950
    CONTEMPORARY = "contemporary"  # 1950+


@dataclass
class LiteraryWork:
    """Represents a single literary work with metadata."""
    
    title: str
    author: Author
    gutenberg_id: str
    year: Optional[int] = None
    genre: Optional[Genre] = None
    period: Optional[Period] = None
    language: str = "en"
    url: Optional[str] = None
    
    def __post_init__(self):
        """Generate Gutenberg URL if not provided."""
        if not self.url and self.gutenberg_id:
            # Handle both numeric IDs and full URLs
            if self.gutenberg_id.startswith("http"):
                self.url = self.gutenberg_id
            else:
                self.url = f"https://www.gutenberg.org/files/{self.gutenberg_id}/{self.gutenberg_id}-0.txt"


@dataclass  
class LiteraryWord:
    """A word extracted from literature with context."""
    
    word: str
    frequency: int
    works: list[str]  # Which works it appears in
    author: Author
    period: Period
    pos_tag: Optional[str] = None  # Part of speech
    context_examples: list[str] = None  # Sample sentences
    
    def __post_init__(self):
        if self.context_examples is None:
            self.context_examples = []


@dataclass
class AuthorMetadata:
    """Metadata about an author for corpus processing."""
    
    author: Author
    period: Period
    primary_genre: Genre  
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    nationality: Optional[str] = None
    language: str = "en"
    
    def get_semantic_era_index(self) -> int:
        """Map period to semantic era index (0-7)."""
        period_to_era = {
            Period.ANCIENT: 0,
            Period.MEDIEVAL: 1,
            Period.RENAISSANCE: 2,  
            Period.BAROQUE: 3,
            Period.ENLIGHTENMENT: 4,
            Period.ROMANTIC: 5,
            Period.VICTORIAN: 5,  # Also romantic era
            Period.MODERNIST: 6,
            Period.CONTEMPORARY: 7,
        }
        return period_to_era.get(self.period, 7)
    
    def get_semantic_style_index(self) -> int:
        """Map genre to semantic style index (0-7)."""
        genre_to_style = {
            Genre.EPIC: 4,  # Archaic/Classical
            Genre.DRAMA: 3,  # Dramatic/Theatrical 
            Genre.POETRY: 2,  # Poetic/Literary
            Genre.NOVEL: 2,  # Poetic/Literary
            Genre.SHORT_STORY: 1,  # Conversational
            Genre.ESSAY: 0,  # Formal/Academic
            Genre.PHILOSOPHY: 0,  # Formal/Academic
            Genre.BIOGRAPHY: 1,  # Conversational
            Genre.HISTORY: 0,  # Formal/Academic
        }
        return genre_to_style.get(self.primary_genre, 2)
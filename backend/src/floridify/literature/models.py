"""Literature models integrated with Floridify infrastructure.

This module provides literature-specific models that integrate seamlessly
with existing Floridify models, storage, and corpus management systems.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from beanie import Document
from pydantic import BaseModel, Field

from ..models.base import BaseMetadata
from ..search.corpus.models import CorpusType


class Genre(str, Enum):
    """Literary genres for classification."""
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
    ANCIENT = "ancient"  # Pre-500 CE
    MEDIEVAL = "medieval"  # 500-1400
    RENAISSANCE = "renaissance"  # 1400-1600
    BAROQUE = "baroque"  # 1600-1750
    ENLIGHTENMENT = "enlightenment"  # 1700-1800
    ROMANTIC = "romantic"  # 1800-1850
    VICTORIAN = "victorian"  # 1837-1901
    MODERNIST = "modernist"  # 1900-1950
    CONTEMPORARY = "contemporary"  # 1950+


class LiteratureSource(str, Enum):
    """Literature download sources."""
    GUTENBERG = "gutenberg"
    INTERNET_ARCHIVE = "internet_archive"
    WIKISOURCE = "wikisource"
    HATHI_TRUST = "hathi_trust"
    STANDARD_EBOOKS = "standard_ebooks"
    LOCAL_FILE = "local_file"


class Author(BaseModel):
    """Author information with metadata."""
    
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    nationality: Optional[str] = None
    period: Period
    primary_genre: Genre
    language: str = "en"
    
    # Gutenberg-specific
    gutenberg_author_id: Optional[str] = None
    
    # Wiki/external IDs
    wikipedia_url: Optional[str] = None
    wikidata_id: Optional[str] = None
    
    def get_semantic_era_index(self) -> int:
        """Map period to semantic era index (0-7) for WOTD training."""
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
        """Map genre to semantic style index (0-7) for WOTD training."""
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
            Genre.ROMANCE: 2,  # Poetic/Literary
            Genre.SATIRE: 1,  # Conversational
            Genre.TRAGEDY: 3,  # Dramatic/Theatrical
            Genre.COMEDY: 3,  # Dramatic/Theatrical
        }
        return genre_to_style.get(self.primary_genre, 2)


class LiteraryWork(Document):
    """A literary work with comprehensive metadata and source information.
    
    Integrates with Floridify's MongoDB storage using Beanie ODM patterns.
    """
    
    # Work identification
    title: str
    author: Author
    year: Optional[int] = None
    genre: Optional[Genre] = None
    period: Optional[Period] = None
    language: str = "en"
    
    # Source information
    source: LiteratureSource
    source_id: str  # Gutenberg ID, Archive ID, etc.
    source_url: Optional[str] = None
    
    # Content metadata
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    estimated_reading_time_minutes: Optional[int] = None
    
    # Processing metadata
    text_hash: Optional[str] = None  # SHA256 of cleaned text
    last_processed: Optional[datetime] = None
    processing_version: str = "1.0.0"
    
    # Quality metrics
    text_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    completeness_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # How complete is the text
    
    # Integration with existing metadata
    metadata: BaseMetadata = Field(default_factory=BaseMetadata)
    
    class Settings:
        name = "literary_works"
        use_state_management = True
        
    def __str__(self) -> str:
        return f"{self.title} by {self.author.name}"
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for text content."""
        return f"{self.source.value}_{self.source_id}_{self.processing_version}"


class LiteraryWord(BaseModel):
    """A word extracted from literature with context and metadata."""
    
    word: str
    frequency: int
    works: list[str] = Field(default_factory=list)  # Work titles/IDs containing this word
    
    # Author context
    author_name: str
    period: Period
    
    # Linguistic information
    pos_tag: Optional[str] = None
    lemma: Optional[str] = None
    
    # Context examples (limited to conserve space)
    context_examples: list[str] = Field(default_factory=list, max_items=5)
    
    # Usage metadata
    first_occurrence_year: Optional[int] = None  # Earliest known usage
    semantic_domains: list[str] = Field(default_factory=list)  # Themes/domains
    
    def to_search_word(self) -> str:
        """Convert to format suitable for search corpus."""
        return self.word.lower().strip()


class LiteratureCorpusMetadata(Document):
    """Metadata for literature-based corpora, extending existing corpus system.
    
    Integrates with existing CorpusMetadata while adding literature-specific fields.
    """
    
    # Basic corpus identification
    corpus_id: str = Field(..., unique=True)
    name: str
    description: Optional[str] = None
    
    # Literature-specific metadata
    authors: list[Author] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list) 
    languages: list[str] = Field(default_factory=list)
    
    # Source information
    works: list[str] = Field(default_factory=list)  # LiteraryWork IDs
    total_works: int = 0
    total_unique_words: int = 0
    total_word_occurrences: int = 0
    
    # Corpus type integration
    corpus_type: CorpusType = CorpusType.CUSTOM
    
    # Processing metadata
    processing_config: dict[str, Any] = Field(default_factory=dict)
    ai_analysis: Optional[dict[str, Any]] = None  # GPT analysis results
    semantic_classification: Optional[dict[str, Any]] = None
    
    # Quality metrics
    vocabulary_diversity: Optional[float] = Field(None, ge=0.0, le=1.0)
    average_word_length: Optional[float] = None
    readability_score: Optional[float] = None
    
    # Integration with existing systems
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    class Settings:
        name = "literature_corpus_metadata" 
        use_state_management = True
        
    def add_work(self, work: LiteraryWork) -> None:
        """Add a literary work to this corpus."""
        if str(work.id) not in self.works:
            self.works.append(str(work.id))
            self.total_works += 1
            
            # Update aggregate metadata
            if work.author not in self.authors:
                self.authors.append(work.author)
            if work.period and work.period not in self.periods:
                self.periods.append(work.period)
            if work.genre and work.genre not in self.genres:
                self.genres.append(work.genre)
            if work.language not in self.languages:
                self.languages.append(work.language)
                
            self.updated_at = datetime.now()


class AuthorMetadata(BaseModel):
    """Extended author metadata for corpus processing."""
    
    author: Author
    
    # Corpus statistics
    total_works: int = 0
    total_words: int = 0
    unique_vocabulary_size: int = 0
    most_frequent_words: list[str] = Field(default_factory=list, max_items=50)
    
    # Stylistic analysis
    average_sentence_length: Optional[float] = None
    vocabulary_richness: Optional[float] = None  # Type-token ratio
    complexity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Thematic analysis
    dominant_themes: list[str] = Field(default_factory=list)
    semantic_domains: list[str] = Field(default_factory=list) 
    
    # AI analysis results
    ai_style_analysis: Optional[dict[str, Any]] = None
    ai_thematic_analysis: Optional[dict[str, Any]] = None
    
    def to_wotd_author(self):
        """Convert to WOTD Author enum if supported."""
        # This would map to existing WOTD Author enum
        from ..wotd.core import Author as WOTDAuthor
        
        name_mapping = {
            "william shakespeare": WOTDAuthor.SHAKESPEARE,
            "virginia woolf": WOTDAuthor.WOOLF,
            "dante alighieri": WOTDAuthor.DANTE,
            "james joyce": WOTDAuthor.JOYCE,
            # Add more mappings as needed
        }
        
        return name_mapping.get(self.author.name.lower())


# Re-export existing enums for backward compatibility
try:
    from ..wotd.core import Author as WOTDAuthor
    # Make WOTD authors available in literature namespace
    SHAKESPEARE = WOTDAuthor.SHAKESPEARE
    WOOLF = WOTDAuthor.WOOLF
    DANTE = WOTDAuthor.DANTE
    JOYCE = WOTDAuthor.JOYCE
except ImportError:
    # WOTD not available, define minimal set
    pass
# Floridify Architecture

## Synopsis

Floridify is an augmented dictionary, thesaurus, and word learning tool designed to provide comprehensive understanding of words within the English lexicon. The system combines traditional dictionary functionality with modern AI capabilities, flashcard-based learning, and contextual examples from classical literature. Through modular dictionary connectors, vectorized search, and deep AI integration, Floridify aims to create an unobtrusive yet powerful tool for vocabulary acquisition and retention.

## Features

### Core Dictionary Functionality

-   **Robust Dictionary Access**: Fast, unobtrusive dictionary lookup with data aggregation from multiple providers
-   **Super Fuzzy Search**: Vectorized embedding-based search that suggests words or phrases similar to input queries, even with spelling errors
-   **Enhanced Thesaurus**: Vectorized thesaurus with latent word connection extraction for discovering semantic relationships

### Learning Systems

-   **Flashcard Integration**: Bilateral import/export compatibility with Anki platform, with native flashcard support planned
-   **Spaced Repetition**: Integration with established spaced repetition algorithms for optimal learning retention

### Content Management

-   **Word List Management**: Create, edit, and manage word lists natively or through document providers
-   **Document Provider Integration**: Bilateral synchronization with external platforms, including Google Drive, Apple Notes, and local file systems
-   **Literature Knowledge Base**: Contextual word usage examples from classical literature and user-provided documents

### AI-Enhanced Definitions

-   **Comprehensive Entries**: AI-synthesized dictionary entries combining data from multiple dictionary connectors
-   **Contextual Examples**: Modern, tailored example sentences generated for user's specific learning context
    -   **Adaptive Content**: Regenerable and tunable content via natural language interaction

## Architecture

### Data Models; Morphology

The core dictionary entry is organized by provider, with an AI-synthesized provider serving as the primary view. All models use Pydantic for validation and Beanie ODM for MongoDB integration.

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum

import numpy as np
from beanie import Document
from pydantic import BaseModel, Field

class WordType(Enum):
    """Enumeration for part of speech types"""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"

class LiteratureSourceType(Enum):
    """Enumeration for different types of literature sources"""
    BOOK = "book"
    ARTICLE = "article"
    DOCUMENT = "document"

class Word(BaseModel):
    """Represents a word with its text and associated embeddings."""

    text: str
    embedding: dict[str, np.ndarray] = Field(default_factory=dict)


class Pronunciation(BaseModel):
    """Pronunciation data in multiple formats."""

    phonetic: str  # e.g. "en coulisses -> on koo-LEES"
    ipa: str | None = None  # e.g. "/ɑːn kəˈliːs/"


class LiteratureSource(BaseModel):
    """Metadata for literature sources"""
    id: str
    title: str
    author: str | None = None
    text: str = ""

class GeneratedExample(BaseModel):
    """AI-generated modern usage example"""
    sentence: str
    regenerable: bool = True

class LiteratureExample(BaseModel):
    """Real-world usage from literature knowledge base"""
    sentence: str
    source: LiteratureSource

class Examples(BaseModel):
    """Container for different types of usage examples"""
    generated: list[GeneratedExample] = Field(default_factory=list)
    literature: list[LiteratureExample] = Field(default_factory=list)

class SynonymReference(BaseModel):
    """Reference to related word entries"""
    word: Word
    word_type: WordType

class Definition(BaseModel):
    """Single word definition with bound synonyms and examples"""
    word_type: WordType
    definition: str
    synonyms: list[SynonymReference] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    raw_metadata: dict | None = None

class ProviderData(BaseModel):
    """Container for provider-specific definitions and metadata"""
    provider_name: str
    definitions: list[Definition] = Field(default_factory=list)
    is_synthetic: bool = False
    last_updated: datetime = Field(default_factory=datetime.now)
    raw_metadata: dict | None = None

class DictionaryEntry(Document):
    """Main entry point for word data - organized by provider for layered access"""
    word: Word
    pronunciation: Pronunciation
    providers: dict[str, ProviderData] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
        ]

    def add_provider_data(self, provider_data: ProviderData) -> None:
        """Add or update provider data"""
        self.providers[provider_data.provider_name] = provider_data
        self.last_updated = datetime.now()

class SynthesizedDictionaryEntry(Document):
    """Finalized dictionary entry with all necessary data for display.

    The definitions herein are synthetic, aggregated at the word-type-meaning level
    across providers.

    For example, a word like "run" may have multiple definitions across providers,
    but this entry synthesizes them into a single coherent structure for easy access.
    """
    word: Word
    pronunciation: Pronunciation
    definitions: list[Definition] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
        ]

class APIResponseCache(Document):
    """Cache for API responses with TTL"""
    word: str
    provider: str
    response_data: dict
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "api_response_cache"
        indexes = [
            [("word", 1), ("provider", 1)],
            "timestamp",
        ]
```

### Dictionary Connectors

The system employs modular dictionary connectors to aggregate data from multiple authoritative sources:

-   **Wiktionary Connector**: Open-source dictionary data with comprehensive wikitext parsing using wikitextparser
-   **Oxford Dictionary Connector**: Premium dictionary source for authoritative definitions with full API integration
-   **Dictionary.com Connector**: Stub implementation ready for future integration

Each connector implements a standardized interface for data normalization and consistent API interaction through the `DictionaryConnector` abstract base class:

```python
class DictionaryConnector(ABC):
    """Abstract base class for dictionary API connectors."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        pass

    @abstractmethod
    async def fetch_definition(self, word: str) -> ProviderData | None:
        """Fetch definition data for a word."""
        pass
```

All connectors include built-in rate limiting with configurable requests per second to respect API limits and avoid service disruption.

### AI Integration Architecture

The AI system utilizes OpenAI's API with structured outputs and advanced model support:

-   **Structured Outputs**: Uses Pydantic schemas with OpenAI's structured output API for reliable parsing
-   **Model Capability Detection**: Automatic detection of reasoning models vs standard models
-   **Per-Word-Type Synthesis**: AI synthesis organized by grammatical word type across multiple providers' definitions
-   **AI Fallback Generation**: Fallback system for unknown words/phrases with proper dictionary structure -- formulated as a generic "AI Provider" for extensibility
-   **Phonetic Pronunciation**: Automatic generation of phonetic pronunciations if not provided (e.g., "en coulisses" → "on koo-LEES")

### Literature Knowledge Base

#### Document Provider Integration

The system processes various document formats to build contextual examples:

-   **Supported Formats**: PDF, EPUB, DOCX, TXT, and other common text formats
-   **Classical Literature**: Pre-seeded with public domain works for comprehensive word coverage
-   **User Documents**: Custom literature base from user-provided documents
-   **Context Extraction**: Automated extraction of word usage examples with surrounding context

#### Example Categorization

Examples are organized hierarchically for optimal learning:

-   **Word Type Grouping**: Examples categorized by grammatical function
-   **AI-Generated Examples**: Modern, contextually relevant sentences
-   **Literature Examples**: Historical usage from knowledge base documents
-   **Expandable Sections**: Collapsible interface for managing example volume

### Integration Interfaces

#### Anki Integration

Bilateral synchronization with the Anki spaced repetition system:

-   **Export Functionality**: Convert Floridify entries to Anki card format
-   **Import Functionality**: Process existing Anki decks into Floridify word lists
-   **Isomorphic Mapping**: Anki cards serve as frontend representations of AI comprehension entries
-   **Synchronization Options**: Local file-based or cloud-based synchronization

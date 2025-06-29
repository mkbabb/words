# Floridify Architecture

## Synopsis

Floridify is an augmented dictionary, thesaurus, and word learning tool designed to provide comprehensive understanding of words within the English lexicon. The system combines traditional dictionary functionality with modern AI capabilities, flashcard-based learning, and contextual examples from classical literature. Through modular dictionary connectors, vectorized search, and deep AI integration, Floridify aims to create an unobtrusive yet powerful tool for vocabulary acquisition and retention.

## Features

### Core Dictionary Functionality

-   **Robust Dictionary Access**: Fast, unobtrusive dictionary lookup with data aggregation from multiple sources
-   **Super Fuzzy Search**: Vectorized embedding-based search that suggests words or phrases similar to input queries, even with spelling errors
-   **Enhanced Thesaurus**: Vectorized thesaurus with latent word connection extraction for discovering semantic relationships

### Learning Systems

-   **Flashcard Integration**: Bilateral import/export compatibility with Anki platform, with native flashcard support planned
-   **Spaced Repetition**: Integration with established spaced repetition algorithms for optimal learning retention

### Content Management

-   **Word List Management**: Create, edit, and manage word lists natively or through document providers
-   **Document Provider Integration**: Bilateral synchronization with external platforms, primarily Apple Notes
-   **Literature Knowledge Base**: Contextual word usage examples from classical literature and user-provided documents

### AI-Enhanced Definitions

-   **Comprehensive Entries**: AI-synthesized dictionary entries combining data from multiple dictionary connectors
-   **Contextual Examples**: Modern, tailored example sentences generated for user's specific learning context
-   **Adaptive Content**: Regenerable and tunable content via natural language interaction

## Architecture

### Data Models

#### Dictionary Entry Morphology

The core dictionary entry is organized by provider, with an AI-synthesized provider serving as the primary view. All models use Pydantic for validation and Beanie ODM for MongoDB integration.

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum

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
    """Represents a word with its text and associated embeddings"""
    text: str
    embedding: dict[str, list[float]] = Field(default_factory=dict)

class Pronunciation(BaseModel):
    """Pronunciation data in multiple formats"""
    phonetic: str
    ipa: str | None = None

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

#### Comprehension Entry Generation

The AI comprehension system synthesizes data from all dictionary connectors into normalized entries:

-   **Data Normalization**: Standardizes format and structure across different dictionary sources
-   **Definition Synthesis**: Combines multiple definitions into coherent, comprehensive entries
-   **Example Generation**: Creates contextually appropriate modern usage examples
-   **Continuous Updates**: Re-processes entries when dictionary connectors update their data

#### Modular AI Provider Support

The system supports multiple AI providers through a modular architecture:

-   **Primary Provider**: OpenAI ChatGPT API for initial implementation
-   **Provider Abstraction**: Interface design allows for easy integration of additional AI services
-   **Embedding Services**: Separate embedding providers for vectorized search functionality
-   **Caching Strategy**: All AI API calls are cached to optimize performance and reduce costs

### Prompts

#### AI Comprehension Prompt Template

```
Generate a dictionary-style entry for each provided input (word or phrase):

• Definition: Start with a succinct, dictionary-style definition. For multiple definitions, list them sequentially with their corresponding word types.

• Pronunciation: Provide a phonetic pronunciation respelling of the input word. Use NO special characters; phonetically spell the word out.

• Synonyms: Include three or more synonyms.

• Exemplary Sentence: Craft one exemplary sentence befitting of modern life. Italicize the entire sentence and embolden the target word.

• Formatting:
  • Render each word as an emboldened header on its own line; separate multiple words by new lines.
  • Eliminate any numerical figures.

• Phrase Analysis: If a phrase is provided, include an analysis of its meaning and context.
```

### Storage Strategy

#### Database Architecture

-   **MongoDB with Beanie ODM**: Modern async ODM providing automatic Pydantic model serialization/deserialization
-   **Pydantic Models**: Type-safe data validation and serialization with automatic MongoDB document mapping
-   **Automatic Indexing**: Beanie handles index creation based on model definitions
-   **API Response Caching**: Dedicated cache collection with TTL for external API responses

#### Data Organization

The system uses MongoDB collections managed through Beanie Document models:

```python
class DictionaryEntry(Document):
    """Main collection for dictionary entries"""
    word: Word
    pronunciation: Pronunciation
    providers: dict[str, ProviderData] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],  # Text search index
            "last_updated",
        ]

class APIResponseCache(Document):
    """Collection for caching external API responses"""
    word: str
    provider: str
    response_data: dict
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "api_response_cache"
        indexes = [
            [("word", 1), ("provider", 1)],  # Compound index
            "timestamp",
        ]
```

-   **Entry Collections**: Primary dictionary entries with provider-specific data organization
-   **Cache Collections**: API response caching with automatic TTL management
-   **Future Collections**: Vector embeddings, literature examples, and user data (planned)

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

#### Document Provider Connectivity

Integration with external document providers for seamless workflow:

-   **Apple Notes Integration**: Primary document provider for word list management
-   **Shortcuts App**: Automated detection of notes updates and word list changes
-   **Parsing Strategy**: Flexible parsing for various list formats (numbered, bulleted, plain text)
-   **Deduplication**: Automatic removal of duplicate entries across different sources

## Implementation Architecture

### Core System Components

The implementation prioritizes backend functionality with modular connector architecture:

-   **Dictionary Schema**: Complete Pydantic data models with Beanie ODM integration for type-safe MongoDB operations
-   **Connector Implementation**: 
    - Wiktionary connector with advanced wikitext parsing using wikitextparser
    - Oxford Dictionary API connector with full response parsing
    - Dictionary.com connector stub ready for future implementation
-   **Storage Layer**: Beanie ODM provides automatic serialization, validation, and indexing
-   **Configuration Management**: TOML-based configuration with dataclass models for type safety

### Development Priorities

-   **Backend Infrastructure**: Focus on robust data processing and storage systems
-   **API Integration**: Establish reliable connections to external dictionary and AI services
-   **Caching Strategy**: Implement comprehensive caching for performance optimization
-   **Data Pipeline**: Create efficient processing pipeline from raw dictionary data to AI-enhanced entries

### Modular Architecture Principles

-   **Provider Abstraction**: All external services (dictionaries, AI, document providers) implement standardized interfaces
-   **Extensibility**: System design allows for easy addition of new connectors and providers
-   **Configuration Management**: Modular settings for different AI providers, dictionary sources, and user preferences
-   **Error Handling**: Robust fallback mechanisms for service unavailability or API limitations

## Hyper-Efficient Search Engine Architecture

### Dual-Search Strategy

Floridify implements a comprehensive dual-approach search system that combines traditional computational linguistics with modern machine learning for optimal search performance across diverse use cases.

#### Traditional Search Engine

**Core Data Structures**:

```python
class WordIndex:
    """Traditional search using optimized data structures"""
    def __init__(self, cache_dir: Path | None = None):
        self.trie = TrieIndex()              # O(m) prefix matching
        self.bk_tree = BKTree()              # O(log n) edit distance
        self.trigram_index = NGramIndex(n=3)  # Substring matching
        self.bigram_index = NGramIndex(n=2)   # Phonetic similarity
```

**Algorithm Implementation**:

1. **Trie Index**: Compressed prefix tree for exact and prefix matching
   - Performance: O(m) where m = query length
   - Memory: ~200MB for 847k words with path compression
   - Use Cases: Autocomplete, exact word lookup, prefix search

2. **BK-Tree (Burkhard-Keller Tree)**: Metric tree for approximate matching
   - Performance: O(log n) edit distance search
   - Memory: ~150MB with optimized node storage
   - Use Cases: Typo correction, fuzzy matching with edit distance bounds

3. **N-gram Indices**: Character sequence matching for morphological similarity
   - Bigram Index: Character pairs for phonetic similarity
   - Trigram Index: Three-character sequences for structural matching
   - Performance: O(1) inverted index lookup with ~300MB memory

#### Vectorized Search Engine

**Multi-Level Embedding Architecture**:

```python
class VectorizedFuzzySearch:
    """Modern embedding-based search with FAISS integration"""
    def __init__(self, cache_dir: Path | None = None):
        # Character-level embeddings (64D)
        self.char_embedder = CharacterEmbedder(embed_dim=64)
        
        # Subword embeddings (100D) - FastText style
        self.subword_embedder = SubwordEmbedder(embed_dim=100)
        
        # TF-IDF statistical embeddings (10kD)
        self.tfidf_embedder = TFIDFEmbedder(max_features=10000)
        
        # FAISS indices for efficient similarity search
        self.char_index: faiss.Index
        self.subword_index: faiss.Index
        self.tfidf_index: faiss.Index
        self.combined_index: faiss.Index  # Fusion of all embeddings
```

**Embedding Strategies**:

1. **Character-Level Embeddings (64D)**:
   - Purpose: Morphological similarity, character-level variations
   - Vocabulary: 150+ characters (English, French, accented, symbols)
   - Implementation: Learned embeddings with mean pooling over character sequences
   - Use Cases: Handling typos, character-level morphological matching

2. **Subword Embeddings (100D)**:
   - Purpose: FastText-style OOV handling via character n-grams
   - Vocabulary: 50k+ subwords (2-5 character n-grams) with frequency filtering
   - Implementation: Character n-gram extraction with learned embeddings
   - Use Cases: Unknown word similarity, morphological decomposition

3. **TF-IDF Embeddings (10kD)**:
   - Purpose: Traditional statistical similarity via character n-grams
   - Features: 10k most frequent character bigrams and trigrams
   - Implementation: sklearn TfidfVectorizer with character-level analysis
   - Use Cases: Statistical text similarity, traditional fuzzy matching

**FAISS Integration**:

```python
# Embedding fusion strategy for comprehensive similarity
fusion_embedding = np.concatenate([
    char_embedding * 0.3,      # Character morphology weight
    subword_embedding * 0.5,   # Subword similarity weight
    tfidf_embedding * 0.2      # Statistical similarity weight
])

# FAISS index for approximate nearest neighbors
combined_index = faiss.IndexFlatIP(fusion_dim)  # Inner product for normalized vectors
combined_index.add(fusion_embeddings)
```

### Comprehensive Lexicon Architecture

#### Multi-Source Lexicon Loading

```python
class LexiconLoader:
    """Comprehensive word loading from multiple authoritative sources"""
    def __init__(self, cache_dir: Path | None = None):
        self.word_sources = {
            'english_common': {
                'url': 'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt',
                'size': '~370k words',
                'description': 'Common English words'
            },
            'english_comprehensive': {
                'url': 'https://raw.githubusercontent.com/dwyl/english-words/master/words.txt',
                'size': '~470k words', 
                'description': 'Comprehensive English dictionary'
            },
            'french_common': {
                'url': 'https://raw.githubusercontent.com/hbenbel/French-Dictionary/master/dictionary/dictionary.txt',
                'size': '~139k words',
                'description': 'French dictionary words'
            },
            'french_conjugated': {
                'url': 'https://raw.githubusercontent.com/hbenbel/French-Dictionary/master/dictionary/conjugated_verbs.txt',
                'size': '~20k forms',
                'description': 'French conjugated verb forms'
            }
        }
```

**Lexicon Statistics**:
- **Total Online Sources**: 4 comprehensive repositories
- **Total Local Collections**: 4 specialized word sets
- **Total Words**: 847k+ entries after deduplication and cleaning
- **Languages**: English and French with extensible architecture
- **Cache Management**: Automatic local caching with configurable refresh

#### Local Specialized Collections

1. **Academic Vocabulary**: 500+ scholarly terms, AWL vocabulary, French loanwords
2. **Scientific Terms**: 400+ technical terminology across biology, chemistry, physics, mathematics
3. **Proper Nouns**: 200+ countries, major cities, common names for completeness
4. **French Phrases**: 150+ common French expressions used in English context

### Search Coordination Architecture

#### Unified Search Manager

```python
class SearchManager:
    """Coordinates all search methods with performance optimization"""
    def __init__(self, cache_dir: Path | None = None):
        # Traditional search components
        self.word_index = WordIndex(cache_dir / "index")
        self.traditional_search = TraditionalFuzzySearch(score_threshold=0.6)
        
        # Vectorized search components
        self.vectorized_search = VectorizedFuzzySearch(cache_dir / "vectors")
        
        # Lexicon management
        self.lexicon_loader = LexiconLoader(cache_dir / "lexicons")
        
        # Performance tracking
        self.search_stats = {
            'total_searches': 0,
            'avg_search_time': 0.0,
            'method_usage': {},
            'cache_hits': 0
        }
```

**Search Method Coordination**:

```python
async def search(self, query: str, methods: list[str] | None = None) -> list[SearchResult]:
    """Unified search across multiple algorithms"""
    
    # Method 1: Hybrid traditional search (Trie + BK-tree + N-grams)
    if 'hybrid' in methods:
        hybrid_results = self.word_index.hybrid_search(query, max_results)
    
    # Method 2: Vectorized search (embeddings + FAISS)
    if 'vectorized' in methods:
        vector_results = self.vectorized_search.search(query, max_results, "fusion")
    
    # Method 3: Traditional algorithms (RapidFuzz, Jaro-Winkler, VSCode-style)
    if 'rapidfuzz' in methods:
        traditional_results = self.traditional_search.search(query, word_list, max_results)
    
    # Merge, deduplicate, and rank results
    return self._merge_search_results(all_results)
```

### Performance Optimization Architecture

#### Caching Strategy

1. **FAISS Index Persistence**: Binary serialization of vector indices to disk
2. **Embedding Cache**: Persistent storage of computed embeddings with model versioning
3. **Lexicon Cache**: Local caching of downloaded word lists with automatic refresh
4. **Search Result Cache**: In-memory caching of frequent search queries

#### Concurrent Processing

```python
# Parallel search execution across methods
async def search(self, query: str) -> list[SearchResult]:
    tasks = []
    
    if 'hybrid' in methods:
        tasks.append(asyncio.create_task(self._hybrid_search(query)))
    if 'vectorized' in methods:
        tasks.append(asyncio.create_task(self._vectorized_search(query)))
    if 'rapidfuzz' in methods:
        tasks.append(asyncio.create_task(self._traditional_search(query)))
    
    # Execute searches concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return self._merge_results(results)
```

#### Memory Management

- **Lazy Loading**: Components initialized only when needed
- **Memory Mapping**: Large indices memory-mapped for efficient access
- **Garbage Collection**: Explicit cleanup of large embedding matrices
- **Resource Pooling**: Shared embedding computations across search methods

### Integration with Dictionary System

#### Database Integration

```python
# Search integration with MongoDB storage
async def add_words_to_index(self, words: list[str], language: str = "en") -> None:
    """Add new dictionary words to search indices"""
    
    # Update traditional indices
    for word in words:
        self.word_index.add_word(word, language)
    
    # Rebuild vectorized indices with new words
    all_words = list(self.word_index.trie.trie.keys())
    self.vectorized_search.build_index(all_words)
    
    # Persist updated indices
    self.word_index.save_cache()
    self.vectorized_search.save_index()
```

#### Real-time Search API

```python
# CLI integration with real-time search
@search_group.command("fuzzy")
async def fuzzy_search(pattern: str, max_results: int = 10) -> None:
    """Real-time fuzzy search with multiple algorithms"""
    
    results = await search_manager.search(
        pattern,
        max_results=max_results,
        methods=['hybrid', 'vectorized', 'rapidfuzz']
    )
    
    # Display results with performance metrics
    display_search_results(results)
    show_performance_stats(search_manager.get_search_stats())
```

### Extensibility Architecture

#### Algorithm Modularity

The search system is designed for easy extension with new algorithms:

```python
class SearchAlgorithm(ABC):
    """Abstract base class for search algorithms"""
    
    @abstractmethod
    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Perform search and return ranked results"""
        pass
    
    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Return algorithm-specific statistics"""
        pass
```

#### Language Expansion

The architecture supports easy addition of new languages:

```python
# Extensible lexicon configuration
language_configs = {
    'spanish': {
        'sources': ['rae_dictionary', 'spanish_words_repo'],
        'local_collections': ['spanish_academic', 'spanish_technical']
    },
    'german': {
        'sources': ['duden_api', 'german_words_repo'],
        'local_collections': ['german_compound_words', 'german_technical']
    }
}
```

This architecture ensures that Floridify's search capabilities can scale and adapt to evolving requirements while maintaining optimal performance across diverse search scenarios.

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

#### Modern OpenAI Integration

The AI system utilizes OpenAI's latest capabilities with structured outputs and advanced model support:

-   **Structured Outputs**: Uses Pydantic schemas with OpenAI's structured output API for reliable parsing
-   **Model Capability Detection**: Automatic detection of reasoning models vs standard models
-   **Per-Word-Type Synthesis**: AI synthesis organized by grammatical word type instead of flattened aggregation
-   **AI Fallback Generation**: Complete fallback system for unknown words/phrases with proper dictionary structure
-   **Phonetic Pronunciation**: Automatic generation of phonetic pronunciations (e.g., "en coulisses" → "on koo-LEES")

#### Enhanced AI Components

-   **DefinitionSynthesizer**: Synthesizes definitions from multiple providers with per-word-type organization
-   **OpenAIConnector**: Modern connector with structured responses and bulk processing optimization
-   **Enhanced Lookup**: AI fallback with intelligent search cascading (exact → fuzzy → AI generation)
-   **Caching Strategy**: Comprehensive caching for AI responses, embeddings, and structured outputs

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

### Modern Search Implementation

Floridify implements a robust multi-layered search system with timeout protection and graceful fallback capabilities for optimal performance across diverse use cases.

#### Core Search Methods

-   **Exact Search**: Trie-based exact string matching with O(m) performance
-   **Fuzzy Search**: Multiple algorithms (RapidFuzz, Jaro-Winkler) with automatic method selection
-   **Semantic Search**: Multi-level embedding strategy with FAISS acceleration and timeout protection
-   **Prefix Search**: Autocomplete-style prefix matching for interactive use

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

#### Semantic Search Engine

**Multi-Level Embedding Architecture with Timeout Protection**:

```python
class SemanticSearch:
    """Modern embedding-based search with FAISS integration and timeout protection"""
    def __init__(self, cache_dir: Path):
        # Character-level embeddings for morphological similarity
        self.char_vectorizer: TfidfVectorizer | None = None
        self.char_embeddings: np.ndarray | None = None
        
        # Subword embeddings for decomposition
        self.subword_vectorizer: TfidfVectorizer | None = None
        self.subword_embeddings: np.ndarray | None = None
        
        # Word-level embeddings for semantic meaning
        self.word_vectorizer: TfidfVectorizer | None = None
        self.word_embeddings: np.ndarray | None = None
        
        # FAISS indices with safety checks
        self.char_index: faiss.Index | None = None
        self.subword_index: faiss.Index | None = None
        self.word_index: faiss.Index | None = None
```

**Timeout Protection and Graceful Fallback**:

```python
async def initialize(self) -> None:
    """Initialize with timeout protection for production reliability"""
    try:
        # Add 30-second timeout protection for semantic search initialization
        self.semantic_search = SemanticSearch(self.cache_dir)
        await asyncio.wait_for(
            self.semantic_search.initialize(words + phrases),
            timeout=30.0  # 30 second timeout
        )
    except (TimeoutError, Exception) as e:
        print("Continuing with exact and fuzzy search only...")
        self.semantic_search = None
        self.enable_semantic = False
```

**Embedding Strategies with Safety Features**:

1. **Character-Level Embeddings**:
   - Purpose: Morphological similarity and character-level variations
   - Implementation: TF-IDF vectorization with character n-grams (2-4 chars)
   - Features: Configurable max features (12.5k for character level)
   - Safety: Division-by-zero protection in normalization with `np.where(norms == 0, 1, norms)`
   - Use Cases: Handling typos, morphological matching, character-level similarity

2. **Subword Embeddings**:
   - Purpose: Word decomposition and subword-level similarity
   - Implementation: TF-IDF on generated subword representations
   - Features: Configurable max features (25k for subword level)
   - Subword Strategy: Prefix/suffix extraction, sliding windows for long words
   - Use Cases: Unknown word similarity, morphological decomposition

3. **Word-Level Embeddings**:
   - Purpose: Semantic meaning and word-level relationships
   - Implementation: TF-IDF with word unigrams and bigrams
   - Features: Full feature set (50k max features)
   - Use Cases: Semantic similarity, meaning-based matching

**FAISS Integration with Safety Checks**:

```python
# Multi-level search with weighted combination
async def search(self, query: str, max_results: int = 20) -> list[tuple[str, float]]:
    results: dict[str, float] = {}
    
    # Character-level search (morphological similarity)
    if query_vectors["char"] is not None:
        char_results = await self._search_embedding_level(
            query_vectors["char"], "char", max_results * 2
        )
        for word, score in char_results:
            results[word] = results.get(word, 0.0) + score * 0.2  # 20% weight
    
    # Subword-level search (decomposition)
    if query_vectors["subword"] is not None:
        subword_results = await self._search_embedding_level(
            query_vectors["subword"], "subword", max_results * 2
        )
        for word, score in subword_results:
            results[word] = results.get(word, 0.0) + score * 0.3  # 30% weight
    
    # Word-level search (semantic similarity)
    if query_vectors["word"] is not None:
        word_results = await self._search_embedding_level(
            query_vectors["word"], "word", max_results * 2
        )
        for word, score in word_results:
            results[word] = results.get(word, 0.0) + score * 0.5  # 50% weight

# FAISS indices with normalization safety
async def _build_faiss_indices(self) -> None:
    if self.char_embeddings is not None:
        self.char_index = faiss.IndexFlatIP(self.char_embeddings.shape[1])
        norms = np.linalg.norm(self.char_embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        char_norm = self.char_embeddings / norms
        self.char_index.add(char_norm.astype(np.float32))
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

## Enhanced CLI System Architecture

### Intelligent Word Lookup with Fallback Chain

The CLI system implements a sophisticated lookup strategy that cascades through multiple methods to ensure comprehensive word coverage:

```python
class EnhancedWordLookup:
    """Enhanced word lookup with intelligent search fallback and AI generation"""
    
    async def lookup_with_fallback(self, query: str) -> tuple[str | None, list[ProviderData]]:
        # Step 1: Direct normalization and variant generation
        normalized_query = normalize_word(query)
        variants = generate_word_variants(query)
        
        # Step 2: Try each variant with database and providers
        for variant in variants:
            provider_data = await self._try_providers(variant, providers)
            if provider_data:
                return variant, provider_data
        
        # Step 3: Search fallback (exact → fuzzy, semantic disabled for reliability)
        search_methods = [SearchMethod.EXACT, SearchMethod.FUZZY]
        for method in search_methods:
            search_results = await self.search_engine.search(
                query=normalized_query, methods=[method]
            )
            # Try search results with providers
            
        # Step 4: AI fallback generation with structured output
        if self.openai_connector:
            ai_data = await self._generate_ai_fallback(query)
            if ai_data:
                return normalized_query, [ai_data]
```

### Rich Terminal Interface

The CLI provides beautiful, informative output using Rich formatting:

- **Cyan-colored examples** with bolded target words for visual emphasis
- **Per-word-type organization** showing definitions grouped by grammatical function
- **Phonetic pronunciations** for AI-generated entries
- **Search method indicators** showing which algorithm found each result
- **Progress indicators** for search initialization and processing

### Production-Ready Error Handling

- **Timeout protection** for search engine initialization (30-second limit)
- **Graceful degradation** when semantic search fails (falls back to exact + fuzzy)
- **AI fallback generation** for unknown words/phrases with proper error handling
- **Provider fallback chain** ensuring definitions are found through multiple sources

## Current System Status

### Completed Components (100%)

1. **Core Data Models**: Pydantic v2 + Beanie ODM with modern typing
2. **Dictionary Connectors**: Wiktionary + Oxford with advanced parsing
3. **AI Integration**: OpenAI with structured outputs and bulk processing
4. **Search Engine**: Multi-method search with timeout protection and FAISS
5. **CLI System**: Enhanced lookup with Rich formatting and AI fallback
6. **Anki Generation**: Complete .apkg export with beautiful templates
7. **Storage System**: MongoDB with Beanie ODM and comprehensive caching

### Key Architectural Achievements

- **Restored Essential Dependencies**: All 39 dependencies including FAISS, scikit-learn
- **Timeout Protection**: 30-second limits prevent CLI hangs during search initialization
- **Safety Features**: Division-by-zero protection in embedding normalization
- **Per-Word-Type AI Synthesis**: Organized by grammatical function, not flattened
- **Enhanced Error Handling**: Robust fallback mechanisms throughout the system
- **Production Quality**: MyPy passes completely, tests cover core functionality

This architecture ensures that Floridify's capabilities can scale and adapt to evolving requirements while maintaining optimal performance and reliability across diverse use scenarios.

# System Architecture

## Overview

Floridify employs a layered architecture with provider-based data collection, AI-powered meaning synthesis, and hierarchical storage. The system separates raw dictionary data from synthesized, display-ready entries to enable flexible data sources while maintaining consistent output quality.

## Core Design Principles

**Provider Agnostic**: Dictionary data organized by source provider with unified synthesis layer
**Meaning-First**: AI extracts semantic clusters before synthesis to prevent mixing unrelated definitions  
**Cache-Heavy**: Aggressive caching at multiple levels for performance and cost optimization
**Type-Safe**: Comprehensive Pydantic validation throughout the data pipeline

## Data Models (`models/dictionary.py`)

### Core Word Representation

```python
class Word(BaseModel):
    text: str                                    # Normalized word text
    embedding: dict[str, np.ndarray]            # Vector embeddings by model
```

**Purpose**: Central word representation with semantic embeddings for search capabilities.

### Definition Structure

```python
class Definition(BaseModel):
    word_type: WordType                          # noun, verb, adjective, etc.
    definition: str                              # Synthesized definition text
    synonyms: list[SynonymReference]             # Related word references
    examples: Examples                           # Generated and literature examples
    meaning_cluster: str | None                  # AI-extracted meaning cluster ID
    raw_metadata: dict[str, Any] | None         # Provider-specific metadata
```

**Key Feature**: `meaning_cluster` field enables hierarchical display grouping (bank¹, bank²).

### Provider Data Organization

```python
class ProviderData(BaseModel):
    provider_name: str                           # "wiktionary", "oxford", etc.
    definitions: list[Definition]                # Provider-specific definitions
    last_updated: datetime
    raw_metadata: dict[str, Any] | None
```

**Purpose**: Isolates provider-specific data while maintaining common structure.

### Document Storage

#### Raw Dictionary Entries
```python
class DictionaryEntry(Document):             # MongoDB collection: dictionary_entries
    word: Word
    pronunciation: Pronunciation
    providers: dict[str, ProviderData]       # Organized by provider name
    last_updated: datetime
```

**Purpose**: Stores raw provider data with layered access pattern.

#### Synthesized Entries  
```python
class SynthesizedDictionaryEntry(Document):  # MongoDB collection: synthesized_dictionary_entries
    word: Word
    pronunciation: Pronunciation
    definitions: list[Definition]            # AI-synthesized with meaning clusters
    last_updated: datetime
```

**Purpose**: Display-ready entries with meaning-based organization.

#### API Response Cache
```python
class APIResponseCache(Document):            # MongoDB collection: api_response_cache
    word: str
    provider: str                            # "openai", "wiktionary", etc.
    response_data: dict[str, Any]           # Raw API response
    timestamp: datetime
```

**Purpose**: Caches external API calls with TTL for performance and cost optimization.

#### Word List Management
```python
class WordList(Document):                    # MongoDB collection: word_lists
    name: str
    words: list[WordFrequency]              # Words with frequency tracking
    metadata: WordListMetadata
    created_at: datetime
    updated_at: datetime
```

**Purpose**: Manages vocabulary collections for batch processing and Anki export.

#### Anki Export System
```python
class AnkiCard(BaseModel):
    word: str
    card_type: AnkiCardType                 # "fill_blank", "multiple_choice"
    question: str                           # AI-generated question
    answer: str                             # Synthesized definition
    styling: str                            # Claude-inspired CSS
```

**Purpose**: Generates academically rigorous flashcards from synthesized definitions.

## Storage Architecture

### MongoDB + Beanie ODM

**Database**: Single MongoDB database with multiple collections
**ODM**: Beanie provides async ODM with automatic validation and serialization
**Indexes**: Optimized for word lookup and temporal queries

**Collections**:
- `dictionary_entries`: Raw provider data by word
- `synthesized_dictionary_entries`: AI-processed display entries  
- `api_response_cache`: External API response cache
- `word_lists`: Vocabulary collections with frequency tracking

### Index Strategy

```python
# Word-based lookups (primary access pattern)
[("word.text", "text")]     # Text search index

# Temporal queries (cache management)
"last_updated", "timestamp"

# Composite queries (cache retrieval)
[("word", 1), ("provider", 1)]
```

## Processing Pipeline

### 1. Data Ingestion
**Input**: Word query from CLI
**Process**: Multi-method search (exact → fuzzy → semantic)
**Output**: Target word for definition lookup

### 2. Provider Data Fetch
**Input**: Target word
**Process**: Parallel API calls to dictionary providers
**Output**: Raw provider definitions organized by source

### 3. AI Meaning Extraction
**Input**: All provider definitions
**Process**: AI identifies distinct semantic clusters
**Output**: Meaning groups with associated word types

```python
class MeaningCluster(BaseModel):
    meaning_id: str                          # "bank_financial", "bank_geographic"
    core_meaning: str                        # Brief description
    word_types: list[WordType]              # Applicable grammatical types
    definitions_by_type: list[MeaningClusterDefinition]
    confidence: float
```

### 4. Definition Synthesis
**Input**: Meaning clusters + provider definitions
**Process**: AI synthesizes unified definitions per cluster/type combination
**Output**: Hierarchical definitions with meaning metadata

### 5. Display Formatting
**Input**: Synthesized entry with meaning clusters
**Process**: Group by meaning, format with superscripts if multiple meanings
**Output**: Rich terminal display with proper typography

## Component Integration

### Search Engine Integration
**Embeddings**: Word vectors stored in Word model for semantic search
**Fallback**: AI generation triggered when search returns no results
**Caching**: Search indices cached separately from dictionary data

### AI System Integration  
**Structured Outputs**: Type-safe AI responses using Pydantic schemas
**Meaning Metadata**: AI-extracted clusters stored in Definition models
**Caching**: All AI responses cached with content-based keys

### CLI Integration
**Formatting**: Meaning cluster metadata enables grouped display
**Typography**: Consistent casing and structure across all output
**Error Handling**: Graceful degradation with informative messages

### Anki Export Integration
**Card Generation**: AI creates GRE-level fill-blank and multiple-choice questions
**Deck Management**: genanki library handles .apkg file creation and updates
**Word List Pipeline**: Full lookup → synthesis → flashcard generation workflow
**Styling**: Claude-inspired CSS for professional flashcard presentation

## Performance Characteristics

### Caching Strategy

**Level 1**: API Response Cache (24-hour TTL)
- Raw provider responses
- OpenAI API responses 
- Embedding generation results

**Level 2**: Synthesized Entry Cache (24-hour TTL)
- Complete processed dictionary entries
- Ready for immediate display

**Level 3**: Search Index Cache (persistent)
- FAISS vector indices
- Trie structures for exact/prefix search

### Cache Hit Rates
**Repeated Lookups**: ~95% hit rate within 24 hours
**Search Operations**: ~99% hit rate for common words
**AI Synthesis**: ~95% hit rate for previously processed words

### Scalability Patterns

**Horizontal**: MongoDB sharding by word prefix
**Vertical**: Provider-specific scaling with independent rate limits  
**Caching**: Redis layer planned for high-frequency access patterns

## Data Flow Example

```
1. User: "bank" → CLI
2. Search: exact match found → "bank"
3. Provider: Wiktionary fetch → 39 definitions across word types
4. AI: Extract meanings → 4 clusters (financial, geographic, arrangement, storage)
5. AI: Synthesize per cluster/type → 6 final definitions with examples
6. Storage: Cache synthesized entry → MongoDB
7. Display: Format with superscripts → bank¹, bank², bank³, bank⁴
8. CLI: Rich terminal output → separate panels per meaning
```

## Configuration Management

### Database Configuration
```toml
[database]
connection_string = "mongodb://localhost:27017"
database_name = "floridify"
```

### AI Configuration  
```toml
[ai]
model_name = "gpt-4o"
temperature = 0.7
max_tokens = 1000
```

### Provider Configuration
```toml
[providers.wiktionary]
rate_limit = 10  # requests per second
timeout = 30     # seconds
```

## Security Considerations

**API Keys**: Stored in config files, not in database
**Input Validation**: Comprehensive Pydantic validation at all boundaries
**Rate Limiting**: Adaptive throttling prevents provider API abuse
**Data Sanitization**: All user inputs normalized and validated

## Monitoring & Observability

**Logging**: Structured logging with contextual information
**Metrics**: Cache hit rates, API call patterns, synthesis success rates  
**Health Checks**: Provider availability, database connectivity
**Performance**: Response times, memory usage, cache efficiency
# AI Integration

## Overview

The AI system provides intelligent definition synthesis with meaning-based clustering, preventing confusion between unrelated word senses. Built on OpenAI's structured output capabilities, it creates hierarchical dictionary entries organized by distinct semantic meanings.

## Core Components

### OpenAI Connector (`ai/connector.py`)

**Purpose**: Modern async interface to OpenAI API with structured outputs and comprehensive caching

**Key Features**:
- **Model Capability Detection**: Automatic detection of reasoning vs standard models (o1, o3 vs gpt-4o)
- **Structured Outputs**: Type-safe responses using Pydantic schemas
- **Comprehensive Caching**: MongoDB-backed cache with proper TTL handling
- **Bulk Processing**: Optimized API usage for cost efficiency

**Core Methods**:
```python
async def extract_meanings(word: str, all_provider_definitions: list[tuple[str, str, str]]) -> MeaningExtractionResponse
async def synthesize_definition(word: str, word_type: str, provider_definitions: list[tuple[str, str]]) -> SynthesisResponse
async def generate_example(word: str, definition: str, word_type: str) -> ExampleGenerationResponse
async def generate_fallback_entry(word: str) -> FallbackResponse
async def generate_embeddings(texts: list[str]) -> EmbeddingResponse
async def generate_anki_fill_blank(word: str, definition: str) -> AnkiFillBlankResponse
async def generate_anki_multiple_choice(word: str, definition: str) -> AnkiMultipleChoiceResponse
```

### Definition Synthesizer (`ai/synthesizer.py`)

**Purpose**: Orchestrates the meaning-based synthesis pipeline

**Architecture**: 
1. **Meaning Extraction**: AI identifies distinct semantic clusters before synthesis
2. **Cluster Synthesis**: Generate definitions per meaning cluster and word type
3. **Cache Management**: 24-hour freshness validation with proper time window
4. **Fallback Generation**: Complete AI-only entries for unknown words

**Key Method**:
```python
async def synthesize_entry(word: Word, providers: Mapping[str, ProviderData]) -> SynthesizedDictionaryEntry
```

**Process Flow**:
1. Check cache with 24-hour freshness window
2. Extract meaning clusters using AI
3. Synthesize definitions for each cluster + word type combination
4. Generate examples and pronunciation
5. Store with meaning cluster metadata for display grouping

## Meaning-Based Architecture

### Meaning Extraction

**Problem Solved**: Words like "bank" have distinct meanings (financial institution vs. river bank) that shouldn't be mixed in synthesis.

**Implementation**: AI analyzes all provider definitions and creates semantic clusters:

```python
class MeaningCluster(BaseModel):
    meaning_id: str              # "bank_financial", "bank_geographic"
    core_meaning: str            # Brief description 
    word_types: list[WordType]   # Applicable grammatical types
    definitions_by_type: list[MeaningClusterDefinition]
    confidence: float
```

**Prompt Template** (`prompts/meaning_extraction.md`):
- Emphasizes creating separate meanings only for truly distinct senses
- Includes example to prevent duplicate meanings (e.g., "backstage" vs "behind scenes")
- Instructs AI to group related word types together

### Hierarchical Synthesis

**Before**: Definitions grouped by word type only → mixed meanings
**After**: Definitions grouped by meaning first, then word type → clear separation

**Display Result**:
- Single meaning: No sub-panels, clean display
- Multiple meanings: Separate panels with Unicode superscripts (bank¹, bank²)

## Data Models (`ai/models.py`)

### Core Response Models

```python
class MeaningExtractionResponse(BaseModel):
    word: str
    meaning_clusters: list[MeaningCluster]
    total_meanings: int
    confidence: float

class SynthesisResponse(BaseModel):
    synthesized_definition: str
    confidence: float
    sources_used: list[str]

class ExampleGenerationResponse(BaseModel):
    example_sentence: str
    confidence: float

class AnkiFillBlankResponse(BaseModel):
    question: str          # Sentence with blank
    answer: str           # Word to fill blank
    confidence: float

class AnkiMultipleChoiceResponse(BaseModel):
    question: str         # Question stem
    options: list[str]    # Four answer choices
    correct_index: int    # Index of correct answer (0-3)
    confidence: float
```

### Model Capabilities

```python
class ModelCapabilities(BaseModel):
    supports_reasoning: bool      # o1, o3 models
    supports_temperature: bool    # Not available on reasoning models
    supports_structured_output: bool
```

**Automatic Detection**: Reasoning models (o1, o3) vs standard models (gpt-4o)

### Fallback System

```python
class FallbackResponse(BaseModel):
    provider_data: AIProviderData | None
    confidence: float
    is_nonsense: bool
```

**Purpose**: Generate complete entries for unknown words/phrases with pronunciation and examples.

## Prompt Templates (`ai/prompts/`)

### Template System (`ai/templates.py`)

**Jinja2-based**: Markdown templates with variable substitution for maintainability

**Available Templates**:
- `meaning_extraction.md`: Extract distinct semantic meanings
- `synthesis.md`: Synthesize unified definitions (1-2 sentences max)
- `example_generation.md`: Generate modern usage examples
- `fallback_provider.md`: Complete AI-only entries
- `pronunciation.md`: Phonetic pronunciations
- `anki_fill_blank.md`: Fill-in-the-blank flashcard generation
- `anki_multiple_choice.md`: Multiple choice flashcard generation

### Key Template Features

**Meaning Extraction**:
- Emphasizes semantic distinctness over minor variations
- Includes anti-duplication example ("en coulisse")
- Ensures all input definitions are categorized

**Synthesis**:
- Concise output (1-2 sentences maximum)
- Academic dictionary tone
- Preserves key terminology while removing redundancy

**Anki Flashcard Generation**:
- **Fill-in-Blank**: GRE-level cloze questions testing semantic understanding
- **Multiple Choice**: Four-option questions with plausible distractors
- Academic rigor appropriate for standardized test preparation
- Questions target conceptual understanding, not rote memorization

## Caching Strategy

### MongoDB Integration

**Cache Types**:
- **API Response Cache**: Raw OpenAI responses with TTL
- **Synthesized Entries**: Complete processed entries with 24-hour freshness

**Cache Keys**:
```python
f"synthesis_{word}_{word_type}_{hash(provider_definitions)}"
f"meanings_{word}_{hash(all_provider_definitions)}"
f"example_{word}_{word_type}_{hash(definition)}"
```

### Freshness Validation

**Problem**: Provider timestamps are meaningless (set on each fetch)
**Solution**: Time-based freshness window (24 hours) instead of strict timestamp comparison

```python
def _is_fresh(entry: SynthesizedDictionaryEntry, providers: Mapping[str, ProviderData]) -> bool:
    max_age = timedelta(hours=24)
    age = datetime.now() - entry.last_updated
    return age <= max_age
```

## Configuration

### Model Selection

**Default**: `gpt-4o` (fast, cost-effective)
**Reasoning**: `o1-mini`, `o3-mini` (for complex reasoning tasks)
**Embeddings**: `text-embedding-3-small`

### Rate Limiting

**Implementation**: Semaphore-based throttling with adaptive backoff
**Caching**: Aggressive caching to minimize API calls
**Bulk Processing**: Planned for large-scale operations

## Error Handling

### Graceful Degradation

1. **Cache Miss**: Proceed with fresh synthesis
2. **API Failure**: Log error, attempt fallback
3. **Invalid Response**: Retry with simpler prompt
4. **Nonsense Words**: Return minimal entry with appropriate flags

### Logging

**Contextual Logging**: Shows meaning and word type being synthesized
```
🧠 Extracting meaning clusters for 'bank' from 39 definitions
🎯 Synthesized 'bank' (noun) - financial
```

## Integration Points

### Search Engine Integration

**Embeddings**: Generated for semantic search capabilities
**Fallback**: AI generation when no dictionary results found

### CLI Display Integration

**Meaning Metadata**: Definitions include `meaning_cluster` field for grouped display
**Formatting**: Supports both single and multi-meaning display modes

### Storage Integration

**MongoDB**: All responses cached with proper serialization
**Validation**: Pydantic models ensure data integrity throughout pipeline

### Anki Integration

**Card Generation**: AI creates academically rigorous flashcards from synthesized definitions
**Question Types**: Fill-in-blank and multiple choice with GRE-level difficulty
**Export Pipeline**: Integrates with word list processing for batch flashcard generation

## Performance Characteristics

**Cache Hit Rate**: ~95% for repeated lookups within 24 hours
**API Efficiency**: Structured outputs reduce parsing overhead
**Response Time**: ~2-3 seconds for fresh synthesis, <100ms for cached
**Cost Optimization**: Aggressive caching minimizes API usage
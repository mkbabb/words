# AI Integration

## Overview

The AI system provides intelligent definition synthesis with meaning-based clustering, preventing confusion between unrelated word senses. Built on structured output capabilities from OpenAI (GPT-5 series) and Anthropic (Claude), it creates hierarchical dictionary entries organized by distinct semantic meanings. Embeddings are handled locally via sentence-transformers (Qwen3-0.6B), not through any external API.

## Core Components

### AI Connector (`ai/connector/`)

**Purpose**: Unified async interface supporting OpenAI and Anthropic with structured outputs and task-based model routing.

**Key Features**:
- **Multi-provider support**: OpenAI GPT-5 series and Anthropic Claude via a unified `AIConnector` class
- **Task-based model routing**: Automatic model selection based on task complexity (see Model Selection below)
- **Structured Outputs**: Type-safe responses using Pydantic schemas
- **Comprehensive Caching**: MongoDB-backed cache with TTL handling

**Submodules**: `base.py` (core connector), `synthesis.py`, `generation.py`, `assessment.py`, `suggestions.py`

### Definition Synthesizer (`ai/synthesizer.py`)

**Purpose**: Orchestrates the meaning-based synthesis pipeline

**Process Flow**:
1. Check cache with freshness window
2. Deduplicate provider definitions via AI
3. Cluster deduplicated definitions into semantic groups
4. Parallel synthesis: definitions, pronunciation, etymology, facts via `asyncio.gather`
5. Post-synthesis enhancement: up to 11 sub-tasks per definition (synonyms, examples, antonyms, word forms, CEFR, frequency, register, domain, grammar patterns, collocations, usage notes)
6. Store with versioned history via content-addressable SHA-256 chains

### Prompt Manager (`ai/prompt_manager.py`)

Manages Jinja2-based markdown prompt templates in `ai/prompts/`. Templates include meaning extraction, synthesis, example generation, fallback provider, pronunciation, and Anki card generation.

## 3-Tier Model Selection (`ai/model_selection.py`)

All GPT-5 series. Task complexity determines which model handles each request:

| Tier | Model | Tasks |
|------|-------|-------|
| HIGH | gpt-5.4 | Definition synthesis, clustering, suggestions, synthetic corpus, literature analysis |
| MEDIUM | gpt-5-mini | Synonyms, examples, dedup, etymology, Anki cards, collocations, word forms, antonyms |
| LOW | gpt-5-nano | CEFR, frequency, register, domain, pronunciation, usage notes, grammar patterns |

Temperature routing: creative tasks (facts, examples, suggestions) get 0.8; classification tasks (CEFR, frequency, register) get 0.3; default 0.7.

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

### Hierarchical Synthesis

- Single meaning: No sub-panels, clean display
- Multiple meanings: Separate panels with Unicode superscripts (bank^1, bank^2)

## Embeddings

Embeddings for semantic search are generated **locally** using sentence-transformers with the Qwen3-0.6B model (1024D vectors). No external embedding API is used. FAISS HNSW indices provide sub-millisecond query times. See `search/` for details.

## Caching Strategy

**Cache Types**:
- **API Response Cache**: Raw AI responses with TTL
- **Synthesized Entries**: Complete processed entries with freshness window

**Freshness Validation**: Time-based freshness window rather than strict timestamp comparison, since provider timestamps are set on each fetch and are not meaningful for staleness detection.

## Error Handling

1. **Cache Miss**: Proceed with fresh synthesis
2. **API Failure**: Log error, attempt fallback
3. **Invalid Response**: Retry with simpler prompt
4. **Nonsense Words**: Return minimal entry with appropriate flags (`is_nonsense`)

## Integration Points

- **Search**: AI fallback generation when no dictionary results found
- **CLI**: Meaning metadata in definitions enables grouped display with Rich panels
- **Anki**: AI creates fill-in-blank and multiple choice flashcards from synthesized definitions
- **Storage**: All responses cached in MongoDB with Pydantic validation throughout

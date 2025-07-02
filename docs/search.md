# Search Engine

Multi-method search with FAISS acceleration for intelligent word discovery.

## Core Engine

**SearchEngine** (`search/core.py`) provides unified search interface with method cascade: exact → fuzzy → semantic → AI fallback.

```python
class SearchEngine:
    def __init__(
        languages: list[Language] | None = None,
        min_score: float = 0.6,
        enable_semantic: bool = True,
    )
```

**SearchResult** model:
```python
class SearchResult(BaseModel):
    word: str              # Matched word or phrase
    score: float           # Relevance score (0.0-1.0)
    method: SearchMethod   # Search method used
    is_phrase: bool        # Multi-word expression flag
```

## Search Methods

### Exact Search (`search/trie.py`)
- Hash-based O(1) word lookup
- Trie structure for prefix matching
- Case-insensitive with normalization

### Fuzzy Search (`search/fuzzy.py`)
**Algorithms**: Levenshtein, Jaro-Winkler, Soundex
**Features**: Length-aware scoring, phrase boundary detection, adaptive algorithm selection

### Semantic Search (`search/semantic.py`)
**Technology**: FAISS + OpenAI embeddings (text-embedding-3-small)
**Features**: Conceptual similarity, timeout protection, batch processing

### Hybrid Search
Combines all methods with score normalization and deduplication.

## Performance

**Initialization**:
- Cold start: ~3-5 seconds
- Warm start: ~200-300ms

**Search Times**:
- Exact: <1ms
- Prefix: <5ms  
- Fuzzy: 10-50ms
- Semantic: 50-200ms

**Memory**: ~150MB per language

## Multi-Language Support

```python
class Language(Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    # ...
```

**PhraseNormalizer** (`search/phrase.py`) handles multi-word expressions with whitespace standardization and punctuation normalization.

## CLI Integration

```bash
uv run ./scripts/floridify search init      # Initialize indices
uv run ./scripts/floridify search word cogn # Search for matches
```

## Configuration

```toml
[search]
min_score = 0.6
enable_semantic = true
languages = ["en", "fr"]

[search.fuzzy]
levenshtein_threshold = 0.8
max_distance = 3

[search.semantic]
timeout_seconds = 5.0
similarity_threshold = 0.7
```

## Error Handling

**Timeout Protection**: 5-second semantic search timeout with fuzzy fallback
**Graceful Degradation**: Semantic → Fuzzy → Exact → Empty results
**FAISS Recovery**: Automatic index rebuilding on corruption

## Caching

**Multi-level**:
- In-memory LRU cache (1000 entries)
- Disk-based FAISS/lexicon cache
- MongoDB API response cache
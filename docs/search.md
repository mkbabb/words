# Search Engine

## Architecture

**Unified API** with four search methods:
- **Exact**: Trie-based exact matching (~0.001ms)
- **Prefix**: Autocomplete with frequency ranking (~0.001ms) 
- **Fuzzy**: RapidFuzz typo tolerance (~0.01ms)
- **Semantic**: TF-IDF + cosine similarity (~0.1ms)

## Current Implementation

### Core Components
```python
# Single search interface
results = await engine.search(
    query="machine learning",
    methods=[SearchMethod.AUTO],  # Automatic selection
    max_results=20
)
```

### Method Selection
- **Short queries (≤3)**: Prefix + Exact
- **Medium (4-8)**: Exact + Fuzzy  
- **Long (>8)**: Exact + Fuzzy + Semantic
- **Phrases**: Exact + Semantic + Fuzzy

### Lexicon Sources
- **English**: 476k words, 4.5k phrases (verified URLs)
- **French**: 336k words from french-words-array, frequency lists
- **Formats**: TEXT_LINES, JSON_ARRAY, FREQUENCY_LIST, CSV_IDIOMS

## Updated Implementation

### Normalization Pipeline
- **Whitespace**: Strip leading/trailing spaces
- **Case**: Lowercase all entries
- **Diacritics**: Generate variants ("à la carte" + "a la carte")

### Deduplication
- **Master index**: Single normalized set per language
- **Priority**: Frequency lists > dictionaries > phrase collections
- **Result**: ~30-40% size reduction, better search coverage

### Enhanced Phrase Support
- **English phrases**: Common idioms, technical terms
- **French phrases**: Expressions with/without diacritics
- **Automatic variants**: Both normalized and original forms indexed

### CLI Commands
```bash
floridify search init                    # Initialize index
floridify search word "cogn" --method fuzzy  # Search lexicon  
floridify search stats                   # Performance metrics
```

## Performance
- **Index size**: 450k EN words, 300k FR words (post-dedup)
- **Load time**: ~20s initialization
- **Memory**: 200MB total
- **Search**: Sub-millisecond exact, ~10ms fuzzy/semantic
# Lexicon System

Multi-language word and phrase databases for search operations.

## Core Components

**LexiconLoader** (`search/lexicon/lexicon.py`) provides unified interface for loading and caching lexicon data.

```python
class LexiconData(BaseModel):
    words: list[str]                          # Single word entries
    phrases: list[MultiWordExpression]        # Multi-word expressions
    language: Language                        # Target language
    sources: list[str]                        # Loaded source names
    total_entries: int                        # Total entry count
```

**Source Configuration** (`search/lexicon/sources.py`):
```python
class LexiconSourceConfig(BaseModel):
    name: str                                # Unique identifier
    url: str                                 # Download URL
    format: LexiconFormat                    # TEXT_LINES, JSON, CSV
    language: Language                       # Target language
    downloader: DownloaderFunc              # Custom download function
```

## Data Sources

**English**:
- `sowpods_scrabble_words`: SOWPODS Scrabble dictionary (~267k words)
- `google_10k_frequency`: Most common 10k English words
- `english_phrasal_verbs_comprehensive`: Phrasal verb database

**French**:
- `french_scrabble_ods8`: Official French Scrabble dictionary
- `french_frequency_50k`: Top 50k French words by frequency
- `french_expressions_in_english`: French phrases used in English

## Multi-Word Expressions

**MultiWordExpression** model (`search/phrase.py`):
```python
class MultiWordExpression(BaseModel):
    text: str                   # Original phrase text
    normalized: str             # Normalized form
    word_count: int            # Number of words
    language: Language         # Source language
```

**Normalization**: Whitespace standardization, punctuation handling, case normalization, hyphenation consistency.

## Storage and Caching

**File Structure**:
```
data/search/
├── lexicons/           # Raw lexicon files
│   ├── sowpods_scrabble_words.txt
│   └── french_scrabble_ods8.txt
└── index/             # Cached processed data
    ├── en_lexicon.pkl # English lexicon cache
    └── fr_lexicon.pkl # French lexicon cache
```

**Performance**:
- Cold start: ~2-3 seconds
- Warm start: ~10-50ms
- Memory: ~50MB per language

## Language Support

```python
class Language(Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    # Extensible
```

**Adding Languages**:
1. Add language enum value
2. Create source configurations
3. Implement language-specific normalization

## Integration

**Search Engine**: Direct lexicon lookup for word validation, fuzzy candidates, semantic embeddings
**CLI**: `uv run ./scripts/floridify search init` for initialization

## Error Handling

**Download Failures**: Exponential backoff with cached fallback
**Data Corruption**: Automatic cache rebuild on validation failure
**Network Issues**: Graceful degradation with detailed logging
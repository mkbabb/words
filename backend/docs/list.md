# Word List Management

Batch word list processing with dictionary lookup and frequency tracking.

## Core System

**WordListParser** (`word_list/parser.py`) handles multi-format parsing with robust word extraction.
**WordList** (`word_list/models.py`) provides MongoDB storage with frequency tracking and CRUD operations.

## Models

```python
class WordFrequency(BaseModel):
    text: str               # Word text
    frequency: int          # Occurrence count
    created_at: datetime    # First seen timestamp
    updated_at: datetime    # Last seen timestamp

class WordList(Document):
    name: str                      # Human-readable name
    hash_id: str                   # Content-based identifier
    words: list[WordFrequency]     # Words with frequency tracking
    total_words: int               # Total occurrences
    unique_words: int              # Unique word count
    created_at: datetime           # Creation timestamp
    updated_at: datetime           # Last modification
```

## CLI Commands

```bash
# Create word list with full lookup pipeline
uv run ./scripts/floridify word-list create words.txt --name "my-vocab"
uv run ./scripts/floridify word-list create words.txt  # Auto-generated name

# Management operations
uv run ./scripts/floridify word-list list           # Show all lists
uv run ./scripts/floridify word-list show my-vocab  # Show details with heat map
uv run ./scripts/floridify word-list update my-vocab new-words.txt
uv run ./scripts/floridify word-list delete my-vocab
```

**Options**:
- `--provider`: Dictionary provider (wiktionary, oxford, dictionary_com, ai, synthetic)
- `--language`: Language (en, fr, es, de, it)
- `--semantic`: Enable semantic search
- `--no-ai`: Skip AI synthesis

## Supported Formats

**Numbered Lists**: `1. word`, `2) another`
**Comma-Separated**: `word1, word2, phrase`
**Tab-Separated**: `word1	word2	phrase`
**Plain Text**: One word/phrase per line

**Auto-Detection**: Format automatically detected and parsed.

## Processing Pipeline

1. **Parse**: Extract words from file with format detection
2. **Normalize**: Clean and validate word entries
3. **Store**: Save WordList with frequency tracking to database
4. **Lookup**: Process each word through full dictionary pipeline in batches:
   - Word normalization
   - Search engine lookup
   - Provider definition retrieval
   - AI synthesis with meaning extraction
   - Database caching

**Batch Size**: 10 words processed in parallel for optimal performance.

## Auto-Naming

**Generated Names**: Uses coolname library for animal phrases (e.g., "ochre-guan", "ebony-tanuki")
**Fallback**: Hash-based naming if generation fails
**Uniqueness**: Automatic collision handling

## Frequency Tracking

**Interest Measurement**: Word frequency indicates importance within the list
**Heat Map Display**: Visual frequency representation with colored bars
**Statistics**: Tracks unique vs. total word counts, most frequent words

## Integration

**Database**: MongoDB storage with Beanie ODM
**Search Engine**: Full integration with search pipeline for word validation
**Lookup Pipeline**: Each word processed through complete dictionary lookup system
**Caching**: All lookups cached for future search and lookup operations

## Error Handling

**File Formats**: Graceful parsing of malformed input
**Encoding**: UTF-8 with latin-1 fallback
**Network**: Timeout protection with graceful degradation
**Duplicates**: Automatic frequency updates for repeat words
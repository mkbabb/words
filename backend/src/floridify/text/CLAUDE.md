# Text Module - Normalization & Processing

Text normalization, lemmatization, signature generation for search optimization.

## Key Functions

**Normalization** (`normalize.py`):
- `normalize()` - Remove diacritics, lowercase, strip whitespace
- `normalize_basic()` - Simple lowercase + strip
- `batch_normalize()` - Parallel processing for large vocabularies
- `lemmatize_comprehensive()` - Convert to base form (running → run)
- `batch_lemmatize()` - Parallel lemmatization

**Signature Generation** (`signature.py`):
- `get_word_signature()` - Consonant-only signature ("perspicacious" → "prsp")
- Used for fuzzy search bucketing

**Utilities**:
- `is_phrase()` - Detect multi-word phrases
- `split_words()` - Tokenization
- `remove_punctuation()` - Clean text

**Performance**: Batch operations use asyncio for 10-100x speedup on large vocabularies

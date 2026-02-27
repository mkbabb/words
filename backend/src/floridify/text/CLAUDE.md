# text/

Text normalization, lemmatization, signature generation.

```
text/
├── normalize.py (614)      # normalize_comprehensive(), lemmatize, LRU cache (50K entries)
├── constants.py (133)      # Regex patterns, Unicode mappings, suffix rules
└── phrase.py (24)          # Phrase detection
```

- `normalize_basic()` — lowercase + strip
- `normalize_comprehensive()` — diacritics, Unicode, contractions, LRU cached
- `lemmatize_comprehensive()` — base form (running → run)
- `batch_normalize()` / `batch_lemmatize()` — parallel for large vocabularies
- `get_word_signature()` — consonant-only signature for fuzzy search bucketing

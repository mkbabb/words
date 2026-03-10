# text/

Text normalization, lemmatization, phrase detection.

```
text/
├── __init__.py
├── constants.py        # Regex patterns, Unicode mappings, suffix rules
├── normalize.py        # normalize_comprehensive(), lemmatize, batch ops
└── phrase.py           # is_phrase()—multi-word detection
```

- `normalize_basic()`—lowercase + strip
- `normalize_comprehensive()`—diacritics, Unicode (ftfy), contractions, LRU cached
- `lemmatize_comprehensive()`—NLTK WordNetLemmatizer with POS tagging
- `batch_normalize()` / `batch_lemmatize()`—ProcessPoolExecutor for large vocabularies
- `is_valid_word()`—length and alphabetic checks

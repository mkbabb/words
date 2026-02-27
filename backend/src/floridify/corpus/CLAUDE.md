# corpus/

Vocabulary management. UUID-based tree hierarchy, per-resource locking, 9 parsers.

```
corpus/
├── core.py (744)           # Corpus: UUID hierarchy, vocabulary indices
├── manager.py (1,364)      # TreeCorpusManager: hierarchy ops, aggregation
├── parser.py (268)         # 9 parsers (text, freq, JSON, CSV, phrasal verbs, etc.)
├── models.py (37)          # CorpusType/CorpusSource enums
├── utils.py (53)           # get_vocabulary_hash() for cache isolation
├── language/core.py (377)  # LanguageCorpus: add/remove/update sources
└── literature/core.py (358) # LiteratureCorpus: add/remove/update works
```

## Corpus Model

`vocabulary`, `original_vocabulary`, `lemmatized_vocabulary`. Signature and length buckets for fuzzy search candidate selection. UUID parent-child relationships (not ObjectIds — stable across versions).

## TreeCorpusManager

Recursive aggregation across parent → child hierarchy. Per-resource locking (3-5x throughput vs global lock). N+1 query fix. Cascade deletion. CRUD with vocabulary diff tracking.

## Parsers

Text, frequency list, JSON, CSV, GitHub wordlist, phrasal verbs, custom format, URL-based, literature extraction.

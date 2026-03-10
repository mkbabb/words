# corpus/

Vocabulary management. UUID-based tree hierarchy, per-resource locking, parsers.

```
corpus/
├── core.py                 # Corpus: UUID hierarchy, vocabulary indices
├── manager.py              # TreeCorpusManager: hierarchy ops, per-resource locking
├── crud.py                 # CRUD operations
├── tree.py                 # Tree traversal, hierarchy operations
├── aggregation.py          # MongoDB aggregation queries
├── semantic_policy.py      # Semantic search policies
├── parser.py               # Parsers (text, freq, JSON, CSV, phrasal verbs, etc.)
├── models.py               # CorpusType/CorpusSource enums
├── utils.py                # get_vocabulary_hash() for cache isolation
├── language/core.py        # LanguageCorpus: add/remove/update sources
└── literature/core.py      # LiteratureCorpus: add/remove/update works
```

## Corpus Model

`vocabulary`, `original_vocabulary`, `lemmatized_vocabulary`. Trigram inverted index and length buckets for fuzzy search candidate selection. UUID parent-child relationships (not ObjectIds—stable across versions).

## TreeCorpusManager

Recursive aggregation across parent → child hierarchy. Per-resource locking. N+1 query fix. Cascade deletion. CRUD with vocabulary diff tracking.

## Parsers

Text, frequency list, JSON, CSV, GitHub wordlist, phrasal verbs, custom format, URL-based, literature extraction.

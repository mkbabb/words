# models/

Pydantic/Beanie models. Type-safe data layer, isomorphic with frontend `types/api/`.

```
models/
├── base.py                 # Language enum, DictionaryProvider enum, BaseMetadata mixin
├── dictionary.py           # Word, Definition, DictionaryEntry (MongoDB documents)
├── relationships.py        # MeaningCluster, Collocation, GrammarPattern, UsageNote
├── parameters.py           # CLI/API shared params (isomorphic with frontend)
├── responses.py            # LookupResponse, SearchResponse, CorpusResponse
├── literature.py           # AuthorInfo, Genre/Period enums
├── registry.py             # ResourceType → Model mapping
└── user.py                 # User(Document) for OAuth
```

## Core Documents

**Word**: `text`, `normalized` (auto-computed), `lemma` (auto-computed), `language`. Indices: `(text, language)`, `normalized`, `lemma`.

**Definition**: `word_id`, `part_of_speech`, `text`, `meaning_cluster`, `synonyms` (0–50), `antonyms` (0–50), `example_ids`, `cefr_level` (A1–C2), `frequency_band` (1–5), `language_register`, `domain`, `grammar_patterns`, `collocations`, `providers`, `model_info`.

**DictionaryEntry**: `word_id`, `definition_ids`, `pronunciation_id`, `fact_ids`, `image_ids`, `provider`, `etymology`, `model_info`.

## Auto-Computed

`Word.__init__()` auto-computes `normalized` via `normalize_basic()` and `lemma` via `lemmatize_comprehensive()`.

## Enums

- **Language**: EN, FR, ES, DE, IT, PT, LA, GRC, ...
- **DictionaryProvider**: WIKTIONARY, OXFORD, DICTIONARY_COM, APPLE_DICTIONARY, FREE_DICTIONARY, MERRIAM_WEBSTER, WORDHIPPO, AI_FALLBACK, SYNTHESIS
- **Genre**: 13 values. **Period**: 9 values.

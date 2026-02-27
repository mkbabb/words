# models/

179+ Pydantic/Beanie models. Type-safe data layer. Isomorphic with frontend `types/api.ts`.

```
models/
├── base.py (143)           # Language enum, DictionaryProvider enum, BaseMetadata mixin
├── dictionary.py (249)     # Word, Definition, DictionaryEntry (MongoDB documents)
├── relationships.py (81)   # MeaningCluster, Collocation, GrammarPattern, UsageNote
├── parameters.py (462)     # CLI/API shared params (isomorphic with frontend)
├── responses.py (416)      # LookupResponse, SearchResponse, CorpusResponse
├── literature.py (102)     # AuthorInfo, Genre/Period enums
├── registry.py (46)        # ResourceType → Model mapping
└── user.py (33)            # User(Document) for OAuth
```

## Core Documents

**Word**: `text`, `normalized` (auto-computed), `lemma` (auto-computed), `language`. Indices: `(text, language)`, `normalized`, `lemma`.

**Definition**: `word_id`, `part_of_speech`, `text`, `meaning_cluster`, `synonyms` (0-50), `antonyms` (0-50), `example_ids`, `cefr_level` (A1-C2), `frequency_band` (1-5), `language_register`, `domain`, `grammar_patterns`, `collocations`, `providers`, `model_info`.

**DictionaryEntry**: `word_id`, `definition_ids`, `pronunciation_id`, `fact_ids`, `image_ids`, `provider`, `etymology`, `model_info`.

## Auto-Computed

`Word.__init__()` auto-computes `normalized` via `normalize_basic()` and `lemma` via `lemmatize_comprehensive()`.

## Enums

- **Language**: EN, FR, ES, DE, IT, PT, LA, GRC, ...
- **DictionaryProvider**: WIKTIONARY, OXFORD, DICTIONARY_COM, APPLE_DICTIONARY, FREE_DICTIONARY, MERRIAM_WEBSTER, WORDHIPPO, AI_FALLBACK, SYNTHESIS
- **Genre**: 13 values. **Period**: 9 values.

# System Architecture

Floridify's architecture separates raw dictionary data from synthesized entries. Multiple dictionary providers feed into an AI synthesis pipeline that deduplicates, clusters, and enhances definitions. The result is a single unified entry per word, stored with full version history.

## Data Models

The data layer uses Beanie ODM documents with `PydanticObjectId` foreign keys throughout—no embedded subdocuments for entities that need independent access.

### Word (`models/dictionary.py`)

```python
class Word(Document, BaseMetadata):
    text: str
    normalized: str  # auto-computed via normalize_basic()
    lemma: str       # auto-computed via lemmatize_comprehensive()
    language: Language
    homograph_number: int | None
```

`Word.__init__()` auto-populates `normalized` and `lemma` on creation. Indices on `(text, language)`, `normalized`, `lemma`, and `(text, homograph_number)`.

### Definition (`models/dictionary.py`)

```python
class Definition(Document, BaseMetadata):
    word_id: PydanticObjectId
    part_of_speech: str
    text: str
    meaning_cluster: MeaningCluster | None
    synonyms: list[str]          # max 50
    antonyms: list[str]          # max 50
    example_ids: list[PydanticObjectId]  # max 20, FK to Example
    cefr_level: Literal["A1"..."C2"] | None
    frequency_band: int | None   # 1-5, Oxford 3000/5000 style
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None
    domain: str | None
    region: str | None
    usage_notes: list[UsageNote]
    grammar_patterns: list[GrammarPattern]
    collocations: list[Collocation]
    transitivity: Literal["transitive", "intransitive", "both"] | None
    word_forms: list[WordForm]
    providers: list[DictionaryProvider]
    model_info: ModelInfo | None
```

`meaning_cluster` drives the grouping that produces superscripted homographs (bank^1, bank^2) in the frontend. Each cluster has an `id`, `name`, `description`, `order`, and `relevance` score.

### DictionaryEntry (`models/dictionary.py`)

```python
class DictionaryEntry(Document, BaseMetadata):
    word_id: PydanticObjectId
    definition_ids: list[PydanticObjectId]  # max 100
    pronunciation_id: PydanticObjectId | None
    fact_ids: list[PydanticObjectId]
    image_ids: list[PydanticObjectId]
    provider: DictionaryProvider
    etymology: Etymology | None
    model_info: ModelInfo | None
```

One `DictionaryEntry` per provider per word. The synthesized entry uses `provider=DictionaryProvider.SYNTHESIS`. Indices on `word_id`, `provider`, and `(word_id, provider)`.

### Supporting Documents

**Pronunciation**: phonetic, IPA, audio file refs, syllables, stress pattern. FK to Word.

**Example**: text, type (`"generated"` or `"literature"`), optional literature source with `text_pos`. FK to Definition.

**Fact**: content, category (`etymology`, `usage`, `cultural`, `linguistic`, `historical`). FK to Word.

**MeaningCluster** (embedded, not a Document): `id`, `name`, `description`, `order`, `relevance`.

## Providers

Six dictionary providers, created via `create_connector()` factory (`providers/factory.py`):

| Provider | Type | Notes |
|----------|------|-------|
| Wiktionary | Scraper (MediaWiki API + HTML) | Default, no auth |
| Apple Dictionary | Local (macOS pyobjc) | Auto-added on Darwin |
| Oxford | API | Requires `app_id` + `api_key` |
| Merriam-Webster | API | Requires `api_key` |
| Free Dictionary | API | No auth |
| WordHippo | Scraper | No auth |

Plus two virtual providers: `AI_FALLBACK` (generated when all providers fail) and `SYNTHESIS` (the merged output).

Rate limiting is handled by `AdaptiveRateLimiter` (`providers/utils.py`)—exponential backoff on errors, speed-up after consecutive successes, Retry-After header support.

## Lookup Pipeline (`core/lookup_pipeline.py`)

Five stages, all async:

```
Query → Search → Cache Check → Provider Fetch → AI Synthesis → Store
```

**1. Search** (`find_best_match`): Normalizes the query via the multi-method search cascade (exact, fuzzy, semantic). If no corpus match, proceeds with the raw query.

**2. Cache Check**: Calls `get_synthesized_entry(word)`. On hit, returns immediately. Skipped when `force_refresh=True`, but the existing entry is preserved in version history.

**3. Provider Fetch**: `asyncio.gather` across all providers, each with a 30-second `asyncio.wait_for` timeout. Results filtered for exceptions and `None`. If every provider fails, falls through to AI fallback (`_ai_fallback_lookup`).

**4. AI Synthesis** (when `no_ai=False`): Passes provider `DictionaryEntry` list to `DefinitionSynthesizer.synthesize_entry()`. Details in the next section.

**5. No-AI Mode** (when `no_ai=True`): `_create_provider_mapped_entry` uses AI only for deduplication and clustering—no content generation. Takes the first provider's data, deduplicates definitions, clusters them, saves the result.

Default providers: Wiktionary + Apple Dictionary (on macOS).

## AI Synthesis Pipeline (`ai/synthesizer.py`)

`DefinitionSynthesizer.synthesize_entry()` runs the full pipeline:

**Dedup**: Batch-loads all definitions from all providers via `Definition.find({"_id": {"$in": all_def_ids}})`. Calls `ai.deduplicate_definitions()` to identify near-duplicates. Creates new `Definition` copies with merged text (originals aren't mutated). Typical reduction: ~50%.

**Cluster**: `cluster_definitions()` groups deduplicated definitions into semantic clusters via AI. Each definition gets a `MeaningCluster` assignment.

**Parallel Synthesis**: Four tasks via `asyncio.gather` with `return_exceptions=True`:

1. `_synthesize_definitions`—groups by cluster, synthesizes one definition per cluster
2. `synthesize_pronunciation`—enhances existing or creates new
3. `synthesize_etymology`—from provider data + AI
4. `generate_facts`—interesting facts about the word

Definitions are required; pronunciation, etymology, and facts degrade gracefully on failure.

**Enhancement**: After the entry is saved, `enhance_definitions_parallel()` runs up to 11 sub-tasks per definition: synonyms, examples, antonyms, word forms, CEFR level, frequency band, register, domain, grammar patterns, collocations, usage notes, regional variants.

**Versioned Save**: `_save_entry_with_version_manager()` stores the entry both in the `VersionedDataManager` chain (history) and as a live `DictionaryEntry` document (current state). Per-resource locks prevent races from concurrent force-refresh calls.

## 3-Tier Model Selection (`ai/model_selection.py`)

All GPT-5 series. Task complexity determines which model handles each request:

| Tier | Model | Tasks |
|------|-------|-------|
| HIGH | gpt-5 | Definition synthesis, clustering, suggestions, synthetic corpus, literature analysis |
| MEDIUM | gpt-5-mini | Synonyms, examples, dedup, etymology, Anki cards, collocations, word forms, antonyms |
| LOW | gpt-5-nano | CEFR, frequency, register, domain, pronunciation, usage notes, grammar patterns |

Temperature routing: reasoning models get `None` (model decides). Creative tasks (facts, examples, suggestions): 0.8. Classification tasks (CEFR, frequency, register): 0.3. Default: 0.7.

The `OpenAIConnector` default model is `gpt-5-nano` (`ai/connector.py`). `get_model_for_task()` overrides per call.

## Search (`search/core.py`)

Three methods, cascading in SMART mode:

| Method | Time | Implementation |
|--------|------|----------------|
| Exact | <1ms | marisa-trie + Bloom filter, O(m) |
| Fuzzy | 10-50ms | RapidFuzz dual-scorer (WRatio + token_set_ratio), signature + length buckets |
| Semantic | 50-200ms | FAISS HNSW, Qwen3-0.6B embeddings (1024D) |

Cascade logic: exact first. If no match, fuzzy. If fuzzy returns <33% high-quality results (score >= 0.7), semantic. Exact match terminates immediately.

FAISS index type scales with corpus size—Flat L2 for <10k words up to OPQ+IVF-PQ for >1M. `SearchEngineManager` hot-reloads indices by polling `vocabulary_hash` every 30 seconds, then atomic-swapping the engine.

## Caching (`caching/`)

Three tiers:

**L1 Memory** (`core.py`): `OrderedDict` LRU per namespace. O(1) get/set/evict via `move_to_end()`. ~0.2ms hit. 13 namespaces with independent limits (50–500 entries) and TTLs (1h–30d).

**L2 Disk** (`filesystem.py`): DiskCache backend, 10GB limit. Per-namespace TTL and optional compression (ZSTD, LZ4, GZIP). ~5ms hit.

**L3 Versioned MongoDB** (`manager.py`): Content-addressable via SHA-256 hashing—identical content reuses versions. `supersedes`/`superseded_by` chains for history. Inline storage for <16KB, external for larger payloads. Per-resource locking (3-5x throughput vs global lock).

## Storage (`storage/mongodb.py`)

Single MongoDB database via Motor (async driver) + Beanie ODM. Connection pool: 50 max, 10 min warm. 28 document models registered at init.

Collections: `words`, `definitions`, `dictionary_entries`, `pronunciations`, `examples`, `facts`, `word_relationships`, `search_indices`, `trie_indices`, `semantic_indices`, `word_lists`, `corpora`, `language_corpora`, `literature_corpora`, plus versioned data and cache collections.

Auto-detects localhost connections to skip TLS (development). Production uses DocumentDB with TLS certificate.

## Anki Export (`anki/`)

`AnkiDeckGenerator` produces `.apkg` files from synthesized entries using genanki. Card types: fill-in-the-blank, multiple choice ("best describes"), definition-to-word, word-to-definition. AI generates card content (questions, distractors) via `OpenAIConnector`. Card styling uses Apple HIG-influenced CSS—system font stack, subdued palette (`#1d1d1f`, `#86868b`, `#007aff`), 12px border radius.

## Configuration

API keys and database URLs live in `auth/config.toml` (not in git). The `Config` singleton (`utils/config.py`) loads it once. Environment-specific database URLs (`development_url`, `production_url`) selected by `ENVIRONMENT` env var.

AI config is code-level: model selection in `ai/model_selection.py`, temperature routing in `get_temperature_for_model()`. No config file for model parameters—it's all in the `TASK_COMPLEXITY_MAP` and `COMPLEXITY_TO_MODEL` dicts.

## Security

Input validation via Pydantic at every boundary. Rate limiting per provider with adaptive backoff. Clerk OAuth middleware (optional). XSS prevention in `utils/sanitization.py`. API keys stored in `auth/config.toml`, never in the database.

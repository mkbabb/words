# Floridify Backend

Async-first Python 3.12+ FastAPI. MongoDB + Beanie ODM. OpenAI/Anthropic AI synthesis. FAISS semantic search.

## Structure

```
backend/src/floridify/
├── api/                    # REST API layer
│   ├── main.py             # FastAPI app factory, lifespan context
│   ├── routers/            # Route handlers
│   │   ├── lookup.py       # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   │   ├── search.py       # GET /search (multi-method cascade)
│   │   ├── ai/             # AI generation endpoints (main.py, assess.py, base.py, generate.py, suggestions.py)
│   │   ├── words/          # Definition CRUD, versions (main.py, definitions.py, examples.py, versions.py)
│   │   ├── wordlist/       # Wordlist CRUD, reviews, SM-2 (main.py, words.py, reviews.py, search.py, utils.py)
│   │   ├── wotd/           # Word-of-the-Day (main.py, ml.py)
│   │   ├── media/          # Image + audio upload/retrieval (images.py, audio.py)
│   │   ├── corpus.py       # Corpus hierarchy management
│   │   ├── users.py        # User management
│   │   └── cache.py, health.py, config.py, database.py, providers.py
│   ├── repositories/       # Data access layers
│   │   ├── word_repository.py, definition_repository.py
│   │   ├── wordlist_repository.py (SM-2 reviews)
│   │   ├── provider_repository.py, synthesis_repository.py
│   │   └── image_, audio_, corpus_, example_, fact_repository.py
│   ├── core/               # API utilities
│   │   ├── base.py         # PaginationParams, SortParams, BaseRepository
│   │   ├── exceptions.py   # Exception types → HTTP mapping
│   │   ├── query.py        # AggregationBuilder, QueryOptimizer
│   │   ├── cache.py        # API-level caching
│   │   └── responses.py, dependencies.py, monitoring.py, protocols.py
│   ├── middleware/          # CORS, auth (Clerk), rate limiting, logging
│   │   ├── auth.py         # Clerk OAuth (optional)
│   │   ├── auth_state.py   # Auth state management
│   │   ├── rate_limiting.py # Adaptive with exponential backoff
│   │   ├── field_selection.py # Dynamic field selection
│   │   └── middleware.py, exception_handlers.py
│   └── services/           # Cleanup, loaders
│
├── core/                   # Business logic pipelines
│   ├── lookup_pipeline.py  # 5-stage: search → cache → providers → AI → store
│   ├── search_pipeline.py  # SearchEngineManager with hot-reload + cascade
│   ├── state_tracker.py    # Real-time progress, multi-subscriber
│   ├── streaming.py        # SSE: chunked responses, heartbeat, timeout
│   └── wotd_pipeline.py    # Word-of-the-Day ML orchestration
│
├── models/                 # Pydantic/Beanie models
│   ├── base.py             # Language enum, DictionaryProvider enum, BaseMetadata
│   ├── dictionary.py       # Word, Definition, DictionaryEntry, Pronunciation, Example, Fact
│   ├── relationships.py    # MeaningCluster, Collocation, GrammarPattern, UsageNote, WordForm
│   ├── parameters.py       # CLI/API shared params (isomorphic with frontend)
│   ├── responses.py        # LookupResponse, SearchResponse, CorpusResponse
│   ├── literature.py       # AuthorInfo, Genre/Period enums
│   ├── registry.py         # ResourceType → Model mapping
│   └── user.py             # User(Document) for OAuth
│
├── search/                 # Multi-method search → docs/search.md
│   ├── core.py             # Search orchestrator, cascade logic
│   ├── trie.py             # marisa-trie + Bloom filter
│   ├── fuzzy.py            # RapidFuzz dual-scorer (WRatio + token_set_ratio)
│   ├── bloom.py            # Bitarray-based membership testing
│   ├── result.py           # SearchResult model
│   ├── search_index.py     # SearchIndex model
│   ├── trie_index.py       # TrieIndex document model
│   ├── language.py         # Multi-corpus orchestration
│   ├── constants.py        # SearchMethod, SearchMode enums
│   ├── utils.py            # Length correction, frequency heuristics
│   └── semantic/           # FAISS vector search
│       ├── core.py         # SemanticSearch: 5-tier index selection, embeddings
│       ├── models.py       # SemanticIndex(Document)
│       ├── constants.py    # Model catalog (Qwen3-0.6B), FAISS thresholds
│       ├── embedding.py    # Embedding computation
│       ├── index_builder.py # FAISS index construction
│       └── persistence.py  # Index save/load
│
├── ai/                     # AI integration → docs/synthesis.md
│   ├── connector/          # AIConnector: async interface to OpenAI/Anthropic
│   │   ├── base.py         # Core client, structured outputs
│   │   ├── config.py       # Provider enum, effort settings
│   │   ├── synthesis.py    # Synthesis-specific methods
│   │   ├── generation.py   # Content generation methods
│   │   ├── assessment.py   # Classification/assessment methods
│   │   └── suggestions.py  # Word suggestion methods
│   ├── synthesis/          # Synthesis pipeline functions
│   │   ├── orchestration.py # Parallel enhancement, clustering
│   │   ├── word_level.py   # Pronunciation, etymology, word forms, facts
│   │   └── definition_level.py # 11 per-definition enhancement functions
│   ├── synthesizer.py      # DefinitionSynthesizer: dedup→cluster→enhance
│   ├── model_selection.py  # 3-tier routing: GPT-5.4/Mini/Nano
│   ├── models.py           # AI response/request Pydantic models
│   ├── batch_processor.py  # OpenAI Batch API
│   ├── prompt_manager.py   # Jinja2 template loading
│   ├── constants.py        # SynthesisComponent enum (17 values)
│   ├── adaptive_counts.py  # Dynamic enhancement counts
│   ├── tournament.py       # Tournament-style word ranking
│   └── prompts/            # Markdown prompt templates
│       ├── assess/         # cefr, collocations, domain, frequency, grammar, regional, register
│       ├── generate/       # examples, facts, word_forms
│       ├── synthesize/     # antonyms, deduplicate, definitions, etymology, pronunciation, synonyms
│       ├── misc/           # anki, lookup, meaning_extraction, query_validation, suggestions, usage_notes
│       ├── shared/         # Shared prompt components
│       └── wotd/           # literature_analysis, synthetic_corpus, word_of_the_day
│
├── caching/                # Multi-tier storage → docs/versioning.md
│   ├── core.py             # GlobalCacheManager: L1 memory + L2 disk
│   ├── manager.py          # VersionedDataManager: L3, SHA-256, version chains
│   ├── config.py           # 13 namespace configs (TTL, compression, limits)
│   ├── decorators.py       # @cached_api_call, @cached_computation, etc.
│   ├── models.py           # CacheNamespace, BaseVersionedData, VersionInfo
│   ├── filesystem.py       # DiskCache backend (10GB limit)
│   ├── keys.py             # Deterministic key generation
│   ├── serialize.py        # Content hashing, JSON serialization
│   ├── delta.py            # DeepDiff-based delta versioning
│   ├── compression.py      # ZSTD, LZ4, GZIP
│   ├── validation.py       # Version validation, corruption detection
│   ├── version_chains.py   # Semantic versioning, chain management
│   ├── gridfs.py           # GridFS large payload storage
│   └── utils.py            # JSON encoder, namespace normalization
│
├── corpus/                 # Vocabulary management
│   ├── core.py             # Corpus: UUID hierarchy, vocabulary indices
│   ├── manager.py          # TreeCorpusManager: per-resource locking
│   ├── crud.py             # CRUD operations
│   ├── tree.py             # Tree traversal, hierarchy operations
│   ├── aggregation.py      # MongoDB aggregation queries
│   ├── semantic_policy.py  # Semantic search policies
│   ├── parser.py           # Parsers (text, freq, JSON, CSV, phrasal verbs)
│   ├── models.py           # CorpusType, CorpusSource enums
│   ├── utils.py            # Corpus utilities
│   ├── language/            # LanguageCorpus source management
│   └── literature/          # LiteratureCorpus work management
│
├── providers/              # External data sources
│   ├── core.py             # BaseConnector, ConnectorConfig
│   ├── factory.py          # create_connector() factory
│   ├── batch.py            # Batch provider operations
│   ├── rate_limiting.py    # AdaptiveRateLimiter with exponential backoff
│   ├── http_client.py      # RespectfulHttpClient
│   ├── dictionary/         # 6 dictionary providers + 1 wholesale
│   │   ├── core.py         # DictionaryConnector base
│   │   ├── models.py       # Provider-specific models
│   │   ├── api/            # Oxford, Merriam-Webster, Free Dictionary
│   │   ├── scraper/        # Wiktionary (+ wikitext_cleaner, wiktionary_parser), WordHippo
│   │   ├── local/          # Apple Dictionary (macOS, pyobjc)
│   │   └── wholesale/      # Wiktionary bulk XML processing
│   ├── language/           # URL + file-based language sources
│   │   ├── core.py, models.py, parsers.py, sources.py
│   │   └── scraper/        # Language-specific scrapers
│   └── literature/         # Gutenberg, Internet Archive + 15 author mappings
│       ├── core.py, models.py, parsers.py
│       ├── api/            # gutenberg.py, internet_archive.py
│       ├── mappings/       # shakespeare, homer, dante, joyce, etc.
│       └── scraper/        # Literature-specific scrapers
│
├── cli/                    # Command-line interface (Click + Rich)
│   ├── cli.py              # Click app, main entry point
│   ├── completion.py       # ZSH autocomplete
│   ├── commands/           # lookup, search, wordlist, config, database, scrape, anki, wotd, wotd_ml
│   └── utils/formatting.py # Rich terminal UI
│
├── text/                   # Text processing
│   ├── normalize.py        # normalize_comprehensive(), lemmatize, LRU cache (50K)
│   ├── constants.py        # Regex patterns, Unicode mappings, suffix rules
│   └── phrase.py           # Phrase detection
│
├── storage/                # MongoDB layer
│   ├── mongodb.py          # Beanie ODM init, document model registration, connection pool
│   └── dictionary.py       # Versioned save operations for dictionary entries
│
├── wordlist/               # Vocabulary lists
│   ├── models.py           # Wordlist(Document), WordlistEntry(Document)
│   ├── review.py           # SM-2 spaced repetition (Bronze → Silver → Gold)
│   ├── parser.py           # Text, JSON, CSV, TSV file parsers
│   ├── stats.py            # Wordlist statistics
│   ├── constants.py, utils.py
│   └── word_of_the_day/    # WordOfTheDay(Document)
│
├── wotd/                   # Word-of-the-Day ML
│   ├── core.py             # WOTD orchestration
│   ├── generator.py        # WordOfTheDayGenerator
│   ├── inference.py        # ML scoring
│   ├── encoders.py         # Semantic + metadata encoding
│   ├── embeddings.py       # SentenceTransformer management
│   ├── sagemaker.py        # SageMaker integration
│   ├── storage.py          # WOTD storage layer
│   ├── storage_minimal.py  # Minimal storage variant
│   ├── constants.py
│   ├── training/           # ML training pipeline
│   │   ├── pipeline.py     # Training orchestration
│   │   ├── dsl_trainer.py  # DSL-based trainer
│   │   └── embedder.py     # Embedding generation for training
│   └── deployment/         # Deployment configurations
│       ├── inference.py    # Inference server
│       ├── local.py        # Local deployment
│       └── train.py        # Training job setup
│
├── anki/                   # Flashcard export
│   ├── generator.py        # AnkiDeckGenerator: .apkg creation
│   ├── templates.py        # Card HTML/CSS templates
│   ├── ankiconnect.py      # AnkiConnect API client
│   └── constants.py
│
├── audio/                  # Multi-language TTS
│   ├── synthesizer.py      # AudioSynthesizer facade — language-based routing
│   ├── kitten_synthesizer.py  # KittenTTS (English, 15M params)
│   ├── kokoro_synthesizer.py  # Kokoro-ONNX (non-English, 82M params, 8 languages)
│   ├── types.py            # Audio type definitions
│   └── utils.py            # audio_to_mp3() WAV→MP3 conversion
│
└── utils/                  # Shared utilities
    ├── logging.py          # Loguru + Rich structured logging
    ├── config.py           # Config singleton (auth/config.toml)
    ├── paths.py            # Platform-specific path management
    ├── sanitization.py     # Input validation, XSS prevention
    ├── threading_config.py # OMP/threading safety for macOS
    ├── language_precedence.py # Language priority ordering
    ├── introspection.py    # Runtime introspection
    ├── json_output.py      # JSON formatting
    └── timeouts.py         # Timeout utilities
```

## Key Pipelines

**Lookup** ([`core/lookup_pipeline.py`](src/floridify/core/lookup_pipeline.py)):
```
Query → Search → Cache check
  → Provider fetch (asyncio.gather, 30s timeout per provider)
  → AI synthesis (dedup→cluster→enhance)
  → MongoDB + cache → Response
```

**Search** ([`search/core.py`](src/floridify/search/core.py)):
```
Query → Exact (<1ms, marisa-trie) → Prefix → Fuzzy (RapidFuzz)
  → Semantic (FAISS HNSW) → Deduplicate → Top N
```
SearchEngineManager: hot-reload via 30s vocabulary_hash polling, atomic swap.

**AI Synthesis** ([`ai/synthesizer.py`](src/floridify/ai/synthesizer.py)):
```
Provider data → Dedup → Cluster
  → Parallel enhance (4 word-level + 11 definition-level)
  → Version + save
```

## Patterns

- **Async-first**: All I/O async. Motor, httpx, asyncio.gather
- **Repository pattern**: Data access layers between API and MongoDB
- **Dependency injection**: FastAPI `Depends()` for loose coupling
- **Factory**: `create_connector()`, `Corpus.create()`, `get_global_cache()`
- **Singleton**: `get_openai_connector()`, `lookup_state_tracker()`
- **Content-addressable**: SHA-256 hashing for L3 cache dedup
- **Per-resource locking**: Fine-grained concurrency in TreeCorpusManager
- **Cascade with early termination**: Search stops when sufficient results found
- **Graceful degradation**: AI synthesis—definitions required, others optional

## Testing

```
backend/tests/
├── conftest.py              # Root: MongoDB infra, factories
├── api/                     # Endpoint integration tests
├── search/                  # All search methods
├── providers/               # All provider types
├── corpus/                  # Tree ops, cascade deletion
├── caching/                 # L1/L2/L3 tiers
├── models/                  # Pydantic validation
├── end_to_end/              # Full pipeline tests
├── utils/                   # Introspection
└── fixtures/                # Test fixtures (epub, pdf)
```

**Strategy**: Real MongoDB per test (unique DB), real FAISS indices, real file ops. Only external APIs mocked (OpenAI, dictionary providers). Session-scoped fixtures for expensive operations (semantic indices).

## Development

```bash
cd backend
uv venv && source .venv/bin/activate
uv sync
uv run scripts/run_api.py                      # Port 8000

# Quality
ruff check --fix && ruff format
mypy src/ --strict
pytest tests/ -v
pytest tests/ --cov=src/floridify --cov-report=html
```

# Floridify Backend

Async-first Python 3.12+ FastAPI. MongoDB + Beanie ODM. OpenAI GPT-5 synthesis. FAISS semantic search. ~60K LOC.

## Structure

```
backend/src/floridify/
├── api/                    # REST API layer
│   ├── main.py             # FastAPI app factory, lifespan context
│   ├── routers/            # 23 router files, 121 endpoints (106 active, 15 wotd commented out)
│   │   ├── lookup.py       # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   │   ├── search.py       # GET /search (multi-method cascade)
│   │   ├── ai/             # 21 AI generation endpoints (main.py, suggestions.py)
│   │   ├── words/          # Definition CRUD, versions (main.py, definitions.py, examples.py, versions.py)
│   │   ├── wordlist/       # Wordlist CRUD, reviews, SM-2 (main.py, words.py, reviews.py, search.py, utils.py)
│   │   ├── wotd/           # Word-of-the-Day (main.py, ml.py)—routers commented out in main.py
│   │   ├── corpus.py       # Corpus hierarchy management
│   │   ├── media/          # Image + audio upload/retrieval (images.py, audio.py)
│   │   └── cache.py, health.py, config.py, database.py, providers.py
│   ├── repositories/       # 10 data access layers
│   │   ├── word_repository.py, definition_repository.py
│   │   ├── wordlist_repository.py (596 LOC, SM-2 reviews)
│   │   ├── provider_repository.py, synthesis_repository.py
│   │   └── image_, audio_, corpus_, example_, fact_repository.py
│   ├── core/               # API utilities (1,789 LOC)
│   │   ├── base.py         # PaginationParams, SortParams, BaseRepository (427 LOC)
│   │   ├── exceptions.py   # 13 exception types → HTTP mapping (384 LOC)
│   │   ├── query.py        # AggregationBuilder, QueryOptimizer
│   │   ├── cache.py        # API-level caching
│   │   └── responses.py, dependencies.py, monitoring.py, protocols.py
│   └── middleware/          # CORS, auth (Clerk), rate limiting, logging
│       ├── auth.py          # Clerk OAuth (optional)
│       ├── rate_limiting.py # Adaptive with exponential backoff
│       ├── field_selection.py # Dynamic field selection
│       └── middleware.py, exception_handlers.py
│
├── core/                   # Business logic pipelines
│   ├── lookup_pipeline.py  # 5-stage: search → cache → providers → AI → store (519 LOC)
│   ├── search_pipeline.py  # SearchEngineManager with hot-reload + cascade (560 LOC)
│   ├── state_tracker.py    # Real-time progress, 21 stages, multi-subscriber (480 LOC)
│   ├── streaming.py        # SSE: chunked responses, heartbeat, timeout (284 LOC)
│   └── wotd_pipeline.py    # Word-of-the-Day ML orchestration (338 LOC)
│
├── models/                 # Pydantic/Beanie models (1,647 LOC)
│   ├── base.py             # Language enum, DictionaryProvider enum, BaseMetadata
│   ├── dictionary.py       # Word, Definition, DictionaryEntry (MongoDB docs)
│   ├── relationships.py    # MeaningCluster, Collocation, GrammarPattern
│   ├── parameters.py       # CLI/API shared params (isomorphic with frontend)
│   ├── responses.py        # LookupResponse, SearchResponse, CorpusResponse
│   ├── literature.py       # AuthorInfo, Genre/Period enums
│   ├── registry.py         # ResourceType → Model mapping
│   └── user.py             # User(Document) for OAuth
│
├── search/                 # Multi-method search
│   ├── core.py             # Search orchestrator (897 LOC), cascade logic
│   ├── trie.py             # marisa-trie + Bloom filter (<1ms)
│   ├── fuzzy.py            # RapidFuzz dual-scorer (WRatio + token_set_ratio)
│   ├── bloom.py            # Bitarray-based membership testing
│   ├── language.py         # Multi-corpus orchestration
│   ├── models.py           # SearchResult, SearchIndex, SearchMode
│   ├── constants.py        # SearchMethod/SearchMode enums
│   ├── utils.py            # Length correction, default frequency heuristics (206 LOC)
│   └── semantic/           # FAISS vector search (2,045 LOC)
│       ├── core.py         # SemanticSearch: 5-tier index selection, embeddings (1,470 LOC)
│       ├── models.py       # SemanticIndex(Document) (480 LOC)
│       └── constants.py    # Model catalog (Qwen3-0.6B), FAISS thresholds, HNSW config (95 LOC)
│
├── ai/                     # OpenAI integration
│   ├── connector.py        # OpenAIConnector: 30 async methods (1,209 LOC)
│   ├── synthesizer.py      # DefinitionSynthesizer: dedup→cluster→enhance (542 LOC)
│   ├── synthesis_functions.py  # 25+ synthesis functions (1,152 LOC)
│   ├── model_selection.py  # 3-tier routing: GPT-5/Mini/Nano (155 LOC)
│   ├── batch_processor.py  # OpenAI Batch API (362 LOC)
│   ├── prompt_manager.py   # Jinja2 templates over markdown prompts (201 LOC)
│   ├── prompts/            # 27 prompt templates (.md files, 5 subdirs)
│   ├── models.py           # 54 AI response/request model classes
│   └── constants.py        # 17 SynthesisComponent enum values
│
├── caching/                # Multi-tier storage
│   ├── core.py             # GlobalCacheManager: L1 memory + L2 disk
│   ├── manager.py          # VersionedDataManager: L3 versioned (SHA-256)
│   ├── config.py           # Namespace configs (TTL, compression, limits)
│   ├── decorators.py       # @cached_api_call, @cached_computation, etc.
│   ├── models.py           # CacheNamespace, BaseVersionedData, VersionInfo
│   ├── filesystem.py       # DiskCache backend (10GB limit)
│   ├── keys.py             # Deterministic key generation
│   ├── serialize.py        # Content hashing, JSON serialization
│   ├── compression.py      # ZSTD, LZ4, GZIP
│   ├── validation.py       # Version validation, corruption detection
│   ├── version_chains.py   # Semantic versioning, chain management
│   ├── delta.py            # Delta-based versioning (132 LOC)
│   └── utils.py            # Cache utilities (117 LOC)
│
├── corpus/                 # Vocabulary management
│   ├── core.py             # Corpus: UUID hierarchy, vocabulary indices
│   ├── manager.py          # TreeCorpusManager: per-resource locking (1,364 LOC)
│   ├── parser.py           # 9 parsers (text, freq, JSON, CSV, phrasal verbs) (268 LOC)
│   ├── models.py           # CorpusType/CorpusSource enums
│   ├── utils.py            # Corpus utilities (53 LOC)
│   ├── language/core.py    # LanguageCorpus source management
│   └── literature/core.py  # LiteratureCorpus work management
│
├── providers/              # External data sources
│   ├── core.py             # BaseConnector, ConnectorConfig
│   ├── factory.py          # create_connector() factory
│   ├── utils.py            # AdaptiveRateLimiter, RespectfulHttpClient
│   ├── dictionary/         # 6 providers + 1 wholesale variant
│   │   ├── api/            # Oxford, Merriam-Webster, Free Dictionary
│   │   ├── scraper/        # Wiktionary (1,121 LOC), WordHippo (577 LOC)
│   │   ├── local/          # Apple Dictionary (macOS, pyobjc)
│   │   └── wholesale/      # Wiktionary bulk XML processing (561 LOC)
│   ├── language/           # URL + file-based language sources
│   └── literature/         # Gutenberg, Internet Archive + 15 author mappings
│
├── cli/                    # Command-line interface
│   ├── cli.py              # Typer app, main entry point
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
│   └── mongodb.py          # Beanie ODM init, 27 document models, 50 conn pool (375 LOC)
│
├── wordlist/               # Vocabulary lists
│   ├── models.py           # Wordlist(Document), WordlistEntry(Document)
│   ├── review.py           # SM-2 spaced repetition (Bronze → Silver → Gold)
│   ├── parser.py           # Text, JSON, CSV, TSV file parsers
│   ├── stats.py            # Wordlist statistics (85 LOC)
│   ├── constants.py        # Wordlist constants (30 LOC)
│   ├── utils.py            # Wordlist utilities (31 LOC)
│   └── word_of_the_day/    # WordOfTheDay(Document)
│
├── wotd/                   # Word-of-the-Day ML
│   ├── trainer.py          # ML training pipeline (1,440 LOC)
│   ├── encoders.py         # Semantic + metadata encoding
│   ├── embeddings.py       # SentenceTransformer management
│   ├── generator.py        # WordOfTheDayGenerator
│   ├── inference.py        # ML scoring
│   ├── core.py             # WOTD orchestration
│   ├── sagemaker.py        # SageMaker integration
│   ├── storage.py          # WOTD storage layer
│   ├── storage_minimal.py  # Minimal storage variant
│   ├── constants.py        # WOTD constants
│   └── deployment/         # Local + SageMaker deployment (Dockerfiles, inference, nginx)
│
├── anki/                   # Flashcard export
│   ├── generator.py        # AnkiDeckGenerator: .apkg creation
│   ├── templates.py        # Card HTML/CSS templates
│   ├── ankiconnect.py      # AnkiConnect API client
│   └── constants.py        # Anki constants
│
├── audio/                  # Speech synthesis
│   └── synthesizer.py      # Google Cloud TTS
│
└── utils/                  # Shared utilities
    ├── logging.py          # Loguru + Rich structured logging
    ├── config.py           # Config singleton (auth/config.toml)
    ├── paths.py            # Platform-specific path management
    ├── sanitization.py     # Input validation, XSS prevention
    └── json_output.py, introspection.py, timeouts.py
```

## Key Pipelines

**Lookup** (`core/lookup_pipeline.py`, 519 LOC):
```
Query → Search (10-100ms) → Cache check (0.2-5ms)
  → Provider fetch (2-5s, asyncio.gather)
  → AI synthesis (1-3s, dedup→cluster→enhance)
  → MongoDB + cache → Response
```

**Search** (`search/core.py`, 897 LOC):
```
Query → Exact (<1ms, marisa-trie) → Fuzzy (10-50ms, RapidFuzz)
  → Semantic (50-200ms, FAISS HNSW) → Deduplicate → Top N
```
SearchEngineManager: hot-reload via 30s vocabulary_hash polling, atomic swap.

**AI Synthesis** (`ai/synthesizer.py`, 542 LOC):
```
Provider data → Dedup → Cluster (3-4 groups)
  → Parallel enhance → Version + save
```

## Patterns

- **Async-first**: All I/O async. Motor, httpx, asyncio.gather
- **Repository pattern**: 10 data access layers between API and MongoDB
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
├── api/                     # 8 files, 133 tests — endpoint integration
├── search/                  # 15 files, 201 tests — all search methods
├── providers/               # 13 files, 170 tests — all provider types
├── corpus/                  # 9 files, 84 tests — tree ops, cascade deletion
├── caching/                 # 8 files, 96 tests — L1/L2/L3 tiers
├── models/                  # 1 file, 19 tests — Pydantic validation
├── end_to_end/              # 1 file, 3 tests — full pipeline
├── utils/                   # 1 file, 14 tests — introspection
├── storage/                 # (empty)
└── fixtures/                # Test fixtures (epub, pdf)
```

**Strategy**: Real MongoDB per test (unique DB), real FAISS indices, real file ops. Only external APIs mocked (OpenAI, dictionary providers). 111 fixtures (90 async). Session-scoped for expensive operations (semantic indices).

**Stats**: 61 test files, ~21K lines, 727 tests.

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| L1 cache hit | 0.2ms | OrderedDict O(1) |
| L2 cache hit | 5ms | DiskCache + decompress |
| Exact search | <1ms | marisa-trie O(m) |
| Fuzzy search | 10-50ms | RapidFuzz dual-scorer |
| Semantic search | 50-200ms | FAISS HNSW |
| Lookup (cached) | <500ms | L1/L2 hit |
| Lookup (uncached) | 2-5s | Provider + AI |
| AI synthesis | 1-3s | Parallel tasks |
| CLI startup | 0.07s | Lazy imports |

## Development

```bash
cd backend
uv venv && source .venv/bin/activate
uv sync
cp auth/config.toml.example auth/config.toml  # Add OpenAI key
uv run scripts/run_api.py                      # Port 8000

# Quality
ruff check --fix && ruff format
mypy src/ --strict
pytest tests/ -v
pytest tests/ --cov=src/floridify --cov-report=html
```

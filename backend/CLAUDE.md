# Floridify Backend

Async-first Python 3.12+ FastAPI. MongoDB + Beanie ODM. OpenAI GPT-5 synthesis. FAISS semantic search. ~50K LOC.

## Structure

```
backend/src/floridify/
├── api/                    # REST API layer → api/CLAUDE.md
│   ├── main.py             # FastAPI app factory, lifespan context
│   ├── routers/            # 17 routers, 111+ endpoints
│   │   ├── lookup.py       # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   │   ├── search.py       # GET /search (multi-method cascade)
│   │   ├── ai/             # 40+ AI generation endpoints
│   │   ├── words/          # Definition CRUD, versions
│   │   ├── wordlist/       # Wordlist CRUD, reviews, SM-2
│   │   ├── corpus.py       # Corpus hierarchy management
│   │   ├── media/          # Image + audio upload/retrieval
│   │   └── cache.py, health.py, config.py, database.py, providers.py
│   ├── repositories/       # 11 data access layers
│   │   ├── word_repository.py, definition_repository.py
│   │   ├── wordlist_repository.py (596 LOC, SM-2 reviews)
│   │   ├── provider_repository.py, synthesis_repository.py
│   │   └── image_, audio_, corpus_, example_, fact_repository.py
│   ├── core/               # API utilities (1,572 LOC)
│   │   ├── base.py         # PaginationParams, SortParams, BaseRepository
│   │   ├── exceptions.py   # 10+ exception types → HTTP mapping
│   │   ├── query.py        # AggregationBuilder, QueryOptimizer
│   │   └── responses.py, dependencies.py, monitoring.py, protocols.py
│   └── middleware/          # CORS, auth (Clerk), rate limiting, logging
│       ├── auth.py          # Clerk OAuth (optional)
│       ├── rate_limiting.py # Adaptive with exponential backoff
│       └── middleware.py, exception_handlers.py
│
├── core/                   # Business logic pipelines → core/CLAUDE.md
│   ├── lookup_pipeline.py  # 5-stage: search → cache → providers → AI → store
│   ├── search_pipeline.py  # SearchEngineManager with hot-reload + cascade
│   ├── state_tracker.py    # Real-time progress, 9 stages, multi-subscriber
│   ├── streaming.py        # SSE: chunked responses, heartbeat, timeout
│   └── wotd_pipeline.py    # Word-of-the-Day ML orchestration
│
├── models/                 # 179+ Pydantic/Beanie models → models/CLAUDE.md
│   ├── base.py             # Language enum, DictionaryProvider enum, BaseMetadata
│   ├── dictionary.py       # Word, Definition, DictionaryEntry (MongoDB docs)
│   ├── relationships.py    # MeaningCluster, Collocation, GrammarPattern
│   ├── parameters.py       # CLI/API shared params (isomorphic with frontend)
│   ├── responses.py        # LookupResponse, SearchResponse, CorpusResponse
│   ├── literature.py       # AuthorInfo, Genre/Period enums
│   ├── registry.py         # ResourceType → Model mapping
│   └── user.py             # User(Document) for OAuth
│
├── search/                 # Multi-method search → search/CLAUDE.md
│   ├── core.py             # Search orchestrator (897 LOC), cascade logic
│   ├── trie.py             # marisa-trie + Bloom filter (<1ms)
│   ├── fuzzy.py            # RapidFuzz dual-scorer (WRatio + token_set_ratio)
│   ├── bloom.py            # Bitarray-based membership testing
│   ├── language.py         # Multi-corpus orchestration
│   ├── models.py           # SearchResult, SearchIndex, SearchMode
│   ├── constants.py        # SearchMethod/SearchMode enums
│   └── semantic/           # FAISS vector search (2,213 LOC)
│       ├── core.py         # SemanticSearch: 7 index types, embeddings
│       ├── models.py       # SemanticIndex(Document)
│       ├── constants.py    # Model catalog (Qwen3-0.6B, BGE-M3)
│       └── config.py       # Index selection by corpus size
│
├── ai/                     # OpenAI integration → ai/CLAUDE.md
│   ├── connector.py        # OpenAIConnector: 32 async methods (1,209 LOC)
│   ├── synthesizer.py      # DefinitionSynthesizer: dedup→cluster→enhance
│   ├── synthesis_functions.py  # 25+ synthesis functions (1,152 LOC)
│   ├── model_selection.py  # 3-tier routing: Nano/Mini/Full (87% savings)
│   ├── batch_processor.py  # OpenAI Batch API (50% discount)
│   ├── prompt_manager.py   # Jinja2 templates, 27 prompts
│   ├── models.py           # 40+ AI response models
│   └── constants.py        # 27 SynthesisComponent enum values
│
├── caching/                # Multi-tier storage → caching/CLAUDE.md
│   ├── core.py             # GlobalCacheManager: L1 memory + L2 disk
│   ├── manager.py          # VersionedDataManager: L3 versioned (SHA-256)
│   ├── config.py           # 13 namespace configs (TTL, compression, limits)
│   ├── decorators.py       # @cached_api_call, @cached_computation, etc.
│   ├── models.py           # CacheNamespace, BaseVersionedData, VersionInfo
│   ├── filesystem.py       # DiskCache backend (10GB limit)
│   ├── keys.py             # Deterministic key generation
│   ├── serialize.py        # Content hashing, JSON serialization
│   ├── compression.py      # ZSTD (2-3x), LZ4 (1.5-2x), GZIP (3-4x)
│   ├── validation.py       # Version validation, corruption detection
│   └── version_chains.py   # Semantic versioning, chain management
│
├── corpus/                 # Vocabulary management → corpus/CLAUDE.md
│   ├── core.py             # Corpus: UUID hierarchy, vocabulary indices
│   ├── manager.py          # TreeCorpusManager: per-resource locking (1,364 LOC)
│   ├── parser.py           # 9 parsers (text, freq, JSON, CSV, phrasal verbs)
│   ├── models.py           # CorpusType/CorpusSource enums
│   ├── language/core.py    # LanguageCorpus source management
│   └── literature/core.py  # LiteratureCorpus work management
│
├── providers/              # External data sources → providers/CLAUDE.md
│   ├── core.py             # BaseConnector, ConnectorConfig
│   ├── factory.py          # create_connector() factory
│   ├── utils.py            # AdaptiveRateLimiter, RespectfulHttpClient
│   ├── dictionary/         # 7 providers
│   │   ├── api/            # Oxford, Merriam-Webster, Free Dictionary
│   │   ├── scraper/        # Wiktionary (1,121 LOC), WordHippo
│   │   ├── local/          # Apple Dictionary (macOS, pyobjc)
│   │   └── wholesale/      # Wiktionary bulk XML processing
│   ├── language/           # URL + file-based language sources
│   └── literature/         # Gutenberg, Internet Archive + 15 author mappings
│
├── cli/                    # Command-line interface → cli/CLAUDE.md
│   ├── cli.py              # Typer app, main entry point
│   ├── completion.py       # ZSH autocomplete
│   ├── commands/           # lookup, search, wordlist, corpus, anki, wotd
│   └── utils/formatting.py # Rich terminal UI
│
├── text/                   # Text processing → text/CLAUDE.md
│   ├── normalize.py        # normalize_comprehensive(), lemmatize, LRU cache (50K)
│   ├── constants.py        # Regex patterns, Unicode mappings, suffix rules
│   └── phrase.py           # Phrase detection
│
├── storage/                # MongoDB layer → storage/CLAUDE.md
│   └── mongodb.py          # Beanie ODM init, 28 document models, 50 conn pool
│
├── wordlist/               # Vocabulary lists → wordlist/CLAUDE.md
│   ├── models.py           # Wordlist(Document), WordlistEntry(Document)
│   ├── review.py           # SM-2 spaced repetition (Bronze → Silver → Gold)
│   ├── parser.py           # Text, JSON, CSV, TSV file parsers
│   └── word_of_the_day/    # WordOfTheDay(Document)
│
├── wotd/                   # Word-of-the-Day ML → wotd/CLAUDE.md
│   ├── trainer.py          # ML training pipeline (1,440 LOC)
│   ├── encoders.py         # Semantic + metadata encoding
│   ├── embeddings.py       # SentenceTransformer management
│   ├── generator.py        # WordOfTheDayGenerator
│   ├── inference.py        # ML scoring
│   └── deployment/         # Local + SageMaker deployment
│
├── anki/                   # Flashcard export → anki/CLAUDE.md
│   ├── generator.py        # AnkiDeckGenerator: .apkg creation
│   ├── templates.py        # Card HTML/CSS templates
│   └── ankiconnect.py      # AnkiConnect API client
│
├── audio/                  # Speech synthesis → audio/CLAUDE.md
│   └── synthesizer.py      # Google Cloud TTS
│
└── utils/                  # Shared utilities → utils/CLAUDE.md
    ├── logging.py          # Loguru + Rich structured logging
    ├── config.py           # Config singleton (auth/config.toml)
    ├── paths.py            # Platform-specific path management
    ├── sanitization.py     # Input validation, XSS prevention
    └── json_output.py, introspection.py, timeouts.py
```

## Key Pipelines

**Lookup** (`core/lookup_pipeline.py`, 504 LOC):
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

**AI Synthesis** (`ai/synthesizer.py`, 432 LOC):
```
Provider data (47 defs) → Dedup (23 defs, 50%)
  → Cluster (3-4 groups) → Parallel enhance (12 tasks)
  → Version + save
```

## Patterns

- **Async-first**: All I/O async. Motor, httpx, asyncio.gather
- **Repository pattern**: 11 data access layers between API and MongoDB
- **Dependency injection**: FastAPI `Depends()` for loose coupling
- **Factory**: `create_connector()`, `Corpus.create()`, `get_global_cache()`
- **Singleton**: `get_openai_connector()`, `lookup_state_tracker()`
- **Content-addressable**: SHA-256 hashing for L3 cache dedup
- **Per-resource locking**: Fine-grained concurrency (3-5x throughput)
- **Cascade with early termination**: Search stops when sufficient results found
- **Graceful degradation**: AI synthesis — definitions required, others optional

## Testing

```
backend/tests/
├── conftest.py              # Root: MongoDB infra, factories, 80+ async fixtures
├── api/                     # 7 files, 119 tests — endpoint integration
├── search/                  # 15 files, 154 tests — all search methods
├── providers/               # 13 files, 141 tests — all provider types
├── corpus/                  # 9 files, 97 tests — tree ops, cascade deletion
├── caching/                 # 8 files, 76 tests — L1/L2/L3 tiers
├── models/                  # 1 file, 19 tests — Pydantic validation
├── end_to_end/              # 1 file, 3 tests — full pipeline
└── utils/                   # 1 file, 14 tests — introspection
```

**Strategy**: Real MongoDB per test (unique DB), real FAISS indices, real file ops. Only external APIs mocked (OpenAI, dictionary providers). 80+ async fixtures. Session-scoped for expensive operations (semantic indices).

**Stats**: 58 files, 19K lines, 707 tests, 80%+ coverage.

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
| AI synthesis | 1-3s | Parallel 12 tasks |
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

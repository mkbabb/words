# Floridify Backend - Python FastAPI

Async-first Python 3.12+ FastAPI REST API, MongoDB + Beanie ODM, OpenAI GPT-5 synthesis, FAISS semantic search.

## Module Structure

```
backend/src/floridify/
├── api/                 # FastAPI REST (111+ endpoints, 17 routers) → CLAUDE.md
│   ├── routers/         # 17 routers: ai, words, wordlist, corpus, media, cache, etc.
│   ├── repositories/    # 11 data access layers
│   ├── services/        # Business logic
│   ├── middleware/      # CORS, caching, logging, error handling
│   └── app.py          # Application factory
│
├── core/                # Business logic pipelines → CLAUDE.md
│   ├── lookup_pipeline.py    # Word lookup: search→providers→AI→storage
│   ├── search_pipeline.py    # Multi-method search orchestration
│   ├── state_tracker.py      # Progress tracking, SSE streaming
│   ├── streaming.py          # Server-Sent Events
│   └── wotd_pipeline.py      # Word-of-the-Day ML pipeline
│
├── models/              # Type-safe data layer (179+ models) → CLAUDE.md
│   ├── base.py          # Base classes, Language enum, metadata
│   ├── dictionary.py    # Word, Definition, DictionaryEntry (MongoDB docs)
│   ├── parameters.py    # CLI/API shared parameters (isomorphic)
│   ├── responses.py     # API response models
│   └── relationships.py # WordForm, MeaningCluster, Collocation
│
├── search/              # Multi-method search engine → CLAUDE.md
│   ├── core.py          # Search orchestrator with cascade
│   ├── language.py      # LanguageSearch (multi-corpus)
│   ├── exact/           # TrieSearch (marisa-trie + Bloom filter, <1ms)
│   ├── fuzzy/           # FuzzySearch (RapidFuzz dual-scorer, 10-50ms)
│   └── semantic/        # SemanticSearch (FAISS + embeddings, 50-200ms)
│
├── ai/                  # OpenAI integration → CLAUDE.md
│   ├── connector.py             # OpenAI client (32 async methods)
│   ├── synthesizer.py           # DefinitionSynthesizer orchestrator
│   ├── synthesis_functions.py   # 25+ synthesis functions
│   ├── model_selection.py       # 3-tier routing (87% cost savings)
│   ├── batch_processor.py       # Batch API (50% discount)
│   ├── prompt_manager.py        # Jinja2 templates
│   └── prompts/                 # 27 Markdown templates
│
├── caching/             # Multi-tier storage → CLAUDE.md
│   ├── core.py          # GlobalCacheManager (L1 memory, L2 disk)
│   ├── manager.py       # VersionedDataManager (L3 versioned, SHA-256)
│   ├── config.py        # 13 namespace configurations
│   ├── decorators.py    # 5 caching decorators
│   └── models.py        # BaseVersionedData, CacheNamespace
│
├── corpus/              # Vocabulary management → CLAUDE.md
│   ├── core.py          # Corpus data model with indices
│   ├── manager.py       # TreeCorpusManager (UUID-based hierarchy)
│   ├── parser.py        # 9 corpus parsers
│   ├── language/        # LanguageCorpus with source management
│   └── literature/      # LiteratureCorpus with work management
│
├── providers/           # External data sources → CLAUDE.md
│   ├── core.py          # BaseConnector, RateLimitPresets
│   ├── factory.py       # create_connector() factory
│   ├── utils.py         # AdaptiveRateLimiter, RespectfulHttpClient
│   ├── dictionary/      # 7 providers: Wiktionary, Oxford, Free, etc.
│   ├── language/        # Language corpus providers
│   └── literature/      # Gutenberg, Internet Archive + 15 author mappings
│
├── cli/                 # Command-line interface → CLAUDE.md
│   ├── lookup.py        # floridify lookup <word>
│   ├── search.py        # floridify search <query>
│   ├── corpus.py        # floridify corpus list/rebuild
│   └── wordlist.py      # floridify wordlist create/review
│
├── text/                # Text processing → CLAUDE.md
│   ├── normalize.py     # Normalization, lemmatization
│   └── signature.py     # Signature generation for fuzzy search
│
├── storage/             # MongoDB layer → CLAUDE.md
│   └── mongodb.py       # Beanie ODM initialization, async operations
│
├── audio/               # Speech synthesis → CLAUDE.md
│   └── synthesizer.py   # Google Cloud TTS integration
│
├── anki/                # Flashcard export → CLAUDE.md
│   └── exporter.py      # .apkg generation from wordlists
│
├── wordlist/            # Vocabulary lists → CLAUDE.md
│   ├── models.py        # Wordlist, WordlistEntry
│   └── sm2.py          # SM-2 spaced repetition algorithm
│
├── wotd/                # Word of the Day → CLAUDE.md
│   └── pipeline.py      # ML pipeline for personalized WOTD
│
└── utils/               # Shared utilities → CLAUDE.md
    ├── logging.py       # Loguru-based structured logging
    ├── config.py        # Config singleton (auth/config.toml)
    ├── paths.py         # Platform-specific paths
    └── validation.py    # Input validation
```

## Key Pipelines

**Lookup** - `core/lookup_pipeline.py:504`
```
User Query → Search (10-100ms) → Provider Fetch (2-5s, parallel)
→ AI Synthesis (1-3s, dedup→cluster→enhance) → MongoDB + Cache → Response
```

**Search** - `search/core.py:1,382`
```
Query → Smart Cascade: Exact (<1ms) → Fuzzy (10-50ms) → Semantic (50-200ms)
→ Deduplicate → Sort by score → Return top N
```

**AI Synthesis** - `ai/synthesizer.py:432`
```
Provider Data (47 defs) → Deduplicate (23 defs) → Cluster (3-4 groups)
→ Parallel Enhancement (12 tasks) → MongoDB → Response
```

## Technology Stack

**Framework**: FastAPI + Uvicorn (async), Pydantic v2, Beanie ODM
**Database**: MongoDB 7.0 with Motor (async driver)
**AI**: OpenAI API (GPT-5 series, 3-tier selection)
**Search**: FAISS (semantic), RapidFuzz (fuzzy), marisa-trie (exact)
**Caching**: Multi-tier (OrderedDict LRU + DiskCache + MongoDB versioning)
**Package Manager**: UV (Rust-based, 10-100x faster than pip)

## Architecture Patterns

- **Async-First**: All I/O async, 80+ async fixtures in tests
- **Type-Safe**: Pydantic v2 throughout, mypy strict mode
- **Isomorphic Types**: Frontend TS mirrors backend Pydantic exactly
- **Repository Pattern**: 11 repositories for data access
- **Dependency Injection**: FastAPI `Depends()` for loose coupling
- **Multi-Tier Caching**: L1 (0.2ms) → L2 (5ms) → L3 (versioned)
- **Content-Addressable**: SHA-256 hashing for deduplication
- **3-Tier Model Selection**: Nano/Mini/Full routing (87% cost savings)

## Performance Targets

| Operation | Time | Notes |
|-----------|------|-------|
| Lookup (cached) | <500ms | L1/L2 hit |
| Lookup (uncached) | 2-5s | Provider fetch + AI synthesis |
| Search exact | <1ms | marisa-trie O(m) |
| Search fuzzy | 10-50ms | RapidFuzz with signature buckets |
| Search semantic | 50-200ms | FAISS HNSW + embeddings |
| AI synthesis | 1-3s | Parallel processing, 12 components |

## Module Documentation

Each module has a dedicated CLAUDE.md:
- **api/CLAUDE.md** - REST endpoints, routers, repositories, services, middleware
- **core/CLAUDE.md** - Pipelines (lookup, search, WOTD), state tracking, SSE
- **models/CLAUDE.md** - Data models (179+), parameters, responses, relationships
- **search/CLAUDE.md** - Multi-method search, cascade logic, FAISS config
- **ai/CLAUDE.md** - OpenAI integration, synthesis functions, 3-tier selection
- **caching/CLAUDE.md** - Multi-tier architecture, versioning, compression
- **corpus/CLAUDE.md** - Vocabulary management, tree operations, aggregation
- **providers/CLAUDE.md** - External sources (11 providers), rate limiting
- **cli/CLAUDE.md** - Command-line interface, Rich terminal UI
- **text/CLAUDE.md** - Normalization, lemmatization, signature generation
- **storage/CLAUDE.md** - MongoDB layer, Beanie ODM integration
- **audio/CLAUDE.md** - Google Cloud TTS integration
- **anki/CLAUDE.md** - Flashcard export to .apkg format
- **wordlist/CLAUDE.md** - SM-2 spaced repetition algorithm
- **wotd/CLAUDE.md** - ML pipeline for WOTD selection
- **utils/CLAUDE.md** - Logging, config, paths, validation

## Testing

**Coverage**: 58 files, 19,000 lines, 639+ test functions, 80%+ coverage
**Strategy**: Real integration tests (actual MongoDB, FAISS indices, file ops)
**Mocking**: Only external APIs (OpenAI, dictionary providers)
**Async**: 80+ async fixtures, asyncio.gather for parallel operations

## Statistics

- **23 modules**, **179+ Pydantic models**, **111+ API endpoints**
- **3 core pipelines**: lookup, search, WOTD
- **4,582 LOC** search module, **4,837 LOC** AI module, **9,863 LOC** providers
- **Total backend**: ~50,000 LOC Python

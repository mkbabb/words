# API Module - REST Endpoints

Production FastAPI REST layer with 111+ endpoints across 17 routers, 11 repositories, 4 middleware components.

## Structure

```
api/
├── routers/              # 17 REST routers (3,715 LOC)
│   ├── ai/
│   │   └── main.py      # 40+ AI synthesis endpoints (819 LOC)
│   ├── words/
│   │   ├── definitions.py    # Definition CRUD (554 LOC)
│   │   ├── lookup.py         # Word lookup + streaming (425 LOC)
│   │   └── search.py         # Multi-method search (559 LOC)
│   ├── wordlist/
│   │   ├── main.py           # Wordlist CRUD (297 LOC)
│   │   └── review.py         # Spaced repetition (232 LOC)
│   ├── corpus/
│   │   ├── main.py           # Corpus CRUD (256 LOC)
│   │   ├── tree.py           # Hierarchy ops (127 LOC)
│   │   └── rebuild.py        # Index rebuilding (187 LOC)
│   ├── media/
│   │   ├── images.py         # Image management (625 LOC)
│   │   └── audio.py          # Audio synthesis (304 LOC)
│   ├── cache.py              # Cache management (185 LOC)
│   ├── database.py           # DB stats/cleanup (254 LOC)
│   ├── provider.py           # Provider status (143 LOC)
│   └── health.py             # Health checks (61 LOC)
├── repositories/         # 11 data access layers (3,982 LOC)
│   ├── wordlist_repository.py        # Wordlist CRUD (563 LOC)
│   ├── word_repository.py            # Word CRUD (481 LOC)
│   ├── definition_repository.py      # Definition CRUD (431 LOC)
│   ├── corpus_repository.py          # Corpus CRUD (418 LOC)
│   ├── image_repository.py           # Image storage (409 LOC)
│   ├── audio_repository.py           # Audio storage (382 LOC)
│   ├── search_index_repository.py    # Search indices (321 LOC)
│   ├── literature_repository.py      # Literature sources (301 LOC)
│   ├── example_repository.py         # Examples (276 LOC)
│   ├── fact_repository.py            # Facts (234 LOC)
│   └── pronunciation_repository.py   # Pronunciation (166 LOC)
├── services/             # Business logic (2,124 LOC)
│   ├── ai_service.py             # AI synthesis orchestration (562 LOC)
│   ├── wordlist_service.py       # Wordlist + review logic (487 LOC)
│   ├── corpus_service.py         # Corpus aggregation (431 LOC)
│   ├── search_service.py         # Search orchestration (298 LOC)
│   ├── image_service.py          # Image processing (192 LOC)
│   └── audio_service.py          # Audio generation (154 LOC)
├── middleware/           # 4 middleware layers (589 LOC)
│   ├── cors.py          # CORS headers (198 LOC)
│   ├── cache.py         # Response caching (187 LOC)
│   ├── logging.py       # Request logging (142 LOC)
│   └── error_handler.py # Exception handling (62 LOC)
├── exceptions.py        # 10+ custom exceptions (147 LOC)
├── dependencies.py      # FastAPI dependencies (89 LOC)
└── app.py              # Application factory (312 LOC)
```

## Key Components

**17 Routers** - REST endpoints organized by domain
- `ai/main.py:819` - 40+ generation endpoints (synonyms, facts, examples, assessment)
- `media/images.py:625` - Image upload, resize, format conversion, batch processing
- `words/search.py:559` - Multi-method cascade (exact→fuzzy→semantic), suggestions
- `words/definitions.py:554` - Definition CRUD, enhancement, validation
- `words/lookup.py:425` - Word lookup with SSE streaming progress

**11 Repositories** - Data access with Beanie ODM
- `wordlist_repository.py:563` - CRUD, frequency tracking, due word calculation
- `word_repository.py:481` - Word CRUD, normalization, lemmatization
- `definition_repository.py:431` - Definition CRUD, POS filtering, word associations

**Services** - Business logic layer
- `ai_service.py:562` - Orchestrates synthesis functions, batch mode, component selection
- `wordlist_service.py:487` - Review algorithm (SM-2), frequency tracking, due date calculation
- `corpus_service.py:431` - Vocabulary aggregation, parent-child tree operations

**Middleware** - Request/response processing
- `cors.py:198` - CORS with credentials support
- `cache.py:187` - Response caching with ETags
- `logging.py:142` - Request/response logging with timing
- `error_handler.py:62` - Structured error responses

## Endpoint Breakdown

**111+ endpoints** organized by domain:

| Domain | Endpoints | Key Operations |
|--------|-----------|----------------|
| AI synthesis | 40+ | generate_*, synthesize_*, assess_* |
| Word lookup | 8 | GET /lookup/{word}, /lookup/{word}/stream (SSE) |
| Search | 6 | GET /search, /search/suggestions, /search/similar |
| Definitions | 12 | CRUD + enhance + validate |
| Wordlist | 15 | CRUD + add_words + review + due_words |
| Corpus | 18 | CRUD + tree ops + rebuild + aggregate |
| Media | 14 | Image/audio upload, processing, batch ops |
| Cache | 6 | Stats, clear, namespace management |
| Database | 5 | Stats, cleanup, health |
| Providers | 3 | Status, rate limits, availability |

## Performance

- Lookup (cached): <500ms
- Lookup (uncached): <3s (includes AI synthesis)
- Search exact: <200ms
- Search semantic: <500ms
- Health check: <50ms
- Streaming: SSE with chunked responses (>32KB)

## Architecture

**Layered Design**:
```
Router → Service → Repository → MongoDB/Cache
  ↓         ↓           ↓            ↓
FastAPI   Logic    Data Access   Storage
```

**Dependency Injection**: FastAPI `Depends()` for repositories, services, config
**Error Handling**: APIException hierarchy with structured responses
**Type Safety**: Pydantic request/response models throughout
**Async-First**: All endpoints async with concurrent operations via `asyncio.gather()`

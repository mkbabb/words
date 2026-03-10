# api/

FastAPI REST layer.

```
api/
├── main.py                     # App factory, lifespan(), router registration
├── routers/
│   ├── __init__.py
│   ├── lookup.py               # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   ├── search.py               # GET /search—multi-method cascade
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── assess.py           # Assessment endpoints
│   │   ├── base.py             # Shared AI router utilities
│   │   ├── generate.py         # Content generation endpoints
│   │   ├── main.py             # AI generation endpoints
│   │   └── suggestions.py      # AI suggestion endpoints
│   ├── words/
│   │   ├── __init__.py
│   │   ├── main.py             # Word CRUD
│   │   ├── definitions.py      # Definition CRUD
│   │   ├── examples.py         # Example management
│   │   └── versions.py         # Version history
│   ├── wordlist/
│   │   ├── __init__.py
│   │   ├── main.py             # Wordlist CRUD
│   │   ├── reviews.py          # SM-2 review endpoints
│   │   ├── words.py            # Wordlist word management
│   │   ├── search.py           # Wordlist search
│   │   └── utils.py            # Wordlist utilities
│   ├── media/
│   │   ├── __init__.py
│   │   ├── images.py           # Image upload/retrieval
│   │   └── audio.py            # Audio upload/retrieval
│   ├── wotd/
│   │   ├── __init__.py
│   │   ├── main.py             # Word-of-the-Day endpoints
│   │   └── ml.py               # WOTD ML endpoints
│   ├── corpus.py               # Corpus hierarchy CRUD
│   ├── users.py                # User profile, preferences, history, admin
│   ├── cache.py                # Cache management
│   ├── config.py               # App config
│   ├── database.py             # DB admin
│   ├── health.py               # Health checks
│   └── providers.py            # Provider management
├── repositories/
│   ├── __init__.py
│   ├── audio_repository.py
│   ├── corpus_repository.py
│   ├── definition_repository.py
│   ├── example_repository.py
│   ├── fact_repository.py
│   ├── image_repository.py
│   ├── provider_repository.py
│   ├── synthesis_repository.py
│   ├── word_repository.py
│   └── wordlist_repository.py
├── core/
│   ├── __init__.py
│   ├── base.py                 # PaginationParams, SortParams, BaseRepository, ResponseBuilder
│   ├── cache.py                # API-level caching
│   ├── dependencies.py         # FastAPI Depends() helpers
│   ├── exceptions.py           # APIException hierarchy (15+ types -> HTTP mapping)
│   ├── monitoring.py           # Request/response monitoring
│   ├── protocols.py            # Protocol definitions
│   ├── query.py                # QueryOptimizer, AggregationBuilder, BulkOperationBuilder
│   └── responses.py            # Response utilities
├── middleware/
│   ├── __init__.py
│   ├── auth.py                 # Clerk OAuth (optional)
│   ├── auth_state.py           # AuthState, DevAuthState models
│   ├── exception_handlers.py   # Global exception handlers
│   ├── field_selection.py      # Response field filtering
│   ├── middleware.py            # CORS, logging, cache headers
│   └── rate_limiting.py        # Adaptive with exponential backoff
└── services/
    ├── __init__.py
    ├── cleanup_service.py      # Resource cleanup
    └── loaders.py              # Data loading utilities
```

## Patterns

- **Repository**: Data access layers between routers and MongoDB
- **Dependency injection**: FastAPI `Depends()` for db, auth, rate limits
- **Exception mapping**: `APIException` subclasses -> HTTP status codes
- **Request dedup**: `@cached_api_call_with_dedup()`—first concurrent call executes, others wait
- **Layered**: Router -> Service -> Repository -> MongoDB/Cache

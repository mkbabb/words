# api/

FastAPI REST layer. 17 routers, 111+ endpoints, 11 repositories, 4 middleware.

```
api/
├── main.py                     # App factory, lifespan, router registration
├── routers/
│   ├── lookup.py (339)         # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   ├── search.py (604)         # GET /search — multi-method cascade
│   ├── ai/main.py (882)       # 40+ AI generation endpoints
│   ├── words/                  # definitions.py, examples.py, versions.py
│   ├── wordlist/               # crud.py (463), reviews.py (324), upload.py (286)
│   ├── corpus.py (445)         # Corpus hierarchy CRUD
│   ├── media/                  # images.py (625), audio.py (446)
│   └── cache.py, health.py, config.py, database.py, providers.py
├── repositories/               # 11 data access layers
│   ├── word_repository.py, definition_repository.py (376)
│   ├── wordlist_repository.py (596) — includes SM-2 review logic
│   ├── provider_repository.py (506), synthesis_repository.py (375)
│   └── corpus_, image_, audio_, example_, fact_repository.py
├── core/                       # Shared utilities (1,572 LOC)
│   ├── base.py (427)          # PaginationParams, SortParams, BaseRepository
│   ├── exceptions.py (384)    # 10+ exception types → HTTP status mapping
│   ├── query.py (306)         # AggregationBuilder, QueryOptimizer
│   └── responses.py, dependencies.py, monitoring.py, protocols.py
└── middleware/
    ├── auth.py (245)           # Clerk OAuth (optional)
    ├── rate_limiting.py (445)  # Adaptive, exponential backoff
    └── middleware.py, exception_handlers.py
```

## Patterns

- **Repository**: 11 data access layers between routers and MongoDB
- **Dependency injection**: FastAPI `Depends()` for db, auth, rate limits
- **Exception mapping**: `APIException` subclasses → HTTP status codes
- **Request dedup**: `@cached_api_call_with_dedup()` — first concurrent call executes, others wait
- **Layered**: Router → Service → Repository → MongoDB/Cache

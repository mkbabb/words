# api/

FastAPI REST layer. 17 routers, 111+ endpoints, 11 repositories, 5 middleware.

```
api/
├── main.py (179)               # App factory, lifespan, router registration
├── routers/
│   ├── lookup.py (339)         # GET /lookup/{word}, /lookup/{word}/stream (SSE)
│   ├── search.py (665)         # GET /search—multi-method cascade
│   ├── ai/
│   │   ├── main.py (882)       # 40+ AI generation endpoints
│   │   └── suggestions.py (158) # AI suggestion endpoints
│   ├── words/
│   │   ├── main.py (284)       # Word CRUD
│   │   ├── definitions.py (554) # Definition CRUD
│   │   ├── examples.py (285)   # Example management
│   │   └── versions.py (209)   # Version history
│   ├── wordlist/
│   │   ├── main.py (463)       # Wordlist CRUD
│   │   ├── reviews.py (286)    # SM-2 review endpoints
│   │   ├── words.py (324)      # Wordlist word management
│   │   ├── search.py (123)     # Wordlist search
│   │   └── utils.py (151)      # Wordlist utilities
│   ├── corpus.py (445)         # Corpus hierarchy CRUD
│   ├── media/
│   │   ├── images.py (625)     # Image upload/retrieval
│   │   └── audio.py (446)      # Audio upload/retrieval
│   ├── wotd/
│   │   ├── main.py (500)       # Word-of-the-Day endpoints
│   │   └── ml.py (344)         # WOTD ML endpoints
│   └── cache.py, health.py, config.py, database.py, providers.py
├── repositories/               # 11 data access layers
│   ├── word_repository.py, definition_repository.py (376)
│   ├── wordlist_repository.py (596)
│   ├── provider_repository.py (506), synthesis_repository.py (375)
│   └── corpus_, image_, audio_, example_, fact_repository.py
├── services/
│   ├── cleanup_service.py (101) # Resource cleanup
│   └── loaders.py (260)        # Data loading utilities
├── core/
│   ├── base.py (427)           # PaginationParams, SortParams, BaseRepository
│   ├── exceptions.py (384)     # 10+ exception types -> HTTP status mapping
│   ├── query.py (306)          # AggregationBuilder, QueryOptimizer
│   ├── monitoring.py (257)     # Request/response monitoring
│   └── cache.py, dependencies.py, protocols.py, responses.py
└── middleware/
    ├── auth.py (245)            # Clerk OAuth (optional)
    ├── rate_limiting.py (445)   # Adaptive, exponential backoff
    ├── field_selection.py (122) # Response field filtering
    └── middleware.py (149), exception_handlers.py (59)
```

## Patterns

- **Repository**: 11 data access layers between routers and MongoDB
- **Dependency injection**: FastAPI `Depends()` for db, auth, rate limits
- **Exception mapping**: `APIException` subclasses -> HTTP status codes
- **Request dedup**: `@cached_api_call_with_dedup()`—first concurrent call executes, others wait
- **Layered**: Router -> Service -> Repository -> MongoDB/Cache

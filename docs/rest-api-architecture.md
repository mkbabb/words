# REST API Architecture

## Technology Stack

- **FastAPI**: Async Python framework
- **MongoDB**: Beanie ODM (existing system)
- **Search**: Current Python/FAISS engine
- **Caching**: Existing multi-tier system
- **Validation**: Pydantic v2

## Endpoints

### GET /api/v1/lookup/{word}
**Parameters:**
- `word`: Word to look up (path)
- `force_refresh`: Boolean (default: false)
- `providers`: List of providers (default: wiktionary)
- `no_ai`: Skip AI synthesis (default: false)

**Response:**
```json
{
  "word": "serendipity",
  "pronunciation": {"phonetic": "ser-uh n-DIP-i-tee", "ipa": "/ˌsɛrənˈdɪpɪti/"},
  "definitions": [{
    "word_type": "noun",
    "definition": "The faculty of making fortunate discoveries...",
    "synonyms": ["chance", "fortune"],
    "examples": {"generated": [{"sentence": "Finding the apartment was serendipity."}]},
    "meaning_cluster": "fortunate_discovery"
  }],
  "last_updated": "2025-01-07T10:30:00Z"
}
```

### GET /api/v1/search
**Parameters:**
- `q`: Search query (required)
- `method`: exact|fuzzy|semantic|hybrid (default: hybrid)
- `max_results`: Max results (default: 20, max: 100)
- `min_score`: Min relevance (default: 0.6)

**Response:**
```json
{
  "query": "cogn",
  "results": [
    {"word": "cognitive", "score": 0.95, "method": "prefix", "is_phrase": false},
    {"word": "cognition", "score": 0.92, "method": "exact", "is_phrase": false}
  ],
  "total_results": 12,
  "search_time_ms": 45
}
```

### GET /api/v1/synonyms/{word}
**Parameters:**
- `word`: Target word
- `max_results`: Max synonyms (default: 10)

**Response:**
```json
{
  "word": "happy",
  "synonyms": [
    {"word": "joyful", "score": 0.9},
    {"word": "cheerful", "score": 0.85}
  ]
}
```

### GET /api/v1/suggestions
**Parameters:**
- `q`: Partial query (min 2 chars)
- `limit`: Max suggestions (default: 10)

**Response:**
```json
{
  "query": "ser",
  "suggestions": ["serendipity", "serene", "serious"]
}
```

### GET /api/v1/health
**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "search_engine": "initialized",
  "cache_hit_rate": 0.87,
  "uptime_seconds": 3600
}
```

## Implementation

### Application Structure
```
src/floridify/api/
├── main.py              # FastAPI app
├── routers/
│   ├── lookup.py        # Lookup endpoints
│   ├── search.py        # Search endpoints
│   └── health.py        # Health endpoints
├── models/
│   ├── requests.py      # Request schemas
│   └── responses.py     # Response schemas
├── dependencies.py      # Shared dependencies
└── middleware.py        # CORS, logging
```

### Integration Points
```python
# Search engine singleton
search_engine = await get_search_engine([Language.ENGLISH])
results = await search_engine.search(query, max_results=20)

# Lookup pipeline
entry = await lookup_word_pipeline(
    word=word,
    providers=[DictionaryProvider.WIKTIONARY],
    force_refresh=force_refresh
)

# Cache decorators
@cached_api_call(ttl_hours=1.0)
async def search_endpoint(query: str):
    # Implementation
```

## Performance

### Caching Layers
- **API responses**: 1 hour TTL
- **Search results**: Memory cache
- **Database queries**: Existing MongoDB cache
- **External APIs**: 24 hour TTL

### Debounced Search
```javascript
const debouncedSearch = debounce(async (query) => {
  if (query.length >= 2) {
    const response = await fetch(`/api/v1/suggestions?q=${query}`);
    return response.json();
  }
}, 200);
```

## Deployment

### Single Service
```
┌─────────────────┐
│   FastAPI App   │
├─────────────────┤
│  Search Engine  │
├─────────────────┤
│  Cache Manager  │
├─────────────────┤
│    MongoDB      │
└─────────────────┘
```

### Configuration
```bash
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=floridify
API_HOST=0.0.0.0
API_PORT=8000
```

### CORS
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"]
)
```

## Security

- Pydantic validation on all inputs
- Query length limit: 100 characters
- Max results per request: 100
- Request timeout: 30 seconds

## Monitoring

### Metrics
- Request count/latency per endpoint
- Cache hit rates
- Database performance
- Search engine performance

### Logging
```python
logger.info("API request", extra={
    "endpoint": "/api/v1/lookup/word",
    "response_time_ms": response_time,
    "cache_hit": cache_hit
})
```
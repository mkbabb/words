# REST API Testing Specification

## Endpoint Categories

### Health & System
- `GET /health` - Service health with database/search/cache status
- Response: `HealthResponse` with status, version, uptime, connection pool stats

### Core Lookup Pipeline
- `GET /api/v1/lookup/{word}` - Comprehensive word lookup with AI synthesis
- `GET /api/v1/lookup/{word}/stream` - Streaming lookup with SSE progress
- Query params: `force_refresh`, `providers`, `languages`, `no_ai`
- Response: `DictionaryEntryResponse` with definitions, pronunciation, etymology, images

### Search Pipeline  
- `GET /api/v1/search?q={query}` - Multi-method word search (exact/fuzzy/semantic)
- `GET /api/v1/search/{query}/suggestions` - Autocomplete suggestions
- `POST /api/v1/search/rebuild-index` - Rebuild search indices
- Response: `SearchResponse` with ranked results, scores, methods

### AI Synthesis (40+ endpoints)
- `POST /api/v1/ai/synthesize/pronunciation` - Generate phonetic/IPA
- `POST /api/v1/ai/synthesize/synonyms` - Context-aware synonyms  
- `POST /api/v1/ai/generate/examples` - Natural usage examples
- `POST /api/v1/ai/generate/facts` - Interesting word facts
- `POST /api/v1/ai/suggestions` - Vocabulary suggestions
- Rate limited with token estimation

### Corpus Management
- `POST /api/v1/corpus` - Create TTL-based searchable corpus
- `POST /api/v1/corpus/{id}/search` - Search within corpus
- `GET /api/v1/corpus/{id}` - Corpus metadata and stats
- TTL cleanup with automatic expiration

### WordList CRUD
- `GET /api/v1/wordlists` - List with filtering/pagination
- `POST /api/v1/wordlists` - Create new wordlist
- `POST /api/v1/wordlists/upload` - File upload with streaming
- `GET /api/v1/wordlists/{id}/words` - Words with learning metadata
- Review system with spaced repetition (SM-2 algorithm)

### Batch Operations
- `POST /api/v1/batch/lookup` - Parallel word lookups (1-50 words)
- `POST /api/v1/batch/execute` - Arbitrary batch operations
- Error isolation with individual operation failure handling

### Media Management
- `GET/POST/PUT/DELETE /api/v1/audio` - Audio file CRUD with format/accent metadata
- `GET/POST/PUT/DELETE /api/v1/images` - Image CRUD with alt text/descriptions
- Binary data handling with proper Content-Type headers

### Data CRUD (Words, Definitions, Examples, Facts)
- Full CRUD operations with optimistic locking via version fields
- ETag support for caching
- Cascading deletion options
- Field selection (include/exclude/expand)

## Response Patterns
- `ResourceResponse` - Single resource with metadata/links
- `ListResponse[T]` - Paginated collections with has_more/total  
- `BatchResponse` - Batch operation results with success/failure counts
- `StreamingResponse` - SSE for real-time progress updates
- Error responses with field-level validation details

## Authentication & Middleware
- CORS-enabled for cross-origin development
- Rate limiting on AI endpoints with token-based throttling
- HTTP caching with ETag support
- Request/response logging with performance metrics
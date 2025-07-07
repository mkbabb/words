# Floridify Caching Strategy Investigation

## Executive Summary

The Floridify codebase implements a comprehensive **multi-layered caching strategy** with both modern and legacy components. Contrary to initial assumptions, the caching system is actively used throughout the application, though some components like `APIResponseCache` appear to be defined but unused in practice.

## Caching Architecture Overview

### 1. **Modern Unified Caching System** (Primary)

The main caching implementation centers around a modern, unified system located in `/src/floridify/caching/`:

#### Core Components

- **`CacheManager`** (`cache_manager.py`): A sophisticated TTL-based cache with both memory and file persistence
  - Memory cache for fast access (LRU-style with configurable limits)
  - File-based persistence using pickle for durability
  - TTL (Time-To-Live) support with automatic expiration
  - Configurable default TTL of 24 hours
  - SHA-256 key generation from function parameters
  - Built-in cleanup and statistics

- **Caching Decorators** (`decorators.py`): Function-level caching decorators
  - `@cached_api_call`: For OpenAI API calls (24h TTL, memory-only by default)
  - `@cached_computation`: For expensive computations (24h TTL, file cache enabled)
  - Supports both sync and async functions
  - Force refresh capability via parameter injection
  - Custom key generation functions

- **HTTP Client Caching** (`http_client.py`): HTTP response caching using **hishel**
  - Filesystem-based HTTP response caching
  - Cache-Control header support
  - TTL-based cache management (24h default for HTTP responses)
  - 168h (1 week) TTL for lexicon files
  - Automatic cache status logging

### 2. **MongoDB-Based Caching** (Legacy/Unused)

Located in `/src/floridify/storage/mongodb.py` and models:

- **`APIResponseCache`** document model: Stores API responses with timestamps
- **MongoDB cache methods**: `cache_api_response()`, `get_cached_response()`, `cleanup_old_cache()`
- **Status**: **DEFINED BUT UNUSED** - Found in 4 files but no actual usage calls in the codebase

### 3. **Semantic Search Caching** (Specialized)

Located in `/src/floridify/search/semantic.py`:

- **Vector/Embedding Cache**: File-based caching of TF-IDF vectorizers and FAISS indices
- **Cache Structure**:
  - Vectorizers (character, subword, word levels) stored as pickle files
  - Embeddings stored as NumPy arrays (.npy files)
  - FAISS indices stored as .faiss files
  - Vocabulary hash-based cache keys for validation
- **Features**: Configuration validation, automatic rebuilding on parameter changes

### 4. **Lexicon Data Caching** (Specialized)

Located in `/src/floridify/search/lexicon/lexicon.py`:

- **Lexicon Cache**: Pickle-based caching of processed lexicon data
- **HTTP Download Cache**: Uses the unified HTTP client for source downloads
- **Multi-level caching**:
  - Raw download cache (HTTP layer)
  - Processed lexicon data cache (pickle files)
  - Language-specific cache files

## Active Usage Patterns

### 1. **OpenAI API Caching**
```python
# src/floridify/ai/connector.py
@cached_api_call(
    ttl_hours=24.0,
    use_file_cache=False,  # Memory-only for API responses
    key_func=lambda self, prompt, response_model, **kwargs: (
        "openai_structured",
        self.model_name,
        hash(prompt),
        response_model.__name__,
        tuple(sorted(kwargs.items())),
    ),
)
async def _make_structured_request(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
```

### 2. **HTTP Request Caching**
```python
# src/floridify/connectors/wiktionary.py
response = await self.http_client.get(
    self.base_url,
    params=params,
    ttl_hours=24.0,  # Cache Wiktionary API responses for 24 hours
    headers={"User-Agent": "Floridify/1.0"},
    timeout=30.0,
)
```

### 3. **Lexicon Download Caching**
```python
# src/floridify/search/lexicon/scrapers/default.py
http_client = get_cached_http_client(
    force_refresh=force_refresh,
    default_ttl_hours=ttl_hours,  # 168h for lexicon files
)

response = await http_client.get(
    url,
    ttl_hours=ttl_hours,
    force_refresh=force_refresh,
    timeout=kwargs.get('timeout', 30.0),
)
```

## Cache Storage Locations

### File System Caches
- **General cache**: `~/.cache/floridify/` (CacheManager)
- **HTTP cache**: `~/.cache/floridify/http/` (hishel-based)
- **Vector cache**: `{cache_dir}/vectors/` (Semantic search)
- **Lexicon cache**: `{cache_dir}/lexicons/` and `{cache_dir}/index/`

### Memory Caches
- **CacheManager**: In-memory LRU cache (max 1000 entries)
- **Global instances**: HTTP client, cache manager singletons

### Database Caches
- **MongoDB collections**: `api_response_cache` (unused), `dictionary_entries`, `synthesized_dictionary_entries`

## Cache Management Features

### 1. **TTL (Time-To-Live) Support**
- Default 24 hours for most operations
- 168 hours (1 week) for lexicon downloads
- Automatic expiration checking
- Configurable per-operation

### 2. **Cache Invalidation**
- Force refresh parameters in HTTP client and decorators
- Manual cache clearing via `clear_all_cache()`
- Automatic cleanup on configuration changes (semantic search)
- LRU eviction for memory caches

### 3. **Cache Validation**
- Hash-based validation for semantic search caches
- Configuration compatibility checking
- Automatic rebuild on parameter mismatches

### 4. **Monitoring and Statistics**
- Cache hit/miss logging throughout the system
- Statistics methods in CacheManager and SemanticSearch
- Memory usage tracking

## Integration Points

### 1. **Dictionary Providers**
- **Wiktionary**: Uses HTTP caching for API responses (24h TTL)
- **Dictionary.com**: Stubbed but uses force_refresh pattern

### 2. **AI Services**
- **OpenAI API**: Memory-cached with custom key generation
- **All AI operations**: Use `@cached_api_call` decorator

### 3. **Search Engine**
- **Semantic Search**: File-based caching of embeddings and indices
- **Lexicon Loading**: Multi-layer caching (HTTP + processed data)

### 4. **CLI Commands**
- **Force refresh**: Supported in lookup and search commands
- **Cache statistics**: Available via search engine stats
- **Database cleanup**: Planned but not implemented

## Unused Components

### 1. **APIResponseCache Model**
- **Status**: Defined in models but never used in practice
- **Location**: `/src/floridify/models/models.py`, `/src/floridify/storage/mongodb.py`
- **Reason**: Superseded by modern caching decorators and HTTP client

### 2. **MongoDB Cache Methods**
- **Methods**: `cache_api_response()`, `get_cached_response()`, `cleanup_old_cache()`
- **Status**: Implemented but no callers found in codebase
- **Possible removal**: Safe to remove unless planned for future use

## Cache Warming and Cleanup

### 1. **Automatic Cache Warming**
- **Lexicon loading**: Caches are populated during search engine initialization
- **Semantic search**: Embeddings built and cached on first use
- **No explicit cache warming commands**

### 2. **Cleanup Processes**
- **Memory cache**: Automatic LRU eviction and TTL cleanup
- **File cache**: No automatic cleanup (relies on TTL checking)
- **HTTP cache**: Managed by hishel library
- **Database cache**: Cleanup planned but not implemented

### 3. **Manual Cache Management**
- **CacheManager**: `clear_all()` method available
- **HTTP Client**: `clear_cache()` method available
- **Semantic Search**: Rebuild triggered by `force_rebuild` parameter
- **CLI integration**: Not fully implemented

## Recommendations

### 1. **Cleanup Opportunities**
- Remove unused `APIResponseCache` model and related MongoDB methods
- Implement CLI cache management commands
- Add automatic file cache cleanup based on TTL

### 2. **Monitoring Improvements**
- Add cache statistics to CLI status commands
- Implement cache health monitoring
- Add cache size tracking and limits

### 3. **Performance Optimizations**
- Consider cache prewarming for common operations
- Implement cache compression for large embeddings
- Add cache hit ratio monitoring

## Conclusion

The Floridify caching system is **actively used and well-designed** with a modern, multi-layered approach. The primary caching mechanism uses a combination of:

1. **CacheManager** for general-purpose caching with TTL support
2. **HTTP Client caching** using hishel for external API calls
3. **Specialized caches** for semantic search and lexicon data

The legacy `APIResponseCache` MongoDB-based system appears to be unused and could be safely removed. The overall caching strategy provides good performance with appropriate TTL settings and cache invalidation mechanisms.
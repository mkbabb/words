# HTTP Cache Headers Implementation

## Problem Analysis

**Current Issue**: API responses lack proper HTTP caching headers, forcing clients to make unnecessary requests for cacheable data.

**Performance Impact**:
- No browser/proxy caching of API responses
- Repeated requests for static search results
- Increased server load for cacheable content
- Poor user experience with redundant network calls

## Current State

```python
# No cache headers in current responses
# Missing: Cache-Control, ETag, Last-Modified
# All requests treated as non-cacheable
```

## Implementation Strategy

### 1. Cache-Control Headers
```python
from fastapi import Response

@router.get("/search")
async def search_words_query(
    response: Response,
    q: str = Query(...),
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    # Set cache headers for search results
    response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
    response.headers["Vary"] = "Accept-Encoding"
    
    # Generate ETag based on query + params
    etag_data = f"{q}:{params.language}:{params.max_results}:{params.min_score}"
    etag = hashlib.md5(etag_data.encode()).hexdigest()
    response.headers["ETag"] = f'"{etag}"'
```

### 2. Conditional Requests Support
```python
from fastapi import Request

async def check_cache_headers(request: Request, etag: str) -> bool:
    """Check if client has cached version."""
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match.strip('"') == etag:
        return True  # Client has current version
    return False
```

### 3. Cache Strategy by Endpoint

#### Search Endpoints (Medium Cache)
- **Cache-Control**: `public, max-age=3600` (1 hour)
- **Rationale**: Search results are relatively stable
- **ETag**: Based on query parameters

#### Lookup Endpoints (Short Cache)
- **Cache-Control**: `public, max-age=1800` (30 minutes)
- **Rationale**: Definitions may be updated periodically
- **ETag**: Based on word + force_refresh flag

#### Health Endpoint (No Cache)
- **Cache-Control**: `no-cache, no-store, must-revalidate`
- **Rationale**: Real-time status information

## Implementation Plan

### Phase 1: Basic Cache Headers
```python
class CacheHeadersMiddleware:
    """Middleware to add appropriate cache headers."""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Wrap send to add headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Add cache headers based on path
                    path = scope["path"]
                    if path.startswith("/api/v1/search"):
                        headers[b"cache-control"] = b"public, max-age=3600"
                    elif path.startswith("/api/v1/lookup"):
                        headers[b"cache-control"] = b"public, max-age=1800"
                    elif path.startswith("/api/v1/health"):
                        headers[b"cache-control"] = b"no-cache, no-store"
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```

### Phase 2: ETag Support
```python
def generate_etag(data: dict) -> str:
    """Generate ETag from response data."""
    content = json.dumps(data, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

@router.get("/search")
async def search_words_query(
    request: Request,
    response: Response,
    q: str = Query(...),
    params: SearchParams = Depends(parse_search_params),
):
    # Generate cache key
    cache_key = f"search:{q}:{params.language}:{params.max_results}:{params.min_score}"
    etag = hashlib.md5(cache_key.encode()).hexdigest()
    
    # Check if client has current version
    if_none_match = request.headers.get("If-None-Match", "").strip('"')
    if if_none_match == etag:
        response.status_code = 304  # Not Modified
        return Response(status_code=304)
    
    # Set cache headers
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    # Continue with normal processing
    return await _cached_search(q, params)
```

### Phase 3: Cache Validation
```python
@router.get("/search")
async def search_words_query(
    request: Request,
    response: Response,
    q: str = Query(...),
    params: SearchParams = Depends(parse_search_params),
):
    # Check cache freshness
    if_modified_since = request.headers.get("If-Modified-Since")
    last_modified = get_last_modified_for_search(q)
    
    if if_modified_since and last_modified:
        if parse_http_date(if_modified_since) >= last_modified:
            return Response(status_code=304)
    
    # Set Last-Modified header
    response.headers["Last-Modified"] = format_http_date(last_modified)
```

## Expected Improvements

### Performance Gains
- **Cache Hit Scenario**: 95%+ reduction in response time (304 responses)
- **Network Usage**: 80-90% reduction in bandwidth for repeated requests
- **Server Load**: 60-80% reduction in processing for cached content
- **User Experience**: Near-instant responses for cached searches

### Cache Effectiveness Metrics
- **Cache Hit Rate**: Target 70-80% for search endpoints
- **Bandwidth Savings**: 80%+ reduction for repeat visitors
- **Server Resource Usage**: 50%+ reduction in CPU/memory for cached responses

## Implementation Timeline

### Week 1: Basic Implementation
1. Add Cache-Control headers to all endpoints
2. Implement basic ETag generation
3. Test cache behavior with curl/browser tools

### Week 2: Advanced Features
1. Add conditional request support (304 responses)
2. Implement cache validation logic
3. Add cache metrics collection

### Week 3: Optimization & Monitoring
1. Fine-tune cache durations based on usage patterns
2. Add cache performance monitoring
3. Optimize ETag generation for performance

## Risk Assessment

- **Low Risk**: Standard HTTP caching mechanisms
- **Compatibility**: All modern browsers support these headers
- **Debugging**: May require cache-busting during development
- **Storage**: No additional server-side storage required

## Verification

Test cache behavior:
```bash
# Test ETag support
curl -H "If-None-Match: \"abc123\"" http://localhost:8000/api/v1/search?q=test

# Test cache headers
curl -I http://localhost:8000/api/v1/search?q=test

# Expected headers:
# Cache-Control: public, max-age=3600
# ETag: "abc123def456"
# Vary: Accept-Encoding
```

## Monitoring

Add cache metrics to health endpoint:
```python
{
    "cache_stats": {
        "requests_total": 1000,
        "cache_hits": 750,
        "cache_hit_rate": 0.75,
        "bandwidth_saved_mb": 45.2
    }
}
```
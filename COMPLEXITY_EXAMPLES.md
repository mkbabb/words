# Complexity Analysis - Detailed Code Examples

## Issue #1: Dual Generator Implementation

**File**: `backend/src/floridify/core/streaming.py`
**Lines**: 209-443 (235 lines total, 110 lines duplicated)

### Problem Code

**First implementation** (Lines 231-327):
```python
async def event_generator() -> AsyncGenerator[str]:
    try:
        if include_stage_definitions:
            config_event = SSEEvent(...)
            yield config_event.format()
        
        progress_task = asyncio.create_task(monitor_and_yield())
        try:
            result = await process_func()
            completion_data = {
                "type": "complete",
                "message": "Process completed successfully",
            }
            if include_completion_data and result is not None:
                completion_data["result"] = result.model_dump(mode="json")
            completion_event = SSEEvent(event_type="complete", data=completion_data)
            yield completion_event.format()
        except Exception as e:
            # ... error handling ...
        finally:
            if not monitor_task.done():
                monitor_task.cancel()
```

**Second implementation** (Lines 329-443, `simple_generator`):
Nearly identical code path, never effectively used.

### Complexity Markers
- 2 nested try/except blocks
- Multiple conditional branches for result serialization
- Magic number: `32768` (line 397)

---

## Issue #2: Category-Based Branching

**File**: `backend/src/floridify/core/state_tracker.py`
**Lines**: 94-279 (186 lines)

### Problem Code

```python
@classmethod
def get_stage_definitions(cls, category: str = "lookup") -> list[ProcessStage]:
    if category == "lookup":
        return [
            ProcessStage(
                name=cls.START,
                progress=5,
                label="Start",
                description="Pipeline initialization and setup",
                category="lookup",
            ),
            ProcessStage(
                name=cls.SEARCH_START,
                progress=10,
                label="Search Start",
                description="Beginning multi-method word search",
                category="lookup",
            ),
            # ... 13 more ProcessStage objects ...
        ]
    
    if category == "upload":
        return [
            ProcessStage(
                name=cls.UPLOAD_START,
                progress=5,
                label="Start",
                description="Initializing upload process",
                category="upload",
            ),
            # ... 7 more similar objects ...
        ]
    
    if category == "image":
        return [
            # ... 5 similar objects ...
        ]
    
    # Generic stages for unknown categories
    return [
        # ... 3 generic stages ...
    ]
```

### Complexity Markers
- 3 separate if-chains (not elif)
- 186 lines of nearly-identical stage definitions
- Magic strings: "lookup", "upload", "image"
- ~95% code duplication

---

## Issue #3: Six Similar Decorators

**File**: `backend/src/floridify/caching/decorators.py`
**Lines**: 89-483 (395 lines of decorator code)

### Problem Pattern (Repeated 4 times)

**Lines 132-175** (cached_api_call):
```python
# Generate cache key efficiently
key_parts = _efficient_cache_key_parts(func, args, filtered_kwargs)
if headers:
    key_parts = (*key_parts, headers)

cache_key = _generate_cache_key(key_parts)

# Get unified cache
cache = await get_global_cache()

# Map key_prefix to namespace
namespace = CACHE_NAMESPACE_MAP.get(key_prefix, CacheNamespace.API)

# Try to get from cache
cached_result = await cache.get(namespace, cache_key)
if cached_result is not None:
    logger.debug(
        f"💨 Cache hit for {func.__name__} (took {(time.time() - start_time) * 1000:.2f}ms)",
    )
    return cast("R", cached_result)

# Call the actual function
try:
    result = await func(*args, **kwargs)

    # Cache the result
    await cache.set(
        namespace,
        cache_key,
        result,
        ttl_override=timedelta(hours=ttl_hours),
    )

    elapsed = (time.time() - start_time) * 1000
    logger.debug(f"✅ Cached result for {func.__name__} (took {elapsed:.2f}ms)")

    return result

except Exception as e:
    elapsed = (time.time() - start_time) * 1000
    logger.warning(f"❌ Error in {func.__name__} after {elapsed:.2f}ms: {e}")
    raise
```

**Same pattern repeated in**:
- `cached_computation_async()` (lines 200-224)
- `cached_computation_sync()` (lines 262-280)
- `cached_api_call_with_dedup()` (lines 440-465)

### Complexity Markers
- 6 decorator functions
- ~90% code duplication
- 4 separate implementations of cache lookup/store logic

---

## Issue #4: Token Parameter Handling

**File**: `backend/src/floridify/ai/connector.py`
**Lines**: 142-164 (23 lines)

### Problem Code

```python
# Use correct token parameter based on model capabilities
if model_tier and model_tier.uses_completion_tokens:
    if model_tier.is_reasoning_model:
        # Reasoning models need massive token allocation for internal thinking
        # For small outputs like 30-50 tokens, we need 10-20x more for reasoning
        reasoning_multiplier = 30 if max_tokens_value <= 50 else 15
        request_params["max_completion_tokens"] = max(
            4000,
            max_tokens_value * reasoning_multiplier,
        )
    else:
        # Non-reasoning models with completion tokens use standard allocation
        request_params["max_completion_tokens"] = max_tokens_value
else:
    # Legacy models use max_tokens
    request_params["max_tokens"] = max_tokens_value
```

### Complexity Markers
- 3-level nesting
- Magic numbers: `30`, `15`, `50`, `4000`
- Parameter-specific logic not reusable

### Followed by scattered validation (Lines 185-236)

```python
# Extract token usage
token_usage = {}
prompt_tokens = None
completion_tokens = None
total_tokens = None
try:
    if response.usage:
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
except AttributeError:
    pass

# ... later at line 219 ...
try:
    result.token_usage = token_usage
except (AttributeError, ValueError):
    pass

# ... later at line 226 ...
try:
    if result.model_info:
        result.model_info.name = active_model
except AttributeError:
    pass
```

### Complexity Markers
- 3 separate try/except blocks with nearly identical logic
- Repeated attribute checking pattern
- No centralized safe attribute setter

---

## Issue #5: Race Condition Guards with Double-Checked Locking

**File**: `backend/src/floridify/search/core.py`
**Lines**: 60-64, 208-214, 162-179

### Problem: State Initialization Boilerplate

```python
# Lines 60-64: State initialization
self._semantic_ready = False
self._semantic_init_task: asyncio.Task[None] | None = None
self._semantic_init_lock: asyncio.Lock = asyncio.Lock()
self._semantic_init_error: str | None = None
```

### Problem: Double-Checked Locking (Line 208-214)

```python
if self.index.semantic_enabled and not self._semantic_ready:
    logger.debug("Semantic search enabled - initializing in background")
    async with self._semantic_init_lock:
        # Double-check after acquiring lock
        if not self._semantic_ready and self._semantic_init_task is None:
            self._semantic_init_task = asyncio.create_task(
                self._initialize_semantic_background()
            )
```

### Problem: Hash Mismatch Special Case (Lines 162-179)

```python
if self.corpus.vocabulary_hash != self.index.vocabulary_hash:
    logger.warning(f"VOCABULARY HASH MISMATCH...")
    
    # Preserve semantic settings before rebuild
    semantic_was_enabled = self.index.semantic_enabled
    
    # Trigger automatic rebuild
    await self.build_indices()
    self.index.vocabulary_hash = self.corpus.vocabulary_hash
    
    # Restore semantic settings after rebuild
    self.index.semantic_enabled = semantic_was_enabled
    self.index.has_semantic = semantic_was_enabled
    
    await self.index.save()
    
    # Re-initialize semantic search
    if semantic_was_enabled and not self._semantic_ready:
        logger.info("Re-initializing semantic search...")
        async with self._semantic_init_lock:
            if not self._semantic_ready and self._semantic_init_task is None:
                self._semantic_init_task = asyncio.create_task(...)
```

### Complexity Markers
- 3-level nesting in hash mismatch
- State preservation logic (save/restore)
- Duplicate task initialization (appears twice: lines 191-193 and 214-216)
- 4 state booleans: `_semantic_ready`, `_semantic_init_task`, `_semantic_init_error`

---

## Issue #6: Multiple If Statements for HTTP Status Codes

**File**: `backend/src/floridify/providers/utils.py`
**Lines**: 247-275

### Problem Code

```python
async def get(self, url: str, **kwargs: Any) -> httpx.Response:
    if not self._session:
        raise ValueError("Client must be used as async context manager")
    
    await self.rate_limiter.acquire()
    
    try:
        response = await self._session.get(url, **kwargs)
        
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_delay = float(retry_after) if retry_after else None
            self.rate_limiter.record_error(retry_delay)
            raise RateLimitError(f"Rate limited: {response.status_code}")
        if response.status_code >= 500:
            self.rate_limiter.record_error()
            raise ScrapingError(f"Server error: {response.status_code}")
        if response.status_code >= 400:
            raise ScrapingError(f"Client error: {response.status_code}")
        # Success (implicit)
        self.rate_limiter.record_success()
        return response
    
    except httpx.RequestError as e:
        self.rate_limiter.record_error()
        raise ScrapingError(f"Request failed: {e}") from e
```

### Complexity Markers
- 4 separate if statements (should use elif or match/case)
- Non-exhaustive conditions (success is implicit)
- Inline type conversion in conditional
- Repeated rate limiter calls

---

## Issue #7: Triple Exception Catching

**File**: `backend/src/floridify/caching/manager.py`

### Problem Code

```python
except (OperationFailure, AttributeError, Exception) as e:
```

### Issue
Catching `Exception` is redundant - it's the parent class of all exceptions.

### Should be
```python
except (OperationFailure, AttributeError) as e:
```

---

## Overall Pattern Summary

| Pattern | Count | Files | Impact |
|---------|-------|-------|--------|
| Nested if/else chains (3+ levels) | 8+ | Multiple | High |
| Duplicated validation logic | 12+ | Multiple | High |
| Magic numbers/strings | 15+ | Multiple | Medium |
| Multiple if statements (not elif) | 6+ | Multiple | Medium |
| Over-specialized functions | 6 | decorators.py | Medium |
| Repeated code patterns | 4+ | Multiple | High |


# Security, Reliability, and UX Audit

**Date**: February 26-27, 2026
**Scope**: Full-stack audit covering authentication, CORS, SSE streaming, caching concurrency, frontend state management, and Playwright-driven validation.
**Commits**: `6db66c3` → `7ec1e23` → `e1297f7` → `8015a6b`
**Test Results**: 712 backend tests pass, 0 console errors in frontend

---

## 1. Clerk JWT Authentication Middleware

**File**: `backend/src/floridify/api/middleware/auth.py` (246 lines, new)

Added a Starlette middleware that validates Clerk-issued JWTs on every request. The middleware classifies all 111+ endpoints into four protection tiers:

| Tier | Auth | Endpoints | Behavior |
|------|------|-----------|----------|
| **1 - Public** | None | GET lookup, search, suggestions, health, config | Bypass auth entirely |
| **2 - Authenticated** | Bearer JWT | All AI synthesis, wordlist CRUD, upload, review | 401 if missing/invalid token |
| **3 - Owner** | JWT + ownership | PUT/DELETE on user-owned resources | (enforced at repository level) |
| **4 - Admin** | JWT + `role=admin` | cache/clear, corpus/rebuild, database/cleanup, metrics | 403 if not admin |

### How it works

1. **OPTIONS** requests pass through (CORS preflight).
2. Public endpoints (matched by `PUBLIC_PREFIXES`) skip auth.
3. All other requests must include `Authorization: Bearer <token>`.
4. The token is validated against Clerk's JWKS endpoint (`/.well-known/jwks.json`), which is fetched and cached for 1 hour.
5. RS256 signature verification via `PyJWT[crypto]` + `RSAAlgorithm.from_jwk()`.
6. On success, `request.state.user_id` and `request.state.user_role` are populated.
7. Admin endpoints additionally check `user_role == "admin"`, returning 403 otherwise.

### Graceful degradation

When `CLERK_DOMAIN` is not set (local development), the middleware logs a warning and passes through all requests. This means the entire auth layer is a no-op in development without any code changes.

### FastAPI dependencies

Three dependency functions are exported for use in router-level protection:

```python
get_current_user(request) -> str          # Returns user_id or raises 401
require_admin(request) -> str             # Returns user_id or raises 403
get_optional_user(request) -> str | None  # Returns user_id or None (no error)
```

### Error responses

| Condition | Status | Body |
|-----------|--------|------|
| Missing Bearer token | 401 | `{"detail":"Authentication required"}` |
| Expired JWT | 401 | `{"detail":"Token expired"}` |
| Invalid JWT signature | 401 | `{"detail":"Invalid authentication token"}` |
| JWKS fetch failure | 503 | `{"detail":"Authentication service unavailable"}` |
| Non-admin on admin endpoint | 403 | `{"detail":"Admin access required"}` |

---

## 2. CORS Hardening

**File**: `backend/src/floridify/api/main.py:93-106`

Before:
```python
allow_headers=["*"]
# No max_age, no explicit exposed headers
```

After:
```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:8080",
    "https://words.babb.dev",
    "https://www.words.babb.dev",
],
allow_credentials=True,
allow_methods=["GET", "POST", "PUT", "DELETE"],
allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Accept", "Cache-Control", "If-None-Match"],
expose_headers=["ETag", "Cache-Control", "X-Process-Time", "X-Request-ID"],
max_age=3600,
```

Changes:
- **`allow_headers`**: Replaced wildcard `*` with explicit allowlist (6 headers).
- **`expose_headers`**: Added 4 headers the frontend needs to read from responses.
- **`max_age=3600`**: Preflight responses cached for 1 hour (reduces OPTIONS requests).
- **`allow_methods`**: Explicit list instead of default.

---

## 3. Middleware Stack Order

**File**: `backend/src/floridify/api/main.py:107-109`

```python
app.add_middleware(CORSMiddleware)        # Outermost - handles preflight
app.add_middleware(CacheHeadersMiddleware) # Add ETag/Cache-Control
app.add_middleware(LoggingMiddleware)      # Log requests with timing
app.add_middleware(ClerkAuthMiddleware)    # Innermost - runs first on request
```

Starlette middleware executes in reverse order on requests, so `ClerkAuthMiddleware` runs first (validates auth), then logging, then cache headers, then CORS wraps the response.

---

## 4. Background TTL Cleanup

**File**: `backend/src/floridify/api/main.py:62-65` (lifespan)

Added a background task that runs every 5 minutes to evict expired L1 cache entries:

```python
cache = await get_global_cache()
cache.start_ttl_cleanup_task(interval_seconds=300.0)
```

Properly shut down on application exit:
```python
await cache.stop_ttl_cleanup_task()
await shutdown_global_cache()
```

---

## 5. SSE Streaming Tests

**File**: `backend/tests/api/test_sse_streaming.py` (462 lines, new)

18 tests covering the full SSE infrastructure without touching the network or MongoDB:

### SSEEvent formatting (3 tests)
- `test_basic_event_format` — validates `event: <type>\ndata: <json>\n\n` format
- `test_event_with_id` — validates `id:` line inclusion
- `test_event_types` — validates config, progress, complete, error event types

### StateTracker event generation (5 tests)
- `test_state_tracker_produces_events` — update_stage emits PipelineState with correct stage and progress
- `test_state_tracker_complete_event` — update_complete sets is_complete=True, progress=100
- `test_state_tracker_error_event` — update_error sets error field and marks complete
- `test_state_tracker_reset` — reset clears state and queue
- `test_multiple_subscribers` — N subscribers each receive all events

### Streaming response (3 tests)
- `test_stream_produces_config_progress_complete` — full event sequence validation
- `test_stream_without_stage_definitions` — config event omitted when disabled
- `test_stream_error_propagation` — process exception becomes SSE error event

### Timeout (1 test)
- `test_stream_timeout_sends_error` — exceeding `SSE_STREAM_TIMEOUT` produces timeout error event (monkey-patches timeout to 300ms)

### Heartbeat (1 test)
- `test_heartbeat_ping_sent_on_idle` — `: ping\n\n` comment sent during idle periods (monkey-patches interval to 300ms)

### PipelineState optimization (4 tests)
- `model_dump_optimized()` excludes redundant fields (message matching stage name, false booleans, empty details)
- Includes details, is_complete, and error only when meaningful

---

## 6. Cache Concurrency Tests

**File**: `backend/tests/caching/test_cache_concurrency.py` (473 lines, new)

14 tests validating thread safety and correctness under concurrent access:

### L1 memory cache (5 tests)
- 20 concurrent writes to same key — final value is one of the written values (no corruption)
- 50 concurrent reads of same key — all return identical data
- 30 concurrent writes to different keys — each key has its own correct value
- Interleaved writes and deletes — no crash, result is value or None
- Namespace isolation — same key in different namespaces holds different values

### VersionedDataManager locking (3 tests)
- **Same-resource serialization**: 5 concurrent saves to `"test_word"` — per-resource lock ensures max 1 concurrent execution, strict start-end ordering verified
- **Different-resource parallelism**: saves to `"apple"`, `"banana"`, `"cherry"` — max concurrent >= 2, total time < 0.2s (not serialized)
- **is_latest invariant**: 5 concurrent saves — exactly 1 version has `is_latest=True` at the end

### @deduplicated decorator (4 tests)
- 5 concurrent calls with same args — only 1 execution, all get same result
- 3 calls with different args — all execute independently
- Error propagation — error from first call propagates to all waiters
- Cleanup — no stale dedup state after completion

### LRU eviction (2 tests)
- Write beyond memory_limit — cache size stays within bounds, evictions > 0
- Stats consistency — hits + misses == total gets under concurrent access

---

## 7. Dark Mode FOUC Prevention

Two bugs caused a flash of light mode on page load in dark mode:

### Bug 1: Wrong localStorage key

**File**: `frontend/index.html:41-48`

The inline script that runs before Vue mounts was reading from the wrong key. Fixed to read from Pinia's persisted `ui-state` key:

```javascript
// Prevent dark mode FOUC - read theme from Pinia persisted ui-state store
(function() {
  try {
    var uiState = JSON.parse(localStorage.getItem('ui-state') || '{}');
    var theme = uiState.theme || 'light';
    document.documentElement.classList.toggle('dark', theme === 'dark');
  } catch(e) {}
})();
```

### Bug 2: Immediate watcher overwriting theme

**File**: `frontend/src/App.vue:29-32`

The theme watcher used `{ immediate: true }`, which ran before Pinia's persistence plugin restored the saved value. Sequence was:

1. Inline script applies `dark` class from localStorage (correct)
2. Vue mounts, Pinia creates store with `DEFAULT_THEME = 'light'`
3. Immediate watcher fires, removes `dark` class (FOUC)
4. Persistence plugin restores `theme = 'dark'` from localStorage
5. Watcher fires again, re-adds `dark` class

Fixed by removing `{ immediate: true }`:

```typescript
// Note: { immediate: true } is intentionally omitted to prevent FOUC.
const ui = useUIStore();
watch(() => ui.resolvedTheme, (theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
});
```

---

## 8. Pinia Readonly Persistence Fix

**Problem**: ~25 Vue warnings per page load: `Set operation on key "X" failed: target is readonly`.

**Root cause**: `pinia-plugin-persistedstate` needs to write to store fields during hydration. Wrapping persisted fields in `readonly()` blocks this.

**Fix**: Removed `readonly()` from all persisted fields across 5 store files. Kept `readonly()` on derived/computed state that should never be externally mutated.

| Store File | Persisted fields (readonly removed) | Non-persisted fields (readonly kept) |
|------------|--------------------------------------|--------------------------------------|
| `stores/ui/ui-state.ts` | theme, sidebarOpen, sidebarCollapsed | resolvedTheme, isDark |
| `stores/search/search-bar.ts` | searchMode, searchSubMode, previousMode, savedQueries, searchQuery, showSearchControls | showDropdown, isFocused, hasErrorAnimation, currentResults, aiSuggestions, processingQueue, searchSelectedIndex, isHovered, isDirectLookup, autocompleteText |
| `stores/search/modes/lookup.ts` | selectedSources, selectedLanguages, noAI, searchMode, selectedCardVariant, pronunciationMode, cursorPosition | isAIQuery, showSparkle, aiSuggestions, results |
| `stores/content/content.ts` | currentWord, sidebarAccordionState | currentEntry, currentThesaurus, definitionError |
| `stores/content/history.ts` | searchHistory, lookupHistory, aiQueryHistory | isLoadingSuggestions |

Console warnings dropped from **39 to 3** per page load (remaining 3 are pre-existing GSAP animation and deprecated meta tag warnings).

---

## 9. Synonyms API Crash Fix

**Problem**: `TypeError: Cannot read properties of undefined (reading 'synonyms')` when switching to thesaurus mode.

### Frontend API layer

**File**: `frontend/src/api/ai.ts:22-46`

Added null-safe property access to handle three response shape variations:

1. Direct response: `response.data.definitions[0].synonyms`
2. Wrapped envelope: `response.data.data.definitions[0].synonyms`
3. Missing/empty: graceful fallback to `{ word, synonyms: [], confidence: 0 }`

### Orchestrator error handling

**File**: `frontend/src/components/custom/search/composables/useSearchOrchestrator.ts:100-115`

Wrapped `getThesaurusData()` in try/catch:

```typescript
const getThesaurusData = async (word: string) => {
    try {
        return await aiApi.synthesize.synonyms(word);
    } catch (error) {
        logger.error('Error fetching synonyms:', error);
        return { word, synonyms: [], confidence: 0, error: error.message };
    }
};
```

---

## 10. HoverCard Attribute Warning Fix

**Problem**: `Extraneous non-props attributes (data-theme) were passed to component but could not be automatically inherited` — 3 warnings per hover card render.

**Root cause**: Radix Vue's `HoverCardPortal` renders a `<Teleport>` root node, which can't auto-inherit non-props attributes like `data-theme`.

**File**: `frontend/src/components/ui/hover-card/HoverCardContent.vue`

Fixed by disabling automatic attribute inheritance and explicitly forwarding attributes:

```vue
<script setup>
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()
</script>

<template>
  <HoverCardPortal>
    <RekaHoverCardContent v-bind="{ ...forwardedProps, ...attrs }">
      <slot />
    </RekaHoverCardContent>
  </HoverCardPortal>
</template>
```

---

## 11. PyJWT Dependency

**File**: `backend/pyproject.toml:58-59`

The auth middleware imports `jwt` (PyJWT) for RS256 validation, but it wasn't listed as a dependency. Added:

```toml
# Authentication
"PyJWT[crypto]>=2.8.0",  # JWT validation for Clerk auth
```

The `[crypto]` extra installs `cryptography` for RSA key support.

---

## Validation

### Playwright (manual browser testing)

| Test | Result |
|------|--------|
| Backend health (`/api/v1/health`) | 200 OK |
| Search autocomplete (semantic + fuzzy) | Results returned |
| Lookup + SSE streaming (full pipeline) | config → progress → complete |
| Dark mode toggle | Toggles correctly |
| Dark mode persistence (hard refresh) | No FOUC |
| Sidebar navigation | Cluster + POS links work |
| Thesaurus mode | Synonyms load without crash |

### Backend test suite

```
712 passed, 6 skipped in 534.51s (8:54)
```

The 6 skips are pre-existing (fixture mock conflicts, missing Oxford/Merriam-Webster API keys, external content storage test).

### Frontend console

```
Before: 39 warnings/errors per page load
After:  3 warnings (pre-existing GSAP + deprecated meta tag)
```

---

## Remaining work (from full audit plan)

The full audit identified 67 issues across 8 workstreams. This implementation covered the foundational items. Remaining work is tracked in the audit plan and includes:

- **Nginx rate limiting** (limit_req_zone, limit_conn_zone)
- **SSE reconnection** with exponential backoff on the frontend
- **Cache stampede prevention** (stale-while-revalidate)
- **Prompt injection sanitization** in AI templates
- **Circuit breaker** for external providers
- **Frontend test suite** (Vitest + @vue/test-utils, currently 0% coverage)
- **Optimistic locking** for concurrent wordlist modification

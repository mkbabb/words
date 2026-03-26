# REST API Reference

A complete endpoint reference for the Floridify Dictionary API, covering authentication, middleware, route map, SSE streaming, error handling, and response caching.

## Table of Contents

1. [Base URL & Versioning](#base-url--versioning)
2. [Authentication](#authentication)
3. [Middleware Stack](#middleware-stack)
4. [Route Map](#route-map)
5. [SSE Streaming](#sse-streaming)
6. [Error Handling](#error-handling)
7. [Response Caching](#response-caching)

---

## Base URL & Versioning

All versioned endpoints are prefixed with `/api/v1`. The API info endpoint at `/api` returns version metadata:

```json
{
  "name": "Floridify Dictionary API",
  "current_version": "v1",
  "versions": {
    "v1": { "status": "stable", "base_url": "/api/v1" }
  }
}
```

Health checks live at `/health` (no version prefix) for compatibility with monitoring tools.

---

## Authentication

### Clerk JWT Validation

Authentication uses [Clerk](https://clerk.com/) JWT tokens. The middleware fetches JWKS from `https://{CLERK_DOMAIN}/.well-known/jwks.json` (cached for 1 hour), verifies the RS256 signature, and extracts the `sub` claim as `clerk_id`. On first login, a `User` document is upserted in MongoDB with profile fields from the JWT claims (`email`, `username`, `image_url`).

### Endpoint Tiers

| Tier | Access | Prefixes / Patterns |
|------|--------|---------------------|
| **1—Public** | No auth required | `GET /api/v1/lookup/*`, `GET /api/v1/search*`, `GET /api/v1/suggestions`, `/health`, `/api`, `GET /api/v1/audio/cache/*`, `POST /api/v1/audio/tts/generate` |
| **2—Authenticated** | Valid JWT required | `/api/v1/users/*`, `/api/v1/wordlists/*`, `POST /api/v1/wordlists/upload` |
| **3—Premium** | `PREMIUM` or `ADMIN` role | `/api/v1/ai/*`, `POST /api/v1/definitions/{id}/regenerate`, `POST /api/v1/examples/{id}/generate` |
| **4—Admin** | `ADMIN` role only | `/api/v1/cache/*`, `/api/v1/config*`, `/api/v1/database/*`, `/api/v1/providers/*`, `/api/v1/corpus/rebuild`, `/api/v1/metrics` |

### Role Model

Three roles are defined in [`models/user.py`](../backend/src/floridify/models/user.py): `USER`, `PREMIUM`, and `ADMIN`. The `CLERK_SUPER_ADMINS` environment variable (comma-separated emails) auto-promotes matching users to `ADMIN` on first login.

### Dev Passthrough

When `CLERK_DOMAIN` is unset and `ENVIRONMENT=development`, the middleware injects a `DevAuthState` granting admin access to all requests. In production without `CLERK_DOMAIN`, non-public endpoints return 503.

### Premium Gating in Lookup

Free users calling `/lookup/{word}` receive `no_ai=True` unless a synthesized entry already exists in the database. This means free users get cached AI synthesis but don't trigger new synthesis. Premium and admin users always get full AI synthesis.

---

## Middleware Stack

Middleware executes from innermost to outermost on the request path, reversed on the response path. Registration order in [`api/main.py`](../backend/src/floridify/api/main.py) determines the execution sequence:

```
Request →  ClerkAuthMiddleware     (innermost—runs first)
       →  RateLimitMiddleware      (tiered: public 60/min, AI 20/min, streaming 10/min, admin 30/min)
       →  LoggingMiddleware        (request ID, timing, X-Process-Time header)
       →  CacheHeadersMiddleware   (ETag, Cache-Control, 304 Not Modified)
       →  CORSMiddleware           (outermost—preflight, allowed origins)
       → Response
```

| Middleware | Responsibility |
|------------|----------------|
| `ClerkAuthMiddleware` | JWT validation, user upsert, tier enforcement, optional auth extraction on public endpoints |
| `RateLimitMiddleware` | Token bucket rate limiting per client (user ID or IP). Skips health checks and OPTIONS |
| `LoggingMiddleware` | Generates `X-Request-ID`, logs method/URL/status/timing, sets `X-Process-Time` header |
| `CacheHeadersMiddleware` | Adds `Cache-Control`, `ETag`, `Vary` headers per endpoint type. Supports `If-None-Match` → 304. Skips `text/event-stream` responses |
| `CORSMiddleware` | Handles preflight, exposes `ETag`/`Cache-Control`/`X-Process-Time`/`X-Request-ID` headers |

---

## Route Map

### Lookup

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/lookup/{word}` | Full word definition lookup with AI synthesis. Query params: `force_refresh`, `providers` (default: `wiktionary`), `languages` (default: `en`), `no_ai` | Public |
| `GET` | `/api/v1/lookup/{word}/stream` | SSE streaming lookup with real-time progress. Same query params as above | Public |
| `GET` | `/api/v1/lookup/{word}/providers` | Raw provider data for a word, grouped by provider | Public |
| `POST` | `/api/v1/lookup/{word}/re-synthesize` | Force re-synthesis from scratch | Admin |
| `POST` | `/api/v1/lookup/{word}/synthesize-from` | Re-synthesize from specific provider version snapshots. Body: `{sources: [{provider, version}], auto_increment}` | Admin |

### Search

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/search?q={query}` | Search by query parameter. Params: `languages`, `max_results` (1-100), `min_score` (0-1), `mode` (smart/exact/fuzzy/semantic), `force_rebuild`, `corpus_id`, `corpus_name`, `semantic` | Public |
| `GET` | `/api/v1/search/{query}` | Search by path parameter. Same params as above | Public |
| `GET` | `/api/v1/search/{query}/suggestions` | Autocomplete suggestions with lower threshold. Additional param: `limit` (1-20, default: 8) | Public |

Modes can be comma-separated (e.g., `mode=exact,fuzzy`) to perform a multi-mode union search.

### Suggestions

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/suggestions` | AI vocabulary suggestions. Params: `words` (seed words, max 10), `count` (4-12) | Public |
| `POST` | `/api/v1/suggestions` | Same as GET, via request body | Public |

### Words & Definitions

**Words** (prefix: `/api/v1/words`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/words` | List words with filtering. Params: `text`, `text_pattern`, `language`, `offensive_flag`, pagination, sorting, field selection | Public |
| `POST` | `/words` | Create word entry | Admin |
| `GET` | `/words/{word_id}` | Get word by ID. Supports `expand=definitions`, field selection, ETag/304 | Public |
| `PUT` | `/words/{word_id}` | Update word with optimistic locking (`version` param) | Admin |
| `DELETE` | `/words/{word_id}` | Delete word. Param: `cascade` (delete related docs) | Admin |

**Definitions** (prefix: `/api/v1/definitions`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/definitions` | List with filtering: `word_id`, `part_of_speech`, `language_register`, `domain`, `cefr_level`, `frequency_band`, `has_examples` | Public |
| `POST` | `/definitions` | Create definition | Admin |
| `GET` | `/definitions/{id}` | Get definition. Supports `expand=examples,images`, field selection, ETag | Public |
| `PUT` | `/definitions/{id}` | Full update with optimistic locking | Admin |
| `PATCH` | `/definitions/{id}` | Partial update. Param: `increment_version` (default: true) | Admin |
| `DELETE` | `/definitions/{id}` | Delete. Param: `cascade` | Admin |
| `POST` | `/definitions/{id}/regenerate` | AI-regenerate components (synonyms, antonyms, examples, cefr_level, frequency_band, register, domain, grammar_patterns, collocations, usage_notes, regional_variants) | Premium |
| `POST` | `/definitions/batch/regenerate` | Batch AI-regenerate across multiple definitions | Premium |

**Version History** (prefix: `/api/v1/words`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/words/{word}/versions` | List all versions of a word's synthesized entry | Public |
| `GET` | `/words/{word}/versions/{version}` | Get specific version content. Param: `hydrate` (resolve IDs to full objects) | Public |
| `GET` | `/words/{word}/diff?from=1.0.0&to=1.0.2` | Diff between two synthesis versions. Param: `hydrate` | Public |
| `POST` | `/words/{word}/rollback?version=1.0.1` | Rollback to a previous version (creates new version, preserves history) | Admin |
| `GET` | `/words/{word}/providers/{provider}/versions` | List versions for a specific provider entry | Public |
| `GET` | `/words/{word}/providers/{provider}/versions/{version}` | Get specific provider version | Public |
| `GET` | `/words/{word}/providers/{provider}/diff?from=...&to=...` | Diff two provider versions | Public |

**Word Enrichment** (prefix: `/api/v1/words`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/words/{word}/synonym-chooser` | Generate MW-style comparative synonym essay | Admin |
| `POST` | `/words/{word}/phrases` | Generate phrases and idioms containing the word | Admin |

**Examples** (prefix: `/api/v1/examples`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/examples/{id}` | Get example by ID | Public |
| `POST` | `/examples/{id}/generate` | AI-generate examples for a definition | Premium |

### Wordlists

**CRUD** (prefix: `/api/v1/wordlists`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/wordlists` | List wordlists with filtering. Params: `name`, `name_pattern`, `owner_id`, `is_public`, `has_tag`, `min_words`, `max_words`, `created_after`, `created_before`, pagination, sorting | Optional |
| `POST` | `/wordlists` | Create wordlist. Body: `{name, description, words, tags, is_public}` | Authenticated |
| `GET` | `/wordlists/generate-name` | Generate random slug name | Public |
| `POST` | `/wordlists/reconcile-preview` | Preview candidate reconciliations before upload. Body: `{entries, limit, min_score}` | Optional |
| `GET` | `/wordlists/{id}` | Get wordlist metadata with mastery distribution | Optional |
| `GET` | `/wordlists/{id}/stats` | Detailed wordlist statistics | Public |
| `PUT` | `/wordlists/{id}` | Update wordlist metadata | Owner/Admin |
| `DELETE` | `/wordlists/{id}` | Delete wordlist | Owner/Admin |
| `POST` | `/wordlists/{id}/clone` | Clone with reset learning stats. Param: `name` | Authenticated |
| `GET` | `/wordlists/{id}/export` | Export as file. Param: `format` (txt/csv/json) | Public |
| `GET` | `/wordlists/{id}/export/anki` | Export as Anki `.apkg` file | Public |
| `POST` | `/wordlists/upload` | Upload wordlist from file (txt/csv/json/tsv). Multipart form: `file`, `name`, `description`, `is_public` | Authenticated |
| `POST` | `/wordlists/upload/stream` | Upload with SSE streaming progress | Authenticated |

**Words** (prefix: `/api/v1/wordlists`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/wordlists/{id}/words` | List words with filtering and sorting. Supports cursor-based and offset pagination. Params: `mastery_levels`, `hot_only`, `due_only`, `min_views`, `max_views`, `reviewed`, `sort_by`, `sort_order`, `cursor` | Public |
| `POST` | `/wordlists/{id}/words` | Add words. Body: `{words: [{source_text, frequency, notes}]}` | Owner/Admin |
| `PATCH` | `/wordlists/{id}/words/{word}` | Update word metadata (notes, tags) | Owner/Admin |
| `DELETE` | `/wordlists/{id}/words/{word}` | Remove a word | Owner/Admin |
| `DELETE` | `/wordlists/{id}/words` | Bulk remove words. Body: `{words: ["word1", "word2"]}` | Owner/Admin |
| `POST` | `/wordlists/{id}/words/{word}/visit` | Mark word as visited/viewed | Owner/Admin |

**Reviews (SM-2 Spaced Repetition)** (prefix: `/api/v1/wordlists`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/wordlists/{id}/review/due` | Get words due for review. Param: `limit` (1-100) | Authenticated |
| `GET` | `/wordlists/{id}/review/session` | Get review session with streak context. Params: `limit` (1-50), `mastery_threshold` (bronze/silver/gold) | Authenticated |
| `POST` | `/wordlists/{id}/review` | Submit single review. Body: `{word, quality}` (quality: 0-5 per SM-2) | Authenticated |
| `POST` | `/wordlists/{id}/review/bulk` | Submit multiple reviews. Body: `{reviews: [{word, quality}]}` | Authenticated |
| `POST` | `/wordlists/{id}/review/study-session` | Record study session. Body: `{duration_minutes, words_studied, words_mastered}` | Authenticated |
| `GET` | `/wordlists/{id}/review/leeches` | List leech items (words with high lapse count) | Authenticated |
| `POST` | `/wordlists/{id}/review/leeches/{word}/suspend` | Suspend a leech from reviews | Authenticated |
| `POST` | `/wordlists/{id}/review/leeches/{word}/unsuspend` | Re-enable a suspended leech | Authenticated |

**Wordlist Search** (prefix: `/api/v1/wordlists`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/wordlists/search-all` | Search words across all user wordlists. Params: `query`, `max_results`, `min_score`, `mode`, `offset`, `limit` | Optional |
| `POST` | `/wordlists/{id}/search` | Search within a specific wordlist with full filtering and sorting. Params: `query`, `max_results`, `min_score`, `mode`, `mastery_levels`, `hot_only`, `due_only`, `sort_by`, `sort_order` | Public |
| `GET` | `/wordlists/search/{query}` | Search wordlists by name (fuzzy). Param: `limit` | Public |

### AI

**Generation** (prefix: `/api/v1/ai`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/ai/suggestions` | AI vocabulary suggestions. Body: `{input_words, count}` | Premium |
| `POST` | `/ai/validate-query` | Validate if query seeks word suggestions. Body: `{query}` | Premium |
| `POST` | `/ai/suggest-words` | Generate word suggestions from descriptive query. Body: `{query, count}` | Premium |
| `GET` | `/ai/suggest-words/stream` | SSE streaming word suggestions. Params: `query`, `count` (1-25) | Premium |
| `POST` | `/ai/synthesize` | Regenerate specific components of a synthesized entry. Body: `{entry_id, components}` | Premium |
| `POST` | `/ai/resynthesize` | Re-synthesize from existing provider data. Body: `{word, languages}` | Premium |
| `POST` | `/ai/synthesize/pronunciation` | AI-generate phonetic pronunciation. Body: `{word}` | Premium |
| `POST` | `/ai/synthesize/synonyms` | AI-generate contextual synonyms. Body: `{word, definition, part_of_speech, existing_synonyms, count}` | Premium |
| `POST` | `/ai/synthesize/antonyms` | AI-generate contextual antonyms. Body: `{word, definition, part_of_speech, existing_antonyms, count}` | Premium |
| `POST` | `/ai/generate/examples` | AI-generate example sentences. Body: `{word, part_of_speech, definition, count}` | Premium |
| `POST` | `/ai/generate/facts` | AI-generate word facts. Body: `{word, definition, count, previous_words}` | Premium |
| `POST` | `/ai/generate/word-forms` | AI-identify morphological forms. Body: `{word, part_of_speech}` | Premium |
| `POST` | `/ai/usage-notes` | Generate usage notes. Body: `{word, definition}` | Premium |

**Assessment** (prefix: `/api/v1/ai`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/ai/assess/frequency` | Assess word frequency band (1-5). Body: `{word, definition}` | Premium |
| `POST` | `/ai/assess/cefr` | Assess CEFR difficulty level (A1-C2). Body: `{word, definition}` | Premium |
| `POST` | `/ai/assess/register` | Classify language register (formal/informal/neutral/slang/technical). Body: `{definition}` | Premium |
| `POST` | `/ai/assess/domain` | Identify subject domain. Body: `{definition}` | Premium |
| `POST` | `/ai/assess/collocations` | Identify collocations. Body: `{word, definition, part_of_speech}` | Premium |
| `POST` | `/ai/assess/grammar-patterns` | Extract grammar patterns. Body: `{definition, part_of_speech}` | Premium |
| `POST` | `/ai/assess/regional-variants` | Detect regional variants. Body: `{definition}` | Premium |

All AI endpoints are rate-limited via the `OpenAIRateLimiter` (50 requests/min, 150K tokens/min, 10K requests/day per client).

### Audio & Images

**Audio** (prefix: `/api/v1/audio`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/audio/tts/generate` | Generate TTS audio. Body: `{word, accent, voice_gender, language}`. Checks MongoDB cache first, generates via KittenTTS/Kokoro-ONNX if missing | Public |
| `GET` | `/audio` | List audio files with filtering (format, accent, quality, duration range) and pagination | Public |
| `POST` | `/audio` | Upload audio file (multipart, max 50MB) | Public |
| `GET` | `/audio/{id}` | Get audio metadata | Public |
| `GET` | `/audio/{id}/content` | Stream audio file content | Public |
| `PUT` | `/audio/{id}` | Update audio metadata. Supports optimistic locking via `version` param | Public |
| `DELETE` | `/audio/{id}` | Delete audio file (DB entry + disk file if in uploads/) | Public |
| `GET` | `/audio/cache/{subdir}/{filename}` | Serve cached TTS audio file by path | Public |

**Images** (prefix: `/api/v1/images`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/images` | List images with filtering (format, dimensions, alt text) and pagination | Public |
| `POST` | `/images` | Upload image (multipart, max 10MB). Extracts dimensions via Pillow | Public |
| `POST` | `/images/upload/stream` | Upload image with SSE streaming progress | Public |
| `GET` | `/images/{id}` | Get image metadata (JSON) or content (binary) based on `Accept` header | Public |
| `GET` | `/images/{id}/content` | Serve image binary content | Public |
| `PUT` | `/images/{id}` | Update image metadata (alt_text, description). Optimistic locking via `version` | Public |
| `DELETE` | `/images/{id}` | Delete image | Public |

### Users

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/users/me` | Get current user profile | Authenticated |
| `PATCH` | `/api/v1/users/me` | Update profile (username, avatar_url) | Authenticated |
| `GET` | `/api/v1/users/me/preferences` | Get user preferences | Authenticated |
| `PUT` | `/api/v1/users/me/preferences` | Set preferences (full replacement). Body: `{preferences: {...}}` | Authenticated |
| `GET` | `/api/v1/users/me/history` | Get search and lookup history | Authenticated |
| `POST` | `/api/v1/users/me/history/sync` | Merge frontend history with backend. Deduplicates by timestamp, caps at 100 entries per category | Authenticated |
| `GET` | `/api/v1/users/me/learning-stats` | Get global learning stats and per-wordlist breakdown | Authenticated |
| `GET` | `/api/v1/users` | List all users. Params: `skip`, `limit` | Admin |
| `PATCH` | `/api/v1/users/{clerk_id}/role` | Change user role. Body: `{role: "USER"|"PREMIUM"|"ADMIN"}` | Admin |

### Corpus

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/corpus` | List corpora with filtering. Params: `language`, `source_type` (custom/language/literature/wordlist), `include_stats`, `offset`, `limit` | Public |
| `GET` | `/api/v1/corpus/stats` | Get corpus cache statistics | Public |
| `GET` | `/api/v1/corpus/{id}` | Get corpus by ID with optional stats | Public |
| `POST` | `/api/v1/corpus` | Create corpus. Body: `{name, vocabulary, language, source_type, enable_semantic, ttl_hours, description}` | Public |
| `PATCH` | `/api/v1/corpus/{id}/semantic` | Set semantic search policy. Body: `{enabled, model_name}` | Public |
| `POST` | `/api/v1/corpus/{id}/search` | Search within corpus. Params: `query`, `max_results`, `min_score` | Public |
| `DELETE` | `/api/v1/corpus/{id}` | Delete corpus. Param: `cascade` (delete children) | Public |
| `POST` | `/api/v1/corpus/{id}/rebuild` | Rebuild corpus and search indices. Body: `{re_aggregate, rebuild_search, components}` | Admin |

### Cache (Admin)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/cache/stats` | Cache statistics by namespace. Params: `namespace`, `include_hit_rate`, `include_size` | Admin |
| `POST` | `/api/v1/cache/clear` | Clear cache entries. Body: `{namespace, dry_run}` | Admin |
| `POST` | `/api/v1/cache/prune` | Prune old versions. Body: `{max_age_days, keep_minimum, dry_run}` | Admin |
| `GET` | `/api/v1/cache/disk-usage` | L2 disk cache consumption (bytes, item count, hit/miss stats) | Admin |
| `POST` | `/api/v1/cache/gridfs/cleanup` | Clean stale GridFS files. Body: `{corpus_uuid, dry_run}` | Admin |

### Database (Admin)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/database/stats` | Database statistics (word/definition/entry counts, provider coverage, quality metrics, storage size). Params: `detailed`, `include_provider_coverage`, `include_storage_size` | Admin |
| `GET` | `/api/v1/database/health` | Database connection health check | Admin |

### Config (Admin)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/config` | Read configuration (API keys masked). Param: `section` | Admin |
| `GET` | `/api/v1/config/{key}` | Read specific config value | Admin |

Write operations (set, edit, reset) are restricted to the CLI for security.

### Providers (Admin)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/providers/status` | All provider statuses with rate limits and cache stats. Params: `include_rate_limits`, `include_cache_stats` | Admin |
| `GET` | `/api/v1/providers/{provider}/status` | Specific provider status | Admin |
| `GET` | `/api/v1/providers/circuit-status` | Circuit breaker state for all providers (closed/open/half-open, failure counts) | Admin |

### Health

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Service health: database, search engine, cache status, uptime, connection pool stats | Public |
| `GET` | `/api/v1/metrics` | Operational metrics: uptime, cache hit rate, L1 stats | Admin |

---

## SSE Streaming

Streaming endpoints return `Content-Type: text/event-stream` with real-time progress updates, implemented in [`core/streaming.py`](../backend/src/floridify/core/streaming.py).

### Protocol

Clients connect via standard GET/POST. The server emits [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) formatted per the SSE specification:

```
event: progress
data: {"stage": "PROVIDER_FETCH_START", "progress": 40, "message": "Fetching from wiktionary..."}

event: complete
data: {"type": "complete", "message": "Process completed successfully", "result": {...}}
```

### Event Types

| Event | When | Payload |
|-------|------|---------|
| `config` | First event | `{category, stages}`—stage definitions for progress visualization |
| `progress` | During processing | `{stage, progress, message, elapsed_ms}`—pipeline stage updates |
| `completion_start` | Large results | `{message, total_definitions}`—signals chunked delivery |
| `completion_chunk` | Large results | `{chunk_type, data}`—incremental definition/example data |
| `complete` | On success | `{type: "complete", message, result}`—final result with full entry data |
| `error` | On failure | `{type: "error", message}`—error description |

### Streaming Endpoints

- `GET /api/v1/lookup/{word}/stream`—word lookup with progress
- `GET /api/v1/ai/suggest-words/stream`—word suggestions with progress
- `POST /api/v1/wordlists/upload/stream`—file upload with progress
- `POST /api/v1/images/upload/stream`—image upload with progress

### Connection Management

- **Heartbeat:** `: ping\n\n` sent every 30 seconds to keep proxies alive
- **Timeout:** 5-minute overall stream timeout, after which the background task is cancelled and an error event is sent
- **Client disconnect:** `GeneratorExit` triggers `task.cancel()` on the background process, ensuring clean resource cleanup
- **Chunked completion:** Responses exceeding ~32KB are split—basic info first, then definitions, then examples in batches of 10
- **Nginx:** `X-Accel-Buffering: no` header disables nginx response buffering. Production nginx config uses `proxy_buffering off` on stream routes

---

## Error Handling

### Exception Hierarchy

The API uses structured exceptions defined in [`api/core/exceptions.py`](../backend/src/floridify/api/core/exceptions.py), with exception handlers registered in [`middleware/exception_handlers.py`](../backend/src/floridify/api/middleware/exception_handlers.py) that map exceptions to HTTP responses.

### Response Format

Error responses follow a consistent structure:

```json
{
  "error": "Word not found",
  "details": [
    {
      "field": "word",
      "message": "No definition found for word: xyzzy",
      "code": "not_found"
    }
  ]
}
```

### HTTP Status Code Mapping

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 400 | Bad Request | Invalid input, malformed word, unsupported provider |
| 401 | Unauthorized | Missing or expired JWT token |
| 403 | Forbidden | Insufficient role (e.g., USER accessing admin endpoint) |
| 404 | Not Found | Word, wordlist, corpus, or version not found |
| 409 | Conflict | Duplicate word, version conflict (optimistic locking), semantic search disabled |
| 413 | Payload Too Large | File upload exceeds limit (10MB images, 50MB audio) |
| 422 | Unprocessable Entity | Validation error (empty query, version has no content) |
| 429 | Too Many Requests | Rate limit exceeded. Check `Retry-After` and `X-RateLimit-*` headers |
| 500 | Internal Server Error | Provider failure, AI synthesis error, database error |
| 501 | Not Implemented | Missing optional dependency (e.g., `genanki` for Anki export) |
| 503 | Service Unavailable | Auth service not configured, user persistence unavailable |

---

## Response Caching

The `CacheHeadersMiddleware` adds HTTP cache headers for successful (200) responses based on endpoint path. SSE streams (`text/event-stream`) are excluded from caching entirely.

| Endpoint Pattern | `Cache-Control` | TTL |
|------------------|-----------------|-----|
| `/api/v1/search*` | `public, max-age=3600` | 1 hour |
| `/api/v1/lookup*` | `public, max-age=1800` | 30 minutes |
| `/api/v1/suggestions*` | `public, max-age=7200` | 2 hours |
| `/api/v1/synonyms*` | `public, max-age=21600` | 6 hours |
| `/health` | `no-cache, no-store, must-revalidate` | None |
| All other endpoints | `public, max-age=300` | 5 minutes |

All cacheable responses include an `ETag` header (MD5 of path + query params). When a client sends `If-None-Match` matching the current `ETag`, the middleware returns `304 Not Modified` with no body, and responses include `Vary: Accept-Encoding` to ensure CDNs cache correctly by encoding.

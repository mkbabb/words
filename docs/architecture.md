# System Architecture

Floridify separates raw dictionary data from synthesized entries: multiple dictionary providers feed into an AI synthesis pipeline that deduplicates, clusters, and enhances definitions, and the synthesized entries are stored with full version history via SHA-256 content-addressable chains.

## Service Topology

Four services communicate over a Docker bridge network (`app-network`), each serving a distinct role:

| Service | Runtime | Host Port | Container Port | Role |
|---------|---------|-----------|----------------|------|
| **backend** | FastAPI (Python 3.12, UV) | 8003 | 8000 | REST API, AI synthesis, search |
| **frontend** | Vue 3.5 (Vite dev / nginx prod) | 3004 | 3004 | SPA, SSE streaming |
| **notification-server** | Express (Node 20) | 3001 | 3001 | PWA push notifications |
| **MongoDB** | Remote hosted instance |—| 27017 | Single database (`floridify`) |

There's no local MongoDB container—all services connect to the same remote instance at `mbabb.friday.institute:27017`. In development, an SSH tunnel forwards a local port (default 37117) to the remote MongoDB, and Docker containers reach it via `host.docker.internal`. The notification server depends on the backend and only starts with the `dev` profile.

Frontend talks to backend via the Docker network in dev (`http://backend:8000`) and via nginx reverse proxy in production (`https://mbabb.friday.institute/words/api`).

## Module Dependency Graph

The backend's 17 modules are layered to prevent circular imports. Higher layers depend on lower ones; arrows point downward.

```
                          ┌─────┐
                          │ api │  ← routers, middleware, repositories
                          └──┬──┘
                             │
                          ┌──┴──┐
                          │core │  ← lookup_pipeline, search_pipeline, streaming
                          └──┬──┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
           ┌──┴──┐       ┌──┴──┐       ┌───┴────┐
           │ ai  │       │search│      │providers│
           └──┬──┘       └──┬──┘       └───┬────┘
              │              │              │
    ┌─────────┼──────────────┼──────────────┤
    │         │              │              │
┌───┴────┐ ┌──┴───┐  ┌──────┴──┐  ┌───────┴──┐
│caching │ │corpus│  │ models  │  │  storage  │
└────────┘ └──────┘  └─────────┘  └──────────┘
                          │
                  ┌───────┼───────┐
                  │       │       │
              ┌───┴──┐ ┌─┴──┐ ┌──┴───┐
              │ text │ │utils│ │audio │
              └──────┘ └────┘ └──────┘
```

Ancillary modules—`wordlist`, `anki`, `wotd`, `cli`—compose from the middle layers but aren't depended on by the core path.

## Application Lifecycle

The FastAPI app uses an async context manager ([`api/main.py`](../backend/src/floridify/api/main.py)) to coordinate startup and shutdown.

**Startup sequence:**

1. **MongoDB init**—`get_storage()` connects via Motor, registers 24 Beanie document models, warms the connection pool (10 min connections).
2. **AI connector**—`get_ai_connector()` singleton; validates OpenAI API key and model availability.
3. **Definition synthesizer**—`get_definition_synthesizer()` singleton; wires AI connector to the synthesis pipeline.
4. **Cache TTL cleanup**—`cache.start_ttl_cleanup_task(interval_seconds=60.0)` runs an `asyncio.Task` that evicts expired L1 entries every 60 seconds across all 14 namespaces.
5. **TTS backends**—Registered but not loaded; KittenTTS and Kokoro-ONNX initialize lazily on first audio request.
6. **Search engine**—`manager.start_background_init()` spawns a non-blocking task that builds marisa-trie, BK-tree, suffix array, and FAISS indices from the current corpus. The API serves requests immediately; search becomes available once the task completes.

**Shutdown sequence:**

1. Stop the TTL cleanup task.
2. Flush and shut down the `GlobalCacheManager` (persists L2 disk state).
3. Motor connection pool is released by the runtime.

## Request Lifecycle

### Middleware Stack

FastAPI processes middleware in registration order, but execution is onion-layered: the middleware registered *last* runs *first* on the request (innermost). The stack in [`api/main.py`](../backend/src/floridify/api/main.py):

```
Request → ClerkAuth → RateLimit → Logging → CacheHeaders → CORS → Router
                                                                      │
Response ← ClerkAuth ← RateLimit ← Logging ← CacheHeaders ← CORS ←──┘
```

| Layer | Responsibility |
|-------|---------------|
| **CORS** | Origin whitelist (localhost dev ports + production domain), credential support, 1h preflight cache |
| **CacheHeaders** | ETag generation (MD5 of path+query), `Cache-Control` per endpoint type, 304 Not Modified. Skips `text/event-stream` responses to avoid buffering SSE |
| **Logging** | UUID request ID, method/URL/IP logging, `X-Process-Time` header (ms) |
| **RateLimit** | Tiered token-bucket limiting (see [Security](#security)) |
| **ClerkAuth** | JWT validation, user upsert, role-based endpoint gating (see [Security](#security)) |

### Path Through the Pipeline

A typical lookup request: `GET /api/v1/lookup/perspicacious/stream`

1. ClerkAuth classifies the path as public (Tier 1), optionally extracts the user from a Bearer token if present.
2. RateLimit checks the `public` tier bucket (60 req/min, 1000 req/hr) keyed by user ID or client IP.
3. The lookup router delegates to `LookupPipeline`, which runs the five-stage pipeline (see [Lookup Pipeline](#lookup-pipeline-corelookup_pipelinepy)).
4. For `/stream` endpoints, `create_streaming_response()` wraps the pipeline in an SSE generator with 30-second heartbeat pings, 5-minute timeout, and chunked delivery for large payloads. Client disconnect cancels the background task.
5. CacheHeaders adds `Cache-Control: public, max-age=1800` and an ETag on the way out.

## Data Models

The data layer uses Beanie ODM documents with `PydanticObjectId` foreign keys throughout, avoiding embedded subdocuments for entities that need independent access.

### Word (`models/dictionary.py`)

```python
class Word(Document, BaseMetadata):
    text: str
    normalized: str  # auto-computed via normalize_basic()
    lemma: str       # auto-computed via lemmatize_comprehensive()
    language: Language
    homograph_number: int | None
```

`Word.__init__()` auto-populates `normalized` and `lemma` on creation. Indices on `(text, language)`, `normalized`, `lemma`, and `(text, homograph_number)`.

### Definition (`models/dictionary.py`)

```python
class Definition(Document, BaseMetadata):
    word_id: PydanticObjectId
    part_of_speech: str
    text: str
    meaning_cluster: MeaningCluster | None
    synonyms: list[str]          # max 50
    antonyms: list[str]          # max 50
    example_ids: list[PydanticObjectId]  # max 20, FK to Example
    cefr_level: Literal["A1"..."C2"] | None
    frequency_band: int | None   # 1-5, Oxford 3000/5000 style
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None
    domain: str | None
    region: str | None
    usage_notes: list[UsageNote]
    grammar_patterns: list[GrammarPattern]
    collocations: list[Collocation]
    transitivity: Literal["transitive", "intransitive", "both"] | None
    word_forms: list[WordForm]
    providers: list[DictionaryProvider]
    model_info: ModelInfo | None
```

`meaning_cluster` drives the grouping that produces superscripted homographs (bank^1, bank^2) in the frontend. Each cluster has an `id`, `name`, `description`, `order`, and `relevance` score.

### DictionaryEntry (`models/dictionary.py`)

```python
class DictionaryEntry(Document, BaseMetadata):
    word_id: PydanticObjectId
    definition_ids: list[PydanticObjectId]  # max 100
    pronunciation_id: PydanticObjectId | None
    fact_ids: list[PydanticObjectId]
    image_ids: list[PydanticObjectId]
    provider: DictionaryProvider
    etymology: Etymology | None
    model_info: ModelInfo | None
```

One `DictionaryEntry` per provider per word. The synthesized entry uses `provider=DictionaryProvider.SYNTHESIS`. Indices on `word_id`, `provider`, and `(word_id, provider)`.

### Supporting Documents

**Pronunciation**: Stores phonetic text, IPA transcription, audio file references, syllables, and stress pattern, with a foreign key to Word.

**Example**: Holds the example text, a type discriminator (`"generated"` or `"literature"`), and an optional literature source with `text_pos`. Foreign key to Definition.

**Fact**: Contains the fact content and a category (`etymology`, `usage`, `cultural`, `linguistic`, `historical`), with a foreign key to Word.

**MeaningCluster** (embedded, not a Document): Groups related definitions under an `id`, `name`, `description`, `order`, and `relevance` score.

## Providers

Seven dictionary providers are available, each instantiated via the `create_connector()` factory (`providers/factory.py`):

| Provider | Type | Notes |
|----------|------|-------|
| Wiktionary | Scraper (MediaWiki API + HTML) | Default, no auth |
| Wiktionary Wholesale | Bulk scraper (full dump) | Offline corpus building |
| Apple Dictionary | Local (macOS pyobjc) | Auto-added on Darwin |
| Oxford | API | Requires `app_id` + `api_key` |
| Merriam-Webster | API | Requires `api_key` |
| Free Dictionary | API | No auth |
| WordHippo | Scraper | No auth |

Two virtual providers complement these: `AI_FALLBACK` (generated when all real providers fail) and `SYNTHESIS` (the merged output of the AI pipeline).

Rate limiting is handled by `AdaptiveRateLimiter` (`providers/rate_limiting.py`), which applies exponential backoff on errors, speeds up after consecutive successes, and respects `Retry-After` headers.

## Lookup Pipeline (`core/lookup_pipeline.py`)

The lookup runs through five stages, all async:

```
Query → Search → Cache Check → Provider Fetch → AI Synthesis → Store
```

**1. Search** (`find_best_match`): Normalizes the query via the multi-method search cascade (exact, fuzzy, semantic). If no corpus match, proceeds with the raw query.

**2. Cache Check**: Calls `get_synthesized_entry(word)`. On hit, returns immediately. Skipped when `force_refresh=True`, but the existing entry is preserved in version history.

**3. Provider Fetch**: `asyncio.gather` across all providers, each with a 30-second `asyncio.wait_for` timeout. Results filtered for exceptions and `None`. If every provider fails, falls through to AI fallback (`_ai_fallback_lookup`).

**4. AI Synthesis** (when `no_ai=False`): Passes provider `DictionaryEntry` list to `DefinitionSynthesizer.synthesize_entry()`. Details in the next section.

**5. No-AI Mode** (when `no_ai=True`): `_create_provider_mapped_entry` uses AI only for deduplication and clustering—no content generation. Takes the first provider's data, deduplicates definitions, clusters them, saves the result.

The default providers are Wiktionary and Apple Dictionary (on macOS).

## AI Synthesis Pipeline (`ai/synthesizer.py`)

`DefinitionSynthesizer.synthesize_entry()` runs the full pipeline:

**Dedup**: Batch-loads all definitions from all providers via `Definition.find({"_id": {"$in": all_def_ids}})`, then calls `ai.deduplicate_definitions()` to identify near-duplicates. New `Definition` copies are created with merged text (originals aren't mutated), typically reducing the definition count by ~50%.

**Cluster**: `cluster_definitions()` groups deduplicated definitions into semantic clusters via AI, assigning each definition a `MeaningCluster`.

**Parallel Synthesis**: Four tasks via `asyncio.gather` with `return_exceptions=True`:

1. `_synthesize_definitions`—groups by cluster, synthesizes one definition per cluster
2. `synthesize_pronunciation`—enhances existing or creates new
3. `synthesize_etymology`—from provider data + AI
4. `generate_facts`—interesting facts about the word

Definitions are the only required output; pronunciation, etymology, and facts degrade gracefully on failure.

**Enhancement**: After the entry is saved, `enhance_definitions_parallel()` runs up to 11 sub-tasks per definition—synonyms, examples, antonyms, word forms, CEFR level, frequency band, register, domain, grammar patterns, collocations, usage notes, and regional variants.

**Versioned Save**: `_save_entry_with_version_manager()` stores the entry both in the `VersionedDataManager` chain (for history) and as a live `DictionaryEntry` document (for current state), with per-resource locks preventing races from concurrent force-refresh calls.

See [docs/synthesis.md](synthesis.md) for the full treatment of AI synthesis, prompt templates, and enhancement components.

## 3-Tier Model Selection (`ai/model_selection.py`)

All three tiers use the GPT-5 series, with task complexity determining which model handles each request:

| Tier | Model | Tasks |
|------|-------|-------|
| HIGH | gpt-5.4 | Definition synthesis, clustering, suggestions, synthetic corpus, literature analysis |
| MEDIUM | gpt-5-mini | Synonyms, examples, dedup, etymology, Anki cards, collocations, word forms, antonyms |
| LOW | gpt-5-nano | CEFR, frequency, register, domain, pronunciation, usage notes, grammar patterns |

Temperature is routed by task category: reasoning models get `None` (model decides), creative tasks (facts, examples, suggestions) get 0.8, classification tasks (CEFR, frequency, register) get 0.3, and everything else defaults to 0.7.

The `AIConnector` supports both OpenAI (GPT-5 series) and Anthropic (Claude) via a unified interface. Default model is `gpt-5-nano` (`ai/connector/`). `get_model_for_task()` overrides per call.

## Search ([`search/engine.py`](../backend/src/floridify/search/engine.py))

Five methods cascade in SMART mode, with early termination when results are sufficient:

| Method | Time | Implementation |
|--------|------|----------------|
| Exact | <1ms | marisa-trie + Bloom filter, O(m) |
| Prefix | <1ms | marisa-trie `keys()` with frequency ranking |
| Substring | 1-5ms | Suffix array (pydivsufsort), O(m log n) |
| Fuzzy | 10-50ms | BK-tree (Damerau-Levenshtein) + phonetic (ICU + Metaphone) + trigram overlap |
| Semantic | 50-200ms | FAISS HNSW, Qwen3-0.6B embeddings (1024D → 512D Matryoshka) |

Exact and prefix always run first since they're cheap and essential for autocomplete. Substring engages for queries of 3+ characters, and fuzzy always runs. If fuzzy returns fewer than 33% high-quality results (score >= 0.7), semantic search kicks in. An exact match terminates the cascade immediately.

FAISS index type scales with corpus size—Flat L2 for <10K words up to OPQ+IVF-PQ for >200K. `SearchEngineManager` ([`core/search_pipeline.py`](../backend/src/floridify/core/search_pipeline.py)) hot-reloads indices by polling `vocabulary_hash` every 30 seconds, then atomic-swapping the engine. See [docs/search.md](search.md) for the full treatment.

## Caching (`caching/`)

The caching system operates across three tiers:

**L1 Memory** (`core.py`): Per-namespace `OrderedDict` LRU with O(1) get/set/evict via `move_to_end()`, hitting in ~0.2ms. Each of the 14 namespaces has independent limits (50-500 entries) and TTLs (1h-30d).

**L2 Disk** (`filesystem.py`): A DiskCache backend with a 10GB limit, per-namespace TTL, and optional compression (ZSTD, LZ4, GZIP), hitting in ~5ms.

**L3 Versioned MongoDB** (`manager.py`): Content-addressable via SHA-256 hashing, so identical content reuses existing versions. History is tracked through `supersedes`/`superseded_by` chains, with inline storage for payloads under 16KB and GridFS for larger ones. Per-resource locking prevents concurrent write conflicts.

See [docs/versioning.md](versioning.md) for version chain mechanics, delta compression, and corruption recovery.

## Storage Layer (`storage/mongodb.py`)

The storage layer uses a single MongoDB database accessed through Motor (async driver) and Beanie ODM. The `MongoDBStorage` class manages connection lifecycle and document model registration.

### Connection Pool

```python
connection_kwargs = {
    "maxPoolSize": 50,           # Max concurrent connections
    "minPoolSize": 10,           # Warm connections maintained
    "maxIdleTimeMS": 30_000,     # Close idle connections after 30s
    "serverSelectionTimeoutMS": 3_000,  # Fast failover (3s)
    "socketTimeoutMS": 20_000,   # Socket timeout (20s)
    "connectTimeoutMS": 10_000,  # Connection timeout (10s)
    "retryWrites": True,         # Retryable writes enabled
    "waitQueueTimeoutMS": 5_000, # Queue timeout for pool exhaustion
}
```

### TLS Handling

TLS policy follows a precedence chain: URI query parameters (`?tls=true`) override the config file's `runtime_tls_required` flag. CA certificate is loaded from `auth/mongodb-ca.pem` (or legacy `auth/rds-ca-2019-root.pem`). Tunnel URLs (localhost) typically disable TLS since the SSH tunnel provides encryption.

### Document Model Registration

24 document models are registered with Beanie at init via `init_beanie()`. This includes core models (Word, Definition, Example, Fact, Pronunciation), media (AudioMedia, ImageMedia), user models (User, UserHistory), versioning (BaseVersionedData plus 6 Metadata subclasses for polymorphic deserialization), search indices (SearchIndex, TrieIndex, SemanticIndex), and operational models (WordList, WordListItemDoc, DictionaryEntry, BatchOperation).

### Health & Reconnection

`ensure_healthy_connection()` pings the database and retries up to 3 times with fresh connections on failure. The storage singleton (`get_storage()`) is initialized lazily on first access.

Collections: `words`, `definitions`, `dictionary_entries`, `pronunciations`, `examples`, `facts`, `word_relationships`, `search_indices`, `trie_indices`, `semantic_indices`, `word_lists`, `corpora`, `language_corpora`, `literature_corpora`, plus versioned data and cache collections.

## Configuration (`utils/config.py`)

The `Config` singleton loads from `auth/config.toml` (not in git) and is implemented as a frozen Pydantic model with strict validation.

### Config Sections

| Section | Key Fields | Notes |
|---------|-----------|-------|
| `[openai]` | `api_key`, `model`, `embedding_model` | Required. Default model: `gpt-5-mini` |
| `[anthropic]` | `api_key`, `model`, `max_tokens` | Optional. Default: `claude-sonnet-4-6` |
| `[database]` | `runtime_url`, `test_url`, `runtime_tls_required`, `tunnel_url`, `tunnel_test_url` | Required (first three). Legacy keys rejected |
| `[oxford]` | `app_id`, `api_key` | Optional |
| `[merriam_webster]` | `api_key` | Optional |
| `[rate_limits]` | `oxford_rps`, `wiktionary_rps`, `openai_bulk_max_concurrent` | Defaults: 10, 50, 5 |
| `[processing]` | `max_concurrent_words`, `batch_size`, `retry_attempts` | Defaults: 100, 50, 3 |
| `[semantic_search]` | `use_hnsw`, `hnsw_m`, `hnsw_ef_construction`, `hnsw_ef_search` | Optional HNSW tuning |
| `[ai]` | `provider`, `effort`, `max_concurrent_requests` | Optional global AI config |

### Environment Variable Overrides

| Variable | Effect |
|----------|--------|
| `MONGODB_URL` | Overrides `runtime_url` entirely (used by Docker) |
| `FLORIDIFY_CONFIG_PATH` | Custom config file location |
| `FLORIDIFY_DB_TARGET` | `"runtime"` (default) or `"test"` |
| `MONGO_TUNNEL_PORT` | Set by `dev.sh`; rewrites tunnel URL port |
| `ENVIRONMENT` | `"development"` or `"production"`; gates local-host validation |

### Database URL Resolution

URL priority for `runtime` target: `MONGODB_URL` env var > tunnel URL (outside Docker) > config file `runtime_url`. Tunnel URLs have their port dynamically resolved—first from `MONGO_TUNNEL_PORT` env var, then by detecting the running SSH tunnel process via `lsof` + `ps`. The `_in_docker()` check (`/.dockerenv` existence) prevents tunnel URLs from being used inside containers, where `MONGODB_URL` with `host.docker.internal` takes over.

## Docker Topology

### Development Compose

Three services run on the `app-network` bridge, with no local MongoDB:

- **backend**: Multi-stage Dockerfile (base → uv-installer → dependencies → development/production). Source mounted at `/app/src` for hot-reload. `auth/` mounted read-only. Threading vars set for Docker's Linux environment (`OMP_NUM_THREADS=4`).
- **frontend**: Multi-stage Dockerfile (base → dependencies → dev-dependencies → development → build → production). Source, config, and public assets mounted for Vite hot-reload. `node_modules` excluded via anonymous volume.
- **notification-server**: Express app, `dev` profile only. Source mounted for `npm run dev`. Health check via `/health` endpoint every 30 seconds.

All three containers use `extra_hosts` or Docker network DNS to reach the SSH tunnel on the host. The backend publishes to host port 8003, frontend to 3004, notifications to 3001.

### Production Compose

`docker-compose.prod.yml` overlays the base config:

- Adds an **nginx** reverse proxy container with SSL termination, HSTS, rate limiting for SSE (`proxy_buffering off`), and path-based routing (`/words/api` → backend, `/words/` → frontend).
- Backend targets the `production` build stage. Frontend builds static assets and serves via nginx.
- There are no volume mounts---images are self-contained.

### Multi-Stage Dockerfiles

**Backend** (4 stages): `base` (Python 3.12-slim + ffmpeg + espeak-ng + libicu), `uv-installer` (UV binary), `dependencies` (compile native extensions), `development`/`production` (final layer).

**Frontend** (6 stages): `base` (Node 20-alpine), `dependencies` (production npm), `dev-dependencies` (full npm), `development` (Vite dev server), `build` (Vue + Vite production build), `production` (nginx with built assets).

## Deployment

### Production (`scripts/deploy.sh`)

```
Local machine                          Remote server
──────────────                         ──────────────
1. Verify SSH                ────SSH──→ mbabb@mbabb.fridayinstitute.net:1022
2. Sync secrets              ────SCP──→ auth/config.toml, .env.production → .env
3.                                      git pull origin master
4.                                      docker compose -f ... -f ...prod.yml build
5.                                      docker compose ... up -d
6. Health check              ────HTTP─→ https://mbabb.friday.institute/words/health
```

The deployment requires two local files: `auth/config.toml` (API keys and DB config) and `.env.production` (environment variables). There's no CI/CD pipeline---deployments are manual via SSH.

### Development (`scripts/dev.sh`)

1. Loads `.env` defaults via Python parser.
2. Finds free ports starting from defaults (backend 8003, frontend 3004) using `lsof`.
3. Delegates to `start-ssh-tunnel.sh` to open/reuse an SSH tunnel to remote MongoDB (default port 37117).
4. Rewrites the tunnel URL from `config.toml` to use `host.docker.internal:<tunnel_port>` for Docker.
5. `docker compose up -d` with development build target.

Subcommands include `--build` (force rebuild), `--down` (stop), `--logs` (tail), and `--restart` (down + up).

## SSE Streaming (`core/streaming.py`)

Lookup and other long-running operations stream progress via Server-Sent Events. The `create_streaming_response()` function wraps an async process in an SSE generator with the following behaviors:
- **Heartbeat**: `: ping\n\n` comment every 30 seconds keeps proxies and load balancers from timing out.
- **Timeout**: 5-minute overall stream timeout; the background task is cancelled on expiry.
- **Client disconnect**: `GeneratorExit` triggers task cancellation—no orphaned background work.
- **Chunked delivery**: Payloads exceeding ~32KB are split by logical unit (basic info, then per-definition, then examples in batches of 10).
- **Event types**: `config` (stage definitions), `progress` (state updates), `complete` (result), `error`.
- **Proxy compatibility**: `X-Accel-Buffering: no` disables nginx buffering. In production, nginx uses `proxy_buffering off` for `/stream` paths.

The `StateTracker` ([`core/state_tracker.py`](../backend/src/floridify/core/state_tracker.py)) tracks 9 pipeline stages (START through COMPLETE) and broadcasts updates to multiple subscribers via `asyncio.Queue`. `model_dump_optimized()` produces ~70% smaller payloads than the full model dump.

## WOTD Pipeline (`wotd/`)

*Experimental---currently disabled in the API router registration.*

The Word-of-the-Day system uses a four-stage ML pipeline for personalized vocabulary selection:

1. **Corpus generation**: AI generates semantically coherent word collections (~100 words each), labeled by style (classical/modern/romantic/neutral), complexity (simple/beautiful/complex/plain), era (shakespearean/victorian/modernist/contemporary), and optionally an author influence (22 authors from Homer to Proust).
2. **Embedding**: Sentence-transformer (GTE-Qwen2-1.5B) encodes each corpus into a 4096D preference vector.
3. **Semantic encoding**: Residual Vector Quantization compresses preference vectors into 4D discrete semantic IDs.
4. **Language model fine-tuning**: Phi-3.5 mini + LoRA generates words conditioned on semantic IDs.

The pipeline is orchestrated by `core/wotd_pipeline.py` and can optionally deploy to AWS SageMaker, with training configs, results, and synthetic data stored in dedicated MongoDB collections.

## Security

### Endpoint Tiers

Four tiers are enforced by `ClerkAuthMiddleware` ([`api/middleware/auth.py`](../backend/src/floridify/api/middleware/auth.py)):

| Tier | Access | Endpoints |
|------|--------|-----------|
| **Public** | No auth | `GET /lookup/*`, `GET /search`, `GET /suggestions`, `/health`, `POST /audio/tts/generate` |
| **Authenticated** | Valid JWT | Wordlist CRUD, user profile, word enrichment |
| **Premium** | `premium` or `admin` role | `POST /ai/*`, definition regeneration, example generation |
| **Admin** | `admin` role only | Cache management, corpus rebuild, database admin, provider management, config |

### Authentication Flow

1. Frontend authenticates via Clerk OAuth (Vue `@clerk/vue` SDK).
2. Bearer JWT sent in `Authorization` header.
3. Middleware fetches Clerk's JWKS from `https://{CLERK_DOMAIN}/.well-known/jwks.json` (cached 1 hour in memory).
4. JWT decoded with RS256 using the matching `kid` key. Claims extracted: `sub` (clerk_id), `email`, `username`, `image_url`.
5. User upserted in MongoDB—first login creates the document. Super-admin emails (from `CLERK_SUPER_ADMINS` env var) are auto-promoted to admin role.
6. `request.state.auth` populated with `AuthState(user_id, user_role, user)`.

**Dev passthrough**: When `CLERK_DOMAIN` is unset and `ENVIRONMENT=development`, all requests receive admin access via `DevAuthState()`. In production without `CLERK_DOMAIN`, protected endpoints return 503 (fail-closed).

### Rate Limiting

Rate limiting uses tiered token buckets via `RateLimitMiddleware`:

| Tier | Requests/min | Requests/hr | Applies to |
|------|-------------|-------------|------------|
| `public` | 60 | 1,000 | Default for all endpoints |
| `ai` | 20 | 200 | `/ai/*` paths |
| `streaming` | 10 | 100 | `/stream` paths |
| `admin` | 30 | 300 | Cache, config, database, corpus, providers |

Clients are identified by authenticated user ID when available, falling back to IP address. `X-Forwarded-For` is only trusted when the direct connection originates from a known proxy network (Docker, loopback, RFC 1918), and the rightmost non-trusted IP is used---not the leftmost, which is spoofable.

### AI Spending Tracker

`SpendingTracker` enforces daily ($10) and hourly ($2) budget caps on AI API calls, estimating cost per model (GPT-5: $0.015/1M tokens, Mini: $0.004, Nano: $0.001). Spend history persists to L2 cache with debounced (3s) writes so it survives process restarts, and warnings fire at 50%, 75%, and 90% of the daily budget.

### Input Validation

Pydantic validation runs at every API boundary, and `utils/sanitization.py` provides XSS prevention. API keys are stored in `auth/config.toml`---never in the database or environment variables (except `MONGODB_URL` for Docker).

## Anki Export (`anki/`)

`AnkiDeckGenerator` produces `.apkg` files from synthesized entries using genanki, supporting four card types: fill-in-the-blank, multiple choice ("best describes"), definition-to-word, and word-to-definition. Card content (questions, distractors) is generated via `AIConnector`, and the styling uses Apple HIG-influenced CSS with a system font stack, subdued palette (`#1d1d1f`, `#86868b`, `#007aff`), and 12px border radius.

## Audio (`audio/`)

The audio subsystem provides multi-language TTS with language-based routing:

| Language | Backend | Model Size |
|----------|---------|------------|
| English | KittenTTS | 15M params |
| French, Spanish, German, Italian, Japanese, Chinese, Hindi, Portuguese | Kokoro-ONNX | 82M params |

Both backends initialize lazily on first request. `AudioSynthesizer` ([`audio/synthesizer.py`](../backend/src/floridify/audio/synthesizer.py)) routes by the word's `language` field and converts the WAV output to MP3 via ffmpeg.

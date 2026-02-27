# Floridify

AI-enhanced dictionary. Python FastAPI backend + Vue 3 TypeScript frontend. MongoDB storage, OpenAI GPT-5 synthesis, FAISS semantic search.

**Production**: https://words.babb.dev

## Project Structure

```
/
├── backend/                    # Python 3.12+ FastAPI (port 8000) → backend/CLAUDE.md
│   ├── src/floridify/          # 23 modules, ~50K LOC
│   │   ├── api/                # REST API: 17 routers, 111+ endpoints, 11 repositories
│   │   ├── core/               # Pipelines: lookup, search, WOTD, SSE streaming
│   │   ├── models/             # 179+ Pydantic/Beanie models
│   │   ├── search/             # Multi-method: exact (<1ms), fuzzy (10-50ms), semantic (50-200ms)
│   │   ├── ai/                 # OpenAI: 32 async methods, 3-tier model selection
│   │   ├── caching/            # L1 memory (0.2ms) → L2 disk (5ms) → L3 versioned MongoDB
│   │   ├── corpus/             # UUID-based tree hierarchy, 9 parsers
│   │   ├── providers/          # 7 dictionary providers, 2 literature, rate limiting
│   │   ├── cli/                # Typer CLI with Rich UI, 0.07s startup
│   │   ├── text/               # Normalization, lemmatization, signatures
│   │   ├── storage/            # MongoDB + Beanie ODM, 28 document models
│   │   ├── wordlist/           # SM-2 spaced repetition, file parsers
│   │   ├── wotd/               # Word-of-the-Day ML pipeline
│   │   ├── anki/               # .apkg flashcard export
│   │   ├── audio/              # Google Cloud TTS
│   │   └── utils/              # Logging, config, paths, validation
│   ├── tests/                  # 58 files, 19K lines, 707 tests, 80%+ coverage
│   ├── scripts/                # run_api.py, benchmark_performance.py
│   └── pyproject.toml          # UV package manager, 60 deps
│
├── frontend/                   # Vue 3.5 TypeScript SPA (port 3000) → frontend/CLAUDE.md
│   ├── src/
│   │   ├── components/         # 173 total: 123 shadcn/ui + 50 custom
│   │   ├── stores/             # 12 Pinia stores, mode-based delegation
│   │   ├── api/                # Axios client, SSE streaming, 14 modules
│   │   ├── composables/        # 20+ composables (search, PWA, texture)
│   │   ├── types/              # Isomorphic types mirroring backend Pydantic
│   │   ├── router/             # 7 routes, SPA deep linking
│   │   ├── views/              # Home.vue (SPA root), NotFound.vue
│   │   └── utils/              # cn(), debounce, animations
│   ├── public/                 # PWA manifest, service worker, icons
│   ├── tailwind.config.ts      # Design system: paper textures, Apple easings
│   ├── nginx.conf              # Production: rate limiting, SSE, security headers
│   └── Dockerfile              # 6-stage: base → deps → dev → build → production (nginx)
│
├── notification-server/        # PWA push notifications (port 3001)
│   ├── src/server.ts           # Express + web-push + MongoDB
│   └── Dockerfile              # Node 20 alpine, multi-stage
│
├── scripts/                    # Development orchestration
│   ├── dev                     # Docker/native mode launcher, SSH tunnel management
│   ├── deploy                  # AWS EC2 deployment via SSH
│   ├── deploy-pwa.sh           # PWA + notification server deployment
│   ├── install-floridify       # CLI installer with ZSH autocomplete
│   └── start-ssh-tunnel.sh     # DocumentDB SSH tunnel
│
├── nginx/                      # Production reverse proxy
│   └── user_conf.d/floridify.conf  # SSL, HSTS, proxy routes, CORS
│
├── docs/                       # 100+ technical docs
│   ├── architecture.md         # System design
│   ├── search.md               # Multi-method search
│   ├── ai.md                   # AI synthesis pipeline
│   ├── prompts/                # 11 deep research prompts
│   ├── word-of-the-day/        # WOTD ML pipeline docs
│   └── texture-research/       # Paper texture implementation
│
├── .github/workflows/deploy.yml  # CI/CD: test → deploy on push to main
├── docker-compose.yml          # Dev: backend, frontend, mongo, notifications
├── docker-compose.prod.yml     # Prod: 4 workers, nginx, SSL, replicas
└── .env / .env.production      # Environment config (not in git)
```

## Data Flow

```
User Query → Multi-Method Search → Provider Fetch (parallel) → AI Synthesis → Cache → Response
```

## Technology

**Backend**: FastAPI, Pydantic v2, Beanie ODM, MongoDB 7.0, Motor (async), UV
**AI/ML**: OpenAI GPT-5 (3-tier: Nano/Mini/Full), sentence-transformers (Qwen3-0.6B), FAISS
**Search**: marisa-trie (exact), RapidFuzz (fuzzy), FAISS HNSW (semantic), Bloom filter
**Cache**: OrderedDict LRU (L1) → DiskCache + ZSTD (L2) → MongoDB versioned (L3, SHA-256)
**Frontend**: Vue 3.5, TypeScript 5.8 strict, Pinia 3.0, shadcn/ui, Tailwind CSS 4.1, Vite 7.0
**Infra**: Docker multi-stage, AWS EC2 + DocumentDB, nginx + Let's Encrypt, GitHub Actions

## Key Pipelines

**Lookup** (`core/lookup_pipeline.py`):
Search (10-100ms) → Cache check (0.2-5ms) → Provider fetch (2-5s parallel) → AI synthesis (1-3s) → Store

**Search** (`search/core.py`):
Exact (<1ms, marisa-trie) → Fuzzy (10-50ms, RapidFuzz) → Semantic (50-200ms, FAISS) — cascade with early termination

**AI Synthesis** (`ai/synthesizer.py`):
Dedup (47→23 defs, 50%) → Cluster (3-4 groups) → Parallel enhance (12 tasks) → Save

## Performance

| Operation | Target | Method |
|-----------|--------|--------|
| Lookup (cached) | <500ms | L1/L2 cache hit |
| Lookup (uncached) | <5s | Parallel provider fetch + AI |
| Search exact | <1ms | marisa-trie O(m) |
| Search fuzzy | 10-50ms | RapidFuzz + signature buckets |
| Search semantic | 50-200ms | FAISS HNSW + Qwen3 |
| AI synthesis | <5s | Parallel 12 components |
| CLI startup | 0.07s | Lazy imports |
| L1 cache hit | 0.2ms | OrderedDict O(1) |

## Design Decisions

- **Isomorphic types**: Frontend TypeScript mirrors backend Pydantic exactly (`types/api.ts` ↔ `models/`)
- **Async-first**: All I/O async. Motor, httpx, asyncio.gather. 80+ async test fixtures
- **Real integration tests**: Actual MongoDB per test, real FAISS indices. Only external APIs mocked
- **Dedup before cluster**: 50% token savings by deduplicating before AI synthesis
- **Mode-based state**: SearchBarStore delegates to mode-specific stores with lifecycle hooks
- **No API calls in stores**: All network operations in composables
- **UUID-based trees**: Corpus parent-child uses UUIDs, not ObjectIds
- **Lazy imports**: Heavy modules (torch, FAISS, sentence-transformers) loaded on demand
- **Content-addressable cache**: L3 uses SHA-256 hashing; identical content reuses versions
- **Per-resource locking**: Fine-grained concurrency (3-5x throughput vs global lock)
- **3-tier model selection**: GPT-5 Nano/Mini/Full routing (87% cost reduction vs naive GPT-4o)

## Configuration

**Environment** (`.env`, not in git):
```bash
ENVIRONMENT=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

**API Keys** (`auth/config.toml`, not in git):
```toml
[openai]
api_key = "sk-..."
model = "gpt-5"

[embedding]
model = "Qwen/Qwen3-Embedding-0.6B"

[database]
development_url = "mongodb://localhost:27018/..."
production_url = "mongodb://..."
```

## Development

```bash
# Docker (recommended)
./scripts/dev                    # All services, hot reload
./scripts/dev --native           # Without Docker

# Manual
cd backend && uv sync && uv run scripts/run_api.py
cd frontend && npm install && npm run dev

# CLI
./scripts/install-floridify
floridify lookup perspicacious
```

## Quality

```bash
# Backend
ruff check --fix && ruff format  # Lint + format
mypy src/ --strict               # Type check
pytest tests/ -v                 # 707 tests

# Frontend
npm run type-check               # TypeScript strict
prettier --write .               # Format
```

## Deployment

```bash
./scripts/deploy                 # SSH to EC2, sync secrets, build, deploy
# Auto: push to main → GitHub Actions → test → deploy → health check
# SSL: Let's Encrypt via nginx-certbot, auto-renewal
# URL: https://words.babb.dev
```

## macOS Note

PyTorch + FAISS + scikit-learn each load separate `libomp.dylib`. Set `OMP_NUM_THREADS=1` at import time to prevent SIGSEGV. `KMP_DUPLICATE_LIB_OK=TRUE` as fallback. Safe parallelism lever: batch_size (32→128).

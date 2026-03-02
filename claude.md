# Floridify

AI-enhanced dictionary. Python FastAPI backend + Vue 3 TypeScript frontend. MongoDB storage, OpenAI GPT-5 synthesis, FAISS semantic search.

**Production**: https://words.babb.dev

## Project Structure

```
/
├── backend/                    # Python 3.12+ FastAPI (port 8000) → backend/CLAUDE.md
│   ├── src/floridify/          # 16 modules, ~60K LOC, 236 .py files
│   │   ├── api/                # REST API: 20 routers, 121 endpoints, 11 repositories
│   │   ├── core/               # Pipelines: lookup, search, WOTD, SSE streaming
│   │   ├── models/             # 187+ Pydantic/Beanie models across codebase
│   │   ├── search/             # Multi-method: exact, fuzzy, semantic (FAISS)
│   │   ├── ai/                 # OpenAI: 30 async methods, 3-tier model selection
│   │   ├── caching/            # L1 memory → L2 disk → L3 versioned MongoDB
│   │   ├── corpus/             # UUID-based tree hierarchy, 9 parsers
│   │   ├── providers/          # 7 dictionary providers, 2 literature APIs, 15 author mappings
│   │   ├── cli/                # Typer CLI with Rich UI
│   │   ├── text/               # Normalization, lemmatization, signatures
│   │   ├── storage/            # MongoDB + Beanie ODM, 19 registered document models
│   │   ├── wordlist/           # SM-2 spaced repetition, file parsers
│   │   ├── wotd/               # Word-of-the-Day ML pipeline
│   │   ├── anki/               # .apkg flashcard export
│   │   ├── audio/              # Google Cloud TTS
│   │   └── utils/              # Logging, config, paths, validation
│   ├── tests/                  # 65 files, ~21K lines, 720 tests
│   ├── scripts/                # run_api.py, benchmark_performance.py
│   └── pyproject.toml          # UV package manager, 39 deps + 13 dev deps
│
├── frontend/                   # Vue 3.5 TypeScript SPA (port 3000) → frontend/CLAUDE.md
│   ├── src/                    # ~34K LOC
│   │   ├── components/         # 229 .vue files: 123 shadcn/ui + 106 custom
│   │   ├── stores/             # 14 Pinia store files, mode-based delegation
│   │   ├── api/                # Axios client, SSE streaming, 14 modules
│   │   │   ├── ai/             # synthesize, generate, assess, suggestions (split)
│   │   │   └── sse/            # SSEClient, types (split)
│   │   ├── composables/        # 5 global composables (iOS PWA, PWA, texture, slug)
│   │   ├── types/              # Isomorphic types mirroring backend Pydantic
│   │   │   └── api/            # models, responses, guards, versions (split)
│   │   ├── router/             # 7 routes, SPA deep linking
│   │   ├── views/              # Home.vue (SPA root), NotFound.vue
│   │   └── utils/              # cn(), debounce, animations
│   ├── public/                 # PWA manifest, service worker, icons
│   ├── tailwind.config.ts      # Design system: paper textures, easings
│   ├── nginx.conf              # Production: rate limiting, SSE, security headers
│   └── Dockerfile              # 6-stage: base → deps → dev-deps → dev → build → production (nginx)
│
├── notification-server/        # PWA push notifications (port 3001)
│   ├── src/server.ts           # Express + web-push + MongoDB
│   └── Dockerfile              # Node multi-stage, 6 stages
│
├── scripts/                    # Development orchestration
│   ├── dev                     # Docker/native mode launcher, SSH tunnel management
│   ├── deploy                  # AWS EC2 deployment via SSH
│   ├── deploy-pwa.sh           # PWA + notification server deployment
│   ├── install-floridify       # CLI installer with ZSH autocomplete
│   ├── backup-mongodb.sh       # MongoDB backup script
│   └── start-ssh-tunnel.sh     # SSH tunnel for remote MongoDB
│
├── nginx/                      # Production reverse proxy
│   └── user_conf.d/floridify.conf  # SSL, HSTS, proxy routes, CORS
│
├── docs/                       # 62 files
│   ├── architecture.md         # System design
│   ├── search.md               # Multi-method search
│   ├── ai.md                   # AI synthesis pipeline
│   ├── prompts/                # 11 deep research prompts
│   ├── word-of-the-day/        # WOTD ML pipeline docs
│   └── texture-research/       # Paper texture implementation
│
├── .github/workflows/deploy.yml  # CI/CD: test → deploy on push to main
├── docker-compose.yml          # Dev: backend, frontend, mongo, notifications
├── docker-compose.prod.yml     # Prod: configurable workers, nginx, SSL
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
**Frontend**: Vue ^3.5, TypeScript ^5.9, Pinia ^3.0, shadcn/ui (Reka UI), Tailwind CSS ^4.2, Vite ^7.3
**Infra**: Docker multi-stage, AWS EC2 + self-hosted MongoDB, nginx + Let's Encrypt, GitHub Actions

## Key Pipelines

**Lookup** (`core/lookup_pipeline.py`, 519 LOC):
Search → Cache check → Provider fetch (asyncio.gather) → AI synthesis → Store

**Search** (`search/core.py`, 897 LOC):
Exact (marisa-trie) → Fuzzy (RapidFuzz) → Semantic (FAISS HNSW)—cascade with early termination

**AI Synthesis** (`ai/synthesizer.py`, 542 LOC):
Dedup → Cluster → Parallel enhance (4 word-level + 11 definition-level components) → Save

## Design Decisions

- **Isomorphic types**: Frontend TypeScript mirrors backend Pydantic exactly (`types/api/` ↔ `models/`)
- **Async-first**: All I/O async. Motor, httpx, asyncio.gather. 80+ async test fixtures
- **Real integration tests**: Actual MongoDB per test, real FAISS indices. Only external APIs mocked
- **Dedup before cluster**: Deduplicate provider definitions before AI clustering to reduce token usage
- **Mode-based state**: SearchBarStore delegates to mode-specific stores with onEnter/onExit lifecycle
- **No API calls in stores**: All network operations in composables
- **UUID-based trees**: Corpus parent-child uses UUIDs, not ObjectIds
- **Lazy imports**: Heavy modules (torch, FAISS, sentence-transformers) loaded on demand
- **Content-addressable cache**: L3 uses SHA-256 hashing; identical content reuses versions
- **Per-resource locking**: Fine-grained concurrency in corpus manager
- **3-tier model selection**: GPT-5 Nano/Mini/Full routing by task complexity

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
development_url = "mongodb://localhost:27017/..."
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
pytest tests/ -v                 # 720 tests

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

PyTorch + FAISS + scikit-learn each load separate `libomp.dylib`. Set `OMP_NUM_THREADS=1` at import time to prevent SIGSEGV. `KMP_DUPLICATE_LIB_OK=TRUE` as fallback. Safe parallelism lever: batch_size (32->128).

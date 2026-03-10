# Floridify

AI-enhanced dictionary. Python FastAPI backend + Vue 3 TypeScript frontend. MongoDB storage, OpenAI GPT-5 synthesis, FAISS semantic search.

**Production**: https://mbabb.friday.institute/words/

## Project Structure

```
/
├── backend/                    # Python 3.12+ FastAPI (port 8000) → backend/CLAUDE.md
│   ├── src/floridify/          # 16 modules
│   │   ├── api/                # REST API: routers, repositories, middleware
│   │   ├── core/               # Pipelines: lookup, search, WOTD, SSE streaming
│   │   ├── models/             # Pydantic/Beanie models
│   │   ├── search/             # Multi-method: exact, fuzzy, semantic (FAISS)
│   │   ├── ai/                 # OpenAI/Anthropic: 3-tier model selection
│   │   ├── caching/            # L1 memory → L2 disk → L3 versioned MongoDB
│   │   ├── corpus/             # UUID-based tree hierarchy, parsers
│   │   ├── providers/          # 7 dictionary providers, 2 literature APIs
│   │   ├── cli/                # Click CLI with Rich UI
│   │   ├── text/               # Normalization, lemmatization
│   │   ├── storage/            # MongoDB + Beanie ODM
│   │   ├── wordlist/           # SM-2 spaced repetition, file parsers
│   │   ├── wotd/               # Word-of-the-Day ML pipeline
│   │   ├── anki/               # .apkg flashcard export
│   │   ├── audio/              # Multi-language TTS (KittenTTS + Kokoro-ONNX)
│   │   └── utils/              # Logging, config, paths, validation
│   ├── tests/                  # Integration tests (real MongoDB, real FAISS)
│   ├── scripts/                # run_api.py, benchmark_performance.py
│   └── pyproject.toml          # UV package manager
│
├── frontend/                   # Vue 3.5 TypeScript SPA (port 3000) → frontend/CLAUDE.md
│   ├── src/
│   │   ├── components/         # shadcn/ui + custom Vue components
│   │   ├── stores/             # Pinia stores, mode-based delegation
│   │   ├── api/                # Axios client, SSE streaming
│   │   │   ├── ai/             # synthesize, generate, assess, suggestions
│   │   │   └── sse/            # SSEClient, types
│   │   ├── composables/        # useIOSPWA, usePWA, useTextureSystem, useSlugGeneration, useStateSync
│   │   ├── types/              # Isomorphic types mirroring backend Pydantic
│   │   │   └── api/            # models, responses, guards, versions
│   │   ├── router/             # SPA deep linking
│   │   ├── views/              # Home, NotFound, Admin, Login, Signup
│   │   ├── lib/                # Utility functions
│   │   ├── plugins/            # Toast plugin
│   │   └── utils/              # cn(), debounce, animations, wordDiff
│   ├── public/                 # PWA manifest, service worker, icons
│   ├── tailwind.config.ts      # Design system: paper textures, easings
│   ├── nginx.conf              # Production: rate limiting, SSE, security headers
│   └── Dockerfile              # 6-stage: base → deps → dev-deps → dev → build → production (nginx)
│
├── notification-server/        # PWA push notifications (port 3001)
│   ├── src/server.ts           # Express + web-push + MongoDB
│   └── Dockerfile              # Node multi-stage
│
├── scripts/                    # Development orchestration
│   ├── dev.sh                  # Docker/native mode launcher, SSH tunnel management
│   ├── deploy.sh               # SSH deployment to production server
│   ├── deploy-pwa.sh           # PWA + notification server deployment
│   ├── install-floridify       # CLI installer with ZSH autocomplete
│   ├── backup-mongodb.sh       # MongoDB backup script
│   └── start-ssh-tunnel.sh     # SSH tunnel for remote MongoDB
│
├── nginx/                      # Production reverse proxy
│   └── user_conf.d/floridify.conf  # SSL, HSTS, proxy routes, CORS
│
├── docs/                       # Documentation
│   ├── architecture.md         # System design
│   ├── synthesis.md            # AI synthesis pipeline
│   ├── search.md               # Multi-method search
│   ├── versioning.md           # Versioning & caching
│   ├── ai.md                   # AI integration details
│   ├── cli.md                  # CLI reference
│   ├── anki.md                 # Flashcard export
│   └── prompts/                # Deep research prompts
│
├── docker-compose.yml          # Dev: backend, frontend, mongo, notifications
├── docker-compose.prod.yml     # Prod: configurable workers, nginx, SSL
└── .env / .env.production      # Environment config (not in git)
```

## Data Flow

```
User Query → Multi-Method Search → Provider Fetch (parallel) → AI Synthesis → Cache → Response
```

## Technology

**Backend**: FastAPI, Pydantic v2, Beanie ODM, MongoDB, Motor (async), UV
**AI/ML**: OpenAI GPT-5 (3-tier: 5.4/Mini/Nano), Anthropic Claude, sentence-transformers (Qwen3-0.6B), FAISS
**Search**: marisa-trie (exact), RapidFuzz (fuzzy), FAISS HNSW (semantic), Bloom filter
**Cache**: OrderedDict LRU (L1) → DiskCache + ZSTD (L2) → MongoDB versioned (L3, SHA-256)
**Frontend**: Vue 3.5, TypeScript 5.9, Pinia, shadcn/ui (Reka UI), Tailwind CSS 4, Vite, Clerk
**TTS**: KittenTTS (English), Kokoro-ONNX (8 languages)
**Infra**: Docker multi-stage, self-hosted (behind VPN), MongoDB, nginx

## Key Pipelines

**Lookup** ([`core/lookup_pipeline.py`](backend/src/floridify/core/lookup_pipeline.py)):
Search → Cache check → Provider fetch (asyncio.gather) → AI synthesis → Store

**Search** ([`search/core.py`](backend/src/floridify/search/core.py)):
Exact (marisa-trie) → Prefix → Fuzzy (RapidFuzz) → Semantic (FAISS HNSW)—cascade with early termination. See [docs/search.md](docs/search.md).

**AI Synthesis** ([`ai/synthesizer.py`](backend/src/floridify/ai/synthesizer.py)):
Dedup → Cluster → Parallel enhance (4 word-level + 11 definition-level components) → Save. See [docs/synthesis.md](docs/synthesis.md).

**Caching** ([`caching/`](backend/src/floridify/caching/)):
L1 memory → L2 disk → L3 versioned MongoDB with SHA-256 dedup and delta compression. See [docs/versioning.md](docs/versioning.md).

## Design Decisions

- **Isomorphic types**: Frontend TypeScript mirrors backend Pydantic exactly (`types/api/` ↔ `models/`)
- **Async-first**: All I/O async. Motor, httpx, asyncio.gather
- **Real integration tests**: Actual MongoDB per test, real FAISS indices. Only external APIs mocked
- **Dedup before cluster**: Deduplicate provider definitions before AI clustering to reduce token usage
- **Mode-based state**: SearchBarStore delegates to mode-specific stores with onEnter/onExit lifecycle
- **No API calls in stores**: All network operations in composables
- **UUID-based trees**: Corpus parent-child uses UUIDs, not ObjectIds
- **Lazy imports**: Heavy modules (torch, FAISS, sentence-transformers) loaded on demand
- **Content-addressable cache**: L3 uses SHA-256 hashing; identical content reuses versions
- **Per-resource locking**: Fine-grained concurrency in corpus manager
- **3-tier model selection**: GPT-5 5.4/Mini/Nano routing by task complexity

## Configuration

**Environment** (`.env`, not in git):
```bash
ENVIRONMENT=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

**API Keys** (`backend/auth/config.toml`, not in git—see [`config.example.toml`](config.example.toml)):
```toml
[openai]
api_key = "sk-..."

[database]
runtime_url = "mongodb://user:pass@host:27017/floridify"
test_url = "mongodb://user:pass@host:27017/test_floridify"

[models]
openai_model = "gpt-5-mini"
```

## Development

```bash
# Docker (recommended)
./scripts/dev.sh                 # All services, hot reload
./scripts/dev.sh --native        # Without Docker

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
pytest tests/ -v                 # Tests

# Frontend
npm run type-check               # TypeScript strict
prettier --write .               # Format
```

## Deployment

```bash
./scripts/deploy.sh              # SSH to server, sync secrets, build, deploy
# Server: mbabb@mbabb.friday.institute -p 1022 (behind VPN)
# No CI/CD — deploy manually
# URL: https://mbabb.friday.institute/words/
```

## macOS Note

PyTorch + FAISS + scikit-learn each load separate `libomp.dylib`. Set `OMP_NUM_THREADS=1` at import time to prevent SIGSEGV. `KMP_DUPLICATE_LIB_OK=TRUE` as fallback. Safe parallelism lever: batch_size (32→128).

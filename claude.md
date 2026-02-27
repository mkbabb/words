# Floridify - AI Dictionary System

**Full-stack dictionary application** with AI-enhanced definition synthesis, multi-method search, and spaced repetition learning.

## Architecture

**Stack**: Python 3.12+ FastAPI backend (port 8000) + Vue 3 TypeScript frontend (port 3000)
**Data**: MongoDB with Beanie ODM, FAISS semantic search, OpenAI GPT-5 synthesis
**Infrastructure**: Docker containers, AWS EC2 + DocumentDB, GitHub Actions CI/CD

**Data Flow**: User Query → Multi-Method Search → Provider Fetch → AI Synthesis → Cache → Response

```
/
├── backend/            # Python FastAPI API + CLI
│   ├── src/floridify/  # Core application (23 modules)
│   ├── tests/          # 58 test files, 19K lines, 639+ tests
│   ├── scripts/        # CLI tools and utilities
│   └── pyproject.toml  # UV package manager config
├── frontend/           # Vue 3 TypeScript SPA
│   ├── src/            # 173 components (123 shadcn/ui + 50 custom)
│   ├── public/         # Static assets and PWA manifest
│   └── package.json    # NPM dependencies
├── docs/               # Technical documentation (50+ files)
├── scripts/            # Development orchestration
│   ├── dev             # Docker/native mode launcher
│   ├── deploy          # AWS EC2 deployment
│   └── install-floridify  # CLI installer with autocomplete
└── docker-compose.yml  # Multi-service orchestration
```

## Core Technologies

**Backend**:
- **Framework**: FastAPI + Uvicorn (async), Pydantic v2 validation
- **Database**: MongoDB 7.0 with Motor (async) + Beanie ODM (179+ models)
- **AI/ML**: OpenAI API (GPT-5 series), sentence-transformers (Qwen3-Embedding-0.6B), FAISS (semantic search)
- **Search**: RapidFuzz (Rust), marisa-trie (C++), PyAhoCorasick, Jellyfish
- **Caching**: Multi-tier (OrderedDict LRU + DiskCache + MongoDB versioning)
- **Package Manager**: UV (Astral, Rust-based, 10-100x faster than pip)

**Frontend**:
- **Framework**: Vue 3.5.17 (Composition API, `<script setup>`)
- **Language**: TypeScript 5.8.3 (strict mode)
- **State**: Pinia 3.0.3 with localStorage persistence
- **UI**: shadcn/ui (123 components, Radix Vue primitives)
- **Styling**: Tailwind CSS 4.1.11 with custom design system
- **Build**: Vite 7.0.3 with esbuild
- **Routing**: Vue Router 4.5.1 (SPA with deep linking)

**Infrastructure**:
- **Containerization**: Docker multi-stage builds, Docker Compose profiles
- **Deployment**: AWS EC2 (Ubuntu), DocumentDB (MongoDB-compatible)
- **Web Server**: Nginx with Let's Encrypt SSL (auto-renewal)
- **CI/CD**: GitHub Actions (test + deploy on push to main)

## Key Features

**AI-Powered Synthesis**:
- Aggressive deduplication (47 → 23 definitions avg, 50% reduction)
- Semantic clustering before synthesis (>70% similarity threshold)
- 3-tier model selection: GPT-5 Nano/Mini/Full (87% cost reduction vs naive GPT-4o)
- Parallel component generation (definitions, pronunciation, etymology, facts, examples)
- Batch processing (50% discount via OpenAI Batch API)

**Multi-Method Search** (cascade with early termination):
- **Exact** (< 1ms): marisa-trie + Bloom filter, O(m) where m = query length
- **Fuzzy** (10-50ms): RapidFuzz with WRatio + token_set_ratio, signature pre-filtering
- **Semantic** (50-200ms): FAISS HNSW + Qwen3 embeddings (1024D), binary quantization
- **AI Fallback**: GPT-5 generation when all methods fail

**Caching Architecture** (sub-millisecond L1, 10-50x speedup):
- **L1 Memory**: OrderedDict LRU per namespace (0.2ms avg, 13 namespaces)
- **L2 Disk**: DiskCache with ZSTD/LZ4/GZIP compression (5ms avg, 10GB limit)
- **L3 Versioned**: MongoDB with content-addressable storage (SHA-256 hashing)
- **Intelligent eviction**: TTL-based (1h-30d) + size-based LRU

**Learning Tools**:
- Spaced repetition (SM-2 algorithm, Bronze → Silver → Gold progression)
- Direct Anki export (no manual card creation)
- Word list management (frequency tracking, review system)
- Progress analytics and vocabulary suggestions

**Web Interface**:
- Mode-based architecture (lookup, wordlist, word-of-the-day)
- SSE streaming with real-time progress (config → progress → completion events)
- Progressive sidebar (cluster navigation, accordion state)
- Dark mode with paper texture system
- PWA support (offline mode, push notifications)

**CLI Interface**:
- Rich-powered terminal UI (Unicode formatting, progress bars)
- ~0.07s startup time (98% faster than original 4.2s via lazy imports)
- ZSH autocomplete with performance optimization
- JSON output mode for scripting

## Development Environment

**Prerequisites**:
- Python 3.12+ with UV (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+ (`nvm install 20`)
- Docker + Docker Compose (`docker --version`)
- MongoDB 7.0 (local or DocumentDB tunnel)

**Quick Start (Docker - Recommended)**:
```bash
./scripts/dev                # Start all services (hot reload)
./scripts/dev --native       # Run servers without Docker
./scripts/dev --logs         # Start and follow logs
./scripts/dev --build        # Rebuild images

# Access services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - MongoDB: localhost:27018 (via SSH tunnel)
```

**Manual Setup**:
```bash
# Backend
cd backend
uv venv && source .venv/bin/activate
uv sync
cp auth/config.toml.example auth/config.toml  # Add OpenAI key
uv run scripts/run_api.py

# Frontend
cd frontend
npm install
npm run dev

# CLI (global installation with autocomplete)
./scripts/install-floridify
floridify lookup perspicacious
```

**Testing**:
```bash
# Backend: 58 files, 639+ tests, 80%+ coverage
cd backend
pytest tests/ -v
pytest tests/ --cov=src/floridify --cov-report=html
pytest tests/ -m "not slow"  # Exclude slow tests

# Frontend: TO BE IMPLEMENTED (gap identified)
cd frontend
npm test  # Currently no tests (Vitest configured but unused)
```

**Quality Checks**:
```bash
# Backend
ruff check --fix     # Linting (Rust-based, 10-100x faster than Flake8)
ruff format          # Formatting (Black-compatible)
mypy src/ --strict   # Type checking (strict mode)

# Frontend
npm run type-check   # TypeScript compilation (strict mode)
prettier --write .   # Code formatting
```

## API Architecture

**REST Endpoints** (111+ total across 6 domains):
- `/api/v1/lookup/{word}` - Full AI-enhanced definition (cached, 24h TTL)
- `/api/v1/lookup/{word}/stream` - SSE streaming with progress events
- `/api/v1/search/{query}` - Multi-method search (20 results, 0.6 score threshold)
- `/api/v1/ai/synthesize/*` - 40+ AI generation endpoints
- `/api/v1/corpus/*` - Corpus CRUD + tree operations
- `/api/v1/wordlist/*` - Wordlist management + review system

**Streaming Protocol** (SSE):
```
event: config
data: {"stages": {"SEARCH_START": 10, "PROVIDER_FETCH": 60, ...}}

event: progress
data: {"stage": "SEARCH_START", "progress": 10, "message": "Searching..."}

event: complete
data: {"word": "ephemeral", "definitions": [...], "pronunciation": {...}}
```

**Performance Targets**:
- Lookup (cached): < 500ms
- Lookup (uncached): < 3s (includes AI synthesis)
- Search (exact): < 200ms
- Search (semantic): < 500ms
- AI synthesis: < 5s (parallel processing)

## Configuration

**Environment Variables** (`.env`):
```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000

# AWS (production)
AWS_REGION=us-east-1
EC2_HOST=44.216.140.209
DOMAIN=words.babb.dev
```

**API Keys** (`auth/config.toml`, **not in git**):
```toml
[openai]
api_key = "sk-..."
model = "gpt-5"              # Reasoning model (o-series)
reasoning_effort = "high"    # low/medium/high for o1/o3

[embedding]
model = "Qwen/Qwen3-Embedding-0.6B"  # Default (1024D, 64.33 MTEB)
# Alternatives:
# - "Qwen/Qwen3-Embedding-8B" (4096D, 70.58 MTEB, SOTA)
# - "BAAI/bge-m3" (1024D, multilingual, 100+ languages)

[database]
production_url = "mongodb://user:pass@docdb.amazonaws.com:27017/..."
development_url = "mongodb://user:pass@localhost:27018/..."

[providers]
oxford_api_key = "..."       # Optional (dictionary.com fallback)
oxford_app_id = "..."

[rate_limits]
openai_rps = 10.0
oxford_rps = 10.0
```

## Deployment

**Production (AWS EC2 + DocumentDB)**:
```bash
./scripts/deploy  # SSH to EC2, sync secrets, deploy containers

# Manual deployment:
ssh ubuntu@44.216.140.209
cd /var/www/floridify
git pull origin main
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose --profile ssl up -d

# Health check:
curl -L https://words.babb.dev/api/health
```

**GitHub Actions CI/CD** (auto-deploys on push to main):
1. **Test**: pytest (backend) + vite build (frontend)
2. **Deploy**: SSH to EC2, add runner to security group, deploy, cleanup
3. **Verify**: Health check after 30s

**SSL Management**:
- Let's Encrypt via nginx-certbot Docker image
- Auto-renewal (certbot checks daily)
- HSTS enabled (63072000s = 2 years)

## Project Statistics

**Codebase Size**:
- Backend: 23 modules, 179+ models, 111+ endpoints, 3 core pipelines
- Frontend: 173 components (123 shadcn/ui + 50 custom), 12 Pinia stores, 20+ composables
- Tests: 58 files, 19,000 lines, 639+ functions (backend only)
- Documentation: 50+ technical docs, 8 architecture guides

**Performance Metrics**:
- CLI startup: 0.07s (vs 4.2s original, 98% improvement)
- L1 cache hit: 0.2ms avg (vs 50ms MongoDB)
- Search exact: < 1ms (marisa-trie + Bloom filter)
- Search semantic: 50-200ms (FAISS HNSW + embeddings)
- AI synthesis: < 5s (parallel processing, 12 components)

**Cost Optimization**:
- 87% reduction vs naive GPT-4o (3-tier model selection + batching)
- 50% discount via OpenAI Batch API (bulk operations)
- Aggressive caching (24h TTL, 90%+ hit rate)
- ~$0.02 per word synthesis (vs ~$0.15 naive)

## Key Design Decisions

**Real Integration Testing**: Tests use actual MongoDB (unique DB per test), real file operations, real FAISS indices—no mocking except external APIs (OpenAI, dictionary providers).

**Async-First Architecture**: 80+ async fixtures, asyncio.gather for parallel operations, Motor/httpx async clients, connection pooling (50 MongoDB connections).

**Isomorphic Types**: Frontend TypeScript types (360 lines in `types/api.ts`) mirror backend Pydantic models exactly—no drift, full type safety across stack.

**Mode-Based State**: SearchBarStore delegates to mode-specific stores (lookup, wordlist, WOTD) with onEnter/onExit lifecycle hooks—no giant monolithic store.

**UUID-Based Trees**: Corpus parent-child relationships use UUIDs (not MongoDB ObjectIds)—stable across version changes, enables proper corpus aggregation.

**Force External Storage**: Large binary data (>16KB) bypasses JSON encoding and goes directly to L2 cache—prevents hanging on 1GB+ semantic indices.

**Semantic First, Then Cluster**: Deduplication (50% reduction) happens *before* clustering—saves tokens, improves quality, reduces API calls.

**Lazy Imports**: Heavy modules (sentence-transformers, FAISS) loaded only when needed—45% boot time reduction (1.3s saved).

## Development Workflow

**Feature Development**:
1. Write types in `backend/src/floridify/models/` (Pydantic)
2. Mirror types in `frontend/src/types/api.ts` (TypeScript)
3. Implement backend logic in `backend/src/floridify/core/`
4. Add API endpoint in `backend/src/floridify/api/routers/`
5. Write backend tests in `backend/tests/` (80%+ coverage)
6. Implement frontend in `frontend/src/components/custom/`
7. Add composable in `frontend/src/composables/` (no API calls in stores)
8. **MISSING**: Write frontend tests (gap identified)

**Git Workflow**:
```bash
git checkout -b feature/my-feature
# ... make changes
ruff check --fix && mypy src/
npm run type-check && prettier --write .
pytest tests/ -v
git commit -m "feat(search): add phonetic search mode"
git push origin feature/my-feature
# Create PR → GitHub Actions runs tests → merge to main → auto-deploy
```

**Common Tasks**:
```bash
# Build semantic search index (one-time per corpus)
floridify corpus rebuild --corpus-name english_master --semantic

# Add literature work to corpus
floridify literature add-work \
  --author shakespeare \
  --work-id 1524 \
  --corpus-name shakespeare_corpus

# Generate VAPID keys for push notifications
cd notification-server && npm run generate-vapid-keys

# Clear cache namespace
curl -X POST http://localhost:8000/api/v1/cache/clear?namespace=SEMANTIC
```

## Documentation Index

**Core Architecture**:
- `CLAUDE.md` (this file) - Project overview
- `backend/CLAUDE.md` - Backend implementation details
- `frontend/CLAUDE.md` - Frontend architecture (**TO BE CREATED**)

**Technical Docs** (`docs/`):
- `architecture.md` - System design and data flow
- `search.md` - Multi-method search deep dive
- `ai.md` - AI synthesis pipeline
- `batch_processing_guide.md` - OpenAI Batch API usage
- `rest-api-architecture.md` - API design patterns
- `corpus-optimization-strategy.md` - Corpus management
- `docker-ssl-ec2-deployment-guide.md` - AWS deployment

**Feature Guides**:
- `cli.md` - Command-line interface
- `anki.md` - Anki integration
- `list.md` - Word list management
- `PWA-Technical-Guide.md` - Progressive Web App setup

## Why This Exists

Words are tools for thinking. An expanded vocabulary isn't about sounding smart—it's about having the right word when you need it. The notion of one's mind being incandescent necessitates a large vocabulary to deploy at a moment's notice.

Traditional dictionaries fail in three ways:
1. **Organization**: Definitions jumbled by historical order, not meaning
2. **Synthesis**: No consolidation across sources (Wiktionary has 12 entries for "sanction", Oxford has 3—same meanings, poor UX)
3. **Learning**: No spaced repetition, no progress tracking, no context

Floridify fixes this with:
- **AI clustering**: Groups by meaning, not etymology (sanction¹ approval vs sanction² penalty)
- **Multi-source synthesis**: Best of Wiktionary + Oxford + Apple + Free Dictionary
- **Learning integration**: SM-2 algorithm, Anki export, vocabulary suggestions
- **Performance**: Sub-second cached lookups, 0.07s CLI startup

Built for those who collect words like others collect stamps, who understand that language is the substrate of thought itself—a proxy for human understanding.

**Look up → Understand → Remember → Use**

---

**Version**: January 2025
**License**: Proprietary
**Author**: Mike Babb (mike@babb.dev)
**Repository**: Private
**Deployment**: https://words.babb.dev

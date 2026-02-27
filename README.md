# Floridify

**AI-enhanced dictionary** that organizes words by meaning, not memorization.

## What It Does

Floridify transforms dictionary chaos into clarity. When you look up "sanction," you get:
- **sanction¹** (approval, authorization)
- **sanction²** (penalty, punishment)

Not a wall of 12 jumbled definitions from Wiktionary.

**Technology**: Python FastAPI backend + Vue 3 frontend, MongoDB storage, OpenAI GPT-5 synthesis, FAISS semantic search.

## Quick Start

**Docker** (recommended):
```bash
git clone <repo-url>
cd floridify
./scripts/dev  # Starts all services with hot reload

# Access:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

**Manual** (requires Python 3.12+, Node 20+):
```bash
# Backend
cd backend
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
uv venv && source .venv/bin/activate
uv sync
cp auth/config.toml.example auth/config.toml  # Add OpenAI key
uv run scripts/run_api.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

# CLI (separate terminal)
./scripts/install-floridify  # Global install with autocomplete
floridify lookup perspicacious
```

## Core Features

### AI-Powered Synthesis
- **Deduplication**: 47 → 23 definitions (50% reduction, preserves quality)
- **Semantic clustering**: Groups by meaning, not etymology
- **Multi-source**: Synthesizes from Wiktionary + Oxford + Apple Dictionary + Free Dictionary
- **Cost-optimized**: 3-tier model selection (87% cheaper than naive GPT-4o)
- **Parallel generation**: Definitions, pronunciation, etymology, facts—all concurrent

### Multi-Method Search
Fast cascading search with early termination:
- **Exact** (< 1ms): marisa-trie + Bloom filter, perfect matches
- **Fuzzy** (10-50ms): RapidFuzz for typos, "perspicac" → "perspicacious"
- **Semantic** (50-200ms): FAISS + embeddings, "happy" → "joyful", "elated"
- **AI Fallback**: GPT-5 generates definition when providers fail

### Smart Caching
Sub-millisecond cached lookups with 3-tier system:
- **L1 Memory**: 0.2ms avg, 13 namespaces (OrderedDict LRU)
- **L2 Disk**: 5ms avg, 10GB limit (DiskCache + ZSTD compression)
- **L3 Versioned**: MongoDB with content-addressable storage (SHA-256)

### Learning Tools
- **Spaced repetition**: SM-2 algorithm (Bronze → Silver → Gold)
- **Direct Anki export**: No manual card creation
- **Word lists**: Frequency tracking, review system
- **Progress analytics**: Vocabulary suggestions with 1-hour cache

### Web Interface
- **Mode-based architecture**: Lookup, wordlist, word-of-the-day
- **Real-time progress**: SSE streaming (config → progress → complete events)
- **Progressive sidebar**: Cluster navigation, accordion state
- **Dark mode**: Paper texture system with warm tones
- **PWA support**: Offline mode, push notifications, standalone mode

### CLI Interface
- **Rich terminal UI**: Unicode formatting, progress bars
- **Lightning fast**: 0.07s startup (98% faster via lazy imports)
- **ZSH autocomplete**: Performance-optimized completion
- **JSON output**: For scripting and automation

## Architecture

```
/
├── backend/            # Python 3.12+ FastAPI (23 modules, ~50K LOC)
│   ├── src/floridify/  # Core: api, core, models, search, ai, caching, corpus, providers, cli, ...
│   └── tests/          # 58 files, 19K lines, 707 tests
├── frontend/           # Vue 3.5 TypeScript SPA (~34K LOC)
│   └── src/            # 173 components, 12 stores, 20+ composables
├── notification-server/ # PWA push notifications (Express + web-push)
├── scripts/            # dev, deploy, install-floridify
├── nginx/              # Production reverse proxy + SSL
├── docs/               # 100+ technical docs
└── docker-compose.yml  # Multi-service orchestration
```

**Data Flow**: User Query → Multi-Method Search → Provider Fetch → AI Synthesis → Cache → Response

**Stack**:
- **Backend**: FastAPI, Pydantic v2, Beanie ODM, MongoDB 7.0, Motor (async), UV
- **AI/ML**: OpenAI GPT-5 (3-tier), sentence-transformers (Qwen3-0.6B), FAISS
- **Search**: marisa-trie, RapidFuzz, FAISS HNSW, Bloom filter
- **Cache**: OrderedDict LRU → DiskCache + ZSTD → MongoDB versioned (SHA-256)
- **Frontend**: Vue 3.5, TypeScript 5.8 strict, Pinia 3.0, shadcn/ui, Tailwind CSS 4.1, Vite 7.0
- **Infra**: Docker multi-stage, AWS EC2 + DocumentDB, nginx + Let's Encrypt, GitHub Actions

## API Endpoints

**REST API** (111+ endpoints):
```bash
# Lookup
GET /api/v1/lookup/{word}              # Full definition
GET /api/v1/lookup/{word}/stream       # SSE streaming with progress

# Search
GET /api/v1/search?q={query}           # Multi-method search (20 results)
GET /api/v1/search/{query}/suggestions # Autocomplete (8 results)

# AI Synthesis
POST /api/v1/ai/synthesize/*           # 40+ generation endpoints

# Corpus
GET /api/v1/corpus/                    # List corpora
POST /api/v1/corpus/                   # Create corpus

# Wordlist
GET /api/v1/wordlist/                  # List wordlists
POST /api/v1/wordlist/                 # Create wordlist
GET /api/v1/wordlist/{id}/due          # Get due words for review
```

## CLI Commands

```bash
# Lookup
floridify lookup perspicacious           # Full definition
floridify lookup --no-ai perspicacious   # Raw provider data
floridify lookup --json perspicacious    # JSON output

# Search
floridify search serendipity             # Multi-method cascade
floridify search --fuzzy serendip        # Fuzzy only
floridify search --semantic happy        # Semantic only

# Corpus
floridify corpus list
floridify corpus rebuild --corpus-name english_master --semantic

# Wordlist
floridify wordlist create my-words word1 word2 word3
floridify wordlist review my-words --due
```

## Testing

**Backend** (comprehensive):
```bash
cd backend
pytest tests/ -v                               # All tests
pytest tests/ --cov=src/floridify --cov-report=html  # With coverage
pytest tests/ -m "not slow"                    # Fast tests only
```

**Coverage**: 58 files, 19K lines, 707 tests, 80%+ coverage.
**Strategy**: Real MongoDB per test, real FAISS indices. Only external APIs mocked.

**Frontend**: Vitest configured but unused (gap identified).

## Quality Checks

```bash
# Backend
ruff check --fix && ruff format  # Lint + format
mypy src/ --strict               # Type check

# Frontend
npm run type-check               # TypeScript strict
prettier --write .               # Format
```

## Configuration

**Environment** (`.env`):
```bash
ENVIRONMENT=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

**API Keys** (`auth/config.toml`, **not in git**):
```toml
[openai]
api_key = "sk-..."
model = "gpt-5"
reasoning_effort = "high"

[embedding]
model = "Qwen/Qwen3-Embedding-0.6B"

[database]
development_url = "mongodb://localhost:27018/..."
production_url = "mongodb://..."
```

## Deployment

**Production** (AWS EC2 + DocumentDB):
```bash
./scripts/deploy  # Automated: SSH → sync secrets → build → deploy → health check
```

**CI/CD** (GitHub Actions):
- Auto-deploys on push to `main`
- Runs tests (backend pytest + frontend build)
- SSH to EC2, build containers, health check
- SSL auto-renewal via Let's Encrypt

**Production URL**: https://words.babb.dev

## Performance

| Operation | Target |
|-----------|--------|
| Lookup (cached) | <500ms |
| Lookup (uncached) | <5s |
| Search exact | <1ms |
| Search fuzzy | 10-50ms |
| Search semantic | 50-200ms |
| AI synthesis | <5s |
| CLI startup | 0.07s |
| Per-word cost | ~$0.02 |

## Documentation

| File | Scope |
|------|-------|
| `CLAUDE.md` | Project architecture (this file's technical counterpart) |
| `backend/CLAUDE.md` | Backend: 23 modules, pipelines, testing |
| `frontend/CLAUDE.md` | Frontend: components, stores, composables |
| `backend/src/floridify/*/CLAUDE.md` | 16 module-level guides |
| `docs/` | 100+ technical docs (architecture, search, AI, deployment) |

## Development Workflow

1. Write types in `backend/src/floridify/models/` (Pydantic)
2. Mirror types in `frontend/src/types/api.ts` (TypeScript)
3. Implement backend logic in `backend/src/floridify/core/`
4. Add API endpoint in `backend/src/floridify/api/routers/`
5. Write backend tests in `backend/tests/` (80%+ coverage)
6. Implement frontend in `frontend/src/components/custom/`
7. Add composable in `frontend/src/composables/`

## Why This Exists

Words are tools for thinking. An expanded vocabulary isn't about sounding smart—it's about having the right word when you need it.

**Traditional dictionaries fail**:
1. **Organization**: Definitions jumbled by historical order, not meaning
2. **Synthesis**: No consolidation (Wiktionary: 12 entries for "sanction", Oxford: 3—same meanings)
3. **Learning**: No spaced repetition, no progress tracking, no context

**Floridify fixes this**:
- **AI clustering**: Groups by meaning (sanction¹ approval vs sanction² penalty)
- **Multi-source synthesis**: Best of Wiktionary + Oxford + Apple + Free Dictionary
- **Learning integration**: SM-2 algorithm, Anki export, vocabulary suggestions
- **Performance**: Sub-second cached lookups, 0.07s CLI startup
- **Intelligence**: Semantic search finds related words by meaning, not spelling

Built for those who collect words like others collect stamps, who understand that language is the substrate of thought itself.

**Look up → Understand → Remember → Use**

## Troubleshooting

**Docker Issues**:
```bash
./scripts/dev --build                   # Rebuild images
docker-compose logs -f backend          # View logs
docker-compose down -v                  # Clean restart
```

**MongoDB Connection**:
```bash
docker-compose ps                       # Check if running
./scripts/start-ssh-tunnel.sh           # DocumentDB tunnel
```

**Frontend Build Errors**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run type-check
```

---

**License**: MIT
**Author**: Mike Babb (mike@babb.dev)
**Deployment**: https://words.babb.dev

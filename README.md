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

**Configuration** (add your OpenAI API key):
```bash
cp auth/config.toml.example auth/config.toml
# Edit auth/config.toml and add your OpenAI API key
```

## Core Features

### AI-Powered Synthesis
- **Deduplication**: 47 → 23 definitions (50% reduction, preserves quality)
- **Semantic clustering**: Groups by meaning, not etymology
- **Multi-source**: Synthesizes from Wiktionary + Oxford + Apple Dictionary
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
- **L3 Versioned**: MongoDB with content-addressable storage
- **Performance**: 10-50x speedup vs direct DB/API calls

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

**Full-stack application** with clear separation:
- **Backend**: Python 3.12+ FastAPI (23 modules, 179+ models, 111+ endpoints)
- **Frontend**: Vue 3 TypeScript (173 components, 12 Pinia stores)
- **Database**: MongoDB 7.0 with Beanie ODM
- **AI**: OpenAI GPT-5 series with 3-tier model selection
- **Search**: FAISS semantic + RapidFuzz fuzzy + marisa-trie exact
- **Infrastructure**: Docker containers, AWS EC2, DocumentDB, GitHub Actions CI/CD

**Data Flow**: User Query → Multi-Method Search → Provider Fetch → AI Synthesis → Cache → Response

## Key Technologies

**Backend**:
- **Framework**: FastAPI (async), Pydantic v2, Uvicorn
- **Database**: MongoDB + Motor (async driver) + Beanie ODM
- **AI**: OpenAI API, sentence-transformers (Qwen3-0.6B), FAISS
- **Search**: RapidFuzz (Rust), marisa-trie (C++), Bloom filters
- **Caching**: Multi-tier (OrderedDict + DiskCache + MongoDB versioning)
- **Package Manager**: UV (Astral, 10-100x faster than pip)

**Frontend**:
- **Framework**: Vue 3.5 (Composition API, `<script setup>`)
- **Language**: TypeScript 5.8 (strict mode, 100% coverage)
- **State**: Pinia 3.0 with localStorage persistence
- **UI**: shadcn/ui (123 components, Radix Vue, accessible)
- **Styling**: Tailwind CSS 4.1 with custom design system
- **Build**: Vite 7.0 with esbuild (fast bundling)

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
GET /api/v1/corpus/{id}                # Get corpus details

# Wordlist
GET /api/v1/wordlist/                  # List wordlists
POST /api/v1/wordlist/                 # Create wordlist
GET /api/v1/wordlist/{id}/due          # Get due words for review
```

**Performance Targets**:
- Lookup (cached): < 500ms
- Lookup (uncached): < 3s (includes AI synthesis)
- Search (exact): < 200ms
- Search (semantic): < 500ms
- AI synthesis: < 5s (parallel, 12 components)

## Configuration

**Environment** (`.env`):
```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

**API Keys** (`auth/config.toml`, **not in git**):
```toml
[openai]
api_key = "sk-..."
model = "gpt-5"              # Reasoning model (o-series)
reasoning_effort = "high"

[embedding]
model = "Qwen/Qwen3-Embedding-0.6B"  # 1024D, 64.33 MTEB

[database]
production_url = "mongodb://..."
development_url = "mongodb://localhost:27018/..."
```

## Testing

**Backend** (comprehensive):
```bash
cd backend
pytest tests/ -v                               # All tests
pytest tests/ --cov=src/floridify --cov-report=html  # With coverage
pytest tests/ -m "not slow"                    # Fast tests only
```

**Coverage**: 58 files, 19,000 lines, 639+ test functions, 80%+ coverage

**Frontend** (TO BE IMPLEMENTED):
```bash
cd frontend
npm test  # Vitest configured but unused (gap identified)
```

## Deployment

**Production** (AWS EC2 + DocumentDB):
```bash
./scripts/deploy  # Automated deployment

# Manual:
ssh ubuntu@44.216.140.209
cd /var/www/floridify
git pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose --profile ssl up -d
```

**CI/CD** (GitHub Actions):
- Auto-deploys on push to `main`
- Runs tests (backend pytest + frontend build)
- SSH to EC2, build containers, health check
- SSL auto-renewal via Let's Encrypt

**Production URL**: https://words.babb.dev

## CLI Commands

**Lookup**:
```bash
floridify lookup perspicacious           # Full definition
floridify lookup --no-ai perspicacious   # Raw provider data (skip AI)
floridify lookup --json perspicacious    # JSON output
```

**Search**:
```bash
floridify search serendipity         # Multi-method search
floridify search --fuzzy serendip    # Fuzzy only (typo-tolerant)
floridify search --semantic happy    # Semantic only (meaning-based)
```

**Corpus**:
```bash
floridify corpus list                                # List all corpora
floridify corpus rebuild --corpus-name english_master --semantic  # Rebuild with semantic indices
```

**Wordlist**:
```bash
floridify wordlist create my-words word1 word2 word3
floridify wordlist add my-words word4 word5
floridify wordlist review my-words --due  # Get due words
```

## Performance Metrics

**Codebase**:
- Backend: 23 modules, 179+ models, 111+ endpoints, 3 core pipelines
- Frontend: 173 components (123 shadcn/ui + 50 custom), 12 stores
- Tests: 58 files, 19,000 lines, 639+ functions (backend only)
- Documentation: 50+ technical docs, 3 CLAUDE.md files

**Performance**:
- CLI startup: 0.07s (vs 4.2s original, 98% improvement)
- L1 cache hit: 0.2ms avg (vs 50ms MongoDB, 250x faster)
- Search exact: < 1ms (marisa-trie O(m))
- Search semantic: 50-200ms (FAISS HNSW + embeddings)
- AI synthesis: < 5s (parallel processing)

**Cost**:
- Per-word synthesis: ~$0.02 (vs ~$0.15 naive GPT-4o)
- 87% reduction: 3-tier model selection + batching
- 50% discount: OpenAI Batch API for bulk operations

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

## Documentation

**Core Architecture**:
- `CLAUDE.md` - Project overview (this file's technical counterpart)
- `backend/CLAUDE.md` - Backend implementation details
- `frontend/CLAUDE.md` - Frontend architecture

**Technical Docs** (`docs/`):
- `architecture.md` - System design and data flow
- `search.md` - Multi-method search deep dive
- `ai.md` - AI synthesis pipeline
- `batch_processing_guide.md` - OpenAI Batch API
- `rest-api-architecture.md` - API design patterns
- `docker-ssl-ec2-deployment-guide.md` - AWS deployment
- `cli.md` - Command-line interface
- `anki.md` - Anki integration
- `PWA-Technical-Guide.md` - Progressive Web App

## Development Workflow

**Feature Development**:
1. Write types in `backend/src/floridify/models/` (Pydantic)
2. Mirror types in `frontend/src/types/api.ts` (TypeScript)
3. Implement backend logic in `backend/src/floridify/core/`
4. Add API endpoint in `backend/src/floridify/api/routers/`
5. Write backend tests in `backend/tests/` (80%+ coverage)
6. Implement frontend in `frontend/src/components/custom/`
7. Add composable in `frontend/src/composables/`

**Quality Checks**:
```bash
# Backend
ruff check --fix && ruff format
mypy src/ --strict
pytest tests/ -v

# Frontend
npm run type-check
prettier --write .
```

**Git Workflow**:
```bash
git checkout -b feature/my-feature
# ... make changes and quality checks
git commit -m "feat(search): add phonetic search mode"
git push origin feature/my-feature
# Create PR → GitHub Actions → Merge → Auto-deploy
```

## Common Tasks

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

# View API documentation
open http://localhost:8000/docs  # Swagger UI
```

## Troubleshooting

**Docker Issues**:
```bash
./scripts/dev --build  # Rebuild images
docker-compose logs -f backend  # View backend logs
docker-compose down -v  # Clean restart (removes volumes)
```

**MongoDB Connection**:
```bash
# Check if MongoDB is running
docker-compose ps

# Connect to MongoDB
docker-compose exec mongodb mongosh

# Check SSH tunnel (for DocumentDB)
ps aux | grep ssh
./scripts/start-ssh-tunnel.sh
```

**Frontend Build Errors**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run type-check  # Check for TypeScript errors
```

## Contributing

This is a private project. For issues or feature requests, contact mike@babb.dev.

## License

Proprietary. All rights reserved.

---

**Version**: January 2025
**Author**: Mike Babb (mike@babb.dev)
**Deployment**: https://words.babb.dev
**Repository**: Private

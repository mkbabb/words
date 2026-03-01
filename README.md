# Floridify

AI-enhanced dictionary. Multi-source definitions synthesized by meaning, not memorization—look up "sanction" and get two coherent senses (approval, penalty), not twelve jumbled entries. Python FastAPI backend, Vue 3 TypeScript frontend, MongoDB storage, OpenAI GPT-5 synthesis, FAISS semantic search.

[words.babb.dev](https://words.babb.dev)

## Quick Start

**Docker** (recommended):
```bash
git clone <repo-url> && cd floridify
./scripts/dev              # all services, hot reload
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

**Manual** (Python 3.12+, Node 20+):
```bash
# Backend
cd backend
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate && uv sync
cp auth/config.toml.example auth/config.toml  # add your OpenAI key
uv run scripts/run_api.py

# Frontend (separate terminal)
cd frontend && npm install && npm run dev

# CLI
./scripts/install-floridify
floridify lookup perspicacious
```

## Features

### Synthesis

Fetches from Wiktionary, Oxford, Apple Dictionary, and Free Dictionary in parallel. GPT-5 deduplicates, clusters by meaning, and generates definitions, pronunciation, etymology, and usage—all concurrently. Three-tier model routing (Nano/Mini/Full) keeps costs down.

### Search

Cascading with early termination:
- **Exact** (<1ms)—marisa-trie + Bloom filter
- **Fuzzy** (10–50ms)—RapidFuzz, handles typos ("perspicac" finds "perspicacious")
- **Semantic** (50–200ms)—FAISS HNSW + Qwen3-0.6B embeddings, "happy" finds "elated"

### Caching

Three tiers: in-memory LRU (0.2ms), DiskCache + ZSTD (5ms), content-addressable MongoDB with SHA-256 versioning. Cached lookups return in under 500ms.

### Learning

SM-2 spaced repetition (Bronze, Silver, Gold progression), Anki `.apkg` export, word lists with frequency tracking, vocabulary suggestions.

### Web & PWA

Mode-based SPA—lookup, wordlist, word-of-the-day. SSE streaming for real-time progress. Dark mode with paper textures. Offline-capable PWA with push notifications.

### CLI

```bash
floridify lookup perspicacious             # full definition
floridify lookup --no-ai perspicacious     # raw provider data
floridify lookup --json perspicacious      # JSON output
floridify search serendipity               # multi-method cascade
floridify search --semantic happy          # semantic only
floridify wordlist create my-words word1 word2 word3
floridify wordlist review my-words --due
```

Rich terminal UI, 0.07s startup via lazy imports, ZSH autocomplete.

## API

111+ endpoints. A few essentials:

```bash
GET  /api/v1/lookup/{word}              # full definition
GET  /api/v1/lookup/{word}/stream       # SSE streaming
GET  /api/v1/search?q={query}           # multi-method search
GET  /api/v1/search/{query}/suggestions # autocomplete
POST /api/v1/ai/synthesize/*            # 40+ generation endpoints
GET  /api/v1/wordlist/{id}/due          # due words for review
```

Full spec at `http://localhost:8000/docs` when the backend's running.

## Stack

- **Backend**: FastAPI, Pydantic v2, Beanie ODM, MongoDB 7.0, Motor (async), UV
- **AI/ML**: OpenAI GPT-5 (3-tier), sentence-transformers (Qwen3-0.6B), FAISS
- **Search**: marisa-trie, RapidFuzz, FAISS HNSW, Bloom filter
- **Cache**: OrderedDict LRU, DiskCache + ZSTD, MongoDB versioned (SHA-256)
- **Frontend**: Vue 3.5, TypeScript 5.9 strict, Pinia 3.0, shadcn/ui (Reka UI), Tailwind CSS 4.2, Vite 7.3
- **Infra**: Docker multi-stage, AWS EC2, nginx + Let's Encrypt, GitHub Actions

## Development

```bash
# Backend
cd backend
ruff check --fix && ruff format    # lint + format
mypy src/ --strict                 # type check
pytest tests/ -v                   # 707 tests, 80%+ coverage

# Frontend
cd frontend
npm run type-check                 # TypeScript strict
prettier --write .                 # format
```

Real MongoDB per test, real FAISS indices. Only external APIs mocked. See [`backend/CLAUDE.md`](backend/CLAUDE.md) and [`frontend/CLAUDE.md`](frontend/CLAUDE.md) for module-level details.

## Configuration

**Environment** (`.env`, not in git):
```bash
ENVIRONMENT=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

**API keys** (`backend/auth/config.toml`, not in git):
```toml
[openai]
api_key = "sk-..."
model = "gpt-5"

[embedding]
model = "Qwen/Qwen3-Embedding-0.6B"

[database]
development_url = "mongodb://localhost:27018/..."
```

## Deployment

```bash
./scripts/deploy    # SSH to EC2, sync secrets, build, deploy, health check
```

Push to `main` triggers GitHub Actions: test, build, deploy, SSL auto-renewal via Let's Encrypt. Production at [words.babb.dev](https://words.babb.dev).

## Why

I've been collecting and cataloguing words for years—an expanded lexicon lets you say exactly what you mean. Existing dictionaries scatter definitions across sources and order them by historical accident; Floridify pulls from all of them, deduplicates, clusters by meaning, and gives you something you can actually learn from. Spaced repetition and Anki export so the words stick.

## Documentation

Project architecture, module guides, and technical docs live in [`CLAUDE.md`](CLAUDE.md), the per-module `CLAUDE.md` files, and [`docs/`](docs/).

---

**License**: MIT | **Author**: Mike Babb (mike@babb.dev)

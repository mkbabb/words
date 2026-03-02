# Floridify

AI-enhanced dictionary and word-collecting tool. Fetches from Wiktionary, Oxford, Apple Dictionary, and Free Dictionary in parallel, then synthesizes the lot—deduplicating, clustering by semantic sense, generating pronunciation, etymology, and usage.

[mbabb.fi.ncsu.edu/words/](https://mbabb.fi.ncsu.edu/words/)

## Quick Start

```bash
# Docker (recommended)
git clone <repo-url> && cd floridify
./scripts/dev              # all services, hot reload
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs

# Manual (Python 3.12+, Node 20+)
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

Synthesis runs through a three-tier GPT-5 pipeline (Nano/Mini/Full) that deduplicates definitions, clusters them by meaning, and enhances each cluster with synonyms, examples, CEFR levels, and collocations—all concurrently via `asyncio.gather`.

Search cascades with early termination: exact match via marisa-trie and Bloom filter (<1ms), fuzzy via RapidFuzz for typos (10–50ms), semantic via FAISS HNSW with Qwen3-0.6B embeddings (50–200ms). Three tiers of caching sit behind it all—in-memory LRU, DiskCache with ZSTD compression, and content-addressable MongoDB with SHA-256 versioning.

Learning tools include SM-2 spaced repetition with mastery progression, Anki `.apkg` export, word lists with frequency tracking, and vocabulary suggestions. The web interface is a mode-based SPA (lookup, wordlist, word-of-the-day) with SSE streaming for real-time progress, dark mode with paper textures, and offline PWA support.

The CLI gives you the same lookup pipeline in the terminal with Rich formatting, 0.07s startup via lazy imports, and ZSH autocomplete:

```bash
floridify lookup perspicacious             # full definition
floridify lookup --no-ai perspicacious     # raw provider data
floridify search serendipity               # multi-method cascade
floridify search --semantic happy          # semantic only
floridify wordlist create my-words word1 word2 word3
floridify wordlist review my-words --due
```

## API

121 endpoints. Full spec at `http://localhost:8000/docs`. A few essentials:

```bash
GET  /api/v1/lookup/{word}              # full definition
GET  /api/v1/lookup/{word}/stream       # SSE streaming
GET  /api/v1/search?q={query}           # multi-method search
GET  /api/v1/search/{query}/suggestions # autocomplete
POST /api/v1/ai/synthesize/*            # AI generation endpoints
GET  /api/v1/wordlist/{id}/due          # due words for review
```

## Stack

**Backend**: FastAPI, Pydantic v2, Beanie ODM, MongoDB 7.0, Motor (async), UV
**AI/ML**: OpenAI GPT-5 (3-tier), sentence-transformers (Qwen3-0.6B), FAISS
**Search**: marisa-trie, RapidFuzz, FAISS HNSW, Bloom filter
**Cache**: OrderedDict LRU, DiskCache + ZSTD, MongoDB versioned (SHA-256)
**Frontend**: Vue 3.5, TypeScript 5.9 strict, Pinia, shadcn/ui (Reka UI), Tailwind CSS 4.2, Vite 7.3
**Infra**: Docker multi-stage, self-hosted (mbabb.fridayinstitute.net:1022, behind VPN), nginx

## Development

```bash
# Backend
cd backend
ruff check --fix && ruff format    # lint + format
mypy src/ --strict                 # type check
pytest tests/ -v                   # ~720 tests, 80%+ coverage

# Frontend
cd frontend
npm run type-check                 # TypeScript strict
prettier --write .                 # format
```

Real MongoDB per test, real FAISS indices—only external APIs mocked. See [`backend/CLAUDE.md`](backend/CLAUDE.md) and [`frontend/CLAUDE.md`](frontend/CLAUDE.md) for the full technical map.

## Configuration

Environment (`.env`, not in git):
```bash
ENVIRONMENT=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

API keys (`backend/auth/config.toml`, not in git):
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
./scripts/deploy    # SSH to server, sync secrets, build, deploy, health check
```

Server: `mbabb@mbabb.fridayinstitute.net -p 1022` (behind VPN). No CI/CD — deploy manually.

## Why

I've been collecting and cataloguing words for years—2,100+ entries and counting. An expanded lexicon is to the interlocutor as an expanded palette is to a painter: it lets you say precisely what you mean. Existing dictionaries scatter their definitions across sources and order them by historical accident; Floridify pulls from all of them, deduplicates, clusters by meaning, and produces something you can actually learn from. Spaced repetition and Anki export so the words stick.

Architecture docs, module guides, and technical references live in [`CLAUDE.md`](CLAUDE.md), the per-module `CLAUDE.md` files, and [`docs/`](docs/).

---

**License**: MIT | **Author**: Mike Babb (mike@babb.dev) | **Production**: [mbabb.fi.ncsu.edu/words/](https://mbabb.fi.ncsu.edu/words/)

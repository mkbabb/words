# Floridify

AI-enhanced dictionary that fetches from a panoply of providers in parallel, deduplicates and clusters definitions by semantic sense, then synthesizes the result with pronunciation, etymology, and real-world usage examples.

[mbabb.friday.institute/words/](https://mbabb.friday.institute/words/)

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Architecture](#architecture)
- [CLI](#cli)
- [API](#api)
- [Stack](#stack)
- [Configuration](#configuration)
- [Development](#development)
- [Why](#why)

## Quick Start

```bash
# Docker (recommended)
git clone <repo-url> && cd words
./scripts/dev.sh              # all services, hot reload
# Frontend: http://localhost:3004
# API: http://localhost:8003/docs

# Manual (Python 3.12+, Node 20+)
cd backend && uv sync && uv run scripts/run_api.py
cd frontend && npm install && npm run dev

# CLI
./scripts/install-floridify
floridify lookup perspicacious
```

## Features

**[AI Synthesis](docs/synthesis.md)**: 5-stage pipeline—dedup, cluster, synthesize, enhance, version—through a 3-tier GPT-5 routing (5.4/Mini/Nano) that produces one coherent entry from all provider data. Definitions get synonyms, examples, CEFR levels, collocations, and more via parallel enhancement.

**[Search Cascade](docs/search.md)**: Five methods cascading with early termination—exact via marisa-trie, prefix, substring via suffix array, fuzzy via BK-tree + phonetic + trigram, semantic via FAISS HNSW with Qwen3-0.6B embeddings. Quality gate before semantic fallback.

**[Versioning & Caching](docs/versioning.md)**: Content-addressable versioning (SHA-256) with 3-tier cache—in-memory LRU, DiskCache+ZSTD, MongoDB with delta compression. TimeMachine UI shows inline diffs between versions.

**Learning Tools**: SM-2 spaced repetition with mastery progression (Bronze→Silver→Gold), Anki `.apkg` export with AI-generated fill-in-the-blank and multiple-choice cards, word lists with frequency tracking.

**Frontend**: Mode-based Vue 3.5 SPA (lookup, wordlist, word-of-the-day) with SSE streaming, dark mode, paper textures, Clerk authentication, and offline PWA support.

## Architecture

```
User Query → Multi-Method Search → Provider Fetch (parallel) → AI Synthesis → Cache → Response
```

Seven dictionary providers, created via [`create_connector()`](backend/src/floridify/providers/factory.py):

| Provider | Type | Auth |
|----------|------|------|
| [Wiktionary](backend/src/floridify/providers/dictionary/scraper/wiktionary.py) | Scraper | None |
| [Apple Dictionary](backend/src/floridify/providers/dictionary/local/apple_dictionary.py) | Local (macOS) | None |
| [Oxford](backend/src/floridify/providers/dictionary/api/oxford.py) | API | `app_id` + `api_key` |
| [Merriam-Webster](backend/src/floridify/providers/dictionary/api/merriam_webster.py) | API | `api_key` |
| [Free Dictionary](backend/src/floridify/providers/dictionary/api/free_dictionary.py) | API | None |
| [WordHippo](backend/src/floridify/providers/dictionary/scraper/wordhippo.py) | Scraper | None |
| AI Synthesis | Generated | OpenAI key |

Plus two literature providers ([Gutenberg](backend/src/floridify/providers/literature/api/gutenberg.py), [Internet Archive](backend/src/floridify/providers/literature/api/internet_archive.py)) for literary example sourcing.

See [docs/architecture.md](docs/architecture.md) for the full system design.

## CLI

```bash
floridify lookup perspicacious             # full definition
floridify lookup --no-ai perspicacious     # raw provider data
floridify search serendipity               # multi-method cascade
floridify search --semantic happy          # semantic only
floridify wordlist create my-words word1 word2 word3
floridify wordlist review my-words --due
floridify anki export my-words             # Anki flashcard deck
```

## API

Full spec at `http://localhost:8003/docs`.

```
GET  /api/v1/lookup/{word}              # full definition
GET  /api/v1/lookup/{word}/stream       # SSE streaming
GET  /api/v1/search?q={query}           # multi-method search
GET  /api/v1/search/{query}/suggestions # autocomplete
POST /api/v1/ai/synthesize/*            # AI generation
GET  /api/v1/wordlist/{id}/due          # due words for review
```

## Stack

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI, Pydantic v2, Beanie ODM, MongoDB, Motor (async), UV |
| AI | OpenAI GPT-5 (3-tier: 5.4/Mini/Nano), Anthropic Claude, sentence-transformers (Qwen3-0.6B), FAISS |
| Search | marisa-trie, BK-tree + phonetic + trigram, suffix array, FAISS HNSW, Bloom filter |
| Cache | OrderedDict LRU, DiskCache + ZSTD, MongoDB versioned (SHA-256) |
| Frontend | Vue 3.5, TypeScript 5.9, Pinia, shadcn/ui (Reka UI), Tailwind CSS 4, Vite, Clerk |
| TTS | KittenTTS (English), Kokoro-ONNX (8 languages) |
| Infra | Docker multi-stage, nginx, self-hosted behind VPN |

## Configuration

Environment (`.env`, not in git):
```bash
ENVIRONMENT=development
BACKEND_PORT=8003
FRONTEND_PORT=3004
MONGO_TUNNEL_PORT=37117
```

API keys (`backend/auth/config.toml`, not in git—see [`config.example.toml`](config.example.toml)):
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
# Backend
cd backend
ruff check --fix && ruff format    # lint + format
mypy src/ --strict                 # type check
pytest tests/ -v                   # tests

# Frontend
cd frontend
npm run type-check                 # TypeScript strict
prettier --write .                 # format
```

Real MongoDB per test, real FAISS indices—only external APIs mocked. See [`backend/CLAUDE.md`](backend/CLAUDE.md) and [`frontend/CLAUDE.md`](frontend/CLAUDE.md) for the full technical map.

## Deployment

```bash
./scripts/deploy.sh    # SSH to server, sync secrets, build, deploy, health check
```

Server: `mbabb@mbabb.friday.institute -p 1022` (behind VPN). No CI/CD—deploy manually.

## Why

An expanded lexicon is to the interlocutor as an expanded palette is to the painter: it lets you say precisely what you mean. Existing dictionaries scatter definitions across sources and order them by historical accident. Floridify pulls from all of them, deduplicates, clusters by meaning, and produces something you can learn from.

---

[Architecture](docs/architecture.md) · [API](docs/api.md) · [Search](docs/search.md) · [AI Synthesis](docs/synthesis.md) · [Versioning](docs/versioning.md) · [Wordlist](docs/wordlist.md) · [Corpus](docs/corpus.md) · [Audio](docs/audio.md) · [CLI](docs/cli.md)

**License**: MIT · **Author**: Mike Babb · **Production**: [mbabb.friday.institute/words/](https://mbabb.friday.institute/words/)

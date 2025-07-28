# `floridify`

A dictionary system that understands words the way we learn them -- by meaning, not memorization.

## What It Is

`floridify` takes the usual dictionary muddle and organizes it sensibly. When you look up "bank," you don't get a wall of text; you get bank¹ (where money lives), bank² (river's edge), bank³ (to arrange). Each meaning stands alone, clear and learnable.

The backend runs on Python with FastAPI, the frontend on Vue 3. MongoDB stores everything, an LLM handles the synthesis, and Docker keeps it all running smoothly.

## Getting Started

```bash
# Spin up everything at once
./scripts/dev

# Open localhost:3000 in your browser
```

For the command line folk:

```bash
cd backend && uv sync
cp auth/config.toml.example auth/config.toml  # Add your OpenAI key
floridify lookup perspicacious
```

## How It Works

The search follows a simple cascade: first it tries an exact match, then fuzzy matching for typos, then semantic search for related concepts. If all else fails, an LLM generates something reasonable.

When you search a word, `floridify` fetches from multiple dictionaries simultaneously, uses an LLM to spot duplicates, groups similar meanings together, then enhances everything with examples and usage notes. The whole process takes 2-4 seconds.

## The Good Parts

### Smart Search

The system uses sentence transformers for semantic search—proper 384-dimensional embeddings, not keyword matching. Falls back gracefully to character and word-level matching when needed. Everything's cached with FAISS indices for speed.

### Learning Tools

Built-in spaced repetition using the SM-2 algorithm (the one Anki uses). Words progress from Bronze to Silver to Gold as you master them. Direct export to Anki if that's your preference—no manual card creation needed.

### Web Interface

A clean Vue app with all the modern niceties: dark mode, search history, persistent preferences. The sidebar appears automatically when a word has multiple distinct meanings. Typography first, with a focus on readability and usability. Tailwind CSS used pervasively and idiomatically for styling.

### Command Line

There's a Rich-powered CLI with Unicode formatting and progress bars. Looks beautiful, works everywhere.

## Development

Backend: `cd backend && uv run uvicorn src.floridify.api.main:app --reload`

Frontend: `cd frontend && npm run dev`

Or just use Docker: `./scripts/dev`

Tests: `pytest` for backend, `npm test` for frontend

## Deployment

Push to main and GitHub Actions handles everything. Or deploy manually:

```bash
./scripts/deploy
```

Runs on EC2 with Nginx handling SSL, DocumentDB for production data storage. Zero-downtime deployments, health checks, the works.

## Configuration

Drop your settings in `auth/config.toml`:

```toml
[api]
openai_api_key = "sk-..."
openai_model = "gpt-4o"  # Also supports o1/o3 for complex reasoning

[general]
default_provider = "wiktionary"
cache_duration_hours = 24
```

## API Endpoints

The basics:

- `/api/v1/lookup/{word}` - Full AI-enhanced definitions
- `/api/v1/search/{query}` - Multi-method search
- `/api/v1/ai/synthesize/*` - Generate specific components
- `/api/v1/batch/lookup` - Look up multiple words at once

Full docs at `localhost:8000/docs` when running.

## Why This Exists

Words are tools for thinking. An expanded vocabulary isn't about sounding smart; it's about having the right word when you need it. The notion of one's mind being incandescent necessitates a large vocabulary to deploy at a moment's notice: `floridify` aids with exactly that by way of system that's fast, performant, and beautiful.

Built for those who collect words like others collect stamps, who understand that language is the substrate of thought itself; a proxy for human understanding.

_Look up → Understand → Remember → Use_

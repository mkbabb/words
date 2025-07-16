# Floridify Backend - July 2025

## Architecture

**Python 3.12+** async web application with **FastAPI** REST API, **MongoDB + Beanie ODM** storage, **OpenAI API** integration, and **FAISS** semantic search.

**Pipeline**: Normalize → Search → Fetch → AI Synthesis → Cache → Display

## Directory Structure

```
src/floridify/
├── ai/                 # OpenAI integration, meaning extraction, synthesis
├── anki/               # Anki flashcard generation and export
├── api/                # FastAPI REST endpoints and middleware
├── batch/              # OpenAI Batch API processing utilities
├── caching/            # HTTP caching layer with decorators
├── cli/                # Rich CLI interface with command groups
├── connectors/         # Dictionary provider abstractions
├── core/               # Business logic pipelines (lookup, search)
├── legendre/           # Polynomial series approximation
├── list/               # Word list management with frequency tracking
├── models/             # Pydantic v2 data models + Beanie ODM
├── search/             # Multi-method search (exact → fuzzy → semantic → AI)
├── storage/            # MongoDB operations and caching
└── utils/              # Formatting, normalization, shared utilities
```

## Core Dependencies

**Web Framework**: FastAPI + Uvicorn (async), Pydantic v2 (validation)
**Database**: MongoDB + Motor (async driver) + Beanie ODM
**AI/ML**: OpenAI API, sentence-transformers, FAISS (CPU), spaCy
**Search**: RapidFuzz, Jellyfish (Rust/C++ backends), Marisa-trie, PyAhoCorasick
**Performance**: NumPy, SciPy, xxhash, asyncio
**CLI**: Rich (terminal UI), Click (commands)
**Development**: uv (package manager), pytest + pytest-asyncio, MyPy (strict), Ruff

## Key Files

**API**: `api/main.py` (FastAPI app), `api/routers/` (endpoints)
**Core**: `core/lookup_pipeline.py` (orchestration), `core/search_pipeline.py` (search)
**AI**: `ai/synthesizer.py` (definition synthesis), `ai/connector.py` (OpenAI)
**Models**: `models/models.py` (Word, Definition, SynthesizedDictionaryEntry)
**Search**: `search/core.py` (unified interface), `search/semantic.py` (FAISS)
**Storage**: `storage/mongodb.py` (Beanie operations)
**CLI**: `cli/__init__.py` (Rich interface), `scripts/floridify` (entry point)

## Configuration

**Package Management**: `pyproject.toml` (uv), `uv.lock` (deterministic deps)
**Auth**: `auth/config.toml` (OpenAI API key)
**Environment**: MongoDB localhost:27017, configurable rate limits
**Testing**: pytest async-aware, 95%+ coverage target

## Development

**Setup**: `uv venv && source .venv/bin/activate && uv sync`
**Quality**: MyPy strict mode, Ruff format/lint, pre-commit hooks
**Testing**: `pytest tests/` (async-aware)
**API**: `uvicorn floridify.api.main:app --reload` (port 8000)
**CLI**: `uv run scripts/floridify [command]`

## Critical Technologies

**Performance**: Async/await throughout, connection pooling, multi-level caching
**AI**: GPT-4 meaning extraction and synthesis, embedding-based semantic search
**Search**: Cascading fallback (exact → fuzzy → semantic → AI)
**Storage**: Document-based MongoDB with Beanie ODM
**NLP**: spaCy preprocessing, sentence-transformers embeddings, FAISS indexing
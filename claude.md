# Floridify - AI-Enhanced Dictionary System - July 2025

## Architecture

**Full-stack application** with **Python FastAPI** backend (port 8000) and **Vue 3** frontend (port 3000). **MongoDB** document storage, **OpenAI API** integration, **FAISS** semantic search, and **Rich CLI** interface.

**Data Flow**: User Input → Multi-Method Search → AI Synthesis → Hierarchical Display → Persistent Storage

## Repository Structure

```
/
├── backend/            # Python FastAPI API + CLI
│   ├── src/floridify/  # Core application package
│   ├── tests/          # Test suite
│   ├── scripts/        # CLI entry points
│   └── docs/           # Backend documentation
├── frontend/           # Vue 3 TypeScript SPA
│   ├── src/            # Source code
│   ├── public/         # Static assets
│   └── dist/           # Build output
├── docs/               # Comprehensive technical documentation
└── dev.sh              # Development server orchestration
```

## Development Environment

**Server Management**: `./scripts/dev` orchestrates Docker-based development environment
**Docker Containers**: Both frontend (localhost:3000) and backend (localhost:8000) run in Docker containers
**Assumption**: Frontend and backend servers are running continuously via Docker
**Restart Policy**: Never restart servers unless explicitly specified
**Monitoring**: Listen to port activity for logging and status information
**Browser Integration**: Leverage browserMCP for frontend state, logging, and debugging

## Core Technologies

**Backend**: Python 3.12+ (FastAPI, MongoDB, OpenAI API, FAISS, Rich CLI)
**Frontend**: Vue 3 + TypeScript (Tailwind CSS, shadcn/ui, Pinia, Vite)
**Database**: MongoDB with Beanie ODM
**AI**: OpenAI GPT-4 for meaning extraction and synthesis
**Search**: Multi-method cascade (exact → fuzzy → semantic → AI)
**Package Management**: uv (backend), npm/pnpm (frontend)

## Key Features

**AI-Powered Synthesis**: Meaning-based clustering before definition synthesis
**Multi-Method Search**: Cascading search with FAISS acceleration
**Hierarchical Display**: Unicode superscripts and separate panels
**Word List Processing**: Batch lookup with frequency tracking
**Anki Integration**: Direct flashcard export
**Rich CLI**: Beautiful terminal interface with progress tracking
**Web Interface**: Modern Vue 3 SPA with persistent state

## Development Workflow

**Setup**: 
- Backend: `cd backend && uv venv && source .venv/bin/activate && uv sync`
- Frontend: `cd frontend && npm install`

**Development**: 
- Docker mode (recommended): `./scripts/dev` (runs both servers in Docker containers)
- Native mode: `./scripts/dev --native` (runs servers directly without Docker)
- With logs: `./scripts/dev --logs` (starts containers and follows logs)
- Rebuild images: `./scripts/dev --build` (rebuilds Docker images)

**Testing**: Backend pytest, frontend Vitest
**Quality**: MyPy + Ruff (backend), TypeScript + Prettier (frontend)

## API Integration

**REST API**: Backend serves comprehensive endpoints at localhost:8000
**Frontend Proxy**: Vite proxies API requests to backend
**WebSocket**: Real-time features for search and processing
**CORS**: Configured for cross-origin development

## State Management

**Frontend**: Pinia with localStorage persistence
**Backend**: MongoDB with multi-level caching
**Search**: FAISS indices with embedding caching
**AI**: OpenAI response caching and batch processing

## Documentation

**Technical**: `/docs/` - comprehensive architecture, API, and feature documentation
**Backend**: `/backend/CLAUDE.md` - Python API and CLI specifics
**Frontend**: `/frontend/CLAUDE.md` - Vue 3 SPA implementation details
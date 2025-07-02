# Floridify - AI-Enhanced Dictionary

## Overview

AI-powered dictionary system with meaning-based clustering, comprehensive search, and batch word list processing. Provides intelligent word lookup with hierarchical display and beautiful CLI formatting.

## Core Features

**AI-Powered Meaning Extraction**: Identifies distinct semantic meanings before synthesis, preventing confusion between unrelated definitions

**Hierarchical Display**: Multiple meanings with Unicode superscripts and separate panels for clear organization

**Multi-Method Search**: Exact → fuzzy → semantic → AI fallback cascade with FAISS acceleration

**Word List Processing**: Batch dictionary lookup with frequency tracking and heat map visualization

**Rich CLI Interface**: Beautiful terminal formatting with progress tracking and consistent enum-based options

## Technology Stack

- **Python 3.12+** with modern typing and async/await patterns
- **MongoDB + Beanie ODM** for document storage and validation  
- **OpenAI API** with structured outputs for AI synthesis
- **FAISS + scikit-learn** for high-performance semantic search
- **Rich + Click** for beautiful CLI interface
- **Pydantic v2** for data validation and serialization

## Architecture

```
src/floridify/
├── models/           # Data models with Pydantic + Beanie ODM
├── ai/              # OpenAI integration and meaning extraction
├── connectors/      # Dictionary providers (Wiktionary, etc.)
├── search/          # Multi-method search engine with FAISS
├── storage/         # MongoDB operations and caching
├── word_list/       # Word list management and frequency tracking
├── cli/             # Rich terminal interface with shared lookup core
└── utils/           # Formatting, normalization, and utilities
```

## Processing Pipeline

1. **Normalize**: Word normalization and validation
2. **Search**: Multi-method word lookup with intelligent fallback
3. **Provider Fetch**: Retrieve definitions from dictionary sources  
4. **Meaning Extraction**: AI identifies distinct semantic meanings
5. **Synthesis**: Generate unified definitions per meaning cluster
6. **Format & Display**: Present with hierarchical panels and proper typography
7. **Cache**: Store results in MongoDB with automatic freshness validation

## Data Models

**Core Models**: `Word`, `Definition`, `SynthesizedDictionaryEntry`, `WordList`, `WordFrequency`
**Storage**: MongoDB documents with Beanie ODM integration  
**Validation**: Pydantic v2 with automatic serialization  
**Caching**: MongoDB-based caching with proper freshness checks

## Usage

```bash
# Setup
uv venv && source .venv/bin/activate && uv sync

# Word lookup with AI synthesis
uv run ./scripts/floridify lookup serendipity

# Search for similar words  
uv run ./scripts/floridify search word "cogn"

# Word list processing with full lookup pipeline
uv run ./scripts/floridify word-list create data/words.txt --name vocab

# Initialize search engine
uv run ./scripts/floridify search init
```

## Configuration

**API Keys**: Set OpenAI key in `auth/config.toml`  
**Database**: MongoDB connection (defaults to localhost:27017)  
**Model**: Configurable OpenAI model selection in settings

## Development Standards

**Python**: 3.12+ with modern typing (`list[str]`, `str | None`)  
**Style**: KISS/DRY principles, functional approach, comprehensive typing  
**Testing**: Async-aware tests with pytest, 95%+ coverage target  
**Quality**: MyPy strict mode, Ruff formatting, comprehensive error handling

## Documentation

**Primary**: This file (CLAUDE.md) contains all essential information  
**Status**: See `./docs/status.md` for current development state  
**CLI**: See `./docs/cli.md` for detailed interface documentation  

## AI Assistant Instructions

**Core Principles**: Use KISS/DRY, maintain type safety, comprehensive error handling  
**Architecture**: Follow meaning-based synthesis pipeline documented above  
**Testing**: Write tests for new functionality, maintain 95%+ coverage  
**Updates**: Regularly update `./docs/status.md` with current state (overwrite, don't append)
**Word Lists**: Process through complete lookup pipeline for database integration
**CLI Design**: Maintain enum-based options and consistent formatting across commands
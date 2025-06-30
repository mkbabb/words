# Floridify - AI-Enhanced Dictionary and Learning Tool

## Project Overview

Floridify is an augmented dictionary, thesaurus, and word learning tool that combines traditional dictionary functionality with modern AI capabilities, flashcard-based learning, and contextual examples from literature. The system aggregates data from multiple dictionary sources, synthesizes definitions using AI, and creates beautiful Anki flashcards for vocabulary learning.

## Core Architecture

### Data-Driven Design

-   **Provider-Based Architecture**: Dictionary entries organized by data provider (Wiktionary, Oxford, Dictionary.com) with AI synthesis as the primary view
-   **MongoDB Storage**: NoSQL database with Beanie ODM for idiomatic Python integration and automatic serialization
-   **AI Integration**: OpenAI o3 model for definition synthesis and example generation using bulk processing API
-   **Vector Embeddings**: Semantic search capabilities with cached embeddings

### Key Technologies

-   **Python 3.12+**: Modern Python with latest typing syntax and performance improvements
-   **MongoDB + Beanie ODM**: Document database with async ODM for automatic serialization and validation
-   **OpenAI API**: Latest API with bulk processing for cost optimization and embedding generation
-   **httpx**: Modern async HTTP client for dictionary API integration
-   **Pydantic v2**: Data validation and serialization with automatic MongoDB integration
-   **wikitextparser**: Proper MediaWiki markup parsing for Wiktionary data extraction
-   **genanki**: Anki package generation for .apkg file export
-   **pytest**: Comprehensive testing framework with async support
-   **Click + Rich**: Modern CLI framework with beautiful terminal formatting and enhanced lookup
-   **FAISS**: High-performance vector similarity search with timeout protection
-   **scikit-learn**: Machine learning tools for TF-IDF embeddings and semantic search

## Project Structure

```
floridify/
├── docs/                          # 📚 Complete project documentation
│   ├── architecture.md            # System architecture and data models
│   └── implementation.md          # Implementation plan and requirements
├── src/
│   ├── floridify/
│   │   ├── models/                # Pydantic v2 models with Beanie ODM integration
│   │   ├── connectors/            # Dictionary API integrations (Wiktionary, Oxford)
│   │   ├── ai/                    # OpenAI integration and AI synthesis
│   │   ├── prompts/               # Markdown-based prompt templates
│   │   ├── parsers/               # Apple Notes and word list parsing
│   │   ├── storage/               # MongoDB operations with Beanie ODM
│   │   ├── anki/                  # Complete Anki flashcard generation (.apkg export)
│   │   ├── cli/                   # Modern CLI interface with enhanced lookup
│   │   ├── search/                # Multi-method search engine with FAISS
│   │   └── utils/                 # Utilities for normalization and formatting
│   └── config/
│       └── settings.toml          # Configuration file with API keys
├── tests/                         # Comprehensive unit and integration tests
└── scripts/                       # Utility scripts and CLI tools
```

## Key Components

### Data Models (`src/floridify/models/`)

-   **Word**: Pydantic model representing a word with its text and associated embeddings dictionary
-   **DictionaryEntry**: Beanie Document (MongoDB collection) for main entries organized by provider
-   **ProviderData**: Pydantic model for provider-specific definitions and metadata
-   **Definition**: Pydantic model for individual word definitions with bound synonyms and examples
-   **SynonymReference**: Pydantic model for references between dictionary entries
-   **Examples**: Pydantic model for AI-generated and literature-based usage examples
-   **APIResponseCache**: Beanie Document for caching external API responses with TTL

### Search Engine (`src/floridify/search/`)

-   **SearchEngine**: Unified interface with exact, fuzzy, and semantic search methods
-   **SemanticSearch**: Multi-level embedding search with FAISS acceleration and timeout protection
-   **FuzzySearch**: Traditional fuzzy matching with multiple algorithms and automatic method selection
-   **TrieSearch**: Efficient exact and prefix matching using compressed trie data structures
-   **Enhanced Safety**: Division-by-zero protection, timeout handling, graceful degradation

### Dictionary Connectors (`src/floridify/connectors/`)

-   **WiktionaryConnector**: Free, comprehensive dictionary source with advanced wikitext parsing using wikitextparser
-   **OxfordConnector**: Premium academic dictionary with full API integration
-   **DictionaryComConnector**: Commercial dictionary service (stub implementation)
-   All connectors implement standardized interface with rate limiting and error handling

### AI Integration (`src/floridify/ai/`)

-   **Modern OpenAI Integration**: Latest API with structured outputs and Pydantic schemas
-   **DefinitionSynthesizer**: Per-word-type AI synthesis instead of flattened aggregation
-   **Enhanced Example Generation**: Contextual examples with proper formatting
-   **AI Fallback System**: Complete fallback for unknown words/phrases with phonetic pronunciation
-   **Model Capability Detection**: Automatic detection of reasoning vs standard models
-   **Bulk Processing**: Optimized API usage with comprehensive caching

### Enhanced CLI System (`src/floridify/cli/`)

-   **EnhancedWordLookup**: Intelligent lookup with search fallback and AI generation
-   **Rich Terminal Interface**: Beautiful formatting with cyan examples and bolded words
-   **Intelligent Cascading**: exact → fuzzy → AI generation with timeout protection
-   **Per-Word-Type Display**: Definitions organized by grammatical function
-   **Phonetic Pronunciations**: Auto-generated for AI fallback entries

### Word Processing Pipeline

1. **Apple Notes Parsing**: Extract words from formatted lists with deduplication
2. **Provider Data Fetching**: Parallel API calls to dictionary sources with advanced wikitext parsing
3. **Enhanced Lookup**: Multi-stage lookup with search engine fallback and AI generation
4. **AI Synthesis**: Generate unified definitions and examples via structured outputs
5. **Storage**: Persist complete entries to MongoDB using Beanie ODM with automatic validation
6. **Anki Generation**: Create beautiful flashcards with multiple choice and fill-in-the-blank formats

## Development Guidelines

### Code Style

-   **Modern Python**: Use Python 3.12+ features, lowercase typing (`list[str]`), union syntax (`str | None`)
-   **Functional Approach**: Prefer pure functions, immutable data, functional composition
-   **KISS/DRY Principles**: Keep implementations simple and avoid repetition
-   **Comprehensive Typing**: Full type annotations with mypy strict mode

### Testing Requirements

-   **Test-Driven Development**: Unit tests for all functions with 95%+ coverage
-   **Property-Based Testing**: Use Hypothesis for robust input validation
-   **Async Testing**: Comprehensive testing of async/await patterns
-   **Integration Testing**: End-to-end pipeline testing with mock services

### Configuration Management

-   **TOML Configuration**: All settings in `auth/config.toml`
-   **Environment Variables**: API keys and sensitive data via environment
-   **Rate Limiting**: Provider-specific limits configurable per service
-   **Model Configuration**: OpenAI model selection and parameters

## Key Files and Documentation

### Essential Documentation

-   **`./docs/architecture.md`**: Complete system architecture, data models, and component relationships
-   **`./docs/implementation.md`**: Detailed implementation plan, success criteria, and testing strategy

### Configuration

-   **`auth/config.toml`**: API keys, rate limits, processing parameters, model configuration

### Data Schema

All data models use Pydantic BaseModel with modern typing and Beanie ODM for MongoDB integration. See architecture documentation for complete schema definitions including:

-   Dictionary entry morphology and provider organization
-   Automatic validation and serialization with Pydantic
-   MongoDB document structure with Beanie
-   Foreign key relationships between entries
-   AI synthesis and embedding storage patterns

## Current Development Status

**Phase 1**: Foundation and Core Pipeline ✅ COMPLETED

-   ✅ Dictionary API connector implementation with advanced Wiktionary parsing using wikitextparser
-   ✅ MongoDB integration with Beanie ODM and Pydantic v2 validation
-   ✅ AI synthesis pipeline with OpenAI API integration and bulk processing capabilities
-   ✅ Prompt template system with markdown-based templates for easy customization
-   ✅ Complete Anki flashcard generation system with .apkg export functionality
-   ✅ Apple Notes and word list parsing infrastructure
-   ✅ Modern CLI interface with Rich formatting and full functionality
-   ✅ Complete word lookup system with AI comprehension integration
-   ✅ Hyper-efficient search engine with dual-approach architecture
-   ✅ End-to-end CLI workflow: `uv run ./scripts/floridify lookup word think`

**Phase 2**: Quality Assurance ✅ COMPLETED (Production Ready)

-   ✅ **Dependencies Restored**: All 39 essential dependencies including FAISS, scikit-learn, scipy
-   ✅ **Search Engine Enhanced**: Timeout protection, graceful fallback, division-by-zero safety
-   ✅ **AI System Modernized**: Structured outputs, per-word-type synthesis, AI fallback generation
-   ✅ **CLI System Complete**: Enhanced lookup with Rich formatting and intelligent search cascading
-   ✅ **Type Safety**: MyPy passes completely with proper error handling
-   ✅ **Core Tests Passing**: AI system, Anki generation, CLI integration working end-to-end
-   ✅ **Production Quality**: Robust error handling, timeout protection, graceful degradation

## Development Commands

```bash
# Setup development environment
uv venv && source .venv/bin/activate
uv sync

# Run tests with coverage
uv run pytest --cov=src/floridify --cov-report=term-missing

# Type checking  
uv run mypy src/

# Linting and formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# CLI commands (working end-to-end)
uv run ./scripts/floridify lookup word [WORD]
uv run ./scripts/floridify search init
uv run ./scripts/floridify search word [QUERY]
```

## Working CLI Examples

```bash
# Look up a word with AI synthesis
uv run ./scripts/floridify lookup word think

# Initialize search engine
uv run ./scripts/floridify search init

# Search for words
uv run ./scripts/floridify search word "cogn"
```

## AI Assistant Guidelines

When working on this project:

1. **Reference Documentation**: Always check `./docs/` for architectural decisions and implementation requirements
2. **Follow Data Schema**: Implement according to the Python dataclass definitions in the architecture
3. **Maintain Test Coverage**: Write comprehensive tests for all new functionality
4. **Respect Rate Limits**: Implement proper throttling for all external API calls
5. **Use Modern Python**: Leverage latest Python features and best practices
6. **Focus on Modularity**: Keep components loosely coupled and easily testable

## External APIs

### Required API Keys (in settings.toml)

-   **OpenAI**: For AI synthesis and embeddings (`openai = "sk-..."`)
-   **Oxford Dictionary**: Premium definitions (`oxford = "..."`)
-   **Dictionary.com**: Secondary source (`dictionary_com = "..."`)

### Rate Limiting Strategy

-   Configurable per-provider limits in TOML
-   Adaptive backoff based on HTTP 429 responses
-   Concurrent worker pools with semaphore throttling
-   Bulk processing for OpenAI to minimize costs

For complete technical details, implementation requirements, and architectural decisions, refer to the comprehensive documentation in `./docs/`.

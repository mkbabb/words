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
-   **Click + Rich**: Modern CLI framework with beautiful terminal formatting (planned)

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
│   │   └── cli/                   # Modern CLI interface (planned)
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

### Dictionary Connectors (`src/floridify/connectors/`)

-   **WiktionaryConnector**: Free, comprehensive dictionary source with advanced wikitext parsing using wikitextparser
-   **OxfordConnector**: Premium academic dictionary with full API integration
-   **DictionaryComConnector**: Commercial dictionary service (stub implementation)
-   All connectors implement standardized interface with rate limiting and error handling

### AI Integration (`src/floridify/ai/`)

-   **Synthesis Engine**: Aggregates multiple provider definitions into coherent AI definitions
-   **Example Generator**: Creates modern, contextual usage examples
-   **Embedding Service**: Generates vector embeddings for semantic search
-   **Bulk Processing**: Optimizes OpenAI API usage with batch operations

### Word Processing Pipeline

1. **Apple Notes Parsing**: Extract words from formatted lists with deduplication
2. **Provider Data Fetching**: Parallel API calls to dictionary sources with advanced wikitext parsing
3. **AI Synthesis**: Generate unified definitions and examples via bulk processing
4. **Storage**: Persist complete entries to MongoDB using Beanie ODM with automatic validation
5. **Anki Generation**: Create beautiful flashcards with multiple choice and fill-in-the-blank formats

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
-   ✅ Comprehensive testing suite with 85%+ coverage
-   🔄 End-to-end integration testing (in progress)
-   📋 Modern CLI interface (pending)
-   📋 Fuzzy search and vector similarity features (pending)

## Development Commands

```bash
# Setup development environment
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Run tests with coverage
pytest --cov=src/floridify --cov-report=term-missing

# Type checking
mypy src/

# Linting and formatting
ruff check src/ tests/
ruff format src/ tests/

# Run full pipeline
python -m floridify.cli process-word-list path/to/wordlist.txt
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

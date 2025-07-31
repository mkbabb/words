# Floridify Backend Test Suite

Comprehensive, modern test suite for the Floridify backend using pytest, UV, and modern testing patterns.

## Architecture

**Test Structure**: Layer-based testing with unit, integration, API, and performance tests
**Database Testing**: Isolated MongoDB test databases with Beanie ODM initialization  
**Async Testing**: Full async/await support with pytest-asyncio
**Mocking Strategy**: External service mocking (OpenAI, dictionary providers)
**Performance**: Built-in benchmarking with pytest-benchmark

## Directory Structure

```
tests/
├── conftest.py              # Global fixtures and test configuration
├── fixtures/                # Shared test data and utilities
│   └── test_data.py         # Comprehensive test datasets
├── unit/                    # Fast isolated unit tests
├── integration/             # Database and service integration tests
│   └── test_error_handling.py   # Comprehensive error scenarios
├── api/                     # REST API endpoint tests
│   ├── test_lookup_pipeline.py       # Lookup functionality
│   ├── test_search_pipeline.py       # Search functionality  
│   ├── test_corpus_pipeline.py       # Corpus management
│   ├── test_wordlist_pipeline.py     # Wordlist operations
│   └── test_ai_synthesis_pipeline.py # AI endpoints
├── performance/             # Performance benchmarking
│   └── test_benchmarks.py   # System performance tests
└── specs/                   # Testing documentation
    ├── rest_api_spec.md      # API specification
    ├── data_model_spec.md    # Data model documentation
    └── testing_approach.md   # Testing methodology
```

## Key Features

### Modern Test Infrastructure
- **UV Integration**: Native UV package manager support
- **Async Testing**: Full async/await patterns with proper fixture scoping
- **Database Isolation**: Unique test database per test function
- **Comprehensive Mocking**: OpenAI, dictionary providers, search engines
- **Performance Benchmarking**: Built-in performance regression detection

### Test Coverage Areas
- **REST API**: All 200+ endpoints with comprehensive validation
- **Lookup Pipeline**: Multi-provider, AI synthesis, caching, error handling
- **Search Pipeline**: Exact, fuzzy, semantic search with performance testing
- **Corpus Management**: TTL-based corpora with expiration validation
- **Wordlist Operations**: CRUD, file upload, spaced repetition, learning analytics
- **AI Synthesis**: All 40+ AI endpoints with proper rate limiting tests
- **Error Handling**: Malicious inputs, edge cases, system resilience

### Performance Testing
- **Benchmarking**: Response time thresholds for all major operations
- **Scalability**: Performance under increasing dataset sizes
- **Concurrency**: Behavior under concurrent load
- **Memory Usage**: Memory leak detection and efficiency monitoring

## Usage

### Quick Start
```bash
# Install dependencies
uv sync --dev

# Run quick smoke tests
./scripts/test.py --quick

# Run comprehensive test suite
./scripts/test.py --all
```

### Test Execution Modes
```bash
# Code quality checks
./scripts/test.py --lint

# Unit tests with coverage
./scripts/test.py --unit

# Integration tests
./scripts/test.py --integration

# Performance benchmarks
./scripts/test.py --performance

# Specific test file
./scripts/test.py --path tests/api/test_lookup_pipeline.py

# Generate comprehensive report
./scripts/test.py --report
```

### Direct pytest Usage
```bash
# All tests with coverage
uv run pytest tests/ --cov=src/floridify --cov-report=html

# Specific test categories
uv run pytest tests/api/ -m "not slow"
uv run pytest tests/performance/ --benchmark-only

# Parallel execution
uv run pytest tests/ -n auto

# Verbose with detailed output
uv run pytest tests/api/test_lookup_pipeline.py -v --tb=short
```

## Test Configuration

### pytest.ini Settings
- **Async Mode**: Automatic async test detection
- **Coverage**: 80% minimum coverage requirement
- **Markers**: Categorized test markers (slow, integration, benchmark, etc.)
- **Timeouts**: 300 second test timeout protection
- **Output**: Comprehensive reporting with HTML and XML outputs

### Environment Requirements
- **MongoDB**: localhost:27017 for integration tests
- **Python**: 3.12+ with UV package manager
- **Dependencies**: All dev dependencies via `uv sync --dev`

## Key Testing Patterns

### Database Testing
```python
@pytest.mark.asyncio
async def test_with_database(test_db, word_factory):
    word = await word_factory(text="test")
    # Test operates on isolated database
    assert word.id is not None
```

### API Testing
```python
@pytest.mark.asyncio
async def test_api_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/lookup/test")
    assert response.status_code == 200
```

### Performance Testing
```python
@pytest.mark.asyncio
async def test_performance(async_client, benchmark, performance_thresholds):
    result = await benchmark.pedantic(operation, iterations=10, rounds=5)
    assert benchmark.stats.stats.mean < performance_thresholds["lookup_simple"]
```

### Error Handling
```python
@pytest.mark.asyncio
async def test_error_scenario(async_client, mocker):
    mock_service = mocker.patch("service.method")
    mock_service.side_effect = Exception("Service error")
    
    response = await async_client.get("/api/endpoint")
    assert response.status_code == 500
```

## Quality Assurance

### Coverage Requirements
- **Minimum**: 80% line coverage
- **Target**: 90%+ coverage for critical paths
- **Reporting**: HTML, XML, and terminal coverage reports

### Performance Thresholds
- **Simple Lookup**: < 1.0 seconds
- **Complex Lookup**: < 2.0 seconds  
- **Search Operations**: < 0.2 seconds
- **Batch Operations**: < 5.0 seconds for 5 items
- **AI Synthesis**: < 3.0 seconds (with mocking)

### Error Coverage
- **Input Validation**: Malformed JSON, invalid parameters
- **Security**: SQL injection, XSS, path traversal attempts
- **System Resilience**: Database failures, API outages, timeouts
- **Concurrency**: Race conditions, deadlocks, resource conflicts

## Continuous Integration

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Run tests
  run: |
    uv sync --dev
    ./scripts/test.py --all --report
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: reports/coverage.xml
```

### Pre-commit Hooks
- **Linting**: Ruff format and lint checks
- **Type Checking**: MyPy validation
- **Test Execution**: Quick smoke tests on commit

## Debugging and Development

### Debugging Failed Tests
```bash
# Run with verbose output and stop on first failure
uv run pytest tests/api/test_lookup_pipeline.py -v -x --tb=long

# Run specific test with debugging
uv run pytest tests/api/test_lookup_pipeline.py::TestLookupPipelineAPI::test_lookup_basic_word_success -s
```

### Test Data Management
- **Fixtures**: Comprehensive test data in `fixtures/test_data.py`
- **Factories**: Model factories for consistent test data creation
- **Cleanup**: Automatic test data cleanup via fixtures
- **Isolation**: Each test operates on clean database state

This test suite provides comprehensive coverage of the Floridify backend with modern testing practices, performance validation, and robust error handling.
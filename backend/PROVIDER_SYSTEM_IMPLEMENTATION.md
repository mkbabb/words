# Versioned Provider Data System Implementation

## Overview

This document describes the comprehensive versioned provider data system implemented for Floridify. The system provides permanent, versioned storage of dictionary provider data with support for batch processing, wholesale downloads, and historical queries.

## Architecture Changes

### 1. Directory Structure

```
connectors/
├── base.py                    # Enhanced base classes with versioning support
├── api/                       # API-based connectors
│   ├── free_dictionary.py    # Free Dictionary API (NEW)
│   ├── merriam_webster.py    # Merriam-Webster API (NEW)
│   └── oxford.py              # Oxford Dictionary API (existing)
├── scraper/                   # Web scraping connectors
│   ├── dictionary_com.py      # Dictionary.com scraper (NEW)
│   └── wiktionary.py          # Wiktionary scraper (existing)
├── local/                     # Local system connectors
│   └── apple_dictionary.py    # Apple Dictionary (refactored)
├── batch/                     # Batch processing utilities (NEW)
│   ├── corpus_walker.py      # Systematic corpus processing
│   └── bulk_downloader.py    # Wholesale data downloads
└── wholesale/                 # Wholesale download implementations (NEW)
    └── wiktionary_wholesale.py # Wiktionary dump processor
```

### 2. Data Models

#### VersionedProviderData (NEW)
```python
class VersionedProviderData(Document, BaseMetadata):
    word_id: PydanticObjectId
    word_text: str
    language: Language
    provider: DictionaryProvider
    version_info: ProviderVersion
    raw_data: dict[str, Any]
    processed_data: dict[str, Any] | None
    provider_metadata: dict[str, Any]
    error: str | None
    error_code: str | None
```

#### BatchOperation (NEW)
```python
class BatchOperation(Document, BaseMetadata):
    operation_id: str
    operation_type: str
    provider: DictionaryProvider
    status: BatchStatus
    total_items: int
    processed_items: int
    failed_items: int
    checkpoint: dict[str, Any]  # For resume capability
```

#### ProviderConfiguration (NEW)
```python
class ProviderConfiguration(Document, BaseMetadata):
    provider: DictionaryProvider
    api_endpoint: str | None
    rate_limit_requests: int | None
    supports_batch: bool
    supports_bulk_download: bool
    last_bulk_download: datetime | None
```

## New Providers Implemented

### 1. Merriam-Webster API
- **Location**: `connectors/api/merriam_webster.py`
- **Features**: Definitions, pronunciations with audio, etymologies, first known use dates
- **Rate Limit**: 10 requests/second
- **Authentication**: API key required

### 2. Free Dictionary API
- **Location**: `connectors/api/free_dictionary.py`
- **Features**: Multiple definitions, IPA pronunciations, synonyms/antonyms
- **Rate Limit**: 60 requests/second
- **Authentication**: None (free API)

### 3. Dictionary.com Scraper
- **Location**: `connectors/scraper/dictionary_com.py`
- **Features**: Definitions, IPA and syllabic pronunciations, etymologies
- **Rate Limit**: 2 requests/second (conservative for scraping)
- **Authentication**: None

### 4. WordHippo Scraper (Placeholder)
- **Location**: Would be `connectors/scraper/wordhippo.py`
- **Status**: Structure created, implementation pending

## Batch Processing Systems

### 1. Corpus Walker
- **Purpose**: Systematically query providers for entire language corpora
- **Features**:
  - Resume capability for interrupted operations
  - Progress tracking with checkpoints
  - Parallel provider support
  - Configurable batch sizes

### 2. Bulk Downloader
- **Purpose**: Download and import wholesale data dumps
- **Features**:
  - Streaming download with progress tracking
  - Compressed file support (gzip, bzip2)
  - Memory-efficient processing
  - Deduplication via content hashing

### 3. Wiktionary Wholesale
- **Purpose**: Process complete Wiktionary XML dumps
- **Features**:
  - Full XML dump parsing
  - Title list extraction for corpus building
  - Wikitext parsing and conversion
  - Incremental updates support

## Version Management

### Version Tracking
- Each provider data entry has comprehensive versioning:
  - `provider_version`: Provider's internal version
  - `schema_version`: Our data schema version
  - `data_hash`: Content hash for deduplication
  - `is_latest`: Flag for current version

### Version Chain
- `superseded_by`: Link to newer version
- `supersedes`: Link to older version
- Enables full history traversal

## Repository Layer

### ProviderDataRepository
```python
# Get latest version
await repo.get_latest(word_id, provider)

# Get specific version
await repo.get_by_version(word_id, provider, version)

# Get history
await repo.get_history(word_id, provider, limit=10)

# Get data as of specific date
await repo.get_by_date(word_id, provider, date)

# Cleanup old versions
await repo.cleanup_old_versions(provider, keep_versions=3)
```

## Backward Compatibility

The system maintains **full backward compatibility** with the existing lookup pipeline:

1. **Existing `fetch_definition` method unchanged**: Returns `ProviderData` as before
2. **New `fetch_with_versioning` method**: Optional versioned storage
3. **Import paths preserved**: Old imports continue to work
4. **Drop-in replacement**: No changes required to existing code

### Usage in Existing Pipeline
```python
# Existing code continues to work
connector = WiktionaryConnector()
result = await connector.fetch_definition(word_obj, state_tracker)

# New versioning capability (optional)
versioned = await connector.fetch_with_versioning(word_obj, force_fetch=True)
```

## Key Design Decisions

### 1. No Enums for Part of Speech
- Uses strings directly for maximum flexibility
- Matches existing model structure
- Avoids type conversion overhead

### 2. Versioning as Enhancement
- Versioning layer added on top, not replacing existing functionality
- Allows gradual migration
- Preserves all existing behaviors

### 3. Persistent Storage vs Caching
- Provider data stored permanently in MongoDB
- Enables historical queries and data preservation
- Cache remains for performance optimization

### 4. Resume Capability
- All batch operations support interruption and resume
- Checkpoint data stored in BatchOperation documents
- Prevents data loss and duplicate work

## Usage Examples

### Corpus Walking
```python
from floridify.connectors.batch import CorpusWalker
from floridify.connectors.api import FreeDictionaryConnector

connector = FreeDictionaryConnector()
walker = CorpusWalker(connector, corpus_name="english_common")

# Walk corpus with resume support
batch_op = await walker.walk_corpus(
    operation_id="corpus_walk_2024",
    resume=True,
    max_words=10000
)
```

### Bulk Download
```python
from floridify.connectors.wholesale import WiktionaryWholesaleConnector

connector = WiktionaryWholesaleConnector(language="en")

# Download and import Wiktionary dump
batch_op = await connector.download_and_import(
    operation_id="wiktionary_bulk_2024",
    resume=True,
    batch_size=1000
)
```

### Provider Configuration
```python
from floridify.api.repositories import ProviderConfigurationRepository

repo = ProviderConfigurationRepository()

# Update rate limit
await repo.update_rate_limit(
    provider=DictionaryProvider.MERRIAM_WEBSTER,
    requests=100,
    period="minute"
)
```

## Testing

Test scripts provided:
- `scripts/test_providers.py`: Basic provider functionality
- `scripts/test_versioned_providers.py`: Versioning and batch operations

## Future Enhancements

1. **Additional Providers**:
   - WordHippo implementation
   - Urban Dictionary
   - Cambridge Dictionary
   - Etymology Online

2. **Data Quality**:
   - Duplicate detection across providers
   - Quality scoring for definitions
   - Conflict resolution strategies

3. **Performance**:
   - Provider response caching optimization
   - Batch operation parallelization
   - Index optimization for version queries

4. **Analytics**:
   - Provider reliability metrics
   - Coverage analysis
   - Usage patterns tracking

## Conclusion

The versioned provider data system provides a robust, scalable foundation for dictionary data management. It preserves all existing functionality while adding powerful new capabilities for data versioning, batch processing, and historical analysis. The system is designed for extensibility and can easily accommodate new providers and data sources.
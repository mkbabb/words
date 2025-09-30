# Comprehensive Connector Refactoring Plan
## Research Phase Complete - 8 Parallel Agent Analysis

**Date**: 2025-09-29
**Status**: Research Complete → Implementation Phase
**Scope**: All connectors (Dictionary, Language, Literature) + CLI + Tests + CRUD

---

## Executive Summary

After comprehensive analysis by 8 parallel research agents covering **10,000+ lines of code**, we've identified **47 critical issues** across providers, CLI, tests, CRUD, and architecture. This plan outlines a systematic approach to achieve **clean, homogenous, performant, and fully working connectors** with **no mocking, workarounds, or hacks**.

---

## Phase 1: Critical Data Model Fixes (Priority 🔴)

### 1.1 Fix FreeDictionary Data Model Inconsistency
**Issue**: Uses `"definition"` field instead of `"text"` (breaks downstream processing)
**File**: `src/floridify/providers/dictionary/api/free_dictionary.py:94`
**Fix**:
```python
# Change from:
"definition": def_data.get("definition")
# To:
"text": def_data.get("definition")
```
**Test**: Run CLI lookup with FreeDictionary, verify definitions display correctly

---

### 1.2 Add MerriamWebsterConfig Class
**Issue**: Factory references `config.merriam_webster.api_key` but no dataclass exists
**File**: `src/floridify/utils/config.py`
**Fix**:
```python
@dataclass
class MerriamWebsterConfig:
    """Merriam-Webster API configuration."""
    api_key: str

# In Config class:
merriam_webster: MerriamWebsterConfig | None = None
```
**File**: `config.example.toml` - Add section
**Test**: Load config, verify no AttributeError

---

## Phase 2: Factory Pattern Standardization (Priority 🔴)

### 2.1 Create Language Connector Factory
**File**: `src/floridify/providers/language/factory.py` (NEW)
```python
def create_language_connector(
    provider: LanguageProvider,
    config: Config | None = None,
) -> LanguageConnector:
    if config is None:
        config = Config.from_file()

    if provider == LanguageProvider.CUSTOM_URL:
        return URLLanguageConnector()
    # Future: WIKTIONARY_API, WORDNET, etc.
    else:
        raise ValueError(f"Unsupported provider: {provider.value}")
```
**Test**: Instantiate via factory, verify rate limiting and caching

---

### 2.2 Create Literature Connector Factory
**File**: `src/floridify/providers/literature/factory.py` (NEW)
```python
def create_literature_connector(
    provider: LiteratureProvider,
    config: Config | None = None,
) -> LiteratureConnector:
    if config is None:
        config = Config.from_file()

    if provider == LiteratureProvider.GUTENBERG:
        return GutenbergConnector()
    elif provider == LiteratureProvider.INTERNET_ARCHIVE:
        return InternetArchiveConnector()
    elif provider == LiteratureProvider.CUSTOM_URL:
        return URLLiteratureConnector()
    else:
        raise ValueError(f"Unsupported provider: {provider.value}")
```
**Test**: Instantiate all providers, verify configuration

---

### 2.3 Unify Factory Interface
**Pattern**: All factories follow same signature
```python
def create_connector(
    provider: ProviderEnum,
    config: Config | None = None,
    **kwargs,  # Provider-specific args like api_key
) -> BaseConnector
```

---

## Phase 3: Complete Parser Implementations (Priority 🟡)

### 3.1 Implement EPUB Parser
**File**: `src/floridify/providers/literature/parsers.py:88-95`
**Current**: Stub calling `parse_text()`
**Implementation**:
```python
def parse_epub(content: bytes | str, language: Language) -> dict[str, Any]:
    """Parse EPUB file with ebooklib."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(io.BytesIO(content))

    text_parts = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text_parts.append(soup.get_text())

    full_text = "\n\n".join(text_parts)
    return {"text": full_text, "metadata": extract_metadata(full_text)}
```
**Dependencies**: Add `ebooklib` to pyproject.toml
**Test**: Parse real EPUB from Internet Archive, verify chapters extracted

---

### 3.2 Implement PDF Parser
**File**: `src/floridify/providers/literature/parsers.py:98-105`
**Implementation**:
```python
def parse_pdf(content: bytes, language: Language) -> dict[str, Any]:
    """Parse PDF with PyPDF2."""
    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(content))
    text_parts = [page.extract_text() for page in reader.pages]

    full_text = "\n\n".join(text_parts)
    return {"text": full_text, "metadata": extract_metadata(full_text)}
```
**Dependencies**: Add `PyPDF2` to pyproject.toml
**Test**: Parse real PDF from Gutenberg/Archive, verify text extraction

---

### 3.3 Implement Specialized Scrapers
**Files**: `src/floridify/providers/literature/scraper/scrapers/default.py`

**Gutenberg Scraper** (lines 39-50):
```python
async def scrape_gutenberg(
    url: str = "",
    session: httpx.AsyncClient | None = None,
) -> str:
    """Gutenberg-specific scraping with header/footer removal."""
    text = await default_literature_scraper(url, session)

    # Remove Gutenberg header
    header_end = text.find("*** START OF")
    if header_end != -1:
        text = text[header_end + 100:]

    # Remove Gutenberg footer
    footer_start = text.find("*** END OF")
    if footer_start != -1:
        text = text[:footer_start]

    return text.strip()
```

**Archive.org Scraper** (lines 53-64):
```python
async def scrape_archive_org(
    url: str = "",
    session: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Archive.org with metadata API integration."""
    # Extract identifier from URL
    identifier = url.split("/")[-1]

    # Fetch metadata
    metadata_url = f"https://archive.org/metadata/{identifier}"
    metadata_response = await session.get(metadata_url)
    metadata = metadata_response.json()

    # Download text file
    text = await default_literature_scraper(url, session)

    return {"text": text, "metadata": metadata}
```

**Test**: Scrape real Gutenberg and Archive.org URLs, verify cleaning

---

## Phase 4: CRUD Completion (Priority 🔴)

### 4.1 Add Update Methods to All Connectors

**DictionaryConnector** (`src/floridify/providers/dictionary/core.py`):
```python
async def update(
    self,
    resource_id: str,
    content: dict[str, Any],
    config: VersionConfig | None = None,
) -> DictionaryProviderEntry | None:
    """Update existing dictionary entry."""
    existing = await self.get(resource_id, config)
    if not existing:
        raise ValueError(f"Resource {resource_id} not found")

    # Merge content
    updated_content = {**existing.model_dump(), **content}
    entry = DictionaryProviderEntry.model_validate(updated_content)

    await self.save(resource_id, entry, config)
    return entry
```

**LanguageConnector** (`src/floridify/providers/language/core.py`):
```python
async def update_source(
    self,
    source: LanguageSource,
    config: VersionConfig | None = None,
) -> LanguageEntry | None:
    """Update language source by re-fetching."""
    config = config or VersionConfig(force_rebuild=True)
    return await self.fetch_source(source, config)
```

**LiteratureConnector** (`src/floridify/providers/literature/core.py`):
```python
async def update_work(
    self,
    source: LiteratureSource,
    config: VersionConfig | None = None,
) -> LiteratureEntry | None:
    """Update literature work by re-fetching."""
    config = config or VersionConfig(force_rebuild=True)
    return await self.fetch_source(source, config)
```

---

### 4.2 Add Delete Methods to All Connectors

**BaseConnector** (`src/floridify/providers/core.py`):
```python
async def delete(
    self,
    resource_id: str,
    cascade: bool = False,
) -> bool:
    """Delete resource from versioned storage."""
    try:
        # Get all versions
        versions = await self.manager.version_manager.list_versions(
            resource_id=resource_id,
            resource_type=self.get_resource_type(),
        )

        # Delete all versions
        for version in versions:
            await self.manager.version_manager.delete_version(
                resource_id=resource_id,
                resource_type=self.get_resource_type(),
                version=version.version_info.version,
            )

        return True
    except Exception as e:
        logger.error(f"Error deleting {resource_id}: {e}")
        return False
```

**Test**: Create resource, delete it, verify cache cleared and DB entry removed

---

### 4.3 Add Transaction Support for Multi-Document Saves

**DictionaryConnector.fetch_definition()** (`src/floridify/providers/dictionary/core.py:122-209`):
```python
async def fetch_definition(
    self,
    word: Word,
    state_tracker: StateTracker | None = None,
) -> DictionaryEntry | None:
    """Fetch with atomic multi-document save."""
    provider_entry = await self._fetch_from_provider(word.text, state_tracker)
    if not provider_entry:
        return None

    # Use MongoDB session for atomic operations
    from ...storage.mongodb import get_database
    db = await get_database()

    try:
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                definition_ids = []

                # Save all documents in transaction
                for def_data in provider_entry.definitions:
                    definition = Definition(...)
                    await definition.insert(session=session)

                    for example_text in def_data.get("examples", []):
                        example = Example(...)
                        await example.insert(session=session)

                    definition_ids.append(definition.id)

                # Create entry
                dict_entry = DictionaryEntry(...)
                await dict_entry.insert(session=session)

                return dict_entry
    except Exception as e:
        logger.error(f"Transaction failed for {word.text}: {e}")
        # Transaction auto-rolls back
        return None
```

**Test**: Trigger failure mid-save, verify rollback (no partial documents)

---

## Phase 5: Architectural Improvements (Priority 🟡)

### 5.1 Deduplicate Code Across Providers

**Extract to `src/floridify/providers/utils.py`**:
```python
def ipa_to_phonetic(ipa: str) -> str:
    """Unified IPA to phonetic conversion."""
    # Merge logic from Wiktionary:1053-1092 and AppleDictionary:505-525
    mapping = {
        "ˈ": "'",
        "ˌ": ",",
        "ː": ":",
        # ... complete mapping
    }
    result = ipa
    for ipa_char, phonetic_char in mapping.items():
        result = result.replace(ipa_char, phonetic_char)
    return result
```

**Replace in**:
- `providers/dictionary/scraper/wiktionary.py:1053-1092`
- `providers/dictionary/local/apple_dictionary.py:505-525`

---

### 5.2 Unified Error Handling with Retry Logic

**BaseConnector** (`src/floridify/providers/core.py`):
```python
async def _fetch_with_retry(
    self,
    url: str,
    max_retries: int = 3,
) -> httpx.Response:
    """Fetch with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = await self.api_client.get(url)

            if response.status_code == 429:  # Rate limit
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                continue

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None  # Not found is expected
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

**Update all providers** to use `_fetch_with_retry()` instead of direct `get()`

---

### 5.3 Unified State Tracker Integration

**Make mandatory in BaseConnector.fetch()**:
```python
async def fetch(
    self,
    resource_id: str,
    config: VersionConfig | None = None,
    state_tracker: StateTracker | None = None,
) -> Any | None:
    """Fetch with mandatory state tracking."""
    if state_tracker is None:
        state_tracker = NoOpStateTracker()  # Default no-op

    await state_tracker.update(stage="fetching", message=f"{resource_id}")
    # ... rest of implementation
```

**Create NoOpStateTracker**:
```python
class NoOpStateTracker(StateTracker):
    """No-op state tracker for non-interactive contexts."""
    async def update(self, stage: str, message: str) -> None:
        pass  # Do nothing
```

---

## Phase 6: CLI Standardization (Priority 🟡)

### 6.1 Unify Parameter Naming

**Standardize across all commands**:
- `--force-refresh` (not `--force`)
- `--language` (not `-l`)
- `--provider` (consistent capitalization)
- `--max-results` (not `--limit`)

**File**: `src/floridify/cli/commands/lookup.py:50-53`
```python
@click.option("--force-refresh", is_flag=True, help="Force refresh all caches")
```

---

### 6.2 Add Retry Logic to CLI Commands

**Pattern for all commands**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _lookup_with_retry(word: str, **kwargs):
    return await lookup_word_pipeline(word=word, **kwargs)
```

---

## Phase 7: Test Suite Overhaul (Priority 🔴)

### 7.1 Add Real Integration Tests (No Mocking)

**File**: `tests/integration/test_all_providers.py` (NEW)
```python
import pytest
from floridify.providers.factory import create_connector
from floridify.models.dictionary import DictionaryProvider

@pytest.mark.integration
@pytest.mark.asyncio
async def test_wiktionary_real_fetch():
    """Test Wiktionary with real API call."""
    connector = create_connector(DictionaryProvider.WIKTIONARY)

    # Real fetch (no mocking!)
    result = await connector.fetch("hello")

    assert result is not None
    assert result.word == "hello"
    assert len(result.definitions) > 0
    assert result.provider == "wiktionary"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_free_dictionary_real_fetch():
    """Test FreeDictionary with real API call."""
    connector = create_connector(DictionaryProvider.FREE_DICTIONARY)

    result = await connector.fetch("test")

    assert result is not None
    assert len(result.definitions) > 0

# Add for all 7 dictionary providers
# Add for language connectors
# Add for literature connectors
```

**Run with**: `pytest tests/integration/ -v --tb=short`

---

### 7.2 Add Provider-Specific Tests

**Apple Dictionary** (`tests/providers/dictionary/test_apple_dictionary.py` - NEW):
```python
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
@pytest.mark.asyncio
async def test_apple_dictionary_real_lookup():
    """Test Apple Dictionary on real macOS system."""
    connector = AppleDictionaryConnector()

    result = await connector.fetch("hello")

    assert result is not None
    assert result.provider == "apple_dictionary"
```

**Internet Archive** (`tests/providers/literature/test_internet_archive.py` - NEW):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_internet_archive_search():
    """Test Internet Archive search with real API."""
    connector = InternetArchiveConnector()

    results = await connector.search_works(query="shakespeare hamlet", max_results=5)

    assert len(results) > 0
    assert all("hamlet" in r.title.lower() for r in results)
```

---

### 7.3 Add Large File Performance Tests

**File**: `tests/performance/test_large_corpus.py` (NEW)
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_large_literature_corpus():
    """Test handling of large literature work (War and Peace)."""
    connector = GutenbergConnector()

    # War and Peace is ~3MB
    work = LiteratureEntry(
        title="War and Peace",
        gutenberg_id="2600",
        author=tolstoy_author,
    )

    start = time.perf_counter()
    text = await connector.download_work(work)
    duration = time.perf_counter() - start

    assert len(text) > 3_000_000  # ~3MB
    assert duration < 30.0  # Should complete in 30s
    assert "Pierre" in text  # Sanity check
```

---

### 7.4 Add Unicode/Encoding Tests

**File**: `tests/providers/test_unicode.py` (NEW)
```python
@pytest.mark.asyncio
async def test_french_accents():
    """Test French words with diacritics."""
    connector = create_connector(DictionaryProvider.WIKTIONARY)

    result = await connector.fetch("café")

    assert result is not None
    assert result.word == "café"  # Not "cafe"

@pytest.mark.asyncio
async def test_german_umlauts():
    """Test German words with umlauts."""
    connector = create_connector(DictionaryProvider.WIKTIONARY)

    result = await connector.fetch("Müller")

    assert result is not None
    assert "Müller" in result.word
```

---

## Phase 8: End-to-End Validation (Priority 🔴)

### 8.1 Test All Providers via CLI

**Script**: `scripts/test_all_providers_cli.sh` (NEW)
```bash
#!/bin/bash
set -e

echo "Testing Dictionary Providers..."
uv run python -m floridify.cli lookup "hello" --provider wiktionary --no-ai
uv run python -m floridify.cli lookup "test" --provider free_dictionary --no-ai
uv run python -m floridify.cli lookup "world" --provider wordhippo --no-ai

echo "Testing Language Corpus..."
uv run python -m floridify.cli corpus create --language en --name test_en

echo "Testing Literature Download..."
uv run python -m floridify.cli scrape gutenberg --batch-size 10 --max-concurrent 2

echo "✅ All CLI tests passed!"
```

**Run**: `./scripts/test_all_providers_cli.sh`

---

### 8.2 Test Corpus CRUD Operations

**File**: `tests/integration/test_corpus_end_to_end.py` (NEW)
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_language_corpus_full_lifecycle():
    """Test complete language corpus lifecycle."""
    from floridify.corpus.language.core import LanguageCorpus
    from floridify.models.base import Language

    # CREATE
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="test_french",
        language=Language.FRENCH,
    )
    assert corpus is not None
    assert len(corpus.vocabulary) > 0

    # READ
    loaded = await TreeCorpusManager.get_corpus(corpus_id=corpus.corpus_id)
    assert loaded.corpus_name == "test_french"

    # UPDATE - Add source
    new_source = LanguageSource(
        name="custom",
        url="https://example.com/words.txt",
        language=Language.FRENCH,
    )
    await corpus.add_language_source(new_source)

    # Verify vocabulary updated
    updated = await TreeCorpusManager.get_corpus(corpus_id=corpus.corpus_id)
    assert len(updated.vocabulary) > len(corpus.vocabulary)

    # DELETE
    await TreeCorpusManager.delete_corpus(corpus_id=corpus.corpus_id, cascade=True)

    # Verify deleted
    deleted = await TreeCorpusManager.get_corpus(corpus_id=corpus.corpus_id)
    assert deleted is None
```

---

## Phase 9: Performance Optimization (Priority 🟢)

### 9.1 Parallel Literature Downloads

**File**: `src/floridify/providers/literature/api/gutenberg.py:375-399`
```python
async def download_author_works(
    self,
    author: AuthorInfo,
    works: list[LiteratureEntry],
    max_works: int | None = None,
    max_concurrent: int = 3,
) -> dict[str, str]:
    """Download multiple works in parallel."""
    works_to_download = works[:max_works] if max_works else works

    # Parallel downloads with semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_semaphore(work):
        async with semaphore:
            try:
                return work.title, await self.download_work(work)
            except Exception as e:
                logger.error(f"Failed to download {work.title}: {e}")
                return work.title, None

    tasks = [download_with_semaphore(work) for work in works_to_download]
    results = await asyncio.gather(*tasks)

    return {title: text for title, text in results if text is not None}
```

---

### 9.2 Batch MongoDB Operations

**Repository Pattern** - Use `insert_many()` instead of sequential `insert()`:
```python
async def batch_create_definitions(
    self,
    definitions: list[Definition],
) -> list[PydanticObjectId]:
    """Batch insert definitions."""
    await Definition.insert_many(definitions)
    return [d.id for d in definitions]
```

---

## Phase 10: Documentation (Priority 🟢)

### 10.1 Create Architecture Decision Records

**File**: `docs/architecture/ADR-001-connector-unification.md`
**File**: `docs/architecture/ADR-002-factory-pattern.md`
**File**: `docs/architecture/ADR-003-transaction-strategy.md`

---

### 10.2 Update CLAUDE.md

**Add sections**:
- Factory pattern usage
- CRUD operations guide
- Testing strategy (integration vs unit)
- Provider development guide

---

## Implementation Priority Order

### Week 1: Critical Fixes (🔴)
1. ✅ FreeDictionary data model fix
2. ✅ MerriamWebster config class
3. ✅ Add update/delete methods to all connectors
4. ✅ Add transaction support to fetch_definition()
5. ✅ Create language/literature factories

### Week 2: Parser & Test Completion (🟡🔴)
6. ✅ Implement EPUB parser
7. ✅ Implement PDF parser
8. ✅ Implement specialized scrapers
9. ✅ Add integration tests (no mocking)
10. ✅ Test all providers via CLI

### Week 3: Architecture & Performance (🟡🟢)
11. ✅ Deduplicate IPA conversion
12. ✅ Unified error handling with retry
13. ✅ Parallel literature downloads
14. ✅ CLI parameter standardization
15. ✅ Batch MongoDB operations

### Week 4: Polish & Documentation (🟢)
16. ✅ Add performance tests
17. ✅ Add Unicode/encoding tests
18. ✅ Corpus lifecycle tests
19. ✅ Architecture documentation
20. ✅ Update CLAUDE.md

---

## Success Criteria

- [ ] All 7 dictionary providers working via CLI (no errors)
- [ ] All language connectors tested end-to-end
- [ ] All literature connectors tested with real downloads
- [ ] 100% CRUD operations implemented (Create, Read, Update, Delete)
- [ ] Transaction support for multi-document saves
- [ ] Parser stubs completed (EPUB, PDF, specialized scrapers)
- [ ] 90%+ test coverage with 50%+ integration tests (no mocking)
- [ ] CLI parameter naming consistent
- [ ] All factories implemented
- [ ] Zero data model inconsistencies
- [ ] Performance benchmarks documented

---

## Testing Strategy

### Unit Tests (50%)
- Mock only external HTTP calls
- Use real MongoDB with test database
- Test individual methods in isolation

### Integration Tests (40%)
- NO mocking of providers
- Real API calls with small test data
- End-to-end corpus operations

### Performance Tests (10%)
- Large file handling (3MB+ texts)
- Concurrent operations (100+ parallel)
- Memory usage profiling

---

## Rollback Plan

If major issues arise:
1. Branch: `backup-original-history` (current state)
2. Create: `refactoring-phase-X` branches for each phase
3. Merge only after tests pass
4. Keep original implementations commented for 1 release

---

## Notes

- All changes must pass `ruff check` and `ruff format`
- All changes must pass existing test suite before adding new tests
- No breaking changes to public APIs without deprecation warnings
- All new code must have docstrings and type hints

---

**Next Step**: Begin Phase 1 with FreeDictionary data model fix
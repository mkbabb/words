# Providers Module - External Data Sources

Abstraction layer for dictionary APIs, web scrapers, local systems, literature sources. 11 providers with rate limiting, versioned caching.

## Structure

```
providers/
├── core.py              # BaseConnector, RateLimitPresets (315 LOC)
├── factory.py           # create_connector() factory (65 LOC)
├── utils.py             # AdaptiveRateLimiter, RespectfulHttpClient (422 LOC)
├── batch.py             # BatchOperation tracking (81 LOC)
├── dictionary/          # 7 dictionary providers
│   ├── core.py                      # DictionaryConnector base (209 LOC)
│   ├── models.py                    # DictionaryProviderEntry (42 LOC)
│   ├── api/                         # REST API providers
│   │   ├── oxford.py               # Oxford Dictionary API (360 LOC)
│   │   ├── merriam_webster.py      # Merriam-Webster API (381 LOC)
│   │   └── free_dictionary.py      # Free Dictionary API (124 LOC)
│   ├── scraper/                    # Web scrapers
│   │   ├── wiktionary.py           # Wiktionary scraper (1,113 LOC)
│   │   └── wordhippo.py            # WordHippo scraper (577 LOC)
│   ├── local/
│   │   └── apple_dictionary.py     # macOS Dictionary Services (525 LOC)
│   └── wholesale/
│       └── wiktionary_wholesale.py # Bulk XML dumps (561 LOC)
├── language/            # Language corpus providers
│   ├── core.py          # LanguageConnector base (176 LOC)
│   ├── models.py        # Language data models (109 LOC)
│   ├── parsers.py       # Text/CSV/JSON parsers (360 LOC)
│   ├── sources.py       # Built-in language sources (146 LOC)
│   └── scraper/
│       ├── url.py       # URLLanguageConnector (128 LOC)
│       └── scrapers/
│           ├── default.py           # Generic scraper (36 LOC)
│           └── wikipedia_french_expressions.py  # French-specific (93 LOC)
└── literature/          # Literature/book providers
    ├── core.py          # LiteratureConnector base (140 LOC)
    ├── models.py        # Literature data models (124 LOC)
    ├── parsers.py       # EPUB/PDF/HTML/Text parsers (199 LOC)
    ├── api/
    │   ├── gutenberg.py             # Project Gutenberg (405 LOC)
    │   └── internet_archive.py      # Internet Archive (209 LOC)
    ├── scraper/
    │   ├── url.py                   # URLLiteratureConnector (129 LOC)
    │   └── scrapers/
    │       └── default.py           # Default scraper (78 LOC)
    └── mappings/         # Pre-configured works (15 authors)
        ├── shakespeare.py (306 LOC)
        ├── dante.py (264 LOC)
        ├── dickens.py (212 LOC)
        └── 12 more authors
```

**Total**: 9,863 LOC across 56 files

## Dictionary Providers (7)

### API-Based (3)

**OxfordConnector** (`dictionary/api/oxford.py:360`):
- Auth: app_id + api_key
- Rate limit: API_CONSERVATIVE (2 RPS, 30s max delay)
- Features: Sense hierarchies, collocations, cross-references, IPA pronunciation, etymology
- Base URL: `https://od-api.oxforddictionaries.com/api/v2`

**MerriamWebsterConnector** (`dictionary/api/merriam_webster.py:381`):
- Auth: api_key
- Rate limit: API_STANDARD (5 RPS, 10s max delay)
- Features: Date of first use, sense hierarchies, audio URLs, etymologies, synonyms/antonyms
- Base URL: `https://dictionaryapi.com/api/v3/references/collegiate/json`

**FreeDictionaryConnector** (`dictionary/api/free_dictionary.py:124`):
- Auth: None (free API)
- Rate limit: API_FAST (10 RPS, 5s max delay)
- Features: Multiple definitions, audio URLs, POS, synonyms/antonyms, source attributions
- Base URL: `https://api.dictionaryapi.dev/api/v2/entries/en`

### Web Scrapers (2)

**WiktionaryConnector** (`dictionary/scraper/wiktionary.py:1,113` - **largest file**):
- Type: MediaWiki API + HTML scraping hybrid
- Rate limit: SCRAPER_RESPECTFUL (1 RPS, 60s max delay)
- Features:
  - WikitextCleaner (lines 37-153): Handles 15+ template types
  - Template parsing: quote, term/mention, gloss, label, wikilinks
  - HTML entity decoding, whitespace normalization
  - POS from section headers, multiple definitions, usage examples
  - Etymology chains, collocations, usage notes
- Key classes:
  - `WikitextCleaner:37-153` - Wikitext template handling
  - `WiktionaryConnector:155-1113` - Main scraper

**WordHippoConnector** (`dictionary/scraper/wordhippo.py:577`):
- Type: HTML scraper with parallel enhancement fetching
- Rate limit: SCRAPER_RESPECTFUL (1 RPS, 60s max delay)
- URL pattern: `https://www.wordhippo.com/what-is/the-meaning-of-the-word/{word}.html`
- Features: Definitions, POS, IPA pronunciation, etymology
- Parallel fetches: synonyms, antonyms, example sentences via separate endpoints

### Local System (1)

**AppleDictionaryConnector** (`dictionary/local/apple_dictionary.py:525`):
- Platform: macOS only (Darwin check)
- Type: PyObjC wrapper for CoreServices.DCSCopyTextDefinition
- Rate limit: LOCAL (100 RPS, no delays)
- Features: Zero network latency, system dictionaries, HTML parsing
- Dependencies: `pyobjc-framework-coreservices` (optional)

### Wholesale/Bulk (1)

**WiktionaryWholesaleConnector** (`dictionary/wholesale/wiktionary_wholesale.py:561`):
- Type: Bulk XML dump processing
- Rate limit: BULK_DOWNLOAD (0.5 RPS, 120s max delay)
- Format support: .bz2, .gz, raw XML
- Features:
  - `WiktionaryTitleListDownloader:~150-250` - Downloads title lists for languages
  - Language filtering (en, fr, es, etc.)
  - Streaming XML parser for large files (>1GB)
  - Resume capability via BatchOperation checkpoints
- Use case: Corpus building from complete language dumps

## Literature Providers (3)

### APIs (2)

**GutenbergConnector** (`literature/api/gutenberg.py:405`):
- Rate limit: SCRAPER_RESPECTFUL (1 RPS, 60s max delay)
- Features:
  - Search with complex query building
  - Multiple formats: ZIP, TXT, HTML
  - 15+ text cleaning patterns
  - Mirror fallback on primary failure
- Base URL: `https://www.gutenberg.org`

**InternetArchiveConnector** (`literature/api/internet_archive.py:209`):
- Rate limit: SCRAPER_RESPECTFUL (1 RPS, 60s max delay)
- Features: Advanced search API, metadata extraction
- Base URL: `https://archive.org`

### Pre-configured Works (15 authors)

**Author mappings** (`literature/mappings/` - 15 files):
- Shakespeare (306 LOC), Dante (264 LOC), Dickens (212 LOC)
- Sophocles, Virgil, Tolstoy, Ovid, Goethe, Aeschylus, Chaucer
- Cervantes, Milton, Homer, Joyce, Euripides
- Total: ~2,500 LOC of pre-configured literary works

## Language Providers

**LanguageConnector** (`language/core.py:176`):
- Base class for language corpus providers
- Features: URL fetching, parsing (text/CSV/JSON), vocabulary extraction

**4 parsers** (`language/parsers.py:360`):
- `parse_text_lines` - One word per line, frequency lists
- `parse_json_vocabulary` - Flexible JSON structures
- `parse_csv_words` - CSV with word/frequency columns
- `parse_scraped_data` - Custom scraper output

## Base Connector

**BaseConnector** (`core.py:315` - abstract class):

```python
class BaseConnector(ABC):
    config: ConnectorConfig
    rate_limiter: AdaptiveRateLimiter
    _scraper_session: httpx.AsyncClient | None
    _api_client: httpx.AsyncClient | None

    # Abstract methods (required by subclasses)
    @abstractmethod
    def get_resource_type(self) -> ResourceType
    @abstractmethod
    def get_cache_namespace(self) -> CacheNamespace
    @abstractmethod
    def model_dump(content: Any) -> Any
    @abstractmethod
    async def fetch(resource_id, config, state_tracker) -> Any
    @abstractmethod
    async def _fetch_from_provider(query, state_tracker) -> Any

    # Concrete methods
    async def get_or_fetch(resource_id, ...) -> Any:
        # Try cache first, fetch if not found

    async def get(resource_id, config) -> Any:
        # Get from versioned storage

    async def save(resource_id, content, config):
        # Save to versioned storage

    @property
    def scraper_session(self) -> httpx.AsyncClient:
        # HTTP/2 session with keepalive

    @property
    def api_client(self) -> httpx.AsyncClient:
        # HTTP/2 session for APIs

    async def close():
        # Cleanup both sessions
```

## Rate Limiting

**AdaptiveRateLimiter** (`utils.py:422`):

Exponential backoff with adaptive speed-up:

```python
class AdaptiveRateLimiter:
    config: RateLimitConfig
    current_rps: float
    consecutive_successes: int
    consecutive_errors: int
    backoff_until: float

    async def acquire():
        # 1. Check backoff period
        if now < self.backoff_until:
            await asyncio.sleep(self.backoff_until - now)

        # 2. Calculate inter-request delay
        min_interval = 1.0 / self.current_rps
        time_since_last = now - self.last_request_time

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            sleep_time += random.uniform(0.1, 0.3)  # Jitter
            await asyncio.sleep(sleep_time)

        self.last_request_time = now

    def record_success():
        self.consecutive_successes += 1
        self.consecutive_errors = 0

        # Speed up after success_threshold (default: 10)
        if self.consecutive_successes >= self.config.success_threshold:
            self.current_rps *= self.config.success_speedup  # 1.05-1.2x
            self.consecutive_successes = 0

    def record_error(retry_after: float | None = None):
        self.consecutive_errors += 1
        self.consecutive_successes = 0

        # Exponential backoff
        if retry_after and self.config.respect_retry_after:
            self.backoff_until = now + retry_after
        else:
            backoff_delay = min(
                self.config.min_delay * (self.config.backoff_multiplier ** self.consecutive_errors),
                self.config.max_delay
            )
            self.backoff_until = now + backoff_delay

        # Reduce rate
        self.current_rps = max(
            self.current_rps / self.config.backoff_multiplier,
            self.config.base_requests_per_second / 4
        )

        if self.consecutive_errors >= self.config.max_consecutive_errors:
            raise RateLimitError(...)
```

**6 Rate Limit Presets** (`core.py:38-109`):

| Preset | RPS | Min Delay | Max Delay | Speedup | Retry-After |
|--------|-----|-----------|-----------|---------|-------------|
| API_FAST | 10 | 0.1s | 5s | 1.2x | No |
| API_STANDARD | 5 | 0.2s | 10s | 1.1x | No |
| API_CONSERVATIVE | 2 | 0.5s | 30s | 1.05x | No |
| SCRAPER_RESPECTFUL | 1 | 1s | 60s | None | Yes |
| SCRAPER_AGGRESSIVE | 2 | 0.5s | 30s | 1.05x | Yes |
| BULK_DOWNLOAD | 0.5 | 2s | 120s | None | No |
| LOCAL | 100 | 0s | 0s | None | No |

## RespectfulHttpClient

**Rate-limited HTTP client** (`utils.py:192-275`):

```python
class RespectfulHttpClient:
    rate_limiter: AdaptiveRateLimiter
    _session: httpx.AsyncClient

    async def get(url, **kwargs) -> httpx.Response:
        # 1. Apply rate limiting gate
        await self.rate_limiter.acquire()

        # 2. Make request
        response = await self._session.get(url, **kwargs)

        # 3. Handle responses
        if response.status_code == 429:
            # Extract Retry-After header
            retry_after = response.headers.get("Retry-After")
            self.rate_limiter.record_error(float(retry_after) if retry_after else None)
            raise RateLimitError(...)
        elif response.status_code >= 500:
            self.rate_limiter.record_error()
            raise ScrapingError(...)
        elif response.status_code >= 400:
            raise ScrapingError(...)
        else:
            self.rate_limiter.record_success()
            return response
```

**Context manager** (`utils.py:351-369`):
```python
@asynccontextmanager
async def respectful_scraper(source, rate_config=None, **kwargs):
    rate_config = rate_config or RateLimitConfig(base_requests_per_second=2.0)
    rate_limiter = AdaptiveRateLimiter(rate_config)

    async with RespectfulHttpClient(rate_limiter, **kwargs) as client:
        try:
            yield client
        except Exception as e:
            logger.error(f"Scraping session failed for {source}: {e}")
            raise
```

## Parsing Logic

### Wiktionary Wikitext (`dictionary/scraper/wiktionary.py:37-153`)

**WikitextCleaner** handles 15+ template types:

| Template | Handling | Example |
|----------|----------|---------|
| Quote templates | Removed | `{{quote-book\|...}}` → removed |
| Term/mention/lang/link | Keep inner content | `{{l\|en\|word}}` → "word" |
| Gloss | Parentheses | `{{gloss\|meaning}}` → "(meaning)" |
| Label/qualifier | Parentheses | `{{lb\|en\|informal}}` → "(informal)" |
| Other templates | Extract first arg | `{{synonym of\|en\|word}}` → "word" |
| Wikilinks | Use display text | `[[word\|display]]` → "display" |

**Process**: Parse with `wikitextparser` → iterate templates → convert wikilinks → regex cleanup → decode HTML entities → normalize whitespace

### Literature Parsing (`literature/parsers.py:199`)

**5 parser functions**:

```python
def parse_text(content: dict | str) -> str:
    """Clean text (remove page numbers, artifacts)"""

def parse_markdown(content: str) -> str:
    """Strip headers, bold, links → plain text"""

def parse_html(content: str) -> str:
    """Remove tags, decode entities → plain text"""

def parse_epub(content: bytes) -> str:
    """Extract from all chapters via ebooklib"""
    book = epub.read_epub(io.BytesIO(content))
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text_parts.append(soup.get_text())
    return parse_text("\n\n".join(text_parts))

def parse_pdf(content: bytes) -> str:
    """Extract from all pages via pypdf"""
```

## Factory Pattern

**create_connector()** (`factory.py:65`):

```python
def create_connector(provider: DictionaryProvider) -> DictionaryConnector:
    """Factory pattern for dictionary connectors"""
    match provider:
        case DictionaryProvider.WIKTIONARY:
            return WiktionaryConnector()
        case DictionaryProvider.OXFORD:
            return OxfordConnector()
        case DictionaryProvider.MERRIAM_WEBSTER:
            return MerriamWebsterConnector()
        case DictionaryProvider.FREE_DICTIONARY:
            return FreeDictionaryConnector()
        case DictionaryProvider.APPLE_DICTIONARY:
            return AppleDictionaryConnector()
        case DictionaryProvider.WORDHIPPO:
            return WordHippoConnector()
        case _:
            raise ValueError(f"Unknown provider: {provider}")
```

## External Dependencies

| Library | Purpose | Used By |
|---------|---------|---------|
| httpx[http2] | Async HTTP with HTTP/2 | All network providers |
| BeautifulSoup4 | HTML/XML parsing | Wiktionary, WordHippo, Gutenberg |
| wikitextparser | MediaWiki wikitext | Wiktionary scraper |
| pypdf | PDF extraction | Literature parser |
| ebooklib | EPUB parsing | Literature parser |
| pyobjc-framework-coreservices | macOS Dictionary | Apple Dictionary (optional) |

## Design Patterns

- **Abstract Base Class** - BaseConnector for all providers
- **Factory** - create_connector() for provider instantiation
- **Context Manager** - respectful_scraper() with automatic cleanup
- **Adapter** - Wraps httpx with rate limiting
- **Singleton** - Global connector instances (optional)
- **Strategy** - Pluggable parsers (text, JSON, CSV, EPUB, PDF)
- **Template Method** - BaseConnector defines workflow, subclasses implement details

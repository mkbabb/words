# providers/

External data sources. 7 dictionary providers, 2 literature APIs, rate limiting.

```
providers/
├── core.py                 # BaseConnector, ConnectorConfig
├── factory.py              # create_connector() factory
├── batch.py                # BatchOperation tracking
├── rate_limiting.py        # AdaptiveRateLimiter with exponential backoff
├── http_client.py          # RespectfulHttpClient
├── dictionary/
│   ├── core.py             # DictionaryConnector abstract
│   ├── models.py           # Dictionary provider models
│   ├── api/                # Oxford, Merriam-Webster, Free Dictionary
│   ├── scraper/            # Wiktionary (+ wikitext_cleaner, wiktionary_parser), WordHippo
│   ├── local/              # Apple Dictionary (macOS, pyobjc)
│   └── wholesale/          # Wiktionary bulk XML processing
├── language/
│   ├── core.py             # LanguageConnector
│   ├── parsers.py          # 4 vocabulary parsers (text, JSON, CSV, custom)
│   ├── models.py           # Language source models
│   ├── sources.py          # Source definitions
│   └── scraper/scrapers/   # URLLanguageConnector, Wikipedia French expressions
└── literature/
    ├── core.py             # LiteratureConnector
    ├── models.py           # Literature models
    ├── parsers.py          # Format parsers (text, MD, HTML, EPUB, PDF)
    ├── api/                # gutenberg.py, internet_archive.py
    ├── scraper/            # URL scraper
    └── mappings/           # 15 author mappings (Shakespeare, Homer, Dante, Joyce, etc.)
```

## Dictionary Providers

| Provider | Type | Rate |
|----------|------|------|
| Wiktionary | Scraper (MediaWiki API + HTML) | 15 RPS |
| WordHippo | Scraper (HTML) | 1 RPS |
| Apple Dictionary | Local (macOS pyobjc) | unlimited |
| Wiktionary Wholesale | Bulk XML dumps | 0.5 RPS |
| Oxford | API (premium) | 2 RPS |
| Merriam-Webster | API (collegiate) | 5 RPS |
| Free Dictionary | API (free) | 10 RPS |

## Rate Limiting

`AdaptiveRateLimiter` (in `rate_limiting.py`): exponential backoff on errors, speed-up after N consecutive successes, respects Retry-After header, random jitter (0.1–0.3s).

Presets: API_FAST (10 RPS), API_STANDARD (5), API_CONSERVATIVE (2), SCRAPER_RESPECTFUL (1), BULK_DOWNLOAD (0.5), LOCAL (100).

## HTTP Client

`RespectfulHttpClient` (in `http_client.py`): wraps httpx with rate limiter integration.

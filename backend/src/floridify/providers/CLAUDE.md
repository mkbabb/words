# providers/

External data sources. 7 dictionary providers, 2 literature APIs, rate limiting.

```
providers/
├── core.py (315)           # BaseConnector, ConnectorConfig
├── factory.py (65)         # create_connector() factory
├── utils.py (542)          # AdaptiveRateLimiter, RespectfulHttpClient
├── batch.py (80)           # BatchOperation tracking
├── dictionary/
│   ├── core.py (219)       # DictionaryConnector abstract
│   ├── models.py (42)      # Dictionary provider models
│   ├── api/                # Oxford (360), Merriam-Webster (381), Free Dictionary (124)
│   ├── scraper/            # Wiktionary (1,121), WordHippo (577)
│   ├── local/              # Apple Dictionary (525, macOS pyobjc)
│   └── wholesale/          # Wiktionary bulk XML (561)
├── language/               # ~1,081 LOC
│   ├── core.py (176)       # LanguageConnector
│   ├── parsers.py (360)    # 4 vocabulary parsers (text, JSON, CSV, custom)
│   ├── models.py (113)     # Language source models
│   ├── sources.py (147)    # Source definitions
│   └── scraper/            # URLLanguageConnector (129), Wikipedia French (93)
└── literature/             # ~1,300 LOC
    ├── core.py (140)       # LiteratureConnector
    ├── models.py (124)     # Literature models
    ├── parsers.py (215)    # 5 format parsers (text, MD, HTML, EPUB, PDF)
    ├── api/                # Gutenberg (405), Internet Archive (209)
    ├── scraper/            # URL scraper (129)
    └── mappings/           # 15 author mappings (Shakespeare, Dante, Dickens, ...)
```

## Dictionary Providers

| Provider | Type | Rate | LOC |
|----------|------|------|-----|
| Wiktionary | Scraper (MediaWiki API + HTML) | 15 RPS | 1,121 |
| WordHippo | Scraper (HTML) | 1 RPS | 577 |
| Apple Dictionary | Local (macOS pyobjc) | unlimited | 525 |
| Wiktionary Wholesale | Bulk XML dumps | 0.5 RPS | 561 |
| Oxford | API (premium) | 2 RPS | 360 |
| Merriam-Webster | API (collegiate) | 5 RPS | 381 |
| Free Dictionary | API (free) | 10 RPS | 124 |

## Rate Limiting

AdaptiveRateLimiter: exponential backoff on errors, speed-up after N consecutive successes, respects Retry-After header, random jitter (0.1-0.3s).

Presets: API_FAST (10 RPS), API_STANDARD (5), API_CONSERVATIVE (2), SCRAPER_RESPECTFUL (1), BULK_DOWNLOAD (0.5), LOCAL (100).

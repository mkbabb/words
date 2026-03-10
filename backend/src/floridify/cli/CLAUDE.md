# cli/

Click CLI with Rich terminal UI. Lazy imports for heavy modules (torch, FAISS, sentence-transformers).

```
cli/
├── __init__.py
├── __main__.py
├── cli.py                  # Click app, main entry point
├── completion.py           # ZSH autocomplete
├── commands/
│   ├── lookup.py           # floridify lookup <word> [--no-ai] [--json] [--providers]
│   ├── search.py           # floridify search <query> [--fuzzy] [--semantic]
│   ├── wordlist.py         # floridify wordlist create/add/review
│   ├── anki.py             # floridify anki export
│   ├── database.py         # floridify database management
│   ├── config.py           # floridify config
│   ├── scrape.py           # floridify scrape
│   ├── wotd.py             # floridify wotd
│   └── wotd_ml.py          # floridify wotd-ml training
└── utils/formatting.py     # Rich terminal formatting
```

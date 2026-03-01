# cli/

Typer CLI with Rich terminal UI. Lazy imports for heavy modules (torch, FAISS, sentence-transformers).

```
cli/
├── cli.py (507)            # Typer app, main entry point
├── completion.py (161)     # ZSH autocomplete
├── commands/
│   ├── lookup.py (161)     # floridify lookup <word> [--no-ai] [--json] [--providers]
│   ├── search.py (379)     # floridify search <query> [--fuzzy] [--semantic]
│   ├── wordlist.py (353)   # floridify wordlist create/add/review
│   ├── anki.py (382)       # floridify anki export
│   ├── database.py (688)   # floridify database management
│   ├── config.py (328)     # floridify config
│   ├── scrape.py (740)     # floridify scrape
│   ├── wotd.py (357)       # floridify wotd
│   └── wotd_ml.py (532)    # floridify wotd-ml training
└── utils/formatting.py (571)  # Rich terminal formatting
```

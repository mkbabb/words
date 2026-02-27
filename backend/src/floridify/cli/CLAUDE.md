# cli/

Typer CLI with Rich terminal UI. 0.07s startup via lazy imports (98% faster than 4.2s original).

```
cli/
├── cli.py (507)            # Typer app, main entry point
├── completion.py (161)     # ZSH autocomplete
├── commands/               # lookup, search, wordlist, corpus, anki, wotd, config, scrape
│   ├── lookup.py (161)     # floridify lookup <word> [--no-ai] [--json] [--providers]
│   ├── search.py (342)     # floridify search <query> [--fuzzy] [--semantic]
│   ├── wordlist.py (353)   # floridify wordlist create/add/review
│   ├── corpus.py           # floridify corpus list/rebuild
│   └── anki.py (382)       # floridify anki export
└── utils/formatting.py (571)  # Rich terminal formatting
```

Key: all heavy imports (torch, FAISS, sentence-transformers) are lazy — only loaded when the command needs them.

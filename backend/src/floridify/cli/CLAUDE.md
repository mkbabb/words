# CLI Module - Command-Line Interface

Rich-powered terminal UI with 0.07s startup time (98% faster via lazy imports).

## Commands

**Lookup** (`lookup.py`):
- `floridify lookup <word>` - Full AI-enhanced definition
- `--no-ai` - Skip AI synthesis
- `--json` - JSON output for scripting
- `--providers` - Select providers (wiktionary, oxford, etc.)

**Search** (`search.py`):
- `floridify search <query>` - Multi-method search
- `--fuzzy` - Fuzzy-only mode
- `--semantic` - Semantic-only mode

**Corpus** (`corpus.py`):
- `floridify corpus list` - List all corpora
- `floridify corpus rebuild --corpus-name <name> --semantic` - Rebuild indices

**Wordlist** (`wordlist.py`):
- `floridify wordlist create <name> <words...>` - Create wordlist
- `floridify wordlist review <name> --due` - Get due words for spaced repetition

**Features**:
- Unicode formatting, progress bars via Rich
- ZSH autocomplete with performance optimization
- Lazy imports for fast startup (0.07s vs 4.2s)
- JSON output mode for scripting

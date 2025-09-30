# Floridify CLI Specification

**Version**: 0.1.0
**Last Updated**: 2025-09-29
**Author**: Automated Documentation System

## Overview

The Floridify CLI provides a comprehensive command-line interface for dictionary lookups, semantic search, word list management, and corpus scraping. Built with Click and Rich for beautiful terminal output, it features lazy loading for fast startup and extensive provider integration.

## Installation & Setup

```bash
# Install from source
cd backend
uv venv && source .venv/bin/activate
uv sync

# Run directly
uv run scripts/floridify <command>

# Or use the entry point
floridify <command>
```

## Global Options

```bash
--version    Show version information
--help       Show help message for any command
```

## Command Reference

### 🔍 **lookup** - Word Definition Lookup

Look up word definitions with AI enhancement and multi-provider synthesis.

**Syntax**:
```bash
floridify lookup <WORD> [OPTIONS]
```

**Arguments**:
- `WORD`: The word to look up (required)

**Options**:
- `--provider <PROVIDER>`: Dictionary providers to use (multiple allowed)
  - Choices: `wiktionary`, `oxford`, `apple_dictionary`, `merriam_webster`, `free_dictionary`, `wordhippo`, `ai_fallback`, `synthesis`
  - Can be specified multiple times: `--provider wiktionary --provider oxford`
- `-l, --language <CODE>`: Language code (default: `en`)
- `--no-ai`: Disable AI synthesis (flag)
- `--force-refresh`: Force refresh from providers, bypass cache (flag)

**Examples**:
```bash
# Basic lookup with default providers
floridify lookup serendipity

# Use specific providers
floridify lookup ephemeral --provider wiktionary --provider oxford

# Disable AI synthesis
floridify lookup cacophony --no-ai

# Force refresh (bypass cache)
floridify lookup ubiquitous --force-refresh

# French word lookup
floridify lookup bonjour --language fr
```

**Aliases**:
- `floridify define <WORD>` (same as lookup)

**Implementation Note**: Calls `lookup_word_command()` from `cli/commands/lookup.py`

---

### 🔎 **search** - Semantic & Fuzzy Search

Search for words using exact, fuzzy, or semantic matching across corpora.

**Syntax**:
```bash
floridify search <QUERY>
```

**Arguments**:
- `QUERY`: Search term or phrase (required)

**Examples**:
```bash
# Basic search
floridify search seren

# Search with typo (fuzzy matching)
floridify search seprendipity

# Semantic search (finds related words)
floridify search happiness
```

**Search Methods** (automatic cascade):
1. **Exact Match**: Direct vocabulary lookup (O(m) complexity)
2. **Prefix Match**: Autocomplete functionality
3. **Fuzzy Match**: Typo tolerance using RapidFuzz (WRatio scoring)
4. **Semantic Match**: Meaning-based similarity using FAISS embeddings

**Implementation Note**: Calls `search_command()` from `cli/commands/search.py`

---

### 🚀 **scrape** - Bulk Provider Scraping

Systematic data collection from dictionary providers with session management.

**Subcommands**:
- `apple-dictionary`: Scrape Apple Dictionary (macOS only)
- `wordhippo`: Scrape WordHippo synonyms/antonyms
- `free-dictionary`: Scrape FreeDictionary API
- `wiktionary-wholesale`: Download complete Wiktionary dumps
- `sessions`: List all scraping sessions
- `status`: Show scraping status
- `resume`: Resume a scraping session
- `delete`: Delete a scraping session
- `cleanup`: Clean up old sessions

#### **scrape apple-dictionary**

Bulk scrape Apple Dictionary for local definitions (macOS only).

**Syntax**:
```bash
floridify scrape apple-dictionary [OPTIONS]
```

**Options**:
- `--skip-existing/--include-existing`: Skip words with existing data (default: `--skip-existing`)
- `--force-refresh`: Force refresh existing data (flag)
- `-n, --session-name <NAME>`: Name for this scraping session
- `-r, --resume-session <ID>`: Resume from existing session ID
- `-c, --max-concurrent <N>`: Maximum concurrent operations
- `-b, --batch-size <N>`: Words per batch
- `-l, --language <LANG>`: Language to scrape
  - Choices: `en`, `fr`, `es`, `de`, `it`
  - Default: `en`

**Examples**:
```bash
# Start new scraping session
floridify scrape apple-dictionary --session-name "english-basics"

# Resume existing session
floridify scrape apple-dictionary --resume-session abc123

# Custom concurrency and batch size
floridify scrape apple-dictionary -c 10 -b 100
```

#### **scrape wordhippo**

Bulk scrape WordHippo for comprehensive synonym/antonym/example data.

**Syntax**:
```bash
floridify scrape wordhippo [OPTIONS]
```

**Options**: (same as apple-dictionary)

**Examples**:
```bash
# Scrape WordHippo
floridify scrape wordhippo --session-name "wordhippo-english"

# Skip existing entries
floridify scrape wordhippo --skip-existing
```

#### **scrape free-dictionary**

Bulk scrape FreeDictionary API for comprehensive coverage.

**Syntax**:
```bash
floridify scrape free-dictionary [OPTIONS]
```

**Options**: (same as apple-dictionary)

#### **scrape wiktionary-wholesale**

Download and process complete Wiktionary dumps.

**Syntax**:
```bash
floridify scrape wiktionary-wholesale [OPTIONS]
```

**Options**: (same as apple-dictionary)

#### **scrape sessions**

List all scraping sessions with status and progress.

**Syntax**:
```bash
floridify scrape sessions
```

**Example Output**:
```
╭─────────────── Scraping Sessions ───────────────╮
│ ID       │ Name              │ Status  │ Progress │
├──────────┼───────────────────┼─────────┼──────────┤
│ abc123   │ english-basics    │ Active  │ 45%      │
│ def456   │ wordhippo-english │ Paused  │ 78%      │
│ ghi789   │ french-vocab      │ Done    │ 100%     │
╰──────────────────────────────────────────────────╯
```

#### **scrape status**

Show scraping status or details for a specific session.

**Syntax**:
```bash
floridify scrape status [SESSION_ID]
```

**Examples**:
```bash
# Show overall status
floridify scrape status

# Show specific session
floridify scrape status abc123
```

#### **scrape resume**

Resume a scraping session by ID.

**Syntax**:
```bash
floridify scrape resume <SESSION_ID>
```

**Example**:
```bash
floridify scrape resume abc123
```

#### **scrape delete**

Delete a scraping session (with confirmation).

**Syntax**:
```bash
floridify scrape delete <SESSION_ID>
```

**Example**:
```bash
floridify scrape delete abc123
# Prompts: "Are you sure you want to delete this session?"
```

#### **scrape cleanup**

Clean up old scraping sessions (with confirmation).

**Syntax**:
```bash
floridify scrape cleanup
```

**Example**:
```bash
floridify scrape cleanup
# Prompts: "Are you sure you want to clean up old sessions?"
```

---

### 📄 **wordlist** - Word List Management

Process word lists with dictionary lookup and storage.

**Syntax**:
```bash
floridify wordlist <FILE_PATH>
```

**Arguments**:
- `FILE_PATH`: Path to word list file (required)

**Supported Formats**:
- Plain text (one word per line)
- CSV (with headers: word, frequency, etc.)
- JSON (array of words or objects)

**Examples**:
```bash
# Process simple word list
floridify wordlist vocab.txt

# Process CSV with frequency data
floridify wordlist frequency_list.csv

# Process JSON word list
floridify wordlist words.json
```

**Implementation Note**: Calls `wordlist_command()` from `cli/commands/wordlist.py`

---

### ⚙️ **config** - Configuration Management

Manage configuration and API keys.

**Syntax**:
```bash
floridify config [SUBCOMMAND]
```

**Subcommands**:
- `show`: Display current configuration
- `set`: Set configuration values
- `get`: Get specific configuration value
- `reset`: Reset to default configuration

**Examples**:
```bash
# Show current config
floridify config show

# Set API key
floridify config set openai.api_key sk-...

# Get specific value
floridify config get openai.api_key
```

**Implementation Note**: Calls `config_group()` from `cli/commands/config.py`

---

### 💾 **database** - Database Operations

Database operations and statistics.

**Syntax**:
```bash
floridify database [SUBCOMMAND]
```

**Subcommands**:
- `stats`: Show database statistics
- `clean`: Clean up orphaned records
- `backup`: Create database backup
- `restore`: Restore from backup
- `export`: Export data to JSON/CSV
- `import`: Import data from JSON/CSV

**Examples**:
```bash
# Show statistics
floridify database stats

# Clean orphaned records
floridify database clean

# Create backup
floridify database backup --output backup.json
```

**Implementation Note**: Calls `database_group()` from `cli/commands/database.py`

---

### 🚀 **wotd-ml** - Word of the Day ML

WOTD (Word of the Day) generation with multi-model support.

**Syntax**:
```bash
floridify wotd-ml
```

**Features**:
- Multi-model ML pipeline for word selection
- Frequency analysis
- Difficulty scoring
- User learning history integration

**Example**:
```bash
floridify wotd-ml
```

**Implementation Note**: Calls `wotd_ml_command()` from `cli/commands/wotd_ml.py`

---

### 🔧 **completion** - Shell Completion

Generate shell completion script for floridify.

**Syntax**:
```bash
floridify completion --shell <SHELL>
```

**Options**:
- `--shell <SHELL>`: Shell to generate completion for
  - Choices: `zsh`, `bash`
  - Default: `zsh`

**Examples**:
```bash
# Generate zsh completion
floridify completion --shell zsh > ~/.local/share/zsh/site-functions/_floridify

# Or add to ~/.zshrc
eval "$(floridify completion --shell zsh)"
```

**Implementation Note**: Calls `generate_zsh_completion()` from `cli/completion.py`

---

## Architecture Notes

### Lazy Loading

The CLI uses a `LazyGroup` class to implement lazy loading:
- Commands are imported only when invoked
- Reduces startup time from ~2s to <100ms
- Imports are cached after first use

### Command Organization

```
cli/
├── fast_cli.py           # Main entry point with lazy loading
├── commands/
│   ├── lookup.py         # Lookup command implementation
│   ├── search.py         # Search command implementation
│   ├── scrape.py         # Scrape subcommands
│   ├── wordlist.py       # Wordlist command
│   ├── config.py         # Config subcommands
│   ├── database.py       # Database subcommands
│   └── wotd_ml.py        # WOTD ML command
└── completion.py         # Shell completion generation
```

### Error Handling

All commands follow a consistent error handling pattern:
1. **Validation Errors**: Display clear error messages with suggestions
2. **API Errors**: Show provider-specific error details
3. **Database Errors**: Graceful degradation with cache fallback
4. **Network Errors**: Retry logic with exponential backoff

### Output Formatting

Uses Rich library for beautiful terminal output:
- **Progress bars**: For long-running operations
- **Tables**: For structured data display
- **Syntax highlighting**: For JSON/code output
- **Color coding**: Consistent semantic colors throughout

### Performance Characteristics

| Command | Cold Start | Warm Start | Notes |
|---------|-----------|------------|-------|
| lookup | ~1.5s | ~0.3s | AI synthesis adds ~1s |
| search | ~0.8s | ~0.1s | FAISS index cached |
| scrape | ~2s | ~0.5s | Database connection overhead |
| wordlist | Variable | Variable | Depends on file size |

## Configuration Files

### Default Locations

```
~/.config/floridify/
├── config.toml          # Main configuration
├── cache/               # HTTP cache
└── logs/                # CLI logs
```

### Environment Variables

```bash
FLORIDIFY_CONFIG_DIR     # Override config directory
FLORIDIFY_OPENAI_API_KEY # OpenAI API key
FLORIDIFY_DB_URI         # MongoDB connection URI
FLORIDIFY_LOG_LEVEL      # Logging level (DEBUG, INFO, WARN, ERROR)
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Command usage error (invalid arguments)
- `3`: API error (provider timeout, rate limit)
- `4`: Database error (connection failed, query error)
- `5`: File I/O error (file not found, permission denied)

## Best Practices

### For Users

1. **Use specific providers** for faster lookups: `--provider wiktionary`
2. **Enable caching** for repeated queries (default behavior)
3. **Use semantic search** for exploring related vocabulary
4. **Batch operations** with wordlist command for large datasets

### For Developers

1. **Add new commands** via lazy loading pattern
2. **Use Rich Console** for all output formatting
3. **Implement proper error handling** with user-friendly messages
4. **Add unit tests** for all command functions
5. **Document options** in docstrings and CLI help text

## Future Enhancements

- [ ] Add `search init` command for first-time index creation
- [ ] Implement `lookup --export` for Anki deck generation
- [ ] Add `scrape schedule` for automated scraping
- [ ] Implement `database migrate` for schema migrations
- [ ] Add `config validate` to check configuration integrity
- [ ] Support for custom provider plugins

## Troubleshooting

### Common Issues

**Issue**: "Command not found: floridify"
- **Solution**: Ensure the virtual environment is activated and floridify is installed

**Issue**: "MongoDB connection failed"
- **Solution**: Check `FLORIDIFY_DB_URI` and ensure MongoDB is running

**Issue**: "OpenAI API key not found"
- **Solution**: Set `FLORIDIFY_OPENAI_API_KEY` or add to config.toml

**Issue**: "Search index not found"
- **Solution**: Run `floridify search init` to build initial index

## Support & Feedback

- **GitHub Issues**: https://github.com/anthropics/floridify/issues
- **Documentation**: https://docs.floridify.dev
- **CLI Help**: `floridify --help` or `floridify <command> --help`

---

**End of CLI Specification**
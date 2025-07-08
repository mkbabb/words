# CLI Interface

## Core Commands

### lookup word [WORD]
**Primary interface for word definitions with AI synthesis**

```bash
uv run ./scripts/floridify lookup word bank
uv run ./scripts/floridify lookup word "en coulisse"  
```

**Features**:
- Meaning-based hierarchical display with superscripts
- Intelligent search cascade: exact → fuzzy → semantic → AI fallback
- Beautiful Rich formatting with separate panels for multiple meanings
- Proper multi-word phrase handling and bolding

**Options**:
- `--provider`: wiktionary (default), oxford, dictionary_com
- `--semantic`: Force semantic search only
- `--no-ai`: Skip AI synthesis

### search
**Multi-method search engine**

```bash
uv run ./scripts/floridify search init      # Initialize indices
uv run ./scripts/floridify search word cogn # Search for matches
```

**Methods**: Exact, fuzzy, semantic with FAISS acceleration

### word-list
**Batch word list processing with dictionary lookup**

```bash
uv run ./scripts/floridify word-list create vocab.txt --name my-vocab
uv run ./scripts/floridify word-list list
uv run ./scripts/floridify word-list show my-vocab
uv run ./scripts/floridify word-list update my-vocab new-words.txt
uv run ./scripts/floridify word-list delete my-vocab
```

**Features**:
- Robust parsing: numbered lists, CSV, tab-separated, plain text
- Auto-generated animal phrase names (e.g., "ochre-guan", "ebony-tanuki")
- Frequency tracking with heat map visualization
- Batch dictionary lookup processing (10 words at a time)
- Beautiful Rich table display with frequency bars
- MongoDB storage with full CRUD operations

**Options**:
- `--name`: Custom name (auto-generated if not provided)
- `--provider`: Dictionary provider (default: wiktionary)
- `--language`: Language (default: en)
- `--semantic`: Enable semantic search
- `--no-ai`: Skip AI synthesis

**Supported Formats**:
```
# Numbered lists
1. word
2. another

# Comma-separated
word, another, third

# Tab-separated
word	another	third

# Plain text
word
another
third
```

## Output Formatting

### Display Format

**Single Meaning**: Direct content in outer panel, no sub-panels
```
╭─ word /pronunciation/ ───────────────────────────────────╮
│ word-type                                                │
│   Definition with proper sentence case.                  │
│                                                          │
│   Example with word bolded in italic cyan.              │
│                                                          │
│ ✨ Sources: provider                                     │
╰──────────────────────────────────────────────────────────╯
```

**Multiple Meanings**: Separate panels with superscripts
```
╭─ word /pronunciation/ ───────────────────────────────────╮
│ ╭─ word¹ (Meaning One) ──────────────────────────────╮   │
│ │ word-type                                          │   │
│ │   Definition for first meaning cluster.           │   │ 
│ │                                                    │   │
│ │   Example sentence with proper formatting.        │   │
│ ╰────────────────────────────────────────────────────╯   │
│ ╭─ word² (Meaning Two) ──────────────────────────────╮   │
│ │ word-type                                          │   │
│ │   Definition for second meaning cluster.          │   │
│ ╰────────────────────────────────────────────────────╯   │
│ ✨ Sources: provider                                     │
╰──────────────────────────────────────────────────────────╯
```

### Typography Rules

**Words**: lowercase (`bank`, `en coulisse`)  
**Pronunciations**: `/phonetic/` notation  
**Meaning clusters**: Title Case display (`Financial`, `Geographic`)  
**Word types**: lowercase (`noun`, `verb`)  
**Definitions**: Sentence case with periods  
**Examples**: Sentence case, phrase bolding when found

## Database Management

### database status
**Check database connection and basic info**

```bash
uv run ./scripts/floridify database status
```

### database stats
**Comprehensive database statistics and metrics**

```bash
uv run ./scripts/floridify database stats                    # Basic stats
uv run ./scripts/floridify database stats --detailed        # Detailed analysis
uv run ./scripts/floridify database stats --connection-string mongodb://user:pass@host:port
```

**Features**:
- Collection counts (words, syntheses, cache)
- Provider coverage analysis
- Quality metrics (average providers per word, definition coverage)
- Estimated database size

### database connect
**Test MongoDB connection**

```bash
uv run ./scripts/floridify database connect                  # Default localhost:27017
uv run ./scripts/floridify database connect --host remote.mongo.com --port 27017
```

### database backup/restore
**Database backup and restore operations**

```bash
uv run ./scripts/floridify database backup                   # Auto-named backup
uv run ./scripts/floridify database backup -o backup.json   # Custom name
uv run ./scripts/floridify database backup --format bson --compress

uv run ./scripts/floridify database restore backup.json     # Restore from backup
uv run ./scripts/floridify database restore backup.json --confirm
```

### database cleanup
**Remove old cache entries and optimize performance**

```bash
uv run ./scripts/floridify database cleanup --dry-run       # Preview cleanup
uv run ./scripts/floridify database cleanup --older-than 30 # Remove cache >30 days
```

### database export/import
**Data export and import in various formats**

```bash
uv run ./scripts/floridify database export --collection words --format json
uv run ./scripts/floridify database export --collection cache --format csv
uv run ./scripts/floridify database import words.json --collection words --upsert
```

## Configuration Management

### config show
**Display current configuration**

```bash
uv run ./scripts/floridify config show                      # Hide API keys
uv run ./scripts/floridify config show --show-keys         # Show masked keys
```

### config set/get
**Manage configuration values**

```bash
uv run ./scripts/floridify config set max_results 20       # Set general option
uv run ./scripts/floridify config set rate_limit_enabled true --section api
uv run ./scripts/floridify config get max_results          # Get value
```

### config keys
**API key management**

```bash
uv run ./scripts/floridify config keys list                # List all API keys
uv run ./scripts/floridify config keys set openai sk-...   # Set OpenAI key
uv run ./scripts/floridify config keys test                # Test all keys
uv run ./scripts/floridify config keys test --service openai
```

### config edit/reset
**Edit and reset configuration**

```bash
uv run ./scripts/floridify config edit                     # Open in $EDITOR
uv run ./scripts/floridify config reset                    # Reset to defaults
uv run ./scripts/floridify config reset --confirm         # Skip confirmation
```

**Configuration File**: `auth/config.toml`

**Default Sections**:
- `general`: Output format, default provider, max results
- `api`: API keys and rate limiting settings
- `anki`: Card types, export settings
- `search`: Fuzzy thresholds, similarity settings

## Anki Flashcard Export

### anki export
**Export word lists as Anki flashcard decks with direct integration**

```bash
uv run ./scripts/floridify anki export vocabulary-list     # Direct export to Anki
uv run ./scripts/floridify anki export gre-words --output ~/decks/gre.apkg
uv run ./scripts/floridify anki export test-words --card-types fill_in_blank
uv run ./scripts/floridify anki export study-set --no-direct --apkg-fallback
```

**Options**:
- `--output, -o`: Output path for .apkg file (defaults to word list name)
- `--card-types, -t`: Types of cards to generate (multiple choice, fill_in_blank)
- `--max-cards, -m`: Maximum cards per type per word (default: 1)
- `--deck-name, -d`: Custom Anki deck name (defaults to word list name)
- `--direct/--no-direct`: Try direct export to Anki via AnkiConnect (default: True)
- `--apkg-fallback/--no-apkg-fallback`: Create .apkg if direct export fails (default: True)

**Export Modes**:
1. **Direct Integration** (default): Cards appear instantly in running Anki app
2. **Hybrid Mode**: Direct export with .apkg backup for manual import
3. **Traditional Mode**: .apkg file creation only (`--no-direct`)

### anki status
**Check AnkiConnect availability and Anki integration status**

```bash
uv run ./scripts/floridify anki status
```

**Features**:
- Verifies AnkiConnect add-on installation and connectivity
- Shows available decks and note types in Anki
- Displays version information and system status
- Provides setup instructions for macOS optimization

### anki info
**Information about flashcard generation**

```bash
uv run ./scripts/floridify anki info
```

**Features**:
- GRE-level academic rigor with strategic question design
- Clean Apple/Tesla-inspired styling with professional typography
- Two card types: fill-in-blank context and multiple choice definitions
- AI-generated content using structured OpenAI responses
- Beautiful HTML preview alongside .apkg export
- Compatible with all Anki platforms (desktop, mobile, web)
- **Direct Anki integration** for instant card availability

**Card Types**:
- **fill_in_blank**: Context sentences with strategic word removal and hints
- **best_describes**: Definition-based questions with intelligent distractors

**AnkiConnect Setup** (for direct integration):
1. Install AnkiConnect add-on in Anki (code: 2055492159)
2. Ensure Anki is running when exporting
3. On macOS, disable App Nap: `defaults write net.ichi2.anki NSAppSleepDisabled -bool true`

**Workflow Options**:

**Direct Integration** (recommended):
1. Install AnkiConnect add-on in Anki
2. Keep Anki running in background
3. Create word list: `floridify word-list create vocab.txt`
4. Export directly: `floridify anki export vocabulary-list`
5. Cards appear instantly in Anki deck

**Traditional Workflow**:
1. Create word list: `floridify word-list create vocab.txt`
2. Export to file: `floridify anki export vocabulary-list --no-direct`
3. Import .apkg file into Anki manually
4. Study with spaced repetition
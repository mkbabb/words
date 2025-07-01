# Floridify CLI

## Core Commands

### lookup
**Purpose**: Word definition lookup with AI enhancement
**Usage**: `floridify lookup <word> [options]`

**Features**:
- Query normalization and search across lexicon languages
- Provider selection: Wiktionary, Oxford, Dictionary.com, AI-only
- Semantic vs hybrid search modes  
- AI synthesis with examples and pronunciation
- Graceful fallback for unknown words

**Options**:
- `--provider`: Dictionary provider (enum: wiktionary, oxford, dictionary_com, ai)
- `--language`: Lexicon languages (enum: english, french, spanish, etc.)
- `--semantic`: Force semantic search mode
- `--no-ai`: Skip AI synthesis

**Output**: Structured display isomorphic to SynthesizedDictionaryEntry

### search
**Purpose**: Vocabulary search and discovery
**Usage**: `floridify search <subcommand>`

**Subcommands**:
- `init`: Initialize search indices
- `word <query>`: Search for words/phrases
- `stats`: Display search statistics

**Options**:
- `--language`: Target languages (consistent enum usage)
- `--method`: Search method (exact, fuzzy, semantic, hybrid)
- `--max-results`: Result limit

### anki  
**Purpose**: Flashcard generation and export
**Usage**: `floridify anki <subcommand>`

**Subcommands**:
- `create <deck>`: Generate Anki deck from word lists
- `export`: Export to .apkg format

### config
**Purpose**: Configuration management
**Usage**: `floridify config <subcommand>`

**Subcommands**:
- `show`: Display current settings
- `set <key> <value>`: Update configuration

## Design Principles

**KISS**: Simple, intuitive command structure
**Rich Output**: Colored formatting with clear hierarchy  
**Performance**: Async operations with progress indicators
**Consistency**: Unified enum usage across all commands
**Graceful Errors**: Clear messages with suggested fixes

## Output Formatting

**Colors**: Cyan examples, green success, yellow warnings, red errors
**Structure**: Hierarchical with proper spacing and alignment
**Icons**: Meaningful Unicode symbols for visual clarity
**Interactive**: Progress bars for long operations
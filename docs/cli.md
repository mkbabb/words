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

### Casing and Typography Standards

**Core Principle**: Maintain consistent, predictable casing that follows standard dictionary conventions while being visually clear and scannable.

#### Word Display
- **Word text**: lowercase (`bank`, `simple`)
- **Pronunciation**: lowercase with standard notation (`/bank/`, `/SIM-pul/`)
- **Superscripts**: Unicode superscripts for multiple meanings (`bank¹`, `bank²`)

#### Meaning Clusters
- **Storage format**: snake_case in database (`bank_financial`, `simple_uncomplicated`)
- **Display format**: Title Case (`Bank Financial`, `Simple Uncomplicated`)
- **Header format**: `word^n (Meaning Cluster)` → `bank¹ (Bank Financial)`

#### Grammar and Content
- **Word types**: lowercase (`noun`, `verb`, `adjective`)
- **Definitions**: Proper sentence case with initial capital
- **Examples**: Proper sentence case with initial capital, quoted when appropriate
- **Sources**: lowercase (`wiktionary`, `ai generated`)

#### Special Cases
- **Pronunciation guides**: Use phonetic notation (`/bank/`, `/SIM-pul/`)
- **Abbreviations**: Standard dictionary format (`IPA`, `adj.`)
- **Technical terms**: Maintain source casing (`MongoDB`, `OpenAI`)

### Display Structure Template

```
╭─ word /pronunciation/ ────────────────────────────────────────────────────╮
│ word¹ (Meaning Cluster One)                                              │
│ word-type                                                                 │
│   Definition text with proper sentence case and punctuation.             │
│                                                                           │
│   Example sentence with proper casing and formatting.                    │
│                                                                           │
│ word² (Meaning Cluster Two)                                              │
│ word-type                                                                 │
│   Second meaning definition text.                                         │
│                                                                           │
│   "Quoted example when appropriate for clarity."                         │
│                                                                           │
│ ✨ Sources: source1, source2                                             │
╰───────────────────────────────────────────────────────────────────────────╯
```

### Implementation Rules

1. **Meaning cluster formatting**: Convert `meaning_id` from snake_case to Title Case for display
2. **Sentence consistency**: All definitions and examples start with capital letter, end with period
3. **Typography**: Use Unicode superscripts (¹²³⁴⁵⁶⁷⁸⁹⁰) for meaning numbering
4. **Spacing**: Consistent indentation and line breaks for visual hierarchy
5. **Quoting**: Use quotes for examples when they contain dialogue or need emphasis

### Visual Design
**Colors**: Cyan examples, green success, yellow warnings, red errors
**Structure**: Hierarchical with proper spacing and alignment
**Icons**: Meaningful Unicode symbols for visual clarity
**Interactive**: Progress bars for long operations
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
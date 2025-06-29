# Floridify CLI Design Specification

## Overview

The Floridify CLI provides a modern, beautiful, and intuitive command-line interface for interacting with the AI-enhanced dictionary and learning system. Inspired by Claude Code's elegant design principles, the CLI emphasizes clarity, rich formatting, and efficient workflows.

## Design Philosophy

### Core Principles
- **Beautiful Output**: Rich formatting with colors, icons, and structured layouts
- **Intuitive Commands**: Self-explanatory command structure with helpful descriptions
- **Performance**: Fast responses with efficient caching and async operations
- **Progressiveness**: Smart defaults with advanced options for power users
- **Accessibility**: Clear error messages and comprehensive help system

### Visual Design
- **Color Scheme**: Claude-inspired gradient colors (blue-purple spectrum)
- **Typography**: Clean, hierarchical text with proper spacing
- **Icons**: Meaningful emoji and Unicode symbols for visual clarity
- **Progress Indicators**: Beautiful progress bars and spinners for long operations
- **Tables**: Well-formatted data presentation with alignment and borders

## Command Structure

### Primary Commands

#### 1. Word Lookup and Management

```bash
# Basic word lookup
floridify lookup <word>
floridify search <word>  # alias

# Fuzzy search
floridify find <partial_word>
floridify fuzzy <pattern>

# Vector similarity search
floridify similar <word> [--count=10]
floridify relate <word>  # alias

# Word details
floridify define <word> [--provider=all|wiktionary|oxford]
floridify examples <word> [--count=5]
floridify synonyms <word> [--depth=2]
```

**Output Example:**
```
🔍 Looking up "serendipity"...

┌─ Serendipity ─────────────────────────────────┐
│ /ˌserənˈdɪpɪti/ • noun                       │
├───────────────────────────────────────────────┤
│ 💡 AI Synthesis                              │
│ The faculty of making fortunate discoveries  │
│ by accident; a pleasant surprise.            │
│                                               │
│ 📚 Examples                                   │
│ • Her serendipity led to a breakthrough.     │
│ • The meeting was pure serendipity.          │
│                                               │
│ 🔗 Synonyms                                   │
│ chance, fortune, luck, accident              │
└───────────────────────────────────────────────┘

✨ Found 3 providers: Wiktionary, Oxford, AI
⏱️  Retrieved in 1.2s
```

#### 2. Anki Deck Management

```bash
# Create Anki deck from word list
floridify anki create <deck_name> [--input=wordlist.txt] [--output=deck.apkg]

# Create deck from individual words
floridify anki add <deck_name> <word1> <word2> ...

# Deck management
floridify anki list
floridify anki info <deck_name>
floridify anki export <deck_name> [--format=apkg|html] [--output=path]
floridify anki delete <deck_name> [--confirm]

# Card type options
floridify anki create <deck_name> --types=multiple_choice,fill_blank
floridify anki create <deck_name> --max-cards=3 --difficulty=intermediate
```

**Output Example:**
```
🎴 Creating Anki deck "Advanced Vocabulary"...

📝 Processing word list...
┌─ Progress ────────────────────────────────────┐
│ ████████████████████▎         ▏ 67% (134/200) │
│ Current: "perspicacious"                      │
│ ⏱️  2m 15s elapsed, ~1m 30s remaining         │
└───────────────────────────────────────────────┘

✅ Generated 268 flashcards
   • 134 Multiple Choice cards
   • 134 Fill-in-the-Blank cards

📦 Exported to: advanced_vocabulary.apkg (2.4 MB)
🌐 Preview at: advanced_vocabulary.html

🎯 Ready to import into Anki!
```

#### 3. Word List Processing

```bash
# Process word lists from files
floridify process <file.txt> [--output=processed.json]
floridify batch <directory> [--pattern="*.txt"] [--recursive]

# Apple Notes integration
floridify import notes <file.md> [--section="Vocabulary"]
floridify import markdown <file.md> [--extract-headers]

# Export options
floridify export <words> --format=json|csv|anki|markdown
floridify export database --words=all --format=json --output=backup.json
```

**Output Example:**
```
📄 Processing word list: vocabulary_2024.txt

🔍 Analyzing file...
   • Format: Plain text
   • Words found: 156 unique entries
   • Duplicates removed: 23

🌐 Fetching definitions...
┌─ Dictionary APIs ─────────────────────────────┐
│ Wiktionary    ████████████████▌   ▏ 89% (139) │
│ Oxford        ███████████████▎    ▏ 82% (128) │
│ AI Synthesis  ████████████████████▏100% (156) │
└───────────────────────────────────────────────┘

✅ Processing complete!
   • 156 words processed
   • 148 successful definitions
   • 8 words need manual review
   
📊 Quality Score: 94.8%
💾 Saved to: processed_vocabulary.json
```

#### 4. Database Management

```bash
# Database operations
floridify db status
floridify db connect [--host=localhost] [--port=27017]
floridify db backup [--output=backup.json]
floridify db restore <backup.json>
floridify db cleanup [--dry-run]

# Statistics and analytics
floridify stats
floridify stats providers
floridify stats words [--by=date|provider|difficulty]
```

**Output Example:**
```
📊 Floridify Database Statistics

┌─ Overview ────────────────────────────────────┐
│ Total Words       │ 15,847                    │
│ Definitions       │ 42,391                    │
│ AI Syntheses      │ 15,230                    │
│ Generated Examples│ 31,456                    │
│ Anki Cards        │ 8,923                     │
└───────────────────────────────────────────────┘

📈 Provider Coverage
┌─ Sources ─────────────────────────────────────┐
│ Wiktionary   ████████████████▌    ▏ 89% (14,104) │
│ Oxford       ███████████▎        ▏ 62% (9,825)  │
│ Dictionary   █████▎              ▏ 28% (4,437)  │
│ AI Synthesis ████████████████████▏100% (15,230) │
└───────────────────────────────────────────────┘

💾 Database size: 2.3 GB
🔄 Last backup: 2 days ago
```

### Secondary Commands

#### 5. Configuration Management

```bash
# Configuration
floridify config show
floridify config set <key> <value>
floridify config edit  # Opens in $EDITOR

# API key management
floridify config keys list
floridify config keys set openai <api_key>
floridify config keys test [--provider=all]

# Rate limiting
floridify config limits show
floridify config limits set wiktionary 100/minute
```

#### 6. Search and Discovery

```bash
# Advanced search
floridify search --fuzzy <pattern>
floridify search --regex <pattern>
floridify search --semantic <concept>
floridify search --difficulty <level>

# Browse and explore
floridify browse recent [--count=20]
floridify browse popular [--timeframe=week]
floridify browse random [--count=5]
floridify browse similar <word>
```

#### 7. Utilities and Tools

```bash
# Utilities
floridify validate <file>  # Validate word list format
floridify clean <file>     # Remove duplicates and format
floridify merge <file1> <file2> [--output=merged.txt]

# Development and debugging
floridify test [--component=all|ai|storage|anki]
floridify debug <word> [--verbose]
floridify benchmark [--operations=1000]
```

## Fuzzy Search Implementation

### Traditional Fuzzy Search (VSCode-style)

```python
# Algorithm: Modified Levenshtein with position weighting
def fuzzy_score(pattern: str, word: str) -> float:
    """Calculate fuzzy match score (0.0 to 1.0)"""
    # Factors:
    # - Character matches (exact, case-insensitive)
    # - Position importance (earlier matches score higher)
    # - Consecutive character bonuses
    # - Word boundary bonuses
    # - Pattern completeness
```

**Features:**
- **Character Matching**: Case-insensitive with accent normalization
- **Position Weighting**: Earlier matches score higher
- **Consecutive Bonuses**: Reward consecutive character matches
- **Word Boundaries**: Bonus for matches at word starts
- **Abbreviation Support**: "syn" matches "synonym", "serendipity"

**Example Usage:**
```bash
$ floridify find "seren"
🔍 Fuzzy matches for "seren":

┌─ Results (showing top 10) ────────────────────┐
│ 95% │ serendipity     │ /ˌserənˈdɪpɪti/    │
│ 87% │ serene          │ /səˈriːn/          │
│ 82% │ serenity        │ /səˈrenɪti/        │
│ 76% │ serenade        │ /ˌserəˈneɪd/       │
│ 71% │ severe          │ /səˈvɪər/          │
│ 68% │ several         │ /ˈsevərəl/         │
│ 64% │ generosity      │ /ˌdʒenəˈrɒsɪti/    │
│ 61% │ reverent        │ /ˈrevərənt/        │
│ 58% │ perseverance    │ /ˌpɜːrsəˈvɪrəns/   │
│ 55% │ regenerate      │ /rɪˈdʒenəreɪt/     │
└───────────────────────────────────────────────┘

⚡ Found 847 candidates in 0.02s
```

### Vector Similarity Search

```python
# Semantic similarity using embeddings
def vector_similarity(word: str, count: int = 10) -> list[SimilarWord]:
    """Find semantically similar words using vector embeddings"""
    # Process:
    # 1. Get embedding for input word
    # 2. Calculate cosine similarity with all stored embeddings
    # 3. Return top N most similar words
    # 4. Include similarity scores and explanations
```

**Features:**
- **Semantic Understanding**: Find conceptually related words
- **Context Awareness**: Consider word usage patterns
- **Multilingual Support**: Cross-language similarity detection
- **Explanation Generation**: AI-powered similarity explanations

**Example Usage:**
```bash
$ floridify similar "happiness" --count=8
🔗 Semantically similar to "happiness":

┌─ Vector Similarity ───────────────────────────┐
│ 94% │ joy          │ Pure emotional delight    │
│ 91% │ bliss        │ Perfect contentment      │
│ 88% │ euphoria     │ Intense elation          │
│ 85% │ contentment  │ Peaceful satisfaction    │
│ 82% │ elation      │ High-spirited joy        │
│ 79% │ cheerfulness │ Optimistic disposition   │
│ 76% │ jubilation   │ Triumphant celebration   │
│ 73% │ delight      │ Great pleasure           │
└───────────────────────────────────────────────┘

💡 Similarity based on: emotional state, positive valence, subjective experience
🧠 Model: text-embedding-3-large
⚡ Computed in 0.15s
```

## Word List Processing

### Supported Formats

#### 1. Plain Text (.txt)
```
# Simple word per line
serendipity
perspicacious
eloquent
# Comments supported
```

#### 2. Markdown (.md)
```markdown
# Vocabulary List

## Advanced Words
- serendipity: happy accident
- perspicacious: having keen insight
- eloquent: fluent and persuasive

## Basic Words
1. happy
2. sad
3. angry
```

#### 3. Structured Formats
```json
{
  "words": [
    {"word": "serendipity", "notes": "from essay reading"},
    {"word": "perspicacious", "source": "academic paper"}
  ]
}
```

### Processing Pipeline

1. **File Detection**: Automatic format recognition
2. **Parsing**: Extract words with metadata preservation
3. **Deduplication**: Remove duplicates while preserving source info
4. **Validation**: Check for valid dictionary words
5. **Batch Processing**: Efficient API calls with rate limiting
6. **Progress Tracking**: Real-time progress with ETA
7. **Error Handling**: Graceful handling of failed lookups
8. **Output Generation**: Multiple export formats

## CLI Architecture

### Technology Stack
- **Click**: Command framework with rich help system
- **Rich**: Beautiful terminal formatting and progress bars
- **Asyncio**: Async operations for better performance
- **FuzzyWuzzy**: Traditional fuzzy string matching
- **NumPy**: Vector operations for similarity search

### Command Organization
```
src/floridify/cli/
├── __init__.py          # Main CLI entry point
├── commands/
│   ├── lookup.py        # Word lookup commands
│   ├── anki.py          # Anki deck management
│   ├── process.py       # Word list processing
│   ├── search.py        # Search and discovery
│   ├── database.py      # Database operations
│   └── config.py        # Configuration management
├── utils/
│   ├── formatting.py    # Rich formatting utilities
│   ├── fuzzy.py         # Fuzzy search implementation
│   ├── progress.py      # Progress tracking
│   └── validation.py    # Input validation
└── templates/
    ├── word_display.py  # Word information templates
    ├── table_formats.py # Table formatting
    └── progress_styles.py # Progress bar styles
```

### Configuration System

#### Configuration File (config.toml)
```toml
[general]
output_format = "rich"  # rich, plain, json
default_provider = "ai_synthesis"
max_results = 10

[api]
openai_key = "sk-..."
oxford_key = "..."
rate_limit_enabled = true

[anki]
default_card_types = ["multiple_choice", "fill_blank"]
max_cards_per_word = 2
export_format = "apkg"

[search]
fuzzy_threshold = 0.6
vector_similarity_threshold = 0.7
max_fuzzy_results = 20

[display]
use_colors = true
show_progress = true
table_style = "rounded"
```

## Error Handling and User Experience

### Error Categories
1. **Network Errors**: API timeouts, connection issues
2. **Authentication Errors**: Invalid API keys
3. **Data Errors**: Malformed input files, invalid words
4. **System Errors**: Database connection, file permissions

### Error Display
```bash
❌ Error: Failed to connect to OpenAI API

🔍 Troubleshooting:
   • Check your API key: floridify config keys test openai
   • Verify network connection
   • Check API usage limits

💡 Need help? Run: floridify config keys set openai <your-key>
```

### Progress Feedback
- **Spinners**: For quick operations (<2 seconds)
- **Progress Bars**: For long operations with known duration
- **Live Updates**: Real-time status for complex workflows
- **Completion Summary**: Detailed results after operations

## Performance Considerations

### Optimization Strategies
1. **Caching**: Intelligent caching of API responses and computations
2. **Batch Operations**: Group API calls for efficiency
3. **Async Processing**: Non-blocking operations for better UX
4. **Lazy Loading**: Load data only when needed
5. **Connection Pooling**: Reuse database connections

### Scalability
- **Large Word Lists**: Efficient processing of 10,000+ words
- **Memory Management**: Stream processing for large files
- **Rate Limiting**: Respect API limits while maximizing throughput
- **Progress Persistence**: Resume interrupted operations

## Integration Points

### Database Integration
- **Async MongoDB**: Non-blocking database operations
- **Connection Management**: Automatic reconnection and pooling
- **Query Optimization**: Efficient lookups and aggregations

### AI Services
- **OpenAI Integration**: Bulk processing for cost optimization
- **Embedding Cache**: Persistent vector storage
- **Error Recovery**: Graceful handling of API failures

### File System
- **Path Handling**: Cross-platform file operations
- **Backup Management**: Automatic backups for critical operations
- **Temporary Files**: Clean temporary file handling

This CLI design provides a comprehensive, beautiful, and efficient interface for all Floridify operations while maintaining the high quality and user experience standards expected from a modern development tool.
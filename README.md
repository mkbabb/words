# Floridify - AI-Enhanced Dictionary

A modern, full-stack dictionary application with AI-powered meaning extraction, semantic search, and beautiful typography. Built for seamless word exploration with both CLI and web interfaces.

## 🌐 Web Interface (NEW!)

Experience Floridify through a beautiful, responsive web interface featuring:

- **Smooth Animations**: GPU-accelerated search bar transitions
- **Typography Excellence**: Fraunces for elegance, Fira Code for technical precision  
- **Intelligent Search**: As-you-type suggestions with debounced API calls
- **Heatmap Visualization**: Color-coded synonym similarity scores
- **Universal Word Linking**: Click any word to explore further
- **Responsive Design**: Perfect on desktop, tablet, and mobile

### Quick Start - Web Interface

```bash
# Start both frontend and backend
npm run dev

# Or start separately:
npm run dev:backend  # Python FastAPI server on :8000
npm run dev:frontend # Vue.js development server on :3000
```

Navigate to `http://localhost:3000` for the web interface.

---

## 📖 CLI Interface (Original)

**AI-Enhanced Dictionary and Vocabulary Learning Tool**

A sophisticated CLI dictionary system that transforms word lookup into an intelligent, meaning-driven experience. Built for serious vocabulary learners, GRE prep, and anyone who demands more than basic definitions.

## ✨ What Makes Floridify Special

**🧠 AI-Powered Intelligence**: Automatically clusters word meanings and synthesizes definitions from multiple sources into clear, hierarchical explanations.

**🔍 Multi-Method Search**: Exact → fuzzy → semantic → AI fallback cascade with sub-second performance across 269k+ words.

**📚 Batch Processing**: Transform word lists into comprehensive vocabulary collections with frequency tracking and beautiful terminal visualizations.

**🎴 Direct Anki Integration**: Generate academic-quality flashcards that appear instantly in your Anki app - no manual import required.

**🎨 Beautiful CLI**: Rich terminal interface with progress tracking, heat maps, and thoughtful typography.

## Quick Example

```bash
# Look up a word with AI-enhanced clustering
$ floridify lookup bank

╭─ bank /bæŋk/ ──────────────────────────────────────────╮
│ ╭─ bank¹ (Financial Institution) ──────────────────╮   │
│ │ noun                                              │   │
│ │   A financial institution that accepts deposits   │   │
│ │   and provides loans and other services.          │   │
│ ╰───────────────────────────────────────────────────╯   │
│ ╭─ bank² (Geographic Feature) ──────────────────────╮   │
│ │ noun                                              │   │
│ │   The sloping land alongside a river or lake.     │   │
│ ╰───────────────────────────────────────────────────╯   │
│ ✨ Sources: wiktionary, ai-synthesis                     │
╰─────────────────────────────────────────────────────────╯

# Process a word list and export to Anki
$ floridify word-list create vocab.txt --name gre-prep
$ floridify anki export gre-prep
✅ Exported 50 flashcards directly to Anki in 3.2s
```

## 🚀 Getting Started

### Prerequisites

-   **Python 3.12+**
-   **MongoDB** (optional, defaults to localhost:27017)
-   **OpenAI API Key** for AI features
-   **uv** package manager

### Installation

```bash
# Clone and setup environment
git clone <repository-url>
cd floridify
uv venv && source .venv/bin/activate
uv sync

# Configure API keys
cp auth/config.toml.example auth/config.toml
# Edit auth/config.toml with your OpenAI API key

# Initialize search engine (one-time setup)
uv run ./scripts/floridify search init

# You're ready to go!
uv run ./scripts/floridify lookup serendipity
```

### Configuration

Edit `auth/config.toml`:

```toml
[api]
openai_api_key = "sk-your-key-here"
rate_limit_enabled = true

[general]
default_provider = "wiktionary"
max_results = 20

[anki]
default_card_types = ["best_describes", "fill_in_blank"]
max_cards_per_word = 2
```

## 🎯 Core Features

### Smart Word Lookup

```bash
# Single words with AI clustering
floridify lookup perspicacious

# Multi-word phrases
floridify lookup "en coulisse"

# Skip AI synthesis for faster results
floridify lookup bank --no-ai
```

### Intelligent Search

```bash
# Find words containing patterns
floridify search word cogn
# Results: recognize, cognitive, incognito...

# Search with different methods
floridify search word --semantic understanding
```

### Word List Management

```bash
# Create from various formats
floridify word-list create vocab.txt --name my-vocabulary
floridify word-list create words.csv --name gre-prep

# View with frequency visualization
floridify word-list show my-vocabulary

# Supported formats:
# - Numbered lists: "1. word", "2) another"
# - CSV: "word1, word2, phrase"
# - Tab-separated: "word1	word2"
# - Plain text: one word per line
```

### Anki Integration

```bash
# Direct export (cards appear immediately in Anki)
floridify anki export my-vocabulary

# Specific card types
floridify anki export gre-prep --card-types fill_in_blank

# Traditional .apkg export
floridify anki export vocab --no-direct

# Check AnkiConnect status
floridify anki status
```

**Anki Setup for Direct Export:**

1. Install [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on (code: `2055492159`)
2. Keep Anki running during export
3. On macOS: `defaults write net.ichi2.anki NSAppSleepDisabled -bool true`

### Database & Configuration

```bash
# View database stats
floridify database stats --detailed

# Manage configuration
floridify config show
floridify config set max_results 50
floridify config keys set openai sk-your-new-key
```

## 🏗️ Architecture

**Data Pipeline**: Normalize → Search → Fetch → Extract Meanings → Synthesize → Display → Cache

**Storage**: MongoDB collections for entries, synthesis results, and word lists

**Search**: FAISS-accelerated semantic search with trie-based exact matching

**AI Integration**: OpenAI GPT models with structured outputs for meaning extraction and synthesis

**Caching**: Multi-level caching (API responses, synthesized entries, search indices) for performance

## 💻 Technology Stack

-   **Python 3.12+** with modern async/await patterns
-   **MongoDB + Beanie ODM** for document storage
-   **OpenAI API** with structured outputs
-   **FAISS + scikit-learn** for semantic search
-   **Rich + Click** for beautiful CLI
-   **uv** for fast, reliable dependency management

## 📊 Performance

-   **Search**: Sub-second across 269k+ words
-   **AI Synthesis**: ~2-4 seconds per word
-   **Batch Processing**: 10 words processed concurrently
-   **Anki Export**: Direct integration in <2 seconds
-   **Cache Hit Rate**: ~95% for repeated lookups

## 🎓 Use Cases

**Academic & Test Prep**

-   GRE/SAT vocabulary with spaced repetition flashcards
-   Language learning with meaning-based clustering
-   Research vocabulary processing

**Professional Development**

-   Technical term exploration
-   Writing enhancement and synonym discovery
-   Industry-specific vocabulary building

**Developers & Researchers**

-   Batch vocabulary analysis
-   Semantic similarity exploration
-   Dictionary data extraction and processing

## 🔧 Advanced Usage

### Batch Processing Large Lists

```bash
# Process large vocabulary lists efficiently
floridify word-list create large-vocab.txt --name comprehensive
floridify anki export comprehensive --max-cards 1
```

### Custom Search Methods

```bash
# Semantic search for related concepts
floridify search word --semantic happiness
# Results: joy, elation, contentment, euphoria...

# Fuzzy search for typos
floridify search word recieve  # → receive
```

### Performance Monitoring

```bash
# Database insights
floridify database stats --detailed
# Shows: collection counts, cache hit rates, performance metrics

# Clear caches for fresh lookups
floridify database cleanup --older-than 7
```

## 🤝 Development

Built with modern Python practices:

-   **Type Safety**: Full MyPy strict mode compliance
-   **Code Quality**: Ruff formatting, comprehensive error handling
-   **Testing**: 95%+ coverage target with pytest
-   **Architecture**: Functional approach with async-first design

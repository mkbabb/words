# 🌻 Floridify — An Efflorescent Dictionary for Word Lovers

A full-stack dictionary system architected for the methodical acquisition and discovery of efflorescent words. Built with meaning-first philosophy, semantic intelligence, and the understanding that an expanded lexicon is akin to an extended color palette for precise articulation.

## Overview

Floridify transcends traditional dictionary lookup through AI-synthesized meaning extraction, transforming the chaotic assemblage of definitions into hierarchical, learnable knowledge. This isn't merely another word application—it's a comprehensive vocabulary acquisition ecosystem designed for those who understand that words are the fundamental substrate of thought itself.

The system employs a sophisticated multi-method search cascade (exact → fuzzy → semantic → AI) across 269k+ lexical entries, synthesizing definitions from disparate sources into coherent, meaning-clustered presentations. Each word becomes a structured learning artifact, complete with spaced repetition algorithms, contextual examples, and direct Anki integration for systematic vocabulary development.

## 🚀 Quick Start

### Full-Stack Development
```bash
# Concurrent frontend (Vue 3) and backend (FastAPI) development
./dev.sh

# Navigate to localhost:3000 for the web interface
# API available at localhost:8000
```

### CLI Installation
```bash
git clone <repository-url>
cd floridify/backend
uv venv && source .venv/bin/activate
uv sync

# Configure authentication
cp auth/config.toml.example auth/config.toml
# Add your OpenAI API key to auth/config.toml

# Initialize search indices (one-time setup)
floridify search init

# Begin your lexical exploration
floridify lookup perspicacious
```

## 🎯 Core Features

### AI-Synthesized Meaning Extraction
The system's architectural innovation lies in **meaning-based clustering before synthesis**. Rather than presenting a bewildering array of disparate definitions, Floridify employs an LLM (configurable provider hereof) to identify semantic clusters and synthesize coherent explanations per meaning group. The result: bank¹ (financial), bank² (geographic), bank³ (arrangement) — each with focused, learnable definitions.

### Multi-Method Search Intelligence
Four-tier search architecture provides comprehensive lexical coverage:
- **Trie-based exact matching** for instant results
- **Fuzzy string algorithms** handling morphological variations  
- **FAISS semantic search** with vector similarity
- **AI fallback generation** for unknown, bespoke, or totally esoteric terms

### Rich Terminal Interface
A beautiful CLI experience leveraging the Rich library with Unicode superscripts, heat-mapped frequency visualization, progress tracking, and thoughtful typography. The terminal becomes a canvas for linguistic exploration.

```bash
# Hierarchical meaning display
floridify lookup sanguine

╭─ sanguine /ˈsæŋɡwɪn/ ────────────────────────────╮
│ ╭─ sanguine¹ (Optimistic Temperament) ──────╮   │
│ │ adjective                                  │   │
│ │   Confidently optimistic and cheerful.    │   │
│ │   synonyms: hopeful, buoyant, ebullient   │   │
│ ╰────────────────────────────────────────────╯   │
│ ╭─ sanguine² (Blood-red Complexion) ────────╮   │
│ │ adjective                                  │   │
│ │   Having a ruddy, healthy complexion.     │   │
│ ╰────────────────────────────────────────────╯   │
╰───────────────────────────────────────────────────╯
```

### Spaced Repetition Learning System
Implements the proven SuperMemo SM-2 algorithm with personalized difficulty adjustment. Each word maintains review schedules, ease factors, and mastery progression (Bronze → Silver → Gold), optimizing long-term retention through scientifically-validated spacing intervals.

### Comprehensive Wordlist Processing
Transform vocabulary corpora through intelligent batch processing:
- **Multi-format parsing**: numbered lists, CSV, tab-separated, plain text
- **Frequency tracking** with heat-map visualization  
- **Cost-effective batch API processing** (50% OpenAI discount)
- **Quality filtering** with configurable aggressiveness levels
- **Auto-generated nomenclature** via animal phrase names ("ochre-guan", "ebony-tanuki")

### Direct Anki Integration
Generate GRE-level flashcards that materialize instantly in your Anki application:
- **Fill-in-blank cards** testing contextual comprehension
- **Best-describes cards** with semantically relevant distractors
- **Professional styling** with gradient backgrounds and typography
- **AnkiConnect API** for seamless deck creation (no manual imports)

### Web Interface Excellence
Modern Vue 3 SPA with Tailwind CSS featuring:
- **GPU-accelerated animations** with scroll-aware search bar behavior
- **Typography-first excellence**: Fraunces serif elegance, Fira Code technical precision
- **Intelligent state persistence** via Pinia with localStorage integration
- **Metallic card variants** (gold, silver, bronze) with sparkle effects
- **Real-time progress streaming** during AI synthesis operations

## 🏗️ Architecture

**Technology Stack**:
- **Backend**: Python 3.12+ (FastAPI, MongoDB, OpenAI, FAISS)
- **Frontend**: Vue 3 + TypeScript (Tailwind CSS, Pinia, Vite)
- **Search**: Multi-method cascade with semantic vector similarity
- **AI**: OpenAI GPT-4 with structured outputs and meaning extraction
- **Storage**: MongoDB with Beanie ODM and multi-level caching

**Data Flow**: User Input → Multi-Method Search → Provider Aggregation → AI Synthesis → Hierarchical Display → Persistent Storage

**Performance Characteristics**:
- Sub-second search across 269k+ entries
- ~95% cache hit rate for repeated lookups  
- 2-4 second AI synthesis with structured outputs
- Concurrent batch processing (10 words parallel)
- FAISS-accelerated semantic similarity matching

## 📚 Advanced Functionality

### Semantic Exploration
```bash
# Discover related concepts through vector similarity
floridify search word --semantic efflorescence
# Results: bloom, flourish, blossom, burgeon...

# Synonym generation with "efflorescence" ranking
floridify similar perspicacious
# Balanced distribution: 40% common, 30% expressive, 20% foreign, 10% technical
```

### Batch Operations
```bash
# Process large vocabulary corpora
floridify word-list create comprehensive-vocab.txt --name advanced-lexicon
floridify word-list show advanced-lexicon  # Heat-mapped frequency display

# Export flashcards with academic rigor
floridify anki export advanced-lexicon --card-types fill_in_blank
```

### Database Management  
```bash
# Performance insights and optimization
floridify database stats --detailed
# Collection counts, cache metrics, synthesis quality scores

# Configuration management with secure key handling
floridify config keys set openai sk-your-api-key
floridify config set max_results 50
```

## 🎓 Use Cases

**Academic Excellence**: GRE/SAT preparation through systematic vocabulary acquisition with spaced repetition algorithms and scientifically-validated review scheduling.

**Professional Development**: Industry-specific terminology expansion with contextual understanding and practical usage examples.

**Linguistic Scholarship**: Comprehensive meaning analysis, etymology exploration, and semantic relationship discovery for serious language study.

**Creative Writing**: Precision in lexical selection through extensive synonym networks and contextual usage guidance.

## 🔧 Configuration

Edit `auth/config.toml` for system customization:

```toml
[api]
openai_api_key = "sk-your-key-here"
openai_model = "gpt-4o"  # Supports reasoning models (o1, o3)
rate_limit_enabled = true

[general]
default_provider = "wiktionary"
max_results = 20
cache_duration_hours = 24

[anki]
default_card_types = ["best_describes", "fill_in_blank"]
max_cards_per_word = 2
direct_export = true  # Requires AnkiConnect add-on
```

## 💻 Development & Deployment

### Local Development
```bash
# Docker mode (recommended)
./dev.sh --build  # Force image rebuild

# Native mode
./dev.sh --native  # Local Python/Node execution
```

### Production Deployment

**One-time setup:**
```bash
# Configure GitHub secrets and EC2 access
./scripts/setup
```

**Deploy to production:**
```bash
# Manual deployment
./scripts/deploy

# Or push to main branch for automated GitHub Actions deployment
git push origin main
```

The system includes comprehensive deployment automation with:
- Docker image building and publishing to GitHub Container Registry
- AWS EC2 deployment with SSL certificate provisioning
- DocumentDB integration with TLS security
- Automated health checks and rollback capabilities


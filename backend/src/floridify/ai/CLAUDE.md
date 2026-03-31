# ai/

Multi-provider AI connector + hybrid synthesis pipeline. Supports OpenAI, Anthropic, and local models (ollama, vLLM, llama.cpp). Local-first where quality matches or exceeds AI.

```
ai/
├── connector/                  # AIConnector: async multi-provider interface
│   ├── base.py                 # Core: structured outputs, retry, caching, provider dispatch
│   ├── config.py               # Provider enum (OPENAI, ANTHROPIC, LOCAL), effort levels
│   ├── synthesis.py            # Synthesis methods (dedup, clustering, etymology)
│   ├── generation.py           # Content generation (examples, facts, word forms)
│   ├── assessment.py           # Classification (CEFR, frequency, register, domain)
│   └── suggestions.py          # Word suggestion methods
│
├── synthesis/                  # Pipeline functions
│   ├── orchestration.py        # Parallel enhancement, clustering, entry enhancement
│   ├── word_level.py           # Pronunciation, etymology, word forms, facts
│   ├── definition_level.py     # Per-definition: synonyms, antonyms, examples, assessments
│   ├── hybrid.py               # Wiktionary + WordNet → AI delta (synonyms, antonyms)
│   ├── language_filter.py      # ISO code normalization, primary language filtering
│   └── postprocess.py          # Domain-in-text strip, definition text cleanup
│
├── assessment/                 # Local-first assessment (replaces AI for most tasks)
│   ├── frequency.py            # wordfreq Zipf + WordNet SemCor sense counts
│   ├── cefr.py                 # Frequency-based CEFR with sense adjustment
│   ├── domain.py               # WordNet lexname + hypernym chain taxonomy
│   ├── register.py             # Keyword-based register classification
│   └── regional.py             # Keyword-based regional variant detection
│
├── clustering/                 # Local sense clustering
│   ├── local_clustering.py     # Agglomerative + silhouette gating + WordNet priors
│   └── slug.py                 # TF-IDF deterministic slug + name generation
│
├── dedup/                      # Local 3-tier deduplication
│   ├── local_dedup.py          # Exact → fuzzy → semantic (Qwen3-0.6B)
│   └── canonicalize.py         # Text canonicalization, content word extraction
│
├── embedding_utils.py          # Shared encoder: encode_texts(), best_synset_by_embedding()
├── synthesizer.py              # DefinitionSynthesizer: dedup→cluster→enhance orchestrator
├── model_selection.py          # Task→model routing, resolve_model_for_provider()
├── constants.py                # SynthesisComponent enum, default component sets
├── batch_processor.py          # OpenAI Batch API (JSONL, 50% cost reduction)
├── prompt_manager.py           # Jinja2 template loading
├── adaptive_counts.py          # Dynamic enhancement counts by language
├── tournament.py               # Tournament-style word ranking
└── prompts/                    # Markdown Jinja2 templates
    ├── assess/                 # cefr, frequency, register, domain, grammar, regional
    ├── generate/               # examples, facts, word_forms
    ├── synthesize/             # definitions, synonyms, antonyms, etymology, pronunciation, dedup
    └── misc/                   # meaning_extraction (clustering), suggestions, validation
```

## Synthesis Pipeline (actual flow)

```
Provider Fetch (Wiktionary + WordNet + Apple + others, parallel)
  ↓
Local 3-Tier Dedup (canonicalized exact → rapidfuzz fuzzy → Qwen3-0.6B semantic)
  ↓
Local Pre-Clustering (agglomerative, cosine distance, silhouette quality gating)
  ↓ if silhouette < 0.4
AI Clustering Refinement (with local cluster hints)
  ↓
Definition Text Synthesis (AI, per cluster)
  ↓
Parallel Enhancement:
  LOCAL:  CEFR, frequency, register, domain, regional, dedup
  HYBRID: synonyms (Wiktionary+WordNet → AI delta), antonyms (same)
  AI:     examples, etymology, facts, word_forms, pronunciation
  ↓
Post-Processing: domain-in-text strip, language filtering (cognates → separate field)
  ↓
Versioned Save (SHA-256 content-addressable, edit metadata, provenance chain)
```

## Provider Support

| Provider | Config Section | Structured Output | Notes |
|----------|---------------|-------------------|-------|
| OpenAI | `[openai]` | GA (`chat.completions.parse`, SDK v2+) | Default. GPT-5 series. |
| Anthropic | `[anthropic]` | GA (`messages.create` + `output_config`) | Claude 4.5/4.6. |
| Local | `[local.high]`, `[local.medium]`, `[local.low]` | Via OpenAI-compatible API | ollama, vLLM, llama.cpp. Per-tier model routing. |

Set active provider in `[ai] provider = "openai" | "anthropic" | "local"`.

## Model Selection

Tasks route to capability tiers (HIGH/MEDIUM/LOW) via `TASK_COMPLEXITY_MAP`. Each provider resolves tiers to specific models:

- **OpenAI**: HIGH→gpt-5.4, MEDIUM→gpt-5-mini, LOW→gpt-5-nano
- **Anthropic**: HIGH→claude-opus-4-6, MEDIUM→claude-sonnet-4-6, LOW→claude-haiku-4-5
- **Local**: Per-tier model from config (e.g., HIGH→qwen3:32b, MEDIUM→qwen3:8b)

Many LOW tasks now bypass AI entirely (local assessment via wordfreq, WordNet, keyword classifiers).

## Embedding-Based Synset Matching

`embedding_utils.py` provides `best_synset_by_embedding()` — matches synthesized definition text to WordNet synsets using Qwen3-0.6B sentence embeddings. Shared by domain classification, sense-level frequency, CEFR adjustment, and hybrid synonym/antonym extraction. Falls back to word-overlap matching when encoder unavailable.

## Batch Processing

`batch_processor.py`: OpenAI Batch API via async context manager. Patches `_make_structured_request()` to collect requests into JSONL → submit → poll (max 1h) → download results. 50% cost reduction vs real-time API.

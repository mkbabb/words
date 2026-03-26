# AI Synthesis Pipeline

The synthesis pipeline reconciles N dictionary providers into one coherent entry by deduplicating near-identical definitions, clustering them by semantic sense, synthesizing canonical definitions in parallel, and progressively enhancing each with metadata—all governed by task-based model routing, adaptive generation counts, and tournament selection.

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [The AIConnector](#the-aiconnector)
4. [Model Selection & Routing](#model-selection--routing)
5. [Prompt Engineering](#prompt-engineering)
6. [Synthesis Components](#synthesis-components)
7. [Adaptive Generation Counts](#adaptive-generation-counts)
8. [Tournament Selection](#tournament-selection)
9. [Batch Processing](#batch-processing)
10. [Orchestration Mechanics](#orchestration-mechanics)
11. [Provenance & Audit Trail](#provenance--audit-trail)
12. [Graceful Degradation](#graceful-degradation)
13. [Quality Testing](#quality-testing)
14. [Token Economics](#token-economics)
15. [Key Files](#key-files)
16. [Glossary](#glossary)

## Overview

A single word queried across seven dictionary providers produces overlapping, contradictory, and variably granular definitions. Wiktionary might split "run" into 47 sub-senses; Oxford condenses it to 12; Apple Dictionary offers 8. The synthesis pipeline takes this raw material and produces one authoritative entry: definitions clustered by semantic sense, enriched with synonyms, antonyms, examples, CEFR levels, frequency bands, collocations, grammar patterns, usage notes, etymology, pronunciation, and interesting facts.

Two architectural decisions underpin the design:

1. **Dedup before cluster.** Clustering is the most expensive AI call (routed to the HIGH tier). Deduplicating definitions first with a cheaper MEDIUM-tier model eliminates near-duplicates and typically reduces input token count by ~40%, making the downstream clustering call proportionally cheaper and more accurate.

2. **Parallel enhancement with graceful degradation.** The four word-level synthesis tasks (definitions, pronunciation, etymology, facts) run concurrently via `asyncio.gather(return_exceptions=True)`. Definitions are the only required output—if that task fails, the pipeline propagates the error. The other three tasks degrade to `None` or empty lists, and the entry is saved regardless. The same policy applies to the 11 definition-level enhancement tasks that follow.

The pipeline supports two operational modes: **immediate** (default), where each AI call hits the API directly, and **batch**, where calls are collected into a JSONL file and submitted via OpenAI's Batch API for 50% cost reduction.

## Pipeline Architecture

The synthesis pipeline comprises five sequential stages, orchestrated by [`DefinitionSynthesizer.synthesize_entry()`](../backend/src/floridify/ai/synthesizer.py):

```
Provider DictionaryEntries (N providers)
  │
  ├─ Stage 1: Dedup ─── AI merges near-duplicates ──────────── MEDIUM tier
  │                      ~40-50% reduction in definitions
  │
  ├─ Stage 2: Cluster ── AI groups by semantic sense ────────── HIGH tier
  │                      Words like "bank" → separate clusters
  │
  ├─ Stage 3: Parallel Synthesis ── asyncio.gather ──────────── HIGH/MEDIUM/LOW
  │                ├─ Definitions (per cluster)                  via tournament
  │                ├─ Pronunciation (from providers + AI)
  │                ├─ Etymology (from providers + AI)
  │                └─ Facts (adaptive count)
  │
  ├─ Stage 4: Versioned Save ── SHA-256 content-addressable ── Storage
  │                              per-resource locks
  │
  └─ Stage 5: Definition Enhancement ── asyncio.gather ──────── MEDIUM/LOW
                   ├─ Synonyms        ├─ CEFR Level
                   ├─ Antonyms        ├─ Frequency Band
                   ├─ Examples        ├─ Register
                   ├─ Word Forms      ├─ Domain
                   ├─ Grammar         ├─ Collocations
                   ├─ Usage Notes     └─ Regional Variants
```

### Stage 1: Deduplication

The synthesizer batch-loads all `Definition` documents from all provider `DictionaryEntry` records via a single MongoDB `$in` query. These definitions are passed to [`AIConnector.deduplicate_definitions()`](../backend/src/floridify/ai/connector/synthesis.py), which uses the `synthesize/deduplicate` prompt template.

The AI identifies groups of near-duplicate definitions and selects the highest-quality representative from each group. Merge criteria: semantic overlap above ~80%, one definition being a strict subset of another, or definitions differing only in example scope. Definitions with different parts of speech, different semantic domains, opposing connotations, or literal vs. figurative senses are kept separate.

New `Definition` copies are created via `model_copy(update={"text": ..., "id": None})`—originals are never mutated, preserving the provider data for provenance tracking.

### Stage 2: Clustering

[`cluster_definitions()`](../backend/src/floridify/ai/synthesis/orchestration.py) prepares `(provider_name, part_of_speech, definition_text)` tuples and calls [`AIConnector.extract_cluster_mapping()`](../backend/src/floridify/ai/connector/synthesis.py). The `misc/meaning_extraction` prompt template instructs the model to group definitions into `MeaningCluster`s, each with:

- `cluster_slug`: structured identifier (e.g., `bank_noun_finance`, `bank_noun_geography`)
- `cluster_description`: 3–6 word summary
- `definition_indices`: which definitions belong to this cluster
- `relevancy`: 0.0–1.0 common usage frequency

Every definition index must appear in exactly one cluster. Different parts of speech are never merged. The prompt includes worked examples for aggressive merging ("phaeton" as carriage/automobile = one cluster) and antonymy preservation ("sanction" as approval vs. penalty = two clusters).

This is the most expensive call in the pipeline—routed to the HIGH tier (GPT-5.4)—because correct clustering requires understanding subtle semantic distinctions.

### Stage 3: Parallel Synthesis

Four word-level tasks execute concurrently via `asyncio.gather(return_exceptions=True)`:

| Task | Function | Tier | Output |
|------|----------|------|--------|
| Definitions | [`_synthesize_definitions()`](../backend/src/floridify/ai/synthesizer.py) → [`synthesize_definition_text()`](../backend/src/floridify/ai/synthesis/definition_level.py) | HIGH (tournament) | One synthesized `Definition` per cluster |
| Pronunciation | [`synthesize_pronunciation()`](../backend/src/floridify/ai/synthesis/word_level.py) | LOW | `Pronunciation` with IPA, phonetic, audio |
| Etymology | [`synthesize_etymology()`](../backend/src/floridify/ai/synthesis/word_level.py) | MEDIUM | `Etymology` with origin, root words, first use |
| Facts | [`generate_facts()`](../backend/src/floridify/ai/synthesis/word_level.py) | MEDIUM | List of categorized `Fact` objects |

Definition synthesis runs per cluster: each cluster's definitions are serialized with provider attribution, then passed to the AI which produces a single canonical definition text and part of speech. When tournament mode is enabled (default), three candidates are generated and ranked to select the highest quality result.

Pronunciation synthesis first checks provider data for existing IPA/phonetic data—if found, it clones and enhances via AI; if not, it generates from scratch. Audio files are then synthesized via the TTS subsystem (KittenTTS for English, Kokoro-ONNX for other languages).

Etymology synthesis collects etymology text from all providers, then asks the AI to produce a unified etymology with origin language, root words, and first known use.

Facts generation uses an adaptive count computed from the word's polysemy (more definitions = more facts, up to 4). The AI produces categorized facts (etymological, cultural, historical, linguistic, usage) with connections to previously searched words when available.

### Stage 4: Versioned Save

[`save_entry_versioned()`](../backend/src/floridify/storage/dictionary.py) stores the synthesized `DictionaryEntry` in the `VersionedDataManager` chain (L3 cache with SHA-256 content-addressable deduplication) and as a live MongoDB document. Per-resource locks prevent race conditions from concurrent force-refresh calls on the same word. An `EditMetadata` record captures the synthesis audit trail (see [Provenance](#provenance--audit-trail)).

### Stage 5: Definition-Level Enhancement

[`enhance_definitions_parallel()`](../backend/src/floridify/ai/synthesis/orchestration.py) runs up to 11 sub-tasks per definition, all concurrently across all definitions. For a word with 3 definitions, this means up to 33 parallel AI calls (bounded by a semaphore). Each task only runs if the field is empty or `force_refresh=True`.

After all tasks complete, [`_dedup_across_definitions()`](../backend/src/floridify/ai/synthesis/orchestration.py) removes synonym and antonym overlap across definitions. Higher-relevance definitions (by cluster relevance score) retain priority for shared words. The enhanced definitions are then batch-saved with version history.

## The AIConnector

[`AIConnector`](../backend/src/floridify/ai/connector/base.py) is the unified interface to external AI providers. It uses mixin composition to organize methods by domain:

| Mixin | Methods | Domain |
|-------|---------|--------|
| [`SynthesisMixin`](../backend/src/floridify/ai/connector/synthesis.py) | `synthesize_definitions`, `extract_etymology`, `synthesize_synonyms`, `synthesize_antonyms`, `deduplicate_definitions`, `extract_cluster_mapping`, `generate_word_of_the_day` | Core synthesis |
| [`GenerationMixin`](../backend/src/floridify/ai/connector/generation.py) | `generate_examples`, `pronunciation`, `generate_facts`, `identify_word_forms`, `generate_text`, `generate_synthetic_corpus`, `generate_anki_fill_blank`, `generate_anki_best_describes`, `suggestions`, `generate_synonym_chooser`, `generate_phrases` | Content generation |
| [`AssessmentMixin`](../backend/src/floridify/ai/connector/assessment.py) | `assess_frequency_band`, `classify_register`, `assess_domain`, `assess_cefr_level`, `assess_grammar_patterns`, `assess_collocations`, `usage_note_generation`, `assess_regional_variants` | Classification |
| [`SuggestionsMixin`](../backend/src/floridify/ai/connector/suggestions.py) | `validate_query`, `suggest_words` | Query handling |

### Dual-Provider Support

The connector supports two providers via the `Provider` enum:

- **OpenAI (GPT-5 series)**: Uses `beta.chat.completions.parse()` for structured outputs. GPT-5 models require the `developer` role (not `system`), `max_completion_tokens` (not `max_tokens`), and default `reasoning.effort=none` for fast structured output without reasoning tokens—which also enables temperature support.
- **Anthropic (Claude 4.5/4.6)**: Uses GA structured outputs via `output_config.format` with `effort` parameter. The `messages.create()` endpoint parses `block.parsed` directly from response content blocks.

Provider selection is configured in `auth/config.toml` under the `[ai]` section. The singleton factory [`get_ai_connector()`](../backend/src/floridify/ai/connector/base.py) reads provider, effort level, and concurrency settings from config.

### Structured Outputs

Every AI call returns a Pydantic model via structured output parsing. The flow:

1. The `response_format` parameter passes the Pydantic model class directly to the API
2. The API returns JSON conforming to the model's schema
3. `model_validate_json()` parses and validates the response
4. On `ValidationError`, the connector retries up to 2 additional times (`MAX_VALIDATION_RETRIES = 2`)
5. Validation error details (field paths, error types) are logged for debugging

### Caching

The cached entry point is `_make_structured_request()`, decorated with `@cached_api_call(ttl_hours=24.0, key_prefix="ai_structured")`. This decorator provides L1 (in-memory LRU) and L2 (disk with ZSTD compression) caching. The `system_prompt` parameter is excluded from cache key generation via `ignore_params`.

The uncached entry point `_make_structured_request_impl()` is called directly by tournament selection, which needs diverse uncached candidates.

### Budget Tracking

Before each API call, the connector checks remaining budget via `spending_tracker.check_budget()`. If the budget is exceeded, a `RateLimitError` is raised. After each successful call, token usage is recorded via `spending_tracker.record_spend(model, total_tokens)`.

### Error Handling

Transient API errors (rate limits, timeouts, connection errors) trigger exponential backoff retries up to 3 attempts. Refusal responses from either provider raise `ValueError`. The connector tracks `ModelInfo` (model name, token usage, response time, temperature) after each successful call via the `last_model_info` property.

## Model Selection & Routing

[`model_selection.py`](../backend/src/floridify/ai/model_selection.py) implements a three-tier routing system that maps task names to model tiers based on complexity requirements.

### The Three Tiers

| Tier | Model | Properties |
|------|-------|------------|
| HIGH | `gpt-5.4` | Frontier reasoning. Complex synthesis, clustering, suggestion generation. |
| MEDIUM | `gpt-5-mini` | Cost-optimized reasoning. Creative generation, pedagogical tasks, dedup. |
| LOW | `gpt-5-nano` | High-throughput instruction-following. Classification, assessment. |

`ModelTier` is an enum with properties that govern API behavior:

- `is_gpt5`: True for all GPT-5 series models
- `is_o_series`: True for o-series reasoning models (legacy)
- `uses_developer_role`: GPT-5 and o-series use `"developer"` instead of `"system"` role
- `uses_completion_tokens`: GPT-5 and o-series use `max_completion_tokens` instead of `max_tokens`

### Task Complexity Map

The `TASK_COMPLEXITY_MAP` dictionary maps 28 task names to `ModelComplexity` levels:

**HIGH** (5 tasks): `synthesize_definitions`, `suggest_words`, `extract_cluster_mapping`, `generate_synthetic_corpus`, `literature_analysis`

**MEDIUM** (13 tasks): `generate_synonyms`, `generate_synonym_chooser`, `generate_phrases`, `generate_facts`, `generate_examples`, `generate_anki_best_describes`, `generate_anki_fill_blank`, `synthesize_etymology`, `generate_collocations`, `generate_word_forms`, `generate_antonyms`, `generate_suggestions`, `lookup_word`, `deduplicate_definitions`, `literature_augmentation`, `text_generation`

**LOW** (10 tasks): `assess_frequency`, `assess_cefr_level`, `classify_domain`, `classify_register`, `generate_pronunciation`, `generate_usage_notes`, `validate_query`, `identify_grammar_patterns`, `identify_regional_variants`, `rank_candidates`

Unknown tasks default to MEDIUM.

### Temperature Routing

`get_temperature_for_model()` assigns temperature based on task characteristics:

| Task Category | Temperature | Tasks |
|---------------|-------------|-------|
| Creative | 0.8 | `generate_facts`, `generate_examples`, `suggest_words`, `generate_suggestions`, `generate_anki_*` |
| Classification | 0.3 | `assess_frequency`, `assess_cefr_level`, `classify_domain`, `classify_register`, `validate_query` |
| Default | 0.7 | Everything else |
| O-series | `None` | O-series reasoning models never support temperature |

The rationale: creative tasks benefit from diverse, non-obvious outputs. Classification tasks need deterministic, reproducible results. The default 0.7 balances quality with variety for synthesis and generation tasks.

### Token Budget Defaults

GPT-5 models use `max_completion_tokens`, which includes reasoning tokens. The default is 16,384 tokens for GPT-5 series (ensuring output fits after any internal reasoning) and 4,096 for GPT-4 series.

## Prompt Engineering

All prompts are Markdown templates rendered via Jinja2. The [`PromptManager`](../backend/src/floridify/ai/prompt_manager.py) class loads templates from `ai/prompts/`, organizes them by subdirectory, and renders them with automatic input sanitization.

### Template Organization

30 templates organized across 5 categories:

```
prompts/
├── synthesize/   # definitions, deduplicate, etymology, pronunciation, synonyms,
│                 # antonyms, synonym_chooser, phrases
├── generate/     # examples, facts, word_forms
├── assess/       # cefr, frequency, register, domain, grammar_patterns,
│                 # collocations, regional_variants
├── misc/         # anki_best_describes, anki_fill_blank, lookup, meaning_extraction,
│                 # query_validation, rank_candidates, suggestions, usage_note_generation,
│                 # word_suggestion
└── wotd/         # literature_analysis, synthetic_corpus, word_of_the_day
```

Templates use `.md` extension and Jinja2 syntax for variable interpolation, conditionals, and loops. Example from `synthesize/deduplicate.md`:

```markdown
# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions
{% for def in definitions %}
{{ loop.index0 }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task
Identify and merge duplicate or near-duplicate definitions...
```

### Sanitization Pipeline

`_sanitize_user_input()` processes all user-provided string values before template rendering:

1. **Length limit**: Hard truncation at 500 characters
2. **Control character stripping**: Removes `\x00`–`\x08`, `\x0b`, `\x0c`, `\x0e`–`\x1f`, `\x7f` (preserves newlines and tabs)
3. **Prompt injection neutralization**: Inserts zero-width spaces (`\u200b`) into triple backticks and role prefixes (`system:`, `assistant:`, `user:`, `<|im_start|>`, `<|im_end|>`)
4. **XML injection prevention**: Strips `<system>`, `<tool>`, `<function>`, `<assistant>`, `<human>` tags

`_sanitize_context()` recursively applies sanitization to all string values in nested dicts and lists.

### Design Principles

Across the 30 templates, several consistent patterns emerge:

- **Numbered input format**: Definitions are indexed by `loop.index0` so the AI can reference them by number in clustering and dedup responses
- **Explicit merge/keep-separate rules**: Templates include both positive and negative criteria with worked examples
- **Output constraints**: Maximum word counts for reasoning fields (e.g., "max 10 words" for merge reasoning)
- **Scoring rubrics**: Assessment templates include specific point allocations (e.g., ranking criteria: Accuracy 3pts, Completeness 3pts, Clarity 2pts, Distinctiveness 2pts)

## Synthesis Components

The [`SynthesisComponent`](../backend/src/floridify/ai/constants.py) enum defines 19 enhancement targets, organized into four categories:

### Word-Level (4)

| Component | Function | Output |
|-----------|----------|--------|
| `PRONUNCIATION` | [`synthesize_pronunciation()`](../backend/src/floridify/ai/synthesis/word_level.py) | `Pronunciation` with IPA, phonetic, syllables, audio |
| `ETYMOLOGY` | [`synthesize_etymology()`](../backend/src/floridify/ai/synthesis/word_level.py) | `Etymology` with text, origin language, root words, first use |
| `WORD_FORMS` | [`synthesize_word_forms()`](../backend/src/floridify/ai/synthesis/word_level.py) | List of `WordForm` (type + text) |
| `FACTS` | [`generate_facts()`](../backend/src/floridify/ai/synthesis/word_level.py) | Categorized `Fact` objects |

### Definition-Level (11)

| Component | Function | Model Tier | Output |
|-----------|----------|------------|--------|
| `SYNONYMS` | [`synthesize_synonyms()`](../backend/src/floridify/ai/synthesis/definition_level.py) | MEDIUM | List of strings (max 50) |
| `ANTONYMS` | [`synthesize_antonyms()`](../backend/src/floridify/ai/synthesis/definition_level.py) | MEDIUM | List of strings (max 50) |
| `EXAMPLES` | [`generate_examples()`](../backend/src/floridify/ai/synthesis/definition_level.py) | MEDIUM | List of example sentences |
| `CEFR_LEVEL` | [`assess_definition_cefr()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | A1–C2 string |
| `FREQUENCY_BAND` | [`assess_definition_frequency()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | 1–5 integer |
| `REGISTER` | [`classify_definition_register()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | formal/informal/neutral/slang/technical |
| `DOMAIN` | [`assess_definition_domain()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | Subject area string |
| `GRAMMAR_PATTERNS` | [`assess_grammar_patterns()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | List of `GrammarPattern` |
| `COLLOCATIONS` | [`assess_collocations()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | List of `Collocation` |
| `USAGE_NOTES` | [`usage_note_generation()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | List of `UsageNote` |
| `REGIONAL_VARIANTS` | [`assess_regional_variants()`](../backend/src/floridify/ai/synthesis/definition_level.py) | LOW | List of region strings |

### Enrichment (2)

| Component | Function | Tier |
|-----------|----------|------|
| `SYNONYM_CHOOSER` | [`generate_synonym_chooser()`](../backend/src/floridify/ai/connector/generation.py) | MEDIUM |
| `PHRASES` | [`generate_phrases()`](../backend/src/floridify/ai/connector/generation.py) | MEDIUM |

`SYNONYM_CHOOSER` generates Merriam-Webster-style comparative synonym essays ("Choose the Right Synonym"), comparing up to 8 near-synonyms with per-word distinction analysis. `PHRASES` generates idioms and phrases containing the word.

### Utility (2)

| Component | Function |
|-----------|----------|
| `DEFINITION_TEXT` | [`synthesize_definition_text()`](../backend/src/floridify/ai/synthesis/definition_level.py) |
| `CLUSTER_DEFINITIONS` | [`cluster_definitions()`](../backend/src/floridify/ai/synthesis/orchestration.py) |

### Default vs. Full Component Sets

`SynthesisComponent` provides class methods for common component sets:

| Method | Components |
|--------|------------|
| `default_definition_components()` | SYNONYMS, EXAMPLES, ANTONYMS |
| `default_word_components()` | PRONUNCIATION, ETYMOLOGY |
| `default_components()` | Union of the above two |
| `word_level_components()` | PRONUNCIATION, ETYMOLOGY, WORD_FORMS, FACTS, SYNONYM_CHOOSER, PHRASES |
| `definition_level_components()` | All 11 definition-level components |

When `enhance_definitions_parallel()` is called with `components=None`, it defaults to `default_components()`. Selective regeneration (via the API) can target any subset.

## Adaptive Generation Counts

[`adaptive_counts.py`](../backend/src/floridify/ai/adaptive_counts.py) implements a three-factor model that scales output counts based on word characteristics, preventing over-generation for simple entries and under-generation for complex ones.

### The Three Factors

**Language factor** (`lang_factor`): English gets a factor of 1.0 while all non-English languages get 0.4, reflecting the denser synonym/antonym relationships available for English in the training data and preventing the AI from hallucinating relationships for less-resourced languages.

**Polysemy factor** (`poly_factor`): Scales linearly with definition count—a single-definition word gets 1.0, and each additional definition adds 0.15, capped at 1.5 via `min(1.0 + (definition_count - 1) * 0.15, 1.5)`.

**Part-of-speech factor** (`pos_factor`): Content words with rich synonym networks get higher counts than function words:

| POS | Factor | Rationale |
|-----|--------|-----------|
| adjective, verb | 1.0 | Rich synonym/antonym relationships |
| noun | 0.8 | Slightly fewer semantic alternatives |
| adverb | 0.7 | Moderate synonym availability |
| interjection | 0.4 | Limited semantic relationships |
| preposition, conjunction, determiner, pronoun, particle | 0.3 | Function words: few meaningful synonyms |

An unknown POS defaults to a factor of 0.5.

### Count Computation

The composite factor `f = lang_factor * poly_factor * pos_factor` scales base counts for each field:

| Field | Base | Formula | Min | Max |
|-------|------|---------|-----|-----|
| Synonyms | 5 | `round(5 * f)` | 2 | 12 |
| Antonyms | 3 | `round(3 * f)` | 1 | 8 |
| Examples | 2 | `round(2 * lang_factor)` | 1 | 4 |
| Facts | 2 | `round(2 * poly_factor)` | 1 | 4 |
| Collocations | 4 | `round(4 * f)` | 2 | 8 |
| Usage Notes | 2 | `round(2 * lang_factor)` | 1 | 3 |
| Grammar Patterns | 2 | `round(2 * pos_factor)` | 1 | 3 |

Examples and usage notes depend only on language (not POS or polysemy), since their value doesn't scale with word complexity. Facts depend only on polysemy (more senses = more interesting things to say). Grammar patterns depend only on POS (verbs have richer patterns than nouns).

### Worked Example

Word: "run" (English verb, 4 definitions)

```
lang_factor  = 1.0          (English)
poly_factor  = min(1.0 + (4-1)*0.15, 1.5) = 1.45
pos_factor   = 1.0          (verb)
f            = 1.0 * 1.45 * 1.0 = 1.45

synonyms         = clamp(round(5 * 1.45), 2, 12) = 7
antonyms         = clamp(round(3 * 1.45), 1, 8)  = 4
examples         = clamp(round(2 * 1.0), 1, 4)   = 2
facts            = clamp(round(2 * 1.45), 1, 4)   = 3
collocations     = clamp(round(4 * 1.45), 2, 8)  = 6
usage_notes      = clamp(round(2 * 1.0), 1, 3)   = 2
grammar_patterns = clamp(round(2 * 1.0), 1, 3)   = 2
```

Contrast with "le" (French determiner, 1 definition):

```
lang_factor  = 0.4          (non-English)
poly_factor  = 1.0          (single definition)
pos_factor   = 0.3          (determiner)
f            = 0.4 * 1.0 * 0.3 = 0.12

synonyms         = clamp(round(5 * 0.12), 2, 12) = 2 (min)
antonyms         = clamp(round(3 * 0.12), 1, 8)  = 1 (min)
examples         = clamp(round(2 * 0.4), 1, 4)   = 1
facts            = clamp(round(2 * 1.0), 1, 4)    = 2
collocations     = clamp(round(4 * 0.12), 2, 8)  = 2 (min)
usage_notes      = clamp(round(2 * 0.4), 1, 3)   = 1
grammar_patterns = clamp(round(2 * 0.3), 1, 3)   = 1
```

## Tournament Selection

[`tournament.py`](../backend/src/floridify/ai/tournament.py) implements a generate-then-rank pattern ported from the gaggle project's `BestOfNConnector`. For high-stakes outputs—currently definition synthesis and word suggestion—multiple candidates are generated in parallel and ranked to select the best.

### How It Works

1. **Generate phase**: N candidates (default 3, configurable 2–8) are generated in parallel using `_make_structured_request_impl()` (uncached, bypassing L1/L2 cache to ensure diversity). The generator tier defaults to MEDIUM, with a temperature boost of +0.15 added to the task's base temperature to increase candidate diversity.

2. **Filter phase**: Failed candidates (API errors, validation failures) are filtered out. If only one valid candidate remains, it's returned without ranking. If all candidates fail, a `RuntimeError` is raised.

3. **Rank phase**: A dedicated ranking prompt (rendered from `misc/rank_candidates`) is sent to the ranker model (default LOW tier—GPT-5-nano). The ranking prompt serializes all candidates as JSON and asks for per-candidate scores on a 0–10 scale across four criteria:
   - **Accuracy** (3 points): Factual correctness, no hallucinated content
   - **Completeness** (3 points): Covers all relevant senses/aspects
   - **Clarity** (2 points): Clear, natural phrasing
   - **Distinctiveness** (2 points): Avoids redundancy between definitions

4. **Select phase**: The candidate with the highest score is selected. If ranking itself fails (API error), the first candidate is returned as a fallback.

### Configuration

[`TournamentConfig`](../backend/src/floridify/ai/tournament.py) controls the tournament:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `n` | 3 | 2–8 | Number of candidates to generate |
| `generator_tier` | MEDIUM | Any `ModelTier` | Model tier for candidate generation |
| `ranker_tier` | LOW | Any `ModelTier` | Model tier for ranking |
| `temperature_boost` | 0.15 | 0.0–0.5 | Added to base temperature for diversity |

Tournament is enabled/disabled globally via `AIConfig.enable_tournament` (default `True`). The candidate count is configurable via `AIConfig.tournament_n`.

### Where Tournaments Run

Currently two methods use tournament selection:

- [`synthesize_definitions()`](../backend/src/floridify/ai/connector/synthesis.py): The most important output of the pipeline
- [`suggest_words()`](../backend/src/floridify/ai/connector/suggestions.py): User-facing word suggestions from descriptive queries

Both check `AIConfig.enable_tournament` and fall back to single-shot generation if disabled.

### Cost Analysis

A tournament with N=3 costs approximately `3 * MEDIUM_cost + 1 * LOW_cost` per invocation—roughly 3.2x a single MEDIUM call. The LOW-tier ranking call is negligible. The cost is justified by measurably better definition quality: ranked definitions avoid circular phrasing, cover more senses, and produce clearer prose.

## Batch Processing

[`batch_processor.py`](../backend/src/floridify/ai/batch_processor.py) enables 50% cost reduction on OpenAI API calls by collecting requests and submitting them as a single batch via the OpenAI Batch API.

### Architecture

Three classes collaborate:

**`BatchCollector`**: Accumulates `AIBatchRequest` objects, each containing a prompt, response model, and an `asyncio.Future` that callers await. When all requests are collected, `prepare_batch_file()` serializes them to a JSONL file with the OpenAI Batch API format:

```json
{
  "custom_id": "req-1-a3b2c4d5",
  "method": "POST",
  "url": "/v1/chat/completions",
  "body": {
    "model": "gpt-5-nano",
    "messages": [...],
    "response_format": {"type": "json_schema", "json_schema": {...}}
  }
}
```

The model is resolved per-request from the `task_name` via `get_model_for_task()`, preserving the same tier routing used in immediate mode.

**`BatchExecutor`**: Handles the OpenAI Batch API lifecycle:
1. Upload the JSONL file via `client.files.create(purpose="batch")`
2. Create the batch job via `client.batches.create(completion_window="24h")`
3. Poll for completion with configurable `check_interval` (default 1 second) and `max_wait_time` (default 3600 seconds)
4. Download and parse results from the output file
5. Clean up temporary files

**`BatchContext`**: An async context manager that transparently patches `AIConnector._make_structured_request` during its scope. Code inside the context makes normal AI calls, but those calls are intercepted and collected rather than executed immediately. On exit, the batch is submitted and results resolve the awaited futures.

### Usage

```python
async with batch_synthesis(ai_connector) as batch:
    # All AI calls within this block are collected, not executed
    await enhance_definitions_parallel(definitions, word, ai_connector)
    # Batch execution happens automatically on __aexit__
```

The `batch_mode=True` parameter in `enhance_definitions_parallel()` triggers this path. It's designed for bulk operations (e.g., re-synthesizing an entire wordlist) where latency is less important than cost.

### Error Handling

If the batch job fails, expires, or times out, all collected futures receive the exception. Individual request failures within a successful batch are handled per-request: successful results are parsed and resolved; failed results set exceptions on their respective futures.

## Orchestration Mechanics

### Concurrency Control

[`orchestration.py`](../backend/src/floridify/ai/synthesis/orchestration.py) declares a module-level semaphore:

```python
_MAX_CONCURRENT_AI_CALLS = 20
_ai_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_AI_CALLS)
```

Every enhancement task is wrapped via `_bounded(coro)`, which acquires the semaphore before execution. This prevents overwhelming the AI provider with too many simultaneous requests—particularly important during Stage 5, where a 5-definition word with 11 components generates 55 potential tasks.

The `AIConnector` itself has a separate per-request semaphore (default 10, configurable via `max_concurrent_requests` in config) that governs the actual API call. The orchestration semaphore acts as an outer bound; the connector semaphore as an inner one.

### Cross-Definition Dedup

After all definition-level enhancements complete, [`_dedup_across_definitions()`](../backend/src/floridify/ai/synthesis/orchestration.py) removes synonym and antonym overlap. Definitions are sorted by `meaning_cluster.relevance` descending, and each word is assigned to the first (highest-relevance) definition that claims it. This prevents the same synonym from appearing under multiple definitions.

### Selective Regeneration

[`regenerate_entry_components()`](../backend/src/floridify/ai/synthesizer.py) and [`enhance_synthesized_entry()`](../backend/src/floridify/ai/synthesis/orchestration.py) support regenerating specific components without re-running the entire pipeline. The API can specify any subset of `SynthesisComponent` values, and only those components are re-generated (with `force_refresh=True`).

### Component Registry

The `SYNTHESIS_COMPONENTS` dict maps string names to their implementation functions, providing a unified lookup for the 17 enhancement operations:

```python
SYNTHESIS_COMPONENTS = {
    "pronunciation": synthesize_pronunciation,
    "etymology": synthesize_etymology,
    "word_forms": synthesize_word_forms,
    "facts": generate_facts,
    "synonyms": synthesize_synonyms,
    "examples": generate_examples,
    # ... 11 more
}
```

## Provenance & Audit Trail

Every synthesized entry carries a complete chain of attribution back to its source provider data.

### SourceReference

[`SourceReference`](../backend/src/floridify/models/dictionary.py) links a synthesized definition or entry to the provider data it was derived from:

```python
class SourceReference(BaseModel):
    provider: DictionaryProvider      # e.g., WIKTIONARY, OXFORD
    entry_id: PydanticObjectId        # Provider DictionaryEntry._id
    entry_version: str                # e.g., "1.0.3"
    definition_ids: list[PydanticObjectId]
```

The synthesized `DictionaryEntry` carries `source_entries: list[SourceReference]` at the entry level, and each synthesized `Definition` carries `source_definitions: list[SourceReference]` at the definition level. This two-level provenance allows tracing any synthesized text back to the specific provider definitions that contributed to it.

### SynthesisAuditEntry

[`SynthesisAuditEntry`](../backend/src/floridify/models/base.py) records operational metadata for each synthesis run:

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | `str` | e.g., "gpt-5-mini" |
| `model_tier` | `str | None` | "high", "medium", "low" |
| `components_enhanced` | `list[str]` | SynthesisComponent values processed |
| `total_tokens` | `int | None` | Total token usage |
| `response_time_ms` | `int | None` | Wall-clock duration |
| `source_providers` | `list[str]` | Provider names used as input |
| `definitions_input` | `int` | Count of definitions from providers |
| `definitions_output` | `int` | Count after synthesis |
| `dedup_removed` | `int` | Definitions eliminated by dedup |
| `clusters_created` | `int` | Number of meaning clusters |

### EditMetadata

[`EditMetadata`](../backend/src/floridify/models/base.py) wraps the audit entry with who/when/why context:

```python
class EditMetadata(BaseModel):
    user_id: str | None              # Clerk user_id from JWT
    username: str | None             # Display name
    operation_type: OperationType    # AI_SYNTHESIS, MANUAL_EDIT, etc.
    change_reason: str | None        # Free-text commit message
    field_changes: list[FieldChange] # Field-level diffs
    synthesis_audit: SynthesisAuditEntry | None
```

For AI synthesis, `operation_type` is `OperationType.AI_SYNTHESIS`, `change_reason` is auto-generated (e.g., "AI synthesis from 3 providers"), and `synthesis_audit` contains the detailed audit entry.

### ModelInfo

Every synthesized document (definitions, examples, facts, pronunciations) carries a [`ModelInfo`](../backend/src/floridify/models/base.py) field tracking the specific AI model used:

```python
class ModelInfo(BaseModel):
    name: str              # "gpt-5.4", "gpt-5-mini", etc.
    confidence: float      # 0.0–1.0
    temperature: float     # Generation temperature used
    max_tokens: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    response_time_ms: int | None
    generation_count: int  # Times regenerated (incremented on re-synthesis)
```

## Graceful Degradation

The pipeline enforces a strict hierarchy: **definitions are required; everything else is optional.**

### Stage 3 (Parallel Synthesis)

`asyncio.gather(return_exceptions=True)` runs four tasks. Results are examined individually:

| Task | On Failure | Behavior |
|------|-----------|----------|
| Definitions | **Re-raise** | Pipeline aborts; provider data returned as-is to caller |
| Pronunciation | Log warning | Entry saved with `pronunciation_id=None` |
| Etymology | Log warning | Entry saved with `etymology=None` |
| Facts | Log warning | Entry saved with `fact_ids=[]` |

### Stage 5 (Enhancement)

Each of the 11 definition-level tasks is independent. Failures are counted and logged but don't abort the enhancement run:

```
Enhanced 3 definitions: 28 successes, 5 failures
```

Failed fields are simply left empty (or at their previous values if this is a re-enhancement). Successful fields are applied, cross-definition dedup runs, and definitions are batch-saved.

### Cluster Synthesis Failures

Within Stage 3, each cluster is synthesized independently via `asyncio.gather(*synthesis_tasks, return_exceptions=True)`. If cluster "bank_noun_finance" fails but "bank_noun_geography" succeeds, the entry is created with only the successful cluster's definition. The failure is logged with full stack trace.

### AI Provider Failures

Transient API errors (rate limits, timeouts, connection errors) are retried up to 3 times with exponential backoff. Validation errors on structured output parsing are retried up to 2 additional times. Only after exhausting retries does a task fail.

## Quality Testing

The test suite validates synthesis output across two dimensions.

### Golden Fixtures

[`audit/fixtures.py`](../backend/src/floridify/audit/fixtures.py) provides deterministic test data including Wikitext samples, multi-version payload generators, and corpus builders of various sizes (96 to 200,000 words). These fixtures use seed-based generation for reproducibility without requiring AI API calls.

### Structural Validators

Tests in [`tests/ai/test_synthesis_quality_structural.py`](../backend/tests/ai/test_synthesis_quality_structural.py) verify:

- All required fields are populated after synthesis
- Definition counts fall within expected ranges
- Synonym/antonym lists contain no self-references
- CEFR levels are valid (A1–C2)
- Frequency bands are in range (1–5)
- Etymology has required subfields (text, origin_language)
- Pronunciation has IPA and phonetic representations
- ModelInfo is attached to synthesized documents

### Semantic Validators

Tests in [`tests/ai/test_synthesis_quality_semantic.py`](../backend/tests/ai/test_synthesis_quality_semantic.py) verify:

- Synthesized definitions don't use circular phrasing (defining a word with itself)
- Meaning clusters for polysemous words produce distinct definition texts
- Synonym lists contain semantically related words (not random words)
- Example sentences contain the target word in natural context
- Etymology references real languages and historical periods

Both structural and semantic tests run against real MongoDB instances (per-test databases) with AI API calls mocked to return fixture data.

## Token Economics

### Why Dedup Before Cluster

Clustering is routed to the HIGH tier because it requires understanding subtle semantic distinctions. Dedup is routed to the cheaper MEDIUM tier because near-duplicate detection is a simpler task.

A typical word arrives with 15–30 definitions across 3–5 providers. Deduplication typically removes 40–50% of these. The clustering prompt includes the full text of every definition, so halving the definition count roughly halves the prompt token count for the most expensive call.

Concrete example: "algorithm" from 3 providers yields 12 definitions. Dedup identifies 4 near-duplicate groups, reducing to 7 unique definitions. The clustering prompt drops from ~2,400 tokens to ~1,400 tokens—a 42% reduction on the most expensive API call.

### Tier Cost Ratios

The three GPT-5 tiers have approximately these relative costs per token (as of March 2026):

| Tier | Model | Relative Cost |
|------|-------|---------------|
| HIGH | gpt-5.4 | 1.0x |
| MEDIUM | gpt-5-mini | ~0.15x |
| LOW | gpt-5-nano | ~0.03x |

By routing 10 assessment tasks to LOW instead of MEDIUM, the pipeline saves ~80% on those calls. By routing dedup to MEDIUM instead of HIGH, it saves ~85% on that call. The only tasks at HIGH are clustering, definition synthesis, word suggestions, and a handful of specialized tasks—exactly the ones where reasoning quality materially affects output quality.

### Adaptive Counts as Token Control

Adaptive counts don't just improve output quality—they directly control token usage. Requesting 2 synonyms for a French determiner instead of 12 for an English verb reduces the AI's output token count proportionally. Since the prompt template includes the `count` parameter, the model knows exactly how many items to produce and self-limits accordingly.

### Batch API Savings

The OpenAI Batch API offers a 50% discount on per-token pricing. For bulk operations (re-synthesizing a 500-word wordlist), this compounds with tier routing: a LOW-tier assessment in batch mode costs ~1.5% of a HIGH-tier immediate call.

## Key Files

| File | Role |
|------|------|
| [`ai/synthesizer.py`](../backend/src/floridify/ai/synthesizer.py) | `DefinitionSynthesizer`—main orchestrator, 5-stage pipeline |
| [`ai/synthesis/orchestration.py`](../backend/src/floridify/ai/synthesis/orchestration.py) | Parallel enhancement, clustering, cross-definition dedup, component registry |
| [`ai/synthesis/word_level.py`](../backend/src/floridify/ai/synthesis/word_level.py) | Pronunciation (with TTS), etymology, word forms, facts |
| [`ai/synthesis/definition_level.py`](../backend/src/floridify/ai/synthesis/definition_level.py) | 11 per-definition enhancement functions |
| [`ai/connector/base.py`](../backend/src/floridify/ai/connector/base.py) | `AIConnector`—dual-provider (OpenAI/Anthropic), structured outputs, retry, caching |
| [`ai/connector/synthesis.py`](../backend/src/floridify/ai/connector/synthesis.py) | `SynthesisMixin`—dedup, cluster, synonym, antonym, definition synthesis methods |
| [`ai/connector/generation.py`](../backend/src/floridify/ai/connector/generation.py) | `GenerationMixin`—examples, pronunciation, facts, Anki cards, phrases, synonym chooser |
| [`ai/connector/assessment.py`](../backend/src/floridify/ai/connector/assessment.py) | `AssessmentMixin`—CEFR, frequency, register, domain, grammar, collocations, usage, regions |
| [`ai/connector/suggestions.py`](../backend/src/floridify/ai/connector/suggestions.py) | `SuggestionsMixin`—query validation, word suggestions (with tournament) |
| [`ai/connector/config.py`](../backend/src/floridify/ai/connector/config.py) | `Provider`, `Effort` enums, `AIConfig` with tournament settings |
| [`ai/model_selection.py`](../backend/src/floridify/ai/model_selection.py) | 3-tier routing: `TASK_COMPLEXITY_MAP`, `ModelTier`, temperature routing |
| [`ai/constants.py`](../backend/src/floridify/ai/constants.py) | `SynthesisComponent` enum (19 values), default counts, parameter ordering standard |
| [`ai/adaptive_counts.py`](../backend/src/floridify/ai/adaptive_counts.py) | Three-factor adaptive count model (language, polysemy, POS) |
| [`ai/tournament.py`](../backend/src/floridify/ai/tournament.py) | Tournament selection: N candidates, ranking, `TournamentConfig` |
| [`ai/batch_processor.py`](../backend/src/floridify/ai/batch_processor.py) | OpenAI Batch API: `BatchCollector`, `BatchExecutor`, `BatchContext` |
| [`ai/prompt_manager.py`](../backend/src/floridify/ai/prompt_manager.py) | Jinja2 template loading, sanitization pipeline |
| [`ai/models.py`](../backend/src/floridify/ai/models.py) | Barrel re-export of 60+ Pydantic response models |
| [`ai/prompts/`](../backend/src/floridify/ai/prompts/) | 30 Markdown prompt templates across 5 categories |
| [`models/base.py`](../backend/src/floridify/models/base.py) | `ModelInfo`, `SynthesisAuditEntry`, `EditMetadata`, `OperationType` |
| [`models/dictionary.py`](../backend/src/floridify/models/dictionary.py) | `SourceReference`, `DictionaryEntry`, `Definition`, `Word` |

## Glossary

**Adaptive counts.** Dynamically computed output quantities (synonyms, antonyms, examples, etc.) based on word characteristics—language, polysemy, and part of speech. Prevents over-generation for simple entries and under-generation for complex ones.

**Batch API.** OpenAI's asynchronous processing endpoint that accepts JSONL files of requests and processes them within a 24-hour window at 50% cost reduction. Results are downloaded after completion.

**CEFR level.** Common European Framework of Reference for Languages proficiency scale (A1–C2). Assigned per definition to indicate the vocabulary level at which a learner would encounter a word in that sense.

**Clustering.** The process of grouping deduplicated definitions into semantic sense groups (meaning clusters). A polysemous word like "bank" produces separate clusters for its financial and geographic senses.

**Cross-definition dedup.** Post-enhancement pass that removes synonym and antonym overlap across definitions of the same word. Higher-relevance definitions retain priority.

**Deduplication.** AI-driven identification and merging of near-duplicate definitions across providers before clustering. Reduces token consumption and improves clustering accuracy.

**Developer role.** The GPT-5 series API requires `"developer"` as the system-level message role (replacing the `"system"` role used by GPT-4 and earlier models).

**Frequency band.** Integer 1–5 indicating how commonly a word is used in everyday language. Band 1 is the most common (top 1,000 words); band 5 is rare or archaic.

**Graceful degradation.** Design principle where only definitions are required to succeed. Pronunciation, etymology, facts, and all 11 definition-level enhancements fail independently without aborting the pipeline.

**Meaning cluster.** A group of definitions sharing a core semantic sense, identified by AI clustering. Each cluster has a slug (e.g., `bank_noun_finance`), description, order, and relevance score.

**Model tier.** One of three capability levels in the GPT-5 series: HIGH (gpt-5.4), MEDIUM (gpt-5-mini), LOW (gpt-5-nano). Tasks are routed to tiers based on the `TASK_COMPLEXITY_MAP`.

**Provenance.** The chain of `SourceReference` objects linking a synthesized entry back to the specific provider entries and definitions it was derived from, including version numbers at the time of synthesis.

**Structured outputs.** API feature where the AI response is constrained to a JSON schema derived from a Pydantic model, ensuring type-safe parsing without manual extraction.

**Synthesis audit.** The `SynthesisAuditEntry` record attached to each versioned save, capturing model name, token usage, response time, provider sources, definition counts, and components enhanced.

**Tournament selection.** Generate-then-rank pattern where N candidates are produced with increased temperature diversity, then scored by a cheaper ranker model. Used for definition synthesis and word suggestions.

**Validation retry.** When structured output parsing fails (`ValidationError`), the connector retries the same API call up to 2 additional times, on the assumption that the model may produce valid output on a subsequent attempt.

# AI Synthesis Pipeline

5-stage pipeline from provider data to enhanced dictionary entries. Deduplicates definitions across providers, clusters by semantic sense, synthesizes one coherent entry per cluster, then enhances each definition with synonyms, examples, CEFR levels, and more—all concurrently.

## Table of Contents

- [Pipeline](#pipeline)
- [Model Routing](#model-routing)
- [Synthesis Components](#synthesis-components)
- [Graceful Degradation](#graceful-degradation)
- [Key Files](#key-files)

## Pipeline

```
Provider DictionaryEntries
  → Dedup (merge near-duplicate definitions across providers)
  → Cluster (group by semantic sense via AI)
  → Parallel Synthesize (4 word-level tasks via asyncio.gather)
  → Versioned Save (SHA-256 content-addressable, per-resource locks)
  → Parallel Enhance (11 definition-level tasks per definition)
```

**Stage 1—Dedup**: Batch-loads all `Definition` documents from all providers. [`AIConnector.deduplicate_definitions()`](../backend/src/floridify/ai/connector/synthesis.py) identifies near-duplicates. New `Definition` copies are created with merged text; originals aren't mutated.

**Stage 2—Cluster**: [`AIConnector.extract_cluster_mapping()`](../backend/src/floridify/ai/connector/synthesis.py) groups deduplicated definitions into `MeaningCluster`s. Each cluster gets an `id`, `name`, `description`, `order`, and `relevance` score. Words like "bank" produce separate clusters (financial vs. geographic).

**Stage 3—Synthesize**: Four word-level tasks run in parallel via `asyncio.gather(return_exceptions=True)`:

| Task | Function | Source |
|------|----------|--------|
| Definitions | [`synthesize_definition_text()`](../backend/src/floridify/ai/synthesis/definition_level.py) | Groups by cluster, one definition per cluster |
| Pronunciation | [`synthesize_pronunciation()`](../backend/src/floridify/ai/synthesis/word_level.py) | Enhances existing or creates new |
| Etymology | [`synthesize_etymology()`](../backend/src/floridify/ai/synthesis/word_level.py) | From provider data + AI |
| Facts | [`generate_facts()`](../backend/src/floridify/ai/synthesis/word_level.py) | Interesting facts about the word |

**Stage 4—Save**: [`save_entry_versioned()`](../backend/src/floridify/storage/dictionary.py) stores the entry in the `VersionedDataManager` chain (history) and as a live `DictionaryEntry` document (current state). Per-resource locks prevent races from concurrent force-refresh calls.

**Stage 5—Enhance**: [`enhance_definitions_parallel()`](../backend/src/floridify/ai/synthesis/orchestration.py) runs up to 11 sub-tasks per definition.

## Model Routing

[`model_selection.py`](../backend/src/floridify/ai/model_selection.py) maps task names to `ModelComplexity` (HIGH/MEDIUM/LOW), then to a `ModelTier`:

| Tier | Model | Tasks |
|------|-------|-------|
| HIGH | `gpt-5.4` | `synthesize_definitions`, `suggest_words`, `extract_cluster_mapping`, `generate_synthetic_corpus`, `literature_analysis` |
| MEDIUM | `gpt-5-mini` | `generate_synonyms`, `generate_examples`, `synthesize_etymology`, `deduplicate_definitions`, `generate_antonyms`, `generate_collocations`, `generate_word_forms`, `generate_anki_*` |
| LOW | `gpt-5-nano` | `assess_cefr_level`, `assess_frequency`, `classify_register`, `classify_domain`, `generate_pronunciation`, `generate_usage_notes`, `identify_grammar_patterns` |

Temperature routing: creative tasks (facts, examples, suggestions) get 0.8. Classification tasks (CEFR, frequency, register) get 0.3. Default: 0.7. O-series reasoning models get `None`.

## Synthesis Components

[`SynthesisComponent`](../backend/src/floridify/ai/constants.py) enum defines 17 enhancement targets:

**Word-level** (4): `PRONUNCIATION`, `ETYMOLOGY`, `WORD_FORMS`, `FACTS`

**Definition-level** (11): `SYNONYMS`, `EXAMPLES`, `ANTONYMS`, `CEFR_LEVEL`, `FREQUENCY_BAND`, `REGISTER`, `DOMAIN`, `GRAMMAR_PATTERNS`, `COLLOCATIONS`, `USAGE_NOTES`, `REGIONAL_VARIANTS`

**Utilities** (2): `DEFINITION_TEXT`, `CLUSTER_DEFINITIONS`

Each definition-level component maps to a function in [`definition_level.py`](../backend/src/floridify/ai/synthesis/definition_level.py):

```python
synthesize_synonyms()           # max 50
synthesize_antonyms()           # max 50
generate_examples()             # max 20
assess_definition_cefr()        # A1–C2
assess_definition_frequency()   # 1–5 band
classify_definition_register()  # formal/informal/neutral/slang/technical
assess_definition_domain()      # subject area
assess_grammar_patterns()       # transitivity, patterns
assess_collocations()           # common word pairings
usage_note_generation()         # usage guidance
assess_regional_variants()      # dialect variations
```

## Graceful Degradation

Definitions are **required**—if definition synthesis fails, the pipeline returns provider data as-is. Everything else degrades gracefully:

- Pronunciation failure → entry saved without pronunciation
- Etymology failure → entry saved without etymology
- Facts failure → entry saved without facts
- Any definition-level enhancement failure → that field left empty, others proceed

`asyncio.gather(return_exceptions=True)` ensures one failing task doesn't abort the others.

## Key Files

| File | Role |
|------|------|
| [`ai/synthesizer.py`](../backend/src/floridify/ai/synthesizer.py) | `DefinitionSynthesizer`—main orchestrator |
| [`ai/synthesis/orchestration.py`](../backend/src/floridify/ai/synthesis/orchestration.py) | Parallel enhancement, clustering, validation |
| [`ai/synthesis/word_level.py`](../backend/src/floridify/ai/synthesis/word_level.py) | Pronunciation, etymology, word forms, facts |
| [`ai/synthesis/definition_level.py`](../backend/src/floridify/ai/synthesis/definition_level.py) | 11 per-definition enhancement functions |
| [`ai/connector/`](../backend/src/floridify/ai/connector/) | `AIConnector`—async interface to OpenAI/Anthropic |
| [`ai/model_selection.py`](../backend/src/floridify/ai/model_selection.py) | 3-tier task→model routing |
| [`ai/constants.py`](../backend/src/floridify/ai/constants.py) | `SynthesisComponent` enum |
| [`ai/prompts/`](../backend/src/floridify/ai/prompts/) | Jinja2-rendered Markdown prompt templates |

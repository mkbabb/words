# ai/

OpenAI integration. AIConnector with mixin-based methods, synthesis pipeline, 3-tier model selection, batch processing.

```
ai/
├── connector/                  # AIConnector: async interface to OpenAI
│   ├── __init__.py
│   ├── base.py                 # AIConnector class (mixes in all method groups)
│   ├── config.py               # Provider enum, effort settings
│   ├── synthesis.py            # Synthesis-specific methods
│   ├── generation.py           # Content generation methods
│   ├── assessment.py           # Classification/assessment methods
│   └── suggestions.py          # Word suggestion methods
├── synthesis/                  # Synthesis pipeline functions
│   ├── __init__.py
│   ├── orchestration.py        # Parallel enhancement, clustering
│   ├── word_level.py           # Pronunciation, etymology, word forms, facts
│   └── definition_level.py     # 11 per-definition enhancement functions
├── synthesizer.py              # DefinitionSynthesizer: dedup→cluster→enhance
├── models.py                   # AI response/request Pydantic models
├── model_selection.py          # 3-tier routing: ModelComplexity → ModelTier
├── batch_processor.py          # OpenAI Batch API via context manager
├── prompt_manager.py           # Jinja2 template loading
├── constants.py                # SynthesisComponent enum (17 values), defaults
├── adaptive_counts.py          # Dynamic enhancement counts
├── tournament.py               # Tournament-style word ranking
└── prompts/                    # Markdown templates
    ├── assess/                 # cefr, collocations, domain, frequency, grammar_patterns, regional_variants, register
    ├── generate/               # examples, facts, word_forms
    ├── synthesize/             # antonyms, deduplicate, definitions, etymology, pronunciation, synonyms
    ├── misc/                   # anki_best_describes, anki_fill_blank, lookup, meaning_extraction, query_validation, rank_candidates, suggestions, usage_note_generation, word_suggestion
    ├── shared/                 # Shared prompt components
    └── wotd/                   # literature_analysis, synthetic_corpus, word_of_the_day
```

## SynthesisComponent Enum (17 values)

Word-level: `PRONUNCIATION`, `ETYMOLOGY`, `WORD_FORMS`, `FACTS`
Definition-level: `SYNONYMS`, `EXAMPLES`, `ANTONYMS`, `CEFR_LEVEL`, `FREQUENCY_BAND`, `REGISTER`, `DOMAIN`, `GRAMMAR_PATTERNS`, `COLLOCATIONS`, `USAGE_NOTES`, `REGIONAL_VARIANTS`
Utilities: `DEFINITION_TEXT`, `CLUSTER_DEFINITIONS`

## 3-Tier Model Selection

`model_selection.py` maps task names to `ModelComplexity` (HIGH/MEDIUM/LOW), then to `ModelTier`.

| Tier | Model | Example Tasks |
|------|-------|---------------|
| HIGH | gpt-5.4 | synthesize_definitions, suggest_words, extract_cluster_mapping, generate_synthetic_corpus, literature_analysis |
| MEDIUM | gpt-5-mini | generate_synonyms, generate_facts, generate_examples, synthesize_etymology, deduplicate_definitions, generate_collocations, generate_word_forms, generate_antonyms, generate_anki_*, generate_suggestions, lookup_word, literature_augmentation, text_generation |
| LOW | gpt-5-nano | assess_cefr_level, assess_frequency, classify_register, classify_domain, generate_pronunciation, generate_usage_notes, validate_query, identify_grammar_patterns, identify_regional_variants, rank_candidates |

Additional `ModelTier` values: `O3_MINI`, `GPT_4O`, `GPT_4O_MINI` (legacy). GPT-5 models use `max_completion_tokens` instead of `max_tokens` and use `"developer"` role instead of `"system"`. Temperature's only supported when `reasoning.effort=none`.

## Synthesis Pipeline

Provider data → `deduplicate_definitions()` → `cluster_definitions()` → parallel `asyncio.gather()`:
- `synthesize_definition_text()`, `synthesize_pronunciation()`, `synthesize_etymology()`, `generate_facts()`
- `enhance_definitions_parallel()` (sub-tasks: synonyms, examples, antonyms, CEFR, frequency, register, domain, grammar, collocations, usage notes, regional variants, definition text)

Dedup before cluster reduces token input.

## Batch Processing

`batch_synthesis(connector)` async context manager: patches `_make_structured_request()` to collect requests into `BatchCollector` → JSONL → OpenAI Batch API → poll for completion (max 1h timeout, configurable `check_interval`). `BatchExecutor` handles upload, polling, result download. Futures resolve when batch completes.

Classes: `AIBatchRequest`, `BatchCollector`, `BatchExecutor`, `BatchContext`.

## Structured Outputs

All API calls use Pydantic `response_format` for type-safe structured outputs. `AIResponseBase` is the common base class for AI responses.

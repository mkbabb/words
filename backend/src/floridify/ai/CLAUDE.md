# ai/

OpenAI integration. 30 async methods in connector, 25 synthesis functions, 3-tier model selection, batch processing.

```
ai/
├── connector.py (1,209)         # OpenAIConnector: 30 async + 3 sync methods
├── synthesis_functions.py (1,152) # 25 top-level async synthesis/generation functions
├── synthesizer.py (542)         # DefinitionSynthesizer: dedup->cluster->enhance
├── models.py (544)              # 54 Pydantic response/request models
├── model_selection.py (155)     # 3-tier routing: ModelComplexity -> ModelTier
├── batch_processor.py (362)     # OpenAI Batch API via context manager
├── prompt_manager.py (201)      # Jinja2 template loading
├── constants.py (122)           # SynthesisComponent enum (17 values), defaults
└── prompts/                     # 27 Markdown templates
    ├── assess/ (7)              # cefr, collocations, domain, frequency, grammar_patterns, regional_variants, register
    ├── generate/ (3)            # examples, facts, word_forms
    ├── synthesize/ (6)          # antonyms, deduplicate, definitions, etymology, pronunciation, synonyms
    ├── misc/ (8)                # anki_best_describes, anki_fill_blank, lookup, meaning_extraction, query_validation, suggestions, usage_note_generation, word_suggestion
    └── wotd/ (3)                # literature_analysis, synthetic_corpus, word_of_the_day
```

## SynthesisComponent Enum (17 values)

Word-level: `PRONUNCIATION`, `ETYMOLOGY`, `WORD_FORMS`, `FACTS`
Definition-level: `SYNONYMS`, `EXAMPLES`, `ANTONYMS`, `CEFR_LEVEL`, `FREQUENCY_BAND`, `REGISTER`, `DOMAIN`, `GRAMMAR_PATTERNS`, `COLLOCATIONS`, `USAGE_NOTES`, `REGIONAL_VARIANTS`
Utilities: `DEFINITION_TEXT`, `CLUSTER_DEFINITIONS`

## 3-Tier Model Selection

`model_selection.py` maps task names to `ModelComplexity` (HIGH/MEDIUM/LOW), then to `ModelTier`.

| Tier | Model | Example Tasks |
|------|-------|---------------|
| HIGH | gpt-5 | synthesize_definitions, suggest_words, extract_cluster_mapping, generate_synthetic_corpus, literature_analysis |
| MEDIUM | gpt-5-mini | generate_synonyms, generate_examples, synthesize_etymology, deduplicate_definitions, generate_antonyms, lookup_word, text_generation |
| LOW | gpt-5-nano | assess_cefr_level, assess_frequency, classify_register, classify_domain, generate_pronunciation, validate_query |

Additional `ModelTier` values: `O3_MINI`, `O1_MINI`, `GPT_4O`, `GPT_4O_MINI` (legacy). Reasoning models (o-series, gpt-5*) use `max_completion_tokens` instead of `max_tokens` and do not accept `temperature`.

## Synthesis Pipeline

Provider data -> `deduplicate_definitions()` -> `cluster_definitions()` -> parallel `asyncio.gather()`:
- `synthesize_definition_text()`, `synthesize_pronunciation()`, `synthesize_etymology()`, `generate_facts()`
- `enhance_definitions_parallel()` (sub-tasks: synonyms, examples, antonyms, CEFR, frequency, register, domain, grammar, collocations, usage notes, regional variants, definition text)

Dedup before cluster reduces token input.

## Batch Processing

`batch_synthesis(connector)` async context manager: patches `_make_structured_request()` to collect requests into `BatchCollector` -> JSONL -> OpenAI Batch API -> poll for completion (max 1h timeout, configurable `check_interval`). `BatchExecutor` handles upload, polling, result download. Futures resolve when batch completes.

Classes: `AIBatchRequest`, `BatchCollector`, `BatchExecutor`, `BatchContext`.

## Structured Outputs

All API calls use Pydantic `response_format` for type-safe structured outputs. 54 response/request models in `models.py`. `AIResponseBase` is the common base class for AI responses.

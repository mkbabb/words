# ai/

OpenAI integration. 32 async methods, 25+ synthesis functions, 3-tier model selection, batch processing.

```
ai/
├── connector.py (1,209)        # OpenAIConnector: 32 async methods
├── synthesis_functions.py (1,152) # 25+ synthesis functions
├── synthesizer.py (542)        # DefinitionSynthesizer: dedup→cluster→enhance
├── models.py (544)             # 40+ Pydantic response models
├── model_selection.py (155)    # 3-tier routing (87% cost savings)
├── batch_processor.py (348)    # OpenAI Batch API (50% discount)
├── prompt_manager.py (201)     # Jinja2 templates
├── constants.py (122)          # 27 SynthesisComponent enum values
└── prompts/                    # 27 Markdown templates
    ├── assess/                 # CEFR, domain, register, frequency, etc.
    ├── generate/               # Examples, facts, word_forms
    ├── synthesize/             # Definitions, synonyms, etymology
    └── misc/, wotd/
```

## 3-Tier Model Selection

| Tier | Model | Tasks | Cost |
|------|-------|-------|------|
| HIGH | gpt-5 | synthesize_definitions, clustering, suggestions | $$$ |
| MEDIUM | gpt-5-mini | synonyms, examples, dedup, etymology | $$ |
| LOW | gpt-5-nano | CEFR, frequency, register, domain | $ |

Result: $0.02/word vs $0.15 naive (87% savings).

## Synthesis Pipeline

Provider data (47 defs) → `deduplicate_definitions()` (23 defs, 50%) → `cluster_definitions()` (3-4 groups) → parallel `asyncio.gather()`:
- `synthesize_definition_text()`, `synthesize_pronunciation()`, `synthesize_etymology()`, `generate_facts()`
→ `enhance_definitions_parallel()` (12 sub-tasks: synonyms, examples, antonyms, CEFR, frequency, register, domain, grammar, collocations, usage notes, regional variants, definition text)

Key: dedup *before* cluster saves ~50% tokens.

## Batch Processing

`batch_synthesis()` context manager: patches `_make_structured_request()` to collect requests → JSONL → OpenAI Batch API → 50% discount. Poll for completion (5-10 min typical).

## Structured Outputs

All API calls use Pydantic `response_format` for type-safe structured outputs. 40+ response models. Reasoning models use `max_completion_tokens` instead of `max_tokens`.

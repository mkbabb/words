# AI Module - OpenAI Integration & Synthesis

AI-powered definition synthesis with 40+ generation endpoints, 3-tier model selection, batch processing.

## Structure

```
ai/
├── connector.py             # OpenAI async client wrapper (1,161 LOC)
├── synthesis_functions.py   # 25+ synthesis functions (1,148 LOC)
├── synthesizer.py           # DefinitionSynthesizer orchestrator (432 LOC)
├── batch_processor.py       # OpenAI Batch API integration (335 LOC)
├── models.py                # 40+ Pydantic response models (545 LOC)
├── model_selection.py       # 3-tier complexity routing (156 LOC)
├── prompt_manager.py        # Jinja2 template system (135 LOC)
├── constants.py             # Enums, defaults (123 LOC)
└── prompts/                 # 27 Markdown templates (737 LOC)
    ├── assess/              # 7 assessment prompts (CEFR, domain, register, etc.)
    ├── generate/            # 3 generation prompts (examples, facts, word_forms)
    ├── synthesize/          # 6 synthesis prompts (definitions, synonyms, etymology)
    ├── misc/                # 8 utility prompts (Anki, suggestions, validation)
    └── wotd/                # 3 WOTD prompts (corpus analysis, generation)
```

**Total**: 4,837 LOC (4,100 Python + 737 prompts)

## Core Components

**OpenAIConnector** (`connector.py:1,161` - 32 async methods)

Main API wrapper with structured outputs:

```python
class OpenAIConnector:
    client: AsyncOpenAI
    prompt_manager: PromptManager
    _last_model_info: ModelInfo | None

    async def _make_structured_request(
        response_model: type[BaseModel],
        task_name: str,
        prompt: str,
        **kwargs,
    ) -> BaseModel:
        # 1. Auto model selection: task_name → complexity → model tier
        model = get_model_for_task(task_name)

        # 2. Temperature routing (reasoning models: None, creative: 0.8, etc.)
        temperature = get_temperature_for_task(task_name, model)

        # 3. Token parameter handling (reasoning models use max_completion_tokens)
        if model.is_reasoning_model:
            kwargs["max_completion_tokens"] = max(4000, max_tokens * 15)

        # 4. Cached API call (24h TTL via @cached_api_call decorator)
        response = await self.client.chat.completions.create(
            model=model.value,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_model,  # Structured output
            temperature=temperature,
            **kwargs,
        )

        # 5. Token tracking & provenance
        self._last_model_info = ModelInfo(
            name=model.value,
            total_tokens=response.usage.total_tokens,
            response_time_ms=...,
        )

        return response.parsed  # Returns Pydantic model instance
```

**32 AI endpoints**:
- **Synthesis** (6): definitions, synonyms, antonyms, etymology, pronunciation, deduplication
- **Generation** (4): examples, facts, word_forms, usage_notes
- **Assessment** (7): CEFR level, frequency, register, domain, grammar patterns, collocations, regional variants
- **Anki** (2): fill-blank, multiple-choice flashcards
- **Discovery** (3): suggest_words, suggestions, validate_query
- **WOTD** (3): generate, synthetic_corpus, literature_analysis
- **Misc** (7): lookup_fallback, augment_literature, text_generation, etc.

## 3-Tier Model Selection

**Model Routing** (`model_selection.py:156`):

```python
class ModelTier(Enum):
    GPT_5 = "gpt-5"              # HIGH complexity (gpt-5)
    GPT_5_MINI = "gpt-5-mini"    # MEDIUM complexity
    GPT_5_NANO = "gpt-5-nano"    # LOW complexity

def get_model_for_task(task_name: str) -> ModelTier:
    """Route task to model tier based on TASK_COMPLEXITY_MAP"""
    complexity = TASK_COMPLEXITY_MAP.get(task_name, ModelComplexity.MEDIUM)
    return {
        ModelComplexity.HIGH: ModelTier.GPT_5,
        ModelComplexity.MEDIUM: ModelTier.GPT_5_MINI,
        ModelComplexity.LOW: ModelTier.GPT_5_NANO,
    }[complexity]
```

**Task Complexity Map** (83 tasks):
- **HIGH** (5 tasks): synthesize_definitions, extract_cluster_mapping, suggest_words, synthetic_corpus, literature_analysis
- **MEDIUM** (14 tasks): generate_synonyms, generate_examples, generate_facts, deduplicate_definitions, etc.
- **LOW** (9 tasks): assess_frequency, assess_cefr_level, classify_register, classify_domain, etc.

**Cost Optimization**:
```
Naive approach: All GPT-4o → $0.15 per word
3-tier approach: Mix Nano/Mini/Full → $0.02 per word
Savings: 87% (13.3x cheaper)
```

## Synthesis Pipeline

**DefinitionSynthesizer** (`synthesizer.py:432`):

```python
async def synthesize_entry(
    word: Word,
    providers_data: list[DictionaryEntry],
    components: set[SynthesisComponent] | None = None,
) -> DictionaryEntry:
    # 1. Extract definitions from all providers (say, 47 total)
    all_definitions = extract_all_definitions(providers_data)

    # 2. Deduplicate (47 → 23 definitions)
    dedup_response = await ai.deduplicate_definitions(word.text, all_definitions)

    # 3. Cluster by meaning + POS (23 → 3-4 semantic clusters)
    clustered_defs = await cluster_definitions(word, dedup_response.definitions)

    # 4. Synthesize definition text per cluster
    for cluster in clusters:
        synthesized_text = await ai.synthesize_definitions(word, cluster)

    # 5. Parallel enhancement (asyncio.gather)
    await asyncio.gather(
        synthesize_pronunciation(word),
        synthesize_etymology(word, providers_data),
        generate_facts(word, count=3),
        enhance_definitions_parallel(definitions, word),  # 12 sub-enhancements
    )

    return DictionaryEntry(...)
```

**Key insight**: Deduplication *before* clustering saves ~50% tokens

## Synthesis Functions

**25+ async functions** (`synthesis_functions.py:1,148`):

**Word-level** (4 functions):
- `synthesize_pronunciation:49-108` - Find existing or generate new (IPA, phonetic, audio)
- `synthesize_etymology:167-215` - Extract from provider data or generate
- `synthesize_word_forms:218-242` - Identify inflections per POS
- `generate_facts:476-531` - Generate 3-8 educational facts

**Definition-level** (12 functions):
- `synthesize_synonyms:533-582` - Generate/enhance to target count (default: 10)
- `synthesize_antonyms:245-291` - Generate/enhance to target count (default: 5)
- `generate_examples:585-617` - Contextual example sentences (default: 3)
- `assess_definition_cefr:294-311` - A1-C2 proficiency level
- `assess_definition_frequency:314-331` - 1-5 frequency band
- `classify_definition_register:334-350` - formal/informal/technical/slang
- `assess_definition_domain:353-370` - medical/legal/computing/academic
- `assess_grammar_patterns:372-398` - Grammar construction patterns
- `assess_collocations:400-428` - Common word combinations
- `usage_note_generation:431-454` - Usage guidance and restrictions
- `assess_regional_variants:457-474` - US/UK/AU detection
- `synthesize_definition_text:620-675` - Clean definition from clustered meanings

**Meta-functions** (3):
- `cluster_definitions:678-796` - Semantic clustering + POS grouping
- `enhance_definitions_parallel:799-1012` - Orchestrates 12 enhancements with optional batch mode
- `enhance_synthesized_entry:1015-1132` - Post-synthesis enhancement variant

**Query & validation** (2):
- `validate_query:1134-1140` - Determines if query seeks suggestions
- `suggest_words:1142-1148` - Generate word suggestions from descriptive query

## Batch Processing

**OpenAI Batch API** (`batch_processor.py:335` - 50% cost savings):

```python
async with batch_synthesis(ai_connector) as batch:
    # All OpenAI calls collected instead of executed
    await enhance_definitions_parallel(definitions, word, ai_connector)
    # On context exit, batch automatically executes

# BatchContext lifecycle:
# 1. __aenter__: Patch _make_structured_request() to collect requests
# 2. During with block: Collect all API calls into BatchCollector
# 3. __aexit__: Execute batch, restore original method
```

**Batch workflow**:
1. Collect requests → JSONL file
2. Upload to OpenAI Batch API
3. Poll for completion (5-10 minutes typical)
4. Download results → parse JSONL
5. Resolve futures for awaiting code

**Cost example**:
- Standard mode: 1200 API calls × $0.50 = $600
- Batch mode: 1200 API calls × $0.25 = $300 (50% discount)

## Prompt Engineering

**27 Markdown templates** (`prompts/` - 737 LOC):

**Template system** (`prompt_manager.py:135`):
```python
class PromptManager:
    def render(template_name: str, **variables) -> str:
        """Jinja2 rendering with flexible path handling"""
        # Supports: "synonyms", "synthesize/synonyms", "synonyms.md"
```

**Example prompt** (`prompts/synthesize/synonyms.md`):
```markdown
Generate {{count}} synonyms for "{{word}}" ({{part_of_speech}}).

Distribution: 40% common, 30% expressive, 20% formal, 10% technical.

Definition: {{definition}}

Return format:
- word: synonym text
- language: "en"
- relevance: 0.0-1.0
- efflorescence: 0.0-1.0 (expressiveness)
- explanation: brief context
```

**Prompt characteristics**:
- Ultra-lean token usage (30-50 tokens for simple tasks)
- 2-3 worked examples per prompt
- Specific output formats (JSON schema via Pydantic)
- Aggressive merging instructions for clustering

## Response Models

**40+ Pydantic models** (`models.py:545`):

**Definition & synthesis**:
- `SynthesisResponse` - Multi-definition synthesis with sources_used
- `DeduplicationResponse` - Deduplicated definitions with reasoning
- `ClusterMappingResponse` - Semantic cluster mapping with descriptions

**Generation**:
- `SynonymGenerationResponse` - List[SynonymCandidate] with efflorescence scores
- `ExampleGenerationResponse` - List[str] example sentences
- `FactGenerationResponse` - List[str] with categories metadata
- `EtymologyResponse` - Origin, root words, first known use

**Assessment**:
- `CEFRLevelResponse` - A1-C2 with reasoning
- `FrequencyBandResponse` - 1-5 with reasoning
- `RegisterClassificationResponse` - formal/informal/technical with alias support

**Special purpose**:
- `WordSuggestionResponse` - Query-based suggestions with confidence/efflorescence
- `AnkiFillBlankResponse` - Flashcard: sentence with _____, 4 choices
- `WordOfTheDayResponse` - Complete WOTD with etymology, example, fact

## Data Flow Example

```
lookup_word_pipeline("perspicacious")
  ↓
[Get from providers: Wiktionary, Oxford, Apple] (47 definitions)
  ↓
synthesizer.synthesize_entry()
  ├→ ai.deduplicate_definitions()         [gpt-5-mini]  (47→23 definitions)
  ├→ cluster_definitions()
  │  └→ ai.extract_cluster_mapping()      [gpt-5]       (23→3 clusters)
  ├→ Parallel synthesis (asyncio.gather):
  │  ├→ synthesize_pronunciation()        [gpt-5-nano]
  │  ├→ synthesize_etymology()            [gpt-5-mini]
  │  ├→ generate_facts(3)                 [gpt-5-mini]
  │  └→ synthesize_definition_text()      [gpt-5]
  ├→ enhance_definitions_parallel()
  │  ├→ synthesize_synonyms(10)           [gpt-5-mini]
  │  ├→ generate_examples(3)              [gpt-5-mini]
  │  ├→ synthesize_antonyms(5)            [gpt-5-mini]
  │  ├→ assess_cefr_level()               [gpt-5-nano]
  │  ├→ assess_frequency_band()           [gpt-5-nano]
  │  ├→ classify_register()               [gpt-5-nano]
  │  ├→ assess_domain()                   [gpt-5-nano]
  │  ├→ assess_grammar_patterns()         [gpt-5-nano]
  │  ├→ assess_collocations()             [gpt-5-mini]
  │  ├→ usage_note_generation()           [gpt-5-nano]
  │  └→ assess_regional_variants()        [gpt-5-nano]
  └→ MongoDB save via VersionedDataManager
     ↓
  Complete DictionaryEntry with 3 synthesized definitions, all enhancements
```

**Total API calls**: ~30-40 (parallel + batched)
**Cost**: ~$0.02 vs ~$0.15 naive (87% savings)
**Time**: ~3-5 seconds (parallel execution)

## Performance

| Operation | Time | Model Tier | Tokens |
|-----------|------|-----------|--------|
| Deduplication | 500-1000ms | MEDIUM | 500-2000 |
| Clustering | 800-1500ms | HIGH | 800-3000 |
| Synonym generation | 300-600ms | MEDIUM | 200-500 |
| CEFR assessment | 100-300ms | LOW | 50-150 |
| Full synthesis | 3-5s | Mixed | 5000-15000 |
| Batch processing | 5-10min | All | Variable |

## Design Patterns

- **Singleton** - `get_openai_connector()` maintains global connector instance
- **Context Manager** - `batch_synthesis()` for batch API collection/execution
- **Factory** - PromptManager creates/renders templates on-demand
- **Decorator** - `@cached_api_call` wraps API calls with caching
- **Type Union** - Flexible input: `list[dict] | list[DictionaryEntry]`
- **Parallel Execution** - `asyncio.gather()` for concurrent synthesis tasks
- **Token Routing** - Different `max_tokens` strategies per model tier

## Configuration

**27 synthesis components** (`constants.py:123`):

**Word-level** (4): PRONUNCIATION, ETYMOLOGY, WORD_FORMS, FACTS
**Definition-level** (11): SYNONYMS, EXAMPLES, ANTONYMS, CEFR_LEVEL, FREQUENCY_BAND, REGISTER, DOMAIN, GRAMMAR_PATTERNS, COLLOCATIONS, USAGE_NOTES, REGIONAL_VARIANTS
**Synthesis utilities** (2): DEFINITION_TEXT, CLUSTER_DEFINITIONS

**Default counts**:
- Synonyms: 10
- Antonyms: 5
- Facts: 3
- Examples: 3
- Suggestions: 10
- Usage notes: 3

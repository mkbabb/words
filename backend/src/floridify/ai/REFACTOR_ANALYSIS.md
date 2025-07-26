# AI Function Refactor Analysis

## Function Classification

### SYNTHESIZE Functions (Enhance/Merge Existing Content)
These functions work with existing data from providers, enhancing or synthesizing it:

1. **synthesize_pronunciation** - Enhances existing pronunciation or generates if missing
   - Connector: `pronunciation()` → `PronunciationResponse`
   - Prompt: `pronunciation.md`
   - Parameters: `(word: Word, providers_data, ai, state_tracker)`
   
2. **synthesize_synonyms** - Currently generates but should be renamed for clarity
   - Connector: `generate_synonyms()` → `SynonymGenerationResponse`
   - Prompt: `generate_synonyms.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

3. **synthesize_etymology** - Extracts/synthesizes from provider etymology data
   - Connector: `extract_etymology()` → `EtymologyResponse`
   - Prompt: `etymology_extraction.md`
   - Parameters: `(word: Word, providers_data, ai, state_tracker)`

4. **synthesize_definition_text** - Synthesizes from clustered definitions
   - Connector: `synthesize_definitions()` → `SynthesisResponse`
   - Prompt: `synthesis.md`
   - Parameters: `(clustered_definitions, word: str, ai, state_tracker)`

5. **cluster_definitions** - Groups definitions by meaning
   - Connector: `extract_cluster_mapping()` → `ClusterMappingResponse`
   - Prompt: `meaning_extraction.md`  
   - Parameters: `(word: Word, definitions, ai, state_tracker)`

### GENERATE Functions (Create New Content)
These functions generate entirely new content:

1. **generate_facts** - Creates new facts about a word
   - Connector: `generate_facts()` → `FactGenerationResponse`
   - Prompt: `fact_generation.md`
   - Parameters: `(word: Word, definitions, ai, count=3, state_tracker)`

2. **synthesize_examples** - Should be **generate_examples**
   - Connector: `generate_examples()` → `ExampleGenerationResponse`  
   - Prompt: `generate_examples.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

3. **synthesize_antonyms** - Should be **generate_antonyms** 
   - Connector: `generate_antonyms()` → `AntonymResponse`
   - Prompt: `generate_antonyms.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)` - MISSING count parameter

4. **synthesize_word_forms** - Should be **generate_word_forms**
   - Connector: `identify_word_forms()` → `WordFormResponse`
   - Prompt: `word_form_generation.md`
   - Parameters: `(word: Word, part_of_speech: str, ai, state_tracker)`

5. **generate_usage_notes** - Already correctly named
   - Connector: `generate_usage_notes()` → `UsageNoteResponse`
   - Prompt: `usage_note_generation.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

### ASSESS Functions (Analyze/Classify Existing Content)
These functions analyze and classify content:

1. **assess_definition_cefr** - Assesses CEFR level
   - Connector: `assess_cefr_level()` → `CEFRLevelResponse`
   - Prompt: `cefr_assessment.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

2. **assess_definition_frequency** - Assesses frequency band
   - Connector: `assess_frequency_band()` → `FrequencyBandResponse`
   - Prompt: `frequency_assessment.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

3. **classify_definition_register** - Classifies register
   - Connector: `classify_register()` → `RegisterClassificationResponse`
   - Prompt: `register_classification.md`
   - Parameters: `(definition: Definition, ai, state_tracker)`

4. **identify_definition_domain** - Identifies domain
   - Connector: `identify_domain()` → `DomainIdentificationResponse`
   - Prompt: `domain_identification.md`
   - Parameters: `(definition: Definition, ai, state_tracker)`

5. **extract_grammar_patterns** - Extracts patterns
   - Connector: `extract_grammar_patterns()` → `GrammarPatternResponse`
   - Prompt: `grammar_pattern_extraction.md`
   - Parameters: `(definition: Definition, ai, state_tracker)`

6. **identify_collocations** - Identifies collocations
   - Connector: `identify_collocations()` → `CollocationResponse`
   - Prompt: `collocation_identification.md`
   - Parameters: `(definition: Definition, word: str, ai, state_tracker)`

7. **detect_regional_variants** - Detects variants
   - Connector: `detect_regional_variants()` → `RegionalVariantResponse`
   - Prompt: `regional_variant_detection.md`
   - Parameters: `(definition: Definition, ai, state_tracker)`

## Required Changes

### Function Renaming
- `synthesize_examples` → `generate_examples`
- `synthesize_antonyms` → `generate_antonyms`  
- `synthesize_word_forms` → `generate_word_forms`

### Parameter Standardization
Standard order: `word: str, definition: Definition, ai: OpenAIConnector, count: int = DEFAULT, state_tracker: StateTracker | None = None`

### Missing Parameters
- `generate_antonyms` needs `count` parameter like `generate_synonyms`

### Constants File Creation
Create `constants.py` with:
- DEFAULT_SYNONYM_COUNT = 10
- DEFAULT_ANTONYM_COUNT = 5  
- DEFAULT_FACT_COUNT = 3
- DEFAULT_EXAMPLE_COUNT = 3

### Prompt Reorganization
```
prompts/
├── synthesize/
│   ├── pronunciation.md
│   ├── synonyms.md (rename from generate_synonyms.md) 
│   ├── etymology.md (rename from etymology_extraction.md)
│   └── definitions.md (rename from synthesis.md)
├── generate/
│   ├── facts.md (rename from fact_generation.md)
│   ├── examples.md (rename from generate_examples.md)
│   ├── antonyms.md (rename from generate_antonyms.md)
│   └── word_forms.md (rename from word_form_generation.md)
├── assess/
│   ├── cefr.md (rename from cefr_assessment.md)
│   ├── frequency.md (rename from frequency_assessment.md)
│   ├── register.md (rename from register_classification.md)
│   ├── domain.md (rename from domain_identification.md)
│   ├── grammar_patterns.md (rename from grammar_pattern_extraction.md)
│   ├── collocations.md (rename from collocation_identification.md)
│   └── regional_variants.md (rename from regional_variant_detection.md)
└── misc/
    ├── lookup.md
    ├── meaning_extraction.md
    ├── suggestions.md
    ├── anki_best_describes.md
    ├── anki_fill_blank.md
    └── usage_note_generation.md
```

### Usage Updates Required
Files needing updates:
- `synthesis_functions.py` - Function definitions and registry
- `api/routers/definitions.py` - Function imports and registry
- `ai/synthesizer.py` - Function imports
- `ai/connector.py` - Connector method names
- `ai/templates.py` - Template method names
- All prompt files - Renamed and moved
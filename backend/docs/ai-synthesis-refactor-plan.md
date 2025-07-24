# AI Synthesis Pipeline Refactor Plan

## Overview
Complete refactor of AI synthesis to support all new model fields with parallel execution.

## Phase 1: New AI Response Models

### 1.1 Create Enhanced Response Models
```python
# ai/models.py additions:
- AntonymResponse
- EtymologyResponse  
- WordFormResponse
- EnhancedDefinitionResponse (includes all new fields)
- ComprehensiveSynthesisResponse
```

## Phase 2: New Prompt Templates

### 2.1 Create New Templates
```markdown
# prompts/ directory:
- antonym_generation.md
- etymology_extraction.md
- word_form_generation.md
- register_classification.md
- domain_identification.md
- regional_variant_detection.md
- frequency_assessment.md
```

### 2.2 Template Design Principles
- Structured output format
- Clear examples
- Constraint specifications
- Follow existing prompt style

## Phase 3: OpenAI Connector Enhancement

### 3.1 New Methods
```python
async def generate_antonyms(word, definition, word_type) -> AntonymResponse
async def extract_etymology(word, provider_data) -> EtymologyResponse
async def identify_word_forms(word) -> WordFormResponse
async def assess_frequency_band(word, definition) -> int
async def classify_register(definition) -> str
async def identify_domain(definition) -> str | None
```

### 3.2 Batch Processing
```python
async def batch_enhance_definitions(
    definitions: list[Definition],
    word: str,
    components: set[str]
) -> dict[str, list[Any]]
```

## Phase 4: Synthesis Pipeline Redesign

### 4.1 Core Synthesis Functions
```python
# Atomic synthesis functions:
async def synthesize_pronunciation(word, providers) -> Pronunciation
async def synthesize_etymology(word, providers) -> Etymology | None
async def synthesize_word_forms(word) -> list[WordForm]
async def synthesize_definitions(word, cluster_definitions) -> list[Definition]
async def synthesize_facts(word, definitions) -> list[Fact]
```

### 4.2 Parallel Enhancement Pipeline
```python
async def enhance_synthesized_entry(
    entry: SynthesizedDictionaryEntry,
    components: set[str] | None = None,
    force: bool = False
) -> None:
    """Enhance entry with parallel component synthesis."""
    
    tasks = []
    
    # Word-level enhancements
    if not entry.etymology or force:
        tasks.append(synthesize_etymology(...))
    
    # Definition-level enhancements (parallel per definition)
    for definition in entry.definitions:
        if not definition.antonyms or force:
            tasks.append(generate_antonyms(...))
        if definition.cefr_level is None or force:
            tasks.append(assess_cefr_level(...))
        # ... etc
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4.3 Component Registry
```python
SYNTHESIS_COMPONENTS = {
    # Word-level
    "etymology": synthesize_etymology,
    "word_forms": synthesize_word_forms,
    "pronunciation": synthesize_pronunciation,
    
    # Definition-level  
    "examples": synthesize_examples,
    "synonyms": synthesize_synonyms,
    "antonyms": synthesize_antonyms,
    "cefr_level": assess_cefr_level,
    "grammar_patterns": extract_grammar_patterns,
    "collocations": identify_collocations,
    "usage_notes": generate_usage_notes,
    "register": classify_register,
    "domain": identify_domain,
    "frequency_band": assess_frequency_band,
}
```

## Phase 5: Provenance Tracking

### 5.1 Track Data Sources
```python
class ProvenanceTracker:
    def track_provider_contribution(provider, field, value)
    def track_ai_generation(model, component, confidence)
    def get_provenance_report() -> dict
```

## Phase 6: Integration

### 6.1 Update synthesize_entry Method
- Use new parallel pipeline
- Track all provider contributions
- Store complete provenance
- Support partial regeneration

### 6.2 API Integration
- Update regeneration endpoints
- Add component selection
- Return synthesis metadata

## Testing Strategy

1. Unit tests for each synthesis function
2. Integration tests with mock AI responses
3. Performance benchmarks
4. Quality assessment of generated content
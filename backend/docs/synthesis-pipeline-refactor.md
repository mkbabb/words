# Synthesis Pipeline Refactor Plan

## Current State

The synthesis pipeline processes dictionary entries sequentially:
1. Fetch from providers
2. Cluster definitions by meaning
3. Synthesize each cluster
4. Generate examples per definition
5. Enhance synonyms if needed

## Target State

Functional, parallel pipeline that:
- Executes all AI operations concurrently where possible
- Reuses existing attributes (only synthesize if None)
- Allows individual component regeneration
- Uses existing enums and models
- Minimizes object creation

## Implementation

### Core Functions

```python
# Synthesis functions that operate on Definition objects
async def synthesize_examples(definition: Definition, word: str, ai: OpenAIConnector) -> None
async def synthesize_synonyms(definition: Definition, word: str, ai: OpenAIConnector) -> None
async def assess_cefr_level(definition: Definition, word: str, ai: OpenAIConnector) -> None
async def extract_grammar_patterns(definition: Definition, word: str, ai: OpenAIConnector) -> None
async def identify_collocations(definition: Definition, word: str, ai: OpenAIConnector) -> None
async def generate_usage_notes(definition: Definition, word: str, ai: OpenAIConnector) -> None
```

### Parallel Execution

```python
async def enhance_definitions(
    definitions: list[Definition],
    word: str,
    ai: OpenAIConnector,
    components: set[str] | None = None,
    force: bool = False
) -> None:
    """Execute all enhancement tasks in parallel."""
    tasks = []
    
    for definition in definitions:
        # Check what needs synthesis
        if not force:
            if components is None or "examples" in components:
                if not definition.examples.generated:
                    tasks.append(synthesize_examples(definition, word, ai))
            # ... similar for other components
        else:
            # Force regeneration of requested components
            for component in (components or ALL_COMPONENTS):
                func = COMPONENT_FUNCTIONS[component]
                tasks.append(func(definition, word, ai))
    
    await asyncio.gather(*tasks, return_exceptions=True)
```

### Component Registry

```python
COMPONENT_FUNCTIONS = {
    "examples": synthesize_examples,
    "synonyms": synthesize_synonyms,
    "cefr_level": assess_cefr_level,
    "grammar_patterns": extract_grammar_patterns,
    "collocations": identify_collocations,
    "usage_notes": generate_usage_notes,
}

ALL_COMPONENTS = set(COMPONENT_FUNCTIONS.keys())
```

### Integration Points

1. **synthesizer.py**: Replace sequential processing with `enhance_definitions()`
2. **definitions.py router**: Call specific synthesis functions for regeneration
3. **connector.py**: Add missing AI methods (collocations, grammar patterns)
4. **models.py**: Use existing Definition model fields

### Connector Updates

The OpenAIConnector needs methods for new components:
- `extract_collocations()` 
- `extract_grammar_patterns()`
- `assess_cefr_level()`
- `generate_usage_notes()`

These follow the existing pattern of template-based prompts with structured responses.

### Template Updates

Create prompt templates for new operations:
- `cefr_assessment.md`
- `grammar_extraction.md`
- `collocation_identification.md`
- `usage_note_generation.md`
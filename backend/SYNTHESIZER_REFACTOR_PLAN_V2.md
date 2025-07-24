# Synthesizer Refactoring Plan V2

## Overview
Comprehensive refactoring to use prompt templates, eliminate duplication, and create a unified parallel synthesis pipeline.

## Phase 1: Create Prompt Templates
### New Templates Needed (`backend/src/floridify/ai/prompts/`)
1. **`synonym_generation.md`** - Generate synonyms with efflorescence ranking
2. **`example_synthesis.md`** - Create contextual example sentences  
3. **`definition_synthesis.md`** - Synthesize definition text from clusters
4. **`meaning_cluster_generation.md`** - Generate cluster for single definition

### Template Style Guidelines
- Use Jinja2 templating with `{{ variable }}` syntax
- Include clear sections: Input, Task, Requirements, Output Format
- Follow existing prompt patterns (pithy, exacting, academic tone)
- Include specific examples where helpful
- Use markdown formatting for structure

## Phase 2: Update AI Connector
### Add Template Methods
1. **`get_synonym_generation_prompt()`** - Load synonym generation template
2. **`get_example_synthesis_prompt()`** - Load example synthesis template
3. **`get_definition_synthesis_prompt()`** - Load definition synthesis template
4. **`get_meaning_cluster_prompt()`** - Load meaning cluster template

### Remove `generate()` Method
- Not needed - use existing structured request pattern
- All synthesis should use typed methods with templates

## Phase 3: Refactor Synthesis Functions
### Update All Functions
1. **Remove inline prompts** - Replace with template manager calls
2. **Add AI connector methods** - For each new synthesis function
3. **Use structured responses** - Leverage existing response models
4. **Remove AI None checks** - AI connector is always required

### Function Updates
- `synthesize_synonyms()` → Use `ai.generate_synonyms()` 
- `synthesize_examples()` → Use `ai.synthesize_examples()`
- `synthesize_definition_text()` → Use `ai.synthesize_definition()`
- `generate_meaning_cluster()` → Use `ai.generate_meaning_cluster()`

## Phase 4: Consolidate Parallel Enhancement
### Unified Enhancement Pipeline
1. **Remove `_parallel_enhance_definitions()`** from synthesizer.py
2. **Enhance `enhance_synthesized_entry()`** to be the single enhancement function
3. **Add state_tracker support** throughout enhancement pipeline
4. **Support arbitrary attribute updates** via component selection

### Enhancement Strategy
```python
async def enhance_synthesized_entry(
    entry: SynthesizedDictionaryEntry,
    components: set[str] | None = None,  # None = all, or specific set
    force: bool = False,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> None:
    # Single function for all parallel enhancements
    # Supports selective component enhancement
    # Handles both word-level and definition-level
```

## Phase 5: Data Model Integration
### Key Principles
1. **Respect existing models** - Work within current structure
2. **Incremental updates** - Support updating any subset of attributes
3. **Preserve relationships** - Maintain ID references and associations
4. **Batch operations** - Optimize saves where possible

### Component Registry Enhancement
```python
SYNTHESIS_COMPONENTS = {
    # Word-level (applied once per word)
    "pronunciation": (synthesize_pronunciation, "word"),
    "etymology": (synthesize_etymology, "word"), 
    "word_forms": (synthesize_word_forms, "word"),
    "facts": (synthesize_facts, "word"),
    
    # Definition-level (applied per definition)
    "synonyms": (synthesize_synonyms, "definition"),
    "examples": (synthesize_examples, "definition"),
    "antonyms": (enhance_definition_antonyms, "definition"),
    # ... etc
}
```

## Phase 6: Implementation Order
1. **Create prompt templates** - Write all new .md files
2. **Update connector** - Add template methods, remove generate()
3. **Refactor synthesis functions** - Use templates via connector
4. **Consolidate enhancement** - Single parallel pipeline
5. **Update synthesizer.py** - Use new consolidated approach
6. **Test thoroughly** - Ensure mypy/ruff compliance

## Key Benefits
- **Clean separation** - Prompts in templates, logic in code
- **No duplication** - Single enhancement pipeline
- **Flexible updates** - Can enhance any subset of attributes
- **Maintainable** - Easy to modify prompts without code changes
- **Type safe** - Structured responses throughout
- **Performant** - Efficient parallel processing with proper limits

## Success Criteria
1. All prompts in template files (no inline strings)
2. Single enhancement function for all parallel work
3. Support for selective attribute updates
4. Clean mypy/ruff output
5. Maintained functionality with improved architecture
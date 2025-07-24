# Synthesizer Deduplication Plan

## Objective
Remove duplicate functionality between synthesizer.py and synthesis_functions.py, leveraging abstracted functions and following KISS/DRY principles.

## Current Issues
1. Duplicate methods exist in both files (_synthesize_pronunciation, etc.)
2. generate_fallback_entry doesn't use abstracted functions
3. _synthesize_definitions has duplicate logic
4. synthesize_entry doesn't leverage modular functions
5. Meaning clustering for single definitions should be removed

## Plan

### Phase 1: Research & Analysis
1. Analyze current synthesizer.py implementation
2. Map duplicate methods to synthesis_functions.py equivalents
3. Understand _cluster_definitions implementation
4. Identify all touch points that need refactoring

### Phase 2: Move Core Logic
1. Move _cluster_definitions from synthesizer.py to synthesis_functions.py
2. Add state_tracker support to moved function
3. Remove single definition clustering concept

### Phase 3: Remove Duplicates
1. Remove _synthesize_pronunciation (use synthesize_pronunciation)
2. Remove _synthesize_etymology (use synthesize_etymology)
3. Remove _synthesize_word_forms (use synthesize_word_forms)
4. Remove _synthesize_facts (use synthesize_facts)
5. Remove any other duplicate methods

### Phase 4: Refactor Core Methods
1. **generate_fallback_entry**: Use generate_meaning_cluster, synthesize_definition_text
2. **_synthesize_definitions**: Use enhance_definitions_parallel
3. **synthesize_entry**: Orchestrate using modular functions

### Phase 5: Testing
1. Run mypy for type checking
2. Run ruff for linting
3. Ensure all functionality is preserved

## Key Principles
- KISS: Keep implementations simple and direct
- DRY: No duplicate code between files
- Modular: Small, focused functions
- Type-safe: Proper typing throughout
- State tracking: Consistent state_tracker usage
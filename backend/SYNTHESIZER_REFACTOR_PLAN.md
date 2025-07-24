# Synthesizer Refactoring Plan

## Overview
Comprehensive refactoring of the AI synthesis pipeline to achieve modularity, consistency, and complete state tracking integration.

## Phase 1: Model Reorganization
### AI Models (`backend/src/floridify/ai/models.py`)
1. **Remove** `synonyms` field from `DefinitionResponse`
2. **Create** new response models:
   - `ExampleSynthesisResponse` - For example generation
   - `SynonymSynthesisResponse` - For synonym generation (already exists)
   - `DefinitionSynthesisResponse` - For definition text synthesis
   - `MeaningClusterResponse` - For single-definition clustering
3. **Move** Anki models to bottom of file
4. **Ensure** all response models contain necessary fields for complete synthesis

## Phase 2: Synthesis Functions (`backend/src/floridify/ai/synthesis_functions.py`)
### Create Missing Functions:
1. **`synthesize_synonyms`** - Generate synonyms for definitions
   - Input: Definition, word, AI connector, state_tracker
   - Output: List of synonyms with efflorescence ranking
   - Prompt: Pithy, focused on semantic relevance

2. **`synthesize_examples`** - Generate example sentences
   - Input: Definition, word, AI connector, state_tracker
   - Output: List of Example objects
   - Prompt: Natural, contextual examples

3. **`synthesize_definition_text`** - Synthesize definition text from clusters
   - Input: Clustered definitions, word, AI connector, state_tracker
   - Output: Synthesized definition text
   - Prompt: Clear, concise, comprehensive

4. **`generate_meaning_cluster`** - Create meaning cluster for single definition
   - Input: Definition, word, AI connector, state_tracker
   - Output: Meaning cluster assignment
   - Prompt: Semantic categorization

### Update Existing Functions:
- Add `state_tracker` parameter to all functions
- Add progress tracking within each function
- Ensure consistent error handling

## Phase 3: Synthesizer Refactoring (`backend/src/floridify/ai/synthesizer.py`)
### Core Changes:
1. **Extract** inline synthesis to use modular functions:
   - Replace inline example generation with `synthesize_examples()`
   - Replace inline synonym generation with `synthesize_synonyms()`
   - Use `synthesize_definition_text()` for definition synthesis

2. **Refactor** `_synthesize_definitions`:
   - Remove hardcoded synonym generation
   - Use individual synthesis functions
   - Add state tracking for each synthesis step

3. **Refactor** `generate_fallback_entry`:
   - Use `generate_meaning_cluster()` for single definitions
   - Leverage full synthesis pipeline
   - Remove duplicate synthesis logic

4. **Update** `synthesize_entry`:
   - Add state tracking for all synthesis stages
   - Use modular functions throughout
   - Maintain parallel processing capabilities

## Phase 4: State Tracker Integration
### Add State Tracking To:
1. **AI Connector** (`backend/src/floridify/ai/connector.py`):
   - Track individual AI API calls
   - Add sub-stages for long operations
   - Include token usage in state updates

2. **All Synthesis Functions**:
   - Accept state_tracker parameter
   - Update progress at key points
   - Report errors through state_tracker

3. **Enhancement Pipeline**:
   - Track parallel enhancement progress
   - Report individual component status
   - Aggregate progress updates

## Phase 5: Implementation Order
1. **Update AI models** - Create response objects, reorganize
2. **Create new synthesis functions** - Implement missing functions
3. **Update existing synthesis functions** - Add state tracking
4. **Refactor synthesizer.py** - Use modular functions
5. **Test with mypy/ruff** - Ensure type safety
6. **Integration testing** - Verify full pipeline

## Key Principles
- **KISS**: Simple, focused functions
- **DRY**: No duplicate synthesis logic
- **Modular**: Each function does one thing well
- **Consistent**: Uniform error handling and state tracking
- **Testable**: Pure functions where possible

## Success Criteria
1. All synthesis logic extracted to individual functions
2. Complete state tracking throughout pipeline
3. No hardcoded synthesis in main flow
4. All dictionary attributes have synthesis functions
5. Clean mypy/ruff output
6. Maintained functionality with improved architecture
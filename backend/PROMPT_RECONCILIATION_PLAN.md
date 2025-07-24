# Prompt Reconciliation Sub-Plan

## Current State Analysis

### Existing Prompts That Match Our Needs
1. **`synonyms.md`** ✓
   - Already comprehensive with scoring system
   - Used by: `ai.synonyms()`
   - Action: Use as-is via existing method

2. **`example_generation.md`** ✓
   - Simpler than needed but functional
   - Used by: `ai.examples()`
   - Action: Use as-is via existing method

3. **`synthesis.md`** ⚠️
   - Purpose: Synthesize multiple definitions into one per meaning cluster
   - Used by: `ai.synthesize_definitions()`
   - Issue: We need it to work with already-clustered definitions
   - Action: Review usage and potentially modify

4. **`meaning_extraction.md`** ⚠️
   - Purpose: Extract clusters from multiple definitions
   - Used by: `ai.extract_cluster_mapping()`
   - Issue: We need single-definition clustering for fallback
   - Action: Create new prompt for single-definition case

### Missing Prompts
1. **Single Definition Clustering**
   - Need: Generate meaning cluster for ONE definition (fallback case)
   - Action: Create `meaning_cluster_single.md`

### Implementation Changes Required

## Phase 1: Prompt Adjustments
1. **Review `synthesis.md`** usage
   - Check if it handles pre-clustered definitions correctly
   - May not need modification if used properly

2. **Create `meaning_cluster_single.md`**
   - For generating cluster info for a single definition
   - Used in fallback entry generation

## Phase 2: Update Synthesis Functions
1. **`synthesize_synonyms()`**
   - Remove inline prompt
   - Use: `await ai.synonyms(word, definition.text, definition.part_of_speech)`

2. **`synthesize_examples()`**
   - Remove inline prompt  
   - Use: `await ai.examples(word, definition.part_of_speech, definition.text, count)`

3. **`synthesize_definition_text()`**
   - Remove inline prompt
   - Use: `await ai.synthesize_definitions(word, definitions, meaning_cluster)`
   - Note: May need to convert dict format to Definition objects

4. **`generate_meaning_cluster()`**
   - Remove inline prompt
   - Create new connector method: `ai.generate_single_meaning_cluster()`
   - Use new `meaning_cluster_single.md` prompt

## Phase 3: Connector Updates
1. **Add method for single definition clustering**
   ```python
   async def generate_single_meaning_cluster(
       self,
       word: str,
       definition: str,
       word_type: str,
   ) -> MeaningClusterResponse:
   ```

2. **Remove the generic `generate()` method**
   - Not needed with proper templated methods

## Phase 4: Clean Up
1. **Remove all inline prompts** from synthesis_functions.py
2. **Ensure all synthesis uses connector methods**
3. **Update type hints and imports**

## Benefits
- Leverages existing, tested prompts
- Maintains consistency with current architecture
- Reduces code duplication
- Easier to maintain prompts separately

## Next Steps
1. Create the one missing prompt
2. Update connector with missing method
3. Refactor synthesis functions to use connector
4. Remove inline prompts
5. Test the refactored pipeline
# Batch Synthesis Implementation Requirements

## Context
The Floridify backend uses OpenAI API calls extensively in the synthesis pipeline. The main bottleneck is `enhance_definitions_parallel` in `synthesis_functions.py`, which makes multiple API calls per definition (synonyms, examples, antonyms, CEFR level, frequency band, etc.). For a word with 5 definitions and 10 enhancement components, this results in 50 individual API calls.

## Goal
Implement native batch processing using OpenAI's Batch API to:
1. Reduce costs by 50% (batch API discount)
2. Process all enhancement operations in `enhance_definitions_parallel` as a single batch
3. Maintain existing function signatures and behavior
4. Keep the implementation KISS, DRY, and properly integrated

## Current Architecture Understanding

### Key Files and Functions:
- `synthesis_functions.py`: Contains `enhance_definitions_parallel` which orchestrates all definition enhancements
- `connector.py`: OpenAI connector with `_make_structured_request` method
- `synthesizer.py`: Main synthesis orchestrator

### Current Flow:
1. `enhance_definitions_parallel` creates a list of async tasks
2. Each task calls a synthesis function (e.g., `synthesize_synonyms`)
3. Each synthesis function calls `ai._make_structured_request`
4. Results are gathered with `asyncio.gather()` and applied to definitions

## Implementation Requirements

### 1. Batch Collection Mechanism
- Create a way to intercept/collect OpenAI API calls instead of executing them immediately
- Maintain futures/promises for each request that can be resolved later
- No changes to existing function signatures

### 2. Batch Execution
- Convert collected requests to OpenAI Batch API format (JSONL)
- Submit batch, poll for completion, download results
- Resolve all futures with appropriate results
- Handle errors gracefully

### 3. Integration Points
- Modify `enhance_definitions_parallel` to support a batch_mode parameter
- When batch_mode=True, collect all requests first, then execute as batch
- When batch_mode=False, execute immediately (current behavior)

### 4. Key Constraints
- DO NOT change return types of existing functions
- DO NOT create duplicate implementations
- DO NOT break existing functionality
- MUST maintain type safety throughout
- MUST handle both immediate and batch modes cleanly

### 5. Suggested Approach
Consider implementing at the orchestration level rather than modifying core functions:
- Create a batch context manager or wrapper
- Intercept calls at the appropriate level
- Execute batch operations transparently
- Apply results using existing mechanisms

## Example Usage Vision
```python
# Immediate mode (current)
await enhance_definitions_parallel(definitions, word, ai)

# Batch mode (new)
await enhance_definitions_parallel(definitions, word, ai, batch_mode=True)

# Or with a batch processor
batch_processor = BatchSynthesisProcessor(ai)
await batch_processor.process_definitions(definitions, word)
```

## Success Criteria
1. All tests pass with no type errors
2. Batch mode processes all enhancements with 50% cost reduction
3. Code is clean, maintainable, and follows existing patterns
4. No breaking changes to existing APIs
5. Clear documentation and examples

## Anti-patterns to Avoid
- Changing function return types based on mode
- Creating parallel implementations of existing functions
- Complex promise/future management at low levels
- Breaking type safety with union types everywhere

Please implement a clean, integrated batch processing solution that elegantly handles the requirements above while maintaining the integrity of the existing codebase.
# Batch Implementation Issues

## Type System Conflict

The current implementation has a fundamental type system issue:

### Problem

When `batch_mode=True`, the OpenAI connector methods return `BatchPromise[T]` instead of `T`, but all the method signatures expect `T`. This breaks the type system because:

```python
async def synthesize_synonyms(...) -> SynonymGenerationResponse:
    # In batch mode, returns BatchPromise[SynonymGenerationResponse]
    # This violates the return type annotation
```

### Root Cause

The design tries to make the same methods work in two different modes with different return types, which Python's type system doesn't support well.

### Solutions

#### Option 1: Separate Batch Methods (Recommended)
Create separate methods for batch operations:

```python
class OpenAIConnector:
    # Immediate mode (existing)
    async def synthesize_synonyms(...) -> SynonymGenerationResponse:
        return await self._make_structured_request(...)
    
    # Batch mode (new)
    def synthesize_synonyms_batch(...) -> BatchPromise[SynonymGenerationResponse]:
        return self._add_to_batch(...)
```

#### Option 2: Higher-Level Batching
Instead of modifying the connector, handle batching at the synthesis level:

```python
class BatchSynthesisOrchestrator:
    def __init__(self, ai: OpenAIConnector):
        self.ai = ai
        self.batch_requests = []
    
    async def enhance_definitions_batch(self, definitions: list[Definition], ...):
        # Collect all synthesis operations
        # Submit as batch
        # Process results
```

#### Option 3: Union Return Types
Change all methods to return `T | BatchPromise[T]` and handle both cases:

```python
async def synthesize_synonyms(...) -> SynonymGenerationResponse | BatchPromise[SynonymGenerationResponse]:
    result = await self._make_structured_request(...)
    return result  # Could be either type
```

This requires all callers to handle both cases, which is not ideal.

## Recommendation

The cleanest approach is Option 2 - create a separate BatchSynthesisOrchestrator that:
1. Uses the existing connector methods to build requests
2. Intercepts the actual API calls
3. Batches them using the OpenAI Batch API
4. Returns results that match the expected types

This maintains type safety and doesn't break existing code.
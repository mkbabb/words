# Batch Synthesis Design - Native Integration

## Overview

This document outlines the design for integrating OpenAI Batch API support directly into the existing synthesis pipeline, focusing on `enhance_definitions_parallel` and related functions.

## Current Architecture Analysis

### Current Flow
1. `enhance_definitions_parallel` creates async tasks for each definition × component
2. Each task calls a synthesis function (e.g., `synthesize_synonyms`)
3. Each synthesis function calls the OpenAI connector
4. The connector makes individual API calls with structured outputs
5. Results are cached and applied to definitions

### Problems with Current Approach
- For 5 definitions × 10 components = 50 individual API calls
- Each call has network overhead and counts against rate limits
- No cost benefit from OpenAI's 50% batch discount
- Inefficient for large-scale processing

## Proposed Batch Integration

### Key Design Principles
1. **Minimal API Changes**: Existing functions should work in both immediate and batch modes
2. **Transparent Batching**: Callers shouldn't need to know about batching details
3. **Preserve Caching**: Batch results should populate the cache for individual items
4. **Error Isolation**: Failed items in a batch shouldn't affect others
5. **Progressive Enhancement**: System should work even if batch fails

### Architecture Changes

#### 1. OpenAI Connector Enhancement

Add batch mode support to the connector:

```python
class OpenAIConnector:
    def __init__(self, ..., batch_mode: bool = False):
        self.batch_mode = batch_mode
        self.batch_accumulator = BatchAccumulator() if batch_mode else None
    
    async def _make_structured_request(self, ...):
        if self.batch_mode and self.batch_accumulator:
            # Accumulate request instead of executing
            return self.batch_accumulator.add_request(...)
        else:
            # Execute immediately (existing behavior)
            return await self._execute_request(...)
    
    async def execute_batch(self) -> dict[str, Any]:
        """Execute all accumulated requests as a batch."""
        if not self.batch_accumulator:
            return {}
        
        # Create batch file
        # Submit to OpenAI Batch API
        # Wait for completion or timeout
        # Parse results
        # Update cache for each item
        return batch_results
```

#### 2. BatchAccumulator Class

```python
class BatchAccumulator:
    """Accumulates requests for batch processing."""
    
    def __init__(self):
        self.requests: list[BatchRequest] = []
        self.request_map: dict[str, int] = {}  # Maps request_id to index
    
    def add_request(
        self,
        prompt: str,
        response_model: type[BaseModel],
        **kwargs
    ) -> BatchPromise[T]:
        """Add request and return a promise for the future result."""
        request_id = self._generate_request_id(prompt, response_model, kwargs)
        
        # Create batch request in OpenAI format
        batch_request = self._create_batch_request(
            request_id, prompt, response_model, **kwargs
        )
        
        self.requests.append(batch_request)
        self.request_map[request_id] = len(self.requests) - 1
        
        # Return a promise that will be resolved when batch completes
        return BatchPromise(request_id, response_model)
```

#### 3. Synthesis Function Modifications

Minimal changes to synthesis functions:

```python
async def enhance_definitions_parallel(
    definitions: list[Definition],
    word: Word,
    ai: OpenAIConnector,
    components: set[str] | None = None,
    force_refresh: bool = False,
    batch_mode: bool = False,  # New parameter
) -> None:
    """Enhance definitions with parallel synthesis."""
    
    # Enable batch mode on connector if requested
    if batch_mode:
        ai = OpenAIConnector(
            api_key=ai.api_key,
            model_name=ai.model_name,
            batch_mode=True
        )
    
    # Existing task creation logic remains the same
    tasks = []
    for definition in definitions:
        for component in components:
            task = create_enhancement_task(...)
            tasks.append(task)
    
    if batch_mode:
        # Accumulate all requests
        promises = await asyncio.gather(*tasks)
        
        # Execute batch
        batch_results = await ai.execute_batch()
        
        # Resolve promises with results
        for promise in promises:
            if isinstance(promise, BatchPromise):
                promise.resolve(batch_results.get(promise.request_id))
        
        # Apply results to definitions
        for definition, promise in zip(...):
            result = await promise
            apply_result_to_definition(definition, result)
    else:
        # Existing immediate execution
        results = await asyncio.gather(*tasks)
        # Apply results...
```

#### 4. Batch Promise Pattern

```python
class BatchPromise(Generic[T]):
    """Promise for a batch request result."""
    
    def __init__(self, request_id: str, response_model: type[T]):
        self.request_id = request_id
        self.response_model = response_model
        self._future: asyncio.Future[T] = asyncio.Future()
    
    def resolve(self, result: Any) -> None:
        """Resolve the promise with a result."""
        if result is not None:
            parsed = self.response_model.model_validate(result)
            self._future.set_result(parsed)
        else:
            self._future.set_exception(ValueError("No result found"))
    
    def __await__(self):
        return self._future.__await__()
```

### Implementation Phases

#### Phase 1: Connector Enhancement
1. Add BatchAccumulator class
2. Modify _make_structured_request to support accumulation
3. Implement execute_batch method
4. Add batch file creation and submission logic

#### Phase 2: Promise Pattern
1. Implement BatchPromise class
2. Add request tracking and mapping
3. Handle result resolution

#### Phase 3: Synthesis Integration
1. Add batch_mode parameter to enhance_definitions_parallel
2. Modify task execution flow for batch mode
3. Ensure cache population works correctly

#### Phase 4: Testing & Optimization
1. Test with various batch sizes
2. Handle edge cases (empty batches, failures)
3. Optimize batching strategy
4. Add metrics and monitoring

### Benefits

1. **Cost Reduction**: 50% discount with Batch API
2. **Rate Limit Efficiency**: Single batch counts as one request
3. **Better Performance**: Reduced network overhead
4. **Backwards Compatible**: Existing code continues to work
5. **Flexible**: Can mix batch and immediate modes

### Example Usage

```python
# Immediate mode (default)
await enhance_definitions_parallel(definitions, word, ai)

# Batch mode for bulk processing
await enhance_definitions_parallel(
    definitions, word, ai, 
    batch_mode=True
)

# CLI integration
floridify batch synthesize --words words.txt --batch-mode
```

### Considerations

1. **Batch Size Limits**: OpenAI has limits on batch file size
2. **Timeout Handling**: Batches can take up to 24 hours
3. **Partial Failures**: Need graceful handling
4. **Progress Tracking**: Update StateTracker appropriately
5. **Cache Coherency**: Ensure batch results update cache correctly

This design provides a clean integration of batch processing into the existing synthesis pipeline while maintaining backwards compatibility and the flexibility to use either mode as appropriate.
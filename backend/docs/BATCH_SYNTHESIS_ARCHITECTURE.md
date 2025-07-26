# Batch Synthesis Architecture

## Overview

This document describes the proper architecture for batch synthesis in Floridify, designed to efficiently process large-scale synthesis operations with 50% cost savings using the OpenAI Batch API.

## Design Principles

1. **Separation of Concerns**: Batch processing is handled separately from the core synthesis logic
2. **No API Changes**: Existing synthesis functions remain unchanged
3. **Type Safety**: All operations maintain proper type safety
4. **Flexibility**: Can process any combination of synthesis components
5. **Scalability**: Handles thousands of words efficiently

## Architecture

### Core Components

#### 1. **SynthesisBatchProcessor** (`batch_processor.py`)
The main orchestrator for batch operations:
- Creates batch requests in OpenAI format
- Manages file uploads and batch submission
- Polls for completion
- Processes results

#### 2. **BatchSynthesisCollector** (`batch_synthesis.py`)
Collects synthesis requests during a batch operation:
- Intercepts OpenAI API calls
- Accumulates requests with futures
- Manages promise resolution

#### 3. **InterceptingConnector** (`batch_synthesis.py`)
Wraps the OpenAI connector to intercept calls:
- Maintains API compatibility
- Routes calls to the batch collector
- Preserves type signatures

## How It Works

### 1. Request Collection Phase

```python
# Create batch processor
batch_processor = SynthesisBatchProcessor(openai_connector)

# Prepare word data
words_with_data = [(word1, definitions1), (word2, definitions2), ...]

# Submit for batch processing
result = await batch_processor.process_words_batch(
    words_with_data,
    components={"synonyms", "examples", "cefr_level"}
)
```

### 2. Batch Creation

The processor creates OpenAI-formatted batch requests:

```json
{
    "custom_id": "happy_def0_synonyms",
    "method": "POST",
    "url": "/v1/chat/completions",
    "body": {
        "model": "gpt-4o-mini",
        "messages": [...],
        "response_format": {
            "type": "json_schema",
            "json_schema": {...}
        }
    }
}
```

### 3. Batch Submission

1. Requests are written to a JSONL file
2. File is uploaded to OpenAI
3. Batch job is created with 24-hour completion window

### 4. Polling and Completion

```python
# Check batch status
status = await batch_processor.check_batch_status(batch_id)

# When complete, process results
results = await batch_processor.process_batch_results(
    batch_id, 
    output_file_id
)
```

### 5. Result Processing

Results are parsed and applied to the database:
- Each result is matched to its original request
- Synthesis results are saved to appropriate models
- Errors are logged and handled gracefully

## Usage Patterns

### Basic Batch Processing

```python
# For simple batch operations
ai = get_openai_connector()
processor = SynthesisBatchProcessor(ai)

# Process words in batches
result = await processor.process_words_batch(
    words_with_data,
    batch_size=1000  # 1000 words per batch file
)
```

### Full Workflow with Polling

```python
# Complete workflow including polling
result = await processor.run_full_batch_synthesis(
    word_list,
    poll_interval=60  # Check every minute
)
```

### Custom Component Selection

```python
# Process only specific components
from floridify.ai.constants import SynthesisComponent

components = {
    SynthesisComponent.SYNONYMS.value,
    SynthesisComponent.EXAMPLES.value,
    SynthesisComponent.CEFR_LEVEL.value
}

result = await processor.process_words_batch(
    words_with_data,
    components=components
)
```

## Cost Analysis

### Pricing Comparison (GPT-4o-mini)

| Mode | Input Cost | Output Cost | Total (1M tokens) |
|------|------------|-------------|-------------------|
| Immediate | $0.15/1M | $0.60/1M | $0.75 |
| Batch | $0.075/1M | $0.30/1M | $0.375 |
| **Savings** | **50%** | **50%** | **50%** |

### Example Calculation

For processing 10,000 words with 5 definitions each:
- Components per definition: 10
- Total API calls: 10,000 × 5 × 10 = 500,000
- Estimated tokens: 500,000 × 500 = 250M tokens

**Immediate Mode**: 250 × $0.75 = **$187.50**
**Batch Mode**: 250 × $0.375 = **$93.75**
**Savings**: **$93.75 (50%)**

## Implementation Details

### Batch Request Format

Each synthesis operation is converted to a batch request:

1. **Prompt Generation**: Uses existing template manager
2. **Response Format**: Structured output with JSON schema
3. **Custom ID**: Encodes word, definition index, and component
4. **Model Config**: Uses configured model (gpt-4o-mini recommended)

### Error Handling

- Individual request failures don't fail the entire batch
- Errors are logged with context
- Partial results are still processed
- Retry logic can be implemented at the batch level

### Database Integration

Results are applied through existing models:
- `Definition` updates for components
- `Example` creation for generated examples
- `Pronunciation`, `Etymology`, etc. for word-level data

## Best Practices

1. **Batch Size**: 1000-5000 words per batch file
2. **Timing**: Submit during off-peak hours
3. **Monitoring**: Implement proper logging and alerting
4. **Error Recovery**: Save batch IDs for retry capability
5. **Cost Tracking**: Monitor token usage and costs

## Migration Path

### From Immediate to Batch Processing

1. **No Code Changes Required**: Existing synthesis code remains unchanged
2. **New Entry Point**: Use `SynthesisBatchProcessor` for batch operations
3. **Gradual Migration**: Can run both modes in parallel
4. **Testing**: Start with small batches to verify correctness

### Integration with Existing Pipeline

The batch processor can be integrated at various levels:

1. **CLI Tool**: 
   ```bash
   floridify batch process --words words.txt --components all
   ```

2. **API Endpoint**:
   ```python
   @router.post("/batch/synthesize")
   async def batch_synthesize(request: BatchSynthesisRequest):
       # Use batch processor
   ```

3. **Background Jobs**:
   - Schedule nightly batch processing
   - Process new words in batches
   - Reprocess with updated models

## Limitations and Considerations

1. **Latency**: Batches can take up to 24 hours (usually faster)
2. **No Streaming**: Results arrive all at once
3. **Size Limits**: OpenAI has limits on batch file size
4. **No Cancellation**: Once submitted, batches run to completion

## Future Enhancements

1. **Smart Batching**: Automatically batch when volume exceeds threshold
2. **Priority Queues**: Urgent requests use immediate mode
3. **Result Caching**: Cache batch results for reuse
4. **Progress UI**: Real-time batch progress monitoring
5. **Cost Dashboard**: Track savings and usage

## Conclusion

This batch synthesis architecture provides a clean, efficient way to process large-scale synthesis operations with significant cost savings. By maintaining separation between batch orchestration and core synthesis logic, we preserve code quality while adding powerful batch capabilities.
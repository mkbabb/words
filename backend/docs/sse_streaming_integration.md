# SSE Streaming Integration Guide

## Overview

The search API now fully integrates Server-Sent Events (SSE) streaming with the real search pipeline implementation. This provides real-time progress updates as the search progresses through different methods.

## Key Features

1. **Real-time Progress Tracking**: Stream updates as each search method executes
2. **Partial Results**: Receive incremental results after each search method completes
3. **Performance Metrics**: Get timing information for each search stage
4. **Error Handling**: Graceful error reporting through the event stream

## Implementation Details

### Search Pipeline Integration

The `/api/v1/search/stream` endpoint now:

1. Creates a `PipelineStateTracker` instance for the search operation
2. Passes this tracker to `search_word_pipeline()` for detailed progress updates
3. Monitors state updates and forwards them to the SSE stream
4. Streams partial results as each search method completes

### Search Method Handling

Different search methods are handled appropriately:

- **Exact**: Only runs exact matching
- **Fuzzy**: Only runs fuzzy/prefix matching
- **Semantic**: Enables semantic search (if available)
- **Hybrid**: Runs all applicable methods automatically

### State Tracking Flow

1. **Query Processing** (0-10%): Normalize and prepare the search query
2. **Method Selection** (10-20%): Determine which search methods to use
3. **Search Execution** (20-70%): Run each selected search method
   - Each method reports its own progress and partial results
4. **Deduplication** (70-75%): Remove duplicate results
5. **Filtering** (75-85%): Apply score threshold filtering
6. **Ranking** (85-95%): Sort results by relevance
7. **Completion** (100%): Return final results

## API Usage

### JavaScript/TypeScript Example

```javascript
const eventSource = new EventSource('/api/v1/search/stream?q=cognition&method=hybrid');

eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    console.log(`Progress: ${data.progress * 100}% - ${data.message}`);
    
    // Handle partial results if available
    if (data.partial_results) {
        updateResultsPreview(data.partial_results);
    }
});

eventSource.addEventListener('complete', (event) => {
    const results = JSON.parse(event.data);
    displayFinalResults(results);
    eventSource.close();
});

eventSource.addEventListener('error', (event) => {
    const error = JSON.parse(event.data);
    handleError(error.error);
    eventSource.close();
});
```

### Python Example

```python
import httpx
import json

async def stream_search(query: str):
    url = "http://localhost:8000/api/v1/search/stream"
    params = {"q": query, "method": "hybrid"}
    
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, params=params) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = json.loads(line.split(":", 1)[1])
                    # Process the event data
```

## Event Format

### Progress Event

```json
{
    "stage": "search_fuzzy",
    "progress": 0.45,
    "message": "Searching with fuzzy method",
    "timestamp": "2025-07-18T10:30:45.123Z",
    "partial_results": [
        {
            "word": "cognition",
            "score": 0.95,
            "method": "fuzzy"
        }
    ],
    "metadata": {
        "method": "fuzzy",
        "result_count": 5,
        "time_ms": 23.5
    }
}
```

### Complete Event

```json
{
    "query": "cognition",
    "results": [
        {
            "word": "cognition",
            "score": 0.95,
            "method": "exact",
            "is_phrase": false
        },
        {
            "word": "cognitive",
            "score": 0.85,
            "method": "fuzzy",
            "is_phrase": false
        }
    ],
    "total_results": 10,
    "search_time_ms": 125
}
```

### Error Event

```json
{
    "error": "Search failed: Connection timeout"
}
```

## Performance Considerations

1. **Caching**: Regular search results are cached for 1 hour
2. **Streaming Overhead**: SSE adds minimal overhead (~5-10ms)
3. **Method Selection**: Specific methods (exact, fuzzy) bypass the full pipeline for better performance
4. **Concurrent Requests**: Each SSE connection maintains its own state tracker

## Testing

Two test scripts are provided:

1. **test_sse_search.py**: Tests SSE streaming functionality
2. **test_search_integration.py**: Tests regular search API and caching

Run tests:
```bash
./test_sse_search.py
./test_search_integration.py
```

## Future Enhancements

1. **WebSocket Support**: For bidirectional communication
2. **Batch Streaming**: Stream results for multiple queries
3. **Custom Progress Granularity**: Allow clients to specify update frequency
4. **Result Diffing**: Only send changed results in updates
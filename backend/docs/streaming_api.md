# SSE Streaming API Documentation

## Overview

The streaming lookup endpoint provides real-time progress updates during word lookups using Server-Sent Events (SSE). This allows clients to show progress bars, display partial results as they become available, and provide a better user experience for potentially slow lookups.

## Endpoint

```
GET /api/v1/lookup/{word}/stream
```

### Parameters

- `word` (path parameter): The word to look up
- `force_refresh` (query, optional): Bypass caches for fresh data (default: false)
- `providers` (query, optional): Dictionary providers to use (default: ["wiktionary"])
- `no_ai` (query, optional): Skip AI synthesis (default: false)

## Event Types

### 1. Progress Events

Sent throughout the lookup process to indicate current stage and progress.

```json
event: progress
data: {
  "stage": "search",
  "progress": 0.1,
  "message": "Searching for 'word'",
  "details": {
    "elapsed_ms": 123,
    "word": "serendipity",
    "semantic": false
  },
  "timestamp": "2025-01-18T10:30:45.123456"
}
```

Stages include:
- `initialization`: Starting the lookup
- `search`: Searching the word index
- `provider_fetch`: Fetching from dictionary providers
- `ai_clustering`: Clustering definitions by meaning
- `ai_synthesis`: Synthesizing with AI
- `complete`: Lookup finished

### 2. Provider Data Events

Sent when data from a dictionary provider is ready, allowing immediate display of partial results.

```json
event: provider_data
data: {
  "stage": "provider_data",
  "provider": "wiktionary",
  "definitions_count": 5,
  "has_pronunciation": true,
  "has_etymology": true,
  "data": {
    "provider_name": "wiktionary",
    "definitions": [...],
    "pronunciation": {...},
    "etymology": "..."
  }
}
```

### 3. Complete Event

Sent when the entire lookup is finished with the final synthesized result.

```json
event: complete
data: {
  "word": "serendipity",
  "pronunciation": {...},
  "definitions": [...],
  "last_updated": "2025-01-18T10:30:47.123456"
}
```

### 4. Error Event

Sent if an error occurs during lookup.

```json
event: error
data: {
  "error": "Error message here"
}
```

## Client Implementation

### JavaScript Example

```javascript
const eventSource = new EventSource('/api/v1/lookup/serendipity/stream');

// Track provider results as they come in
const providerResults = new Map();

eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    updateProgressBar(data.progress);
    updateStatusMessage(data.message);
    
    // Show timing information
    if (data.details?.elapsed_ms) {
        updateElapsedTime(data.details.elapsed_ms);
    }
});

eventSource.addEventListener('provider_data', (e) => {
    const data = JSON.parse(e.data);
    
    // Store and display provider results immediately
    providerResults.set(data.provider, data.data);
    displayProviderResults(data.provider, data.data);
    
    // Update UI to show this provider is complete
    markProviderComplete(data.provider);
});

eventSource.addEventListener('complete', (e) => {
    const result = JSON.parse(e.data);
    
    // Display final synthesized result
    displayFinalDefinitions(result);
    
    // Close the connection
    eventSource.close();
});

eventSource.addEventListener('error', (e) => {
    const error = JSON.parse(e.data);
    displayError(error.error);
    eventSource.close();
});

// Handle connection errors
eventSource.onerror = (e) => {
    console.error('SSE connection error:', e);
    eventSource.close();
};
```

### Python Example

```python
import httpx
import json

async def stream_lookup(word: str):
    url = f"http://localhost:8000/api/v1/lookup/{word}/stream"
    
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            event_type = None
            event_data = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    event_data.append(line.split(":", 1)[1].strip())
                elif line == "" and event_type:
                    # Process complete event
                    data = json.loads("".join(event_data))
                    
                    if event_type == "progress":
                        print(f"Progress: {data['progress']:.1%} - {data['message']}")
                    elif event_type == "provider_data":
                        print(f"Provider {data['provider']} ready with {data['definitions_count']} definitions")
                    elif event_type == "complete":
                        print(f"Complete! Found {len(data['definitions'])} definitions")
                        break
                    elif event_type == "error":
                        print(f"Error: {data['error']}")
                        break
                    
                    event_type = None
                    event_data = []
```

## Benefits

1. **Progressive Enhancement**: Show results as soon as they're available
2. **Better UX**: Users see progress and don't wonder if the app is frozen
3. **Performance Metrics**: Timing information helps identify bottlenecks
4. **Graceful Degradation**: If streaming fails, clients can fall back to regular endpoint

## Testing

Use the provided test script:

```bash
cd backend
python test_streaming.py serendipity wiktionary dictionary_com
```

This will show detailed progress information and timing metrics for the lookup.
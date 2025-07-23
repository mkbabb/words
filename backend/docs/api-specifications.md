# Enhanced API Specifications - Floridify Dictionary

## Overview

This document defines the enhanced REST API for granular dictionary operations with a focus on **performance, minimal payloads, and atomic updates**.

## API Design Principles

1. **Atomic Operations**: Every field individually updatable via PATCH
2. **Batch-First**: All operations support batch variants
3. **Field Selection**: GraphQL-style field projection
4. **Conditional Requests**: ETags and If-Modified-Since support
5. **Streaming**: Large datasets use JSON Lines streaming
6. **Idempotency**: All write operations are idempotent

## Authentication & Headers

```http
# Required headers
Content-Type: application/json
Accept: application/json

# Optional performance headers
X-Fields: text,definitions.text  # Field projection
X-Exclude: examples,facts        # Field exclusion
X-Batch-Size: 100               # Batch operation size

# Conditional headers
If-None-Match: "etag123"
If-Modified-Since: Mon, 1 Jan 2024 00:00:00 GMT
```

## Core Endpoints

### Words

#### Get Word
```http
GET /api/v2/words/{word_id}
```

Query Parameters:
- `fields`: Comma-separated field paths (e.g., `text,definitions.text`)
- `exclude`: Fields to exclude
- `include_relations`: Include related documents (default: true)

Response:
```json
{
  "id": "507f1f77bcf86cd799439011",
  "text": "efflorescence",
  "normalized": "efflorescence",
  "language": "en",
  "metadata": {
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "version": 1
  },
  "_links": {
    "self": "/api/v2/words/507f1f77bcf86cd799439011",
    "definitions": "/api/v2/words/507f1f77bcf86cd799439011/definitions",
    "pronunciations": "/api/v2/words/507f1f77bcf86cd799439011/pronunciations"
  }
}
```

#### Batch Word Lookup
```http
POST /api/v2/words/lookup-batch
```

Request:
```json
{
  "words": ["efflorescence", "obstreperous", "perspicacious"],
  "fields": ["text", "definitions.text", "definitions.synonyms"],
  "include_missing": false
}
```

Response:
```json
{
  "results": [
    {
      "word": "efflorescence",
      "found": true,
      "data": { /* word data */ }
    },
    {
      "word": "obstreperous", 
      "found": false,
      "error": "not_found"
    }
  ],
  "stats": {
    "requested": 3,
    "found": 2,
    "duration_ms": 45
  }
}
```

### Definitions

#### Update Definition (Atomic)
```http
PATCH /api/v2/definitions/{definition_id}
```

Headers:
```http
If-Match: "version:3"  # Optimistic locking
```

Request:
```json
{
  "text": "Updated definition text",
  "synonyms": {
    "add": ["new-synonym"],
    "remove": ["old-synonym"]
  },
  "metadata": {
    "quality_score": 0.95
  }
}
```

Response:
```json
{
  "id": "def123",
  "version": 4,
  "updated_fields": ["text", "synonyms", "metadata.quality_score"],
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Batch Definition Updates
```http
PATCH /api/v2/definitions/batch
```

Request:
```json
{
  "updates": [
    {
      "id": "def1",
      "version": 2,
      "changes": {
        "text": "New text",
        "word_type": "noun"
      }
    },
    {
      "id": "def2",
      "version": 5,
      "changes": {
        "synonyms": ["add:new", "remove:old"]
      }
    }
  ],
  "atomic": true  // All succeed or all fail
}
```

### Examples

#### Regenerate Examples
```http
POST /api/v2/definitions/{definition_id}/examples/regenerate
```

Request:
```json
{
  "count": 3,
  "style": "modern",
  "complexity": "intermediate"
}
```

Response (SSE Stream):
```
event: progress
data: {"stage": "generating", "progress": 0.33}

event: example
data: {"id": "ex1", "text": "The efflorescence on the old brick wall..."}

event: complete
data: {"generated": 3, "duration_ms": 2500}
```

### Synonyms

#### Bulk Synonym Management
```http
PUT /api/v2/definitions/{definition_id}/synonyms
```

Request:
```json
{
  "mode": "merge",  // merge|replace|remove
  "synonyms": ["bloom", "flowering", "blossoming"],
  "validate": true,
  "score_threshold": 0.7
}
```

### Facts

#### Generate Facts (Batch)
```http
POST /api/v2/facts/generate-batch
```

Request:
```json
{
  "word_ids": ["word1", "word2"],
  "categories": ["etymology", "cultural"],
  "max_per_word": 5,
  "min_confidence": 0.8
}
```

### Search

#### Advanced Search
```http
GET /api/v2/search
```

Query Parameters:
- `q`: Query string
- `method`: exact|fuzzy|semantic|hybrid|auto (default: auto)
- `filters`: JSON filter object
- `sort`: Comma-separated sort fields
- `cursor`: Pagination cursor
- `limit`: Results per page (max: 100)

Example:
```
GET /api/v2/search?q=flower&method=semantic&filters={"word_type":"noun"}&sort=-score,text
```

### Synthesis

#### Selective Resynthesis
```http
POST /api/v2/words/{word_id}/resynthesize
```

Request:
```json
{
  "components": ["definitions", "examples"],
  "definition_ids": ["def1", "def2"],  // Optional: specific definitions
  "providers": ["oxford", "webster"],
  "force": false
}
```

### Batch Operations

#### Universal Batch Endpoint
```http
POST /api/v2/batch
```

Request:
```json
{
  "operations": [
    {
      "method": "PATCH",
      "path": "/definitions/def1",
      "body": {"text": "Updated"},
      "if_match": "version:2"
    },
    {
      "method": "POST",
      "path": "/examples",
      "body": {"definition_id": "def1", "text": "Example"}
    },
    {
      "method": "DELETE",
      "path": "/facts/fact1"
    }
  ],
  "transaction": true
}
```

Response:
```json
{
  "results": [
    {"index": 0, "status": 200, "body": {...}},
    {"index": 1, "status": 201, "body": {...}},
    {"index": 2, "status": 204}
  ],
  "summary": {
    "total": 3,
    "succeeded": 3,
    "failed": 0,
    "duration_ms": 125
  }
}
```

### Export & Import

#### Stream Export
```http
GET /api/v2/export/words
```

Query Parameters:
- `format`: jsonl|csv|parquet
- `filters`: JSON filter criteria
- `fields`: Field projection
- `compress`: gzip|br|none

Response: Streaming response with progress headers

#### Bulk Import
```http
POST /api/v2/import/words
```

Headers:
```http
Content-Type: multipart/form-data
X-Import-Mode: upsert|replace|skip-existing
```

## Performance Features

### Field Projection

```http
GET /api/v2/words/123?fields=text,definitions(text,synonyms),pronunciations.ipa
```

Returns only requested fields, reducing payload by up to 90%.

### Cursor Pagination

```http
GET /api/v2/definitions?cursor=eyJpZCI6ImRlZjEyMyJ9&limit=50
```

Response includes:
```json
{
  "data": [...],
  "cursors": {
    "next": "eyJpZCI6ImRlZjE3MyJ9",
    "prev": "eyJpZCI6ImRlZjA3MyJ9"
  }
}
```

### Response Caching

All GET endpoints return:
```http
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Cache-Control: private, max-age=300
Last-Modified: Mon, 1 Jan 2024 00:00:00 GMT
```

### Compression

Accept-Encoding supported:
- gzip (default)
- br (Brotli)
- deflate

## Error Handling

Standard error format:
```json
{
  "error": {
    "code": "DEFINITION_NOT_FOUND",
    "message": "Definition with id 'def123' not found",
    "details": {
      "id": "def123",
      "suggestion": "Use GET /api/v2/words/{word_id}/definitions to list all definitions"
    }
  },
  "request_id": "req_123abc",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

Error codes:
- 400: Bad Request (validation errors)
- 404: Not Found
- 409: Conflict (version mismatch)
- 422: Unprocessable Entity
- 429: Rate Limited
- 503: Service Unavailable

## Rate Limiting

Headers returned:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1672531200
```

Limits:
- Standard: 1000 requests/hour
- Batch operations: 100 requests/hour
- Export operations: 10 requests/hour

## WebSocket Support

Real-time updates via WebSocket:
```javascript
ws://api.floridify.com/v2/ws

// Subscribe to word updates
{"action": "subscribe", "topic": "word:123"}

// Receive updates
{"event": "update", "topic": "word:123", "data": {...}}
```

## API Versioning

- URL versioning: `/api/v2/`
- Sunset headers for deprecation:
  ```http
  Sunset: Sat, 1 Jan 2025 00:00:00 GMT
  Link: </api/v3/words>; rel="successor-version"
  ```

## Performance Benchmarks

Target metrics:
- Simple GET: <20ms (p95)
- Complex queries: <50ms (p95)
- Batch operations: >1000 ops/sec
- Streaming export: >10MB/sec
- WebSocket latency: <10ms

## SDK Examples

### Python
```python
from floridify import Client

client = Client(base_url="https://api.floridify.com/v2")

# Atomic update with optimistic locking
word = await client.words.get("efflorescence")
definition = word.definitions[0]
definition.text = "Updated definition"
await client.definitions.update(definition, if_version=definition.version)

# Batch operations
results = await client.batch([
    client.definitions.update(def1, {"text": "New text"}),
    client.examples.create({"definition_id": def1.id, "text": "Example"}),
    client.facts.delete(fact1.id)
])
```

### TypeScript
```typescript
import { FloridifyClient } from '@floridify/sdk';

const client = new FloridifyClient({ baseURL: 'https://api.floridify.com/v2' });

// Field projection
const word = await client.words.get('efflorescence', {
  fields: ['text', 'definitions.text', 'definitions.synonyms']
});

// Streaming updates
const stream = client.definitions.regenerateExamples(def.id);
for await (const event of stream) {
  console.log(event.type, event.data);
}
```
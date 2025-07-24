# Floridify API Documentation

## Overview
The Floridify API provides comprehensive dictionary services with AI-enhanced content generation, multi-method search, and granular component management.

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently, the API does not require authentication. This will be added in a future release.

## Common Patterns

### Response Formats

#### Resource Response
```json
{
  "data": {...},
  "metadata": {
    "version": 1,
    "last_modified": "2025-01-20T10:00:00Z"
  },
  "links": {
    "self": "/resource/123",
    "related": "/related/123"
  }
}
```

#### List Response
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

#### Error Response
```json
{
  "error": "Resource not found",
  "details": [{
    "field": "id",
    "message": "Invalid ID format",
    "code": "invalid_id"
  }],
  "timestamp": "2025-01-20T10:00:00Z",
  "request_id": "req_123"
}
```

### Query Parameters

#### Pagination
- `offset`: Number of items to skip (default: 0)
- `limit`: Number of items to return (default: 20, max: 100)

#### Field Selection
- `include`: Comma-separated fields to include
- `exclude`: Comma-separated fields to exclude
- `expand`: Comma-separated related resources to expand

#### Sorting
- `sort_by`: Field to sort by
- `sort_order`: Sort direction (asc/desc)

### Headers

#### Request Headers
- `Accept`: application/json
- `Content-Type`: application/json
- `If-None-Match`: ETag for conditional requests

#### Response Headers
- `ETag`: Entity tag for caching
- `Cache-Control`: Caching directives
- `X-Response-Time`: Request processing time
- `X-Cache`: Cache hit/miss status

## Endpoints

### Words

#### List Words
```http
GET /words
```

Query Parameters:
- `text`: Exact text match
- `text_pattern`: Regex pattern
- `language`: Language code
- `offensive_flag`: Filter offensive words
- `created_after`: Date filter
- `created_before`: Date filter

#### Get Word
```http
GET /words/{word_id}
```

#### Create Word
```http
POST /words
```

Body:
```json
{
  "text": "example",
  "language": "english",
  "homograph_number": null,
  "offensive_flag": false
}
```

#### Update Word
```http
PUT /words/{word_id}?version=1
```

#### Delete Word
```http
DELETE /words/{word_id}?cascade=true
```

#### Search Words
```http
GET /words/search/{query}
```

### Definitions

#### List Definitions
```http
GET /definitions
```

Query Parameters:
- `word_id`: Filter by word
- `part_of_speech`: Filter by POS
- `cefr_level`: Filter by CEFR level
- `frequency_band`: Filter by frequency (1-5)
- `has_examples`: Filter by example availability

#### Get Definition
```http
GET /definitions/{definition_id}
```

#### Create Definition
```http
POST /definitions
```

#### Update Definition
```http
PUT /definitions/{definition_id}
```

#### Regenerate Components
```http
POST /definitions/{definition_id}/regenerate
```

Body:
```json
{
  "components": ["synonyms", "examples", "grammar_patterns"],
  "force": false
}
```

Available components:
- `synonyms`
- `antonyms`
- `examples`
- `cefr_level`
- `frequency_band`
- `register`
- `domain`
- `grammar_patterns`
- `collocations`
- `usage_notes`
- `regional_variants`

### Examples

#### List Examples
```http
GET /examples
```

#### Get Example
```http
GET /examples/{example_id}
```

#### Generate Examples
```http
POST /examples/definition/{definition_id}/generate
```

Body:
```json
{
  "count": 3,
  "style": "formal",
  "context": "academic writing"
}
```

### Facts

#### List Facts
```http
GET /facts
```

#### Get Fact
```http
GET /facts/{fact_id}
```

#### Generate Facts
```http
POST /facts/word/{word_id}/generate
```

Body:
```json
{
  "count": 5,
  "categories": ["etymology", "cultural"],
  "context_words": ["related", "words"]
}
```

### Synthesis

#### Synthesize Entry
```http
POST /synthesis
```

Body:
```json
{
  "word": "example",
  "language": "english",
  "providers": ["oxford", "webster"],
  "force_refresh": false,
  "components": ["pronunciation", "etymology", "facts"]
}
```

#### Get Synthesized Entry
```http
GET /synthesis/{entry_id}?expand=word,definitions,facts
```

#### Enhance Entry
```http
POST /synthesis/{entry_id}/enhance
```

Body:
```json
{
  "components": ["etymology", "facts"],
  "force": false
}
```

#### Get Component Status
```http
GET /synthesis/{entry_id}/status
```

Response:
```json
{
  "word_components": {
    "etymology": true,
    "pronunciation": false,
    "facts": true
  },
  "definition_components": {
    "def_123": {
      "synonyms": true,
      "examples": false,
      "grammar_patterns": true
    }
  }
}
```

### Batch Operations

#### Batch Word Creation
```http
POST /batch/v2/words/create
```

Body:
```json
{
  "words": [
    {"text": "word1", "language": "english"},
    {"text": "word2", "language": "english"}
  ],
  "skip_existing": true
}
```

#### Batch Definition Update
```http
PATCH /batch/v2/definitions/update
```

Body:
```json
{
  "updates": [
    {"id": "def_123", "cefr_level": "B2"},
    {"id": "def_456", "frequency_band": 3}
  ],
  "validate_versions": false
}
```

#### Batch Delete
```http
DELETE /batch/v2/delete
```

Body:
```json
{
  "model": "word",
  "ids": ["id1", "id2", "id3"],
  "cascade": true
}
```

### Legacy Endpoints (Deprecated)

#### Lookup
```http
GET /lookup/{word}
```

#### Search
```http
GET /search/{query}
```

## Performance Optimization

### Caching
- Use ETags for conditional requests
- Respect Cache-Control headers
- Implement client-side caching

### Field Selection
- Request only needed fields with `include`
- Exclude large fields with `exclude`
- Use `expand` sparingly

### Batch Operations
- Use batch endpoints for bulk operations
- Process large datasets in chunks
- Monitor rate limits

## Rate Limiting
Currently not implemented, but planned:
- 1000 requests per hour per IP
- 100 concurrent requests
- Batch operations count as single request

## Error Handling

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `204`: No Content (successful delete)
- `304`: Not Modified (ETag match)
- `400`: Bad Request
- `404`: Not Found
- `409`: Conflict (version mismatch)
- `429`: Too Many Requests
- `500`: Internal Server Error

### Error Response Format
All errors follow the standard ErrorResponse format with detailed error information.

## Migration Guide

### From Legacy to New API

1. **Update Endpoints**
   - `/lookup/{word}` → `/synthesis` (POST)
   - `/search/{query}` → `/words/search/{query}`
   - `/definitions/{word}/...` → `/definitions/{id}/regenerate`

2. **Update Response Handling**
   - Unwrap data from ResourceResponse
   - Handle new pagination format
   - Parse new error structure

3. **Add Field Selection**
   - Use query parameters for optimization
   - Implement expand for related data

4. **Implement Caching**
   - Store and send ETags
   - Handle 304 responses
   - Respect cache headers
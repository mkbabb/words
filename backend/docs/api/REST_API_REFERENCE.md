# Floridify REST API Reference

## Overview

The Floridify API provides comprehensive dictionary and word management functionality with AI-enhanced features. The API follows RESTful principles and uses JSON for request and response payloads.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

Currently, the API is open and does not require authentication.

## Common Response Formats

### Resource Response
```json
{
  "data": { ... },
  "metadata": { ... },
  "links": {
    "self": "/resource/{id}",
    "related": "/resource/{id}/related"
  }
}
```

### List Response
```json
{
  "items": [ ... ],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

### Error Response
```json
{
  "detail": "Error message",
  "errors": [
    {
      "field": "field_name",
      "message": "Validation error"
    }
  ]
}
```

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response 200**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T12:00:00Z",
  "version": "0.1.0",
  "services": {
    "database": "connected",
    "cache": "connected"
  }
}
```

### Words

#### GET /api/v1/words
List all words with pagination.

**Query Parameters**:
- `offset` (int): Skip first N results (default: 0)
- `limit` (int): Maximum results (default: 20, max: 100)
- `sort_by` (string): Sort field (default: "created_at")
- `sort_order` (string): "asc" or "desc" (default: "desc")
- `language` (string): Filter by language
- `part_of_speech` (string): Filter by part of speech
- `provider` (string): Filter by provider

**Response 200**: `ListResponse[Word]`

#### POST /api/v1/words
Create a new word entry.

**Request Body**:
```json
{
  "word": "example",
  "language": "en",
  "part_of_speech": "noun"
}
```

**Response 201**: `ResourceResponse`

#### GET /api/v1/words/{word_id}
Get word details by ID.

**Response 200**: `ResourceResponse`

#### PATCH /api/v1/words/{word_id}
Update word metadata.

**Request Body**:
```json
{
  "metadata": {
    "tags": ["common", "formal"]
  }
}
```

**Response 200**: `ResourceResponse`

#### DELETE /api/v1/words/{word_id}
Delete a word entry.

**Response 204**: No content

### Definitions

#### GET /api/v1/definitions
List definitions with filtering.

**Query Parameters**:
- `word_id` (string): Filter by word ID
- `part_of_speech` (string): Filter by part of speech
- `provider` (string): Filter by provider
- `language` (string): Filter by language
- `offset` (int): Pagination offset
- `limit` (int): Pagination limit

**Response 200**: `ListResponse[Definition]`

#### POST /api/v1/definitions
Create a new definition.

**Request Body**:
```json
{
  "word_id": "word_123",
  "part_of_speech": "noun",
  "text": "An example or instance",
  "provider": "wiktionary"
}
```

**Response 201**: `ResourceResponse`

#### GET /api/v1/definitions/{definition_id}
Get definition details.

**Response 200**: `ResourceResponse`

#### PATCH /api/v1/definitions/{definition_id}
Update definition.

**Response 200**: `ResourceResponse`

#### DELETE /api/v1/definitions/{definition_id}
Delete definition.

**Response 204**: No content

### Examples

#### GET /api/v1/examples
List usage examples.

**Query Parameters**:
- `word_id` (string): Filter by word
- `definition_id` (string): Filter by definition
- `provider` (string): Filter by source
- Standard pagination parameters

**Response 200**: `ListResponse[Example]`

#### POST /api/v1/examples
Create usage example.

**Request Body**:
```json
{
  "definition_id": "def_123",
  "text": "This is an example sentence.",
  "translation": "Optional translation"
}
```

**Response 201**: `ResourceResponse`

### Word Lookup

#### GET /api/v1/lookup/{word}
Comprehensive word lookup with AI synthesis.

**Query Parameters**:
- `force_refresh` (bool): Force cache refresh
- `providers` (array): Dictionary providers to use
- `languages` (array): Languages to query
- `no_ai` (bool): Skip AI synthesis

**Response 200**:
```json
{
  "word": "example",
  "pronunciation": { ... },
  "definitions": [ ... ],
  "etymology": { ... },
  "last_updated": "2025-07-29T12:00:00Z",
  "metadata": { ... }
}
```

#### GET /api/v1/lookup/{word}/stream
Stream lookup results as Server-Sent Events.

**Response**: SSE stream

### Search

#### GET /api/v1/search/{query}
Multi-method word search.

**Query Parameters**:
- `language` (string): Search language (default: "en")
- `max_results` (int): Maximum results (default: 20)
- `min_score` (float): Minimum relevance score (0-1, default: 0.6)

**Response 200**:
```json
{
  "query": "exampl",
  "results": [
    {
      "word": "example",
      "score": 0.95,
      "method": "fuzzy",
      "is_phrase": false
    }
  ],
  "total_found": 15,
  "language": "en",
  "metadata": { ... }
}
```

### AI Features

#### POST /api/v1/ai/synthesize
Synthesize definitions using AI.

**Request Body**:
```json
{
  "word": "example",
  "definitions": [ ... ],
  "options": {
    "style": "concise",
    "max_clusters": 5
  }
}
```

**Response 200**: Synthesized definitions

#### POST /api/v1/ai/extract-meanings
Extract semantic meanings from definitions.

**Request Body**:
```json
{
  "definitions": [ ... ]
}
```

**Response 200**: Meaning clusters

#### GET /api/v1/suggestions/{query}
Get word suggestions.

**Query Parameters**:
- `limit` (int): Maximum suggestions (default: 10)

**Response 200**: `ListResponse[Suggestion]`

### Word Lists

#### GET /api/v1/wordlists
List user word lists.

**Query Parameters**:
- `name_pattern` (string): Name search pattern
- `owner_id` (string): Filter by owner
- `is_public` (bool): Filter by visibility
- `has_tag` (string): Filter by tag
- `min_words` (int): Minimum word count
- `max_words` (int): Maximum word count
- Standard pagination parameters

**Response 200**: `ListResponse[WordList]`

#### POST /api/v1/wordlists
Create word list.

**Request Body**:
```json
{
  "name": "My Word List",
  "description": "Description",
  "is_public": false,
  "tags": ["study", "english"],
  "words": ["example", "test"]
}
```

**Response 201**: `ResourceResponse`

#### GET /api/v1/wordlists/{wordlist_id}
Get word list details with statistics.

**Response 200**: `ResourceResponse` with statistics

#### PUT /api/v1/wordlists/{wordlist_id}
Update word list metadata.

**Response 200**: `ResourceResponse`

#### DELETE /api/v1/wordlists/{wordlist_id}
Delete word list.

**Response 204**: No content

#### POST /api/v1/wordlists/upload
Upload word list from file.

**Form Data**:
- `file`: Text file with words (one per line)
- `name` (string): Optional list name
- `description` (string): Optional description
- `is_public` (bool): Visibility (default: false)

**Response 201**: `ResourceResponse`

### Word List Words

#### GET /api/v1/wordlists/{wordlist_id}/words
List words in a word list.

**Query Parameters**:
- `mastery_level` (string): Filter by mastery level
- `min_views` (int): Minimum view count
- `max_views` (int): Maximum view count
- `reviewed` (bool): Filter reviewed/unreviewed
- `sort_by` (string): Sort field
- Standard pagination parameters

**Response 200**: `ListResponse[WordListWord]`

#### POST /api/v1/wordlists/{wordlist_id}/words
Add word to list.

**Request Body**:
```json
{
  "word": "example",
  "notes": "Optional notes"
}
```

**Response 201**: `ResourceResponse`

#### DELETE /api/v1/wordlists/{wordlist_id}/words/{word}
Remove word from list.

**Response 204**: No content

### Word List Reviews

#### GET /api/v1/wordlists/{wordlist_id}/review/due
Get words due for review.

**Query Parameters**:
- `limit` (int): Maximum words (default: 20)

**Response 200**: `ListResponse[ReviewWord]`

#### GET /api/v1/wordlists/{wordlist_id}/review/session
Get review session.

**Query Parameters**:
- `limit` (int): Maximum words in session
- `mastery_threshold` (string): Maximum mastery level to include

**Response 200**: Review session data

#### POST /api/v1/wordlists/{wordlist_id}/review
Submit word review.

**Request Body**:
```json
{
  "word": "example",
  "mastery_level": "familiar",
  "quality_score": 0.8
}
```

**Response 200**: `ResourceResponse`

### Media

#### GET /api/v1/images
List images with filtering.

**Query Parameters**:
- `word_id` (string): Filter by word
- `definition_id` (string): Filter by definition
- `source_type` (string): Filter by source
- Standard pagination parameters

**Response 200**: `ListResponse[ImageMedia]`

#### POST /api/v1/images
Create image entry.

**Request Body**:
```json
{
  "url": "https://example.com/image.jpg",
  "word_id": "word_123",
  "alt_text": "Example image",
  "source": "wikipedia"
}
```

**Response 201**: `ResourceResponse`

#### GET /api/v1/images/{image_id}
Get image details.

**Response 200**: `ResourceResponse`

#### PUT /api/v1/images/{image_id}
Update image.

**Response 200**: `ResourceResponse`

#### DELETE /api/v1/images/{image_id}
Delete image.

**Response 204**: No content

#### GET /api/v1/audio
List audio files.

Similar to images endpoint with audio-specific filters.

#### POST /api/v1/audio/generate/{word}
Generate audio pronunciation.

**Response 200**: Audio file URL

### Batch Operations

#### POST /api/v1/batch/lookup
Batch word lookup.

**Request Body**:
```json
{
  "words": ["example", "test", "word"],
  "providers": ["wiktionary"],
  "force_refresh": false
}
```

**Response 200**: Batch results

### Corpus Management

#### POST /api/v1/corpus
Create temporary word corpus.

**Request Body**:
```json
{
  "words": ["example", "test"],
  "phrases": ["example phrase"],
  "name": "Study List",
  "ttl_hours": 1.0
}
```

**Response 201**: Corpus ID and metadata

#### GET /api/v1/corpus/{corpus_id}
Get corpus info.

**Response 200**: Corpus metadata

#### POST /api/v1/corpus/{corpus_id}/search
Search within corpus.

**Request Body**:
```json
{
  "query": "exam",
  "max_results": 20,
  "min_score": 0.6
}
```

**Response 200**: Search results

## Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success with no response body
- `400 Bad Request`: Invalid request
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Rate Limiting

Currently no rate limiting is implemented.

## Changelog

### v1.0.0 (2025-07-29)
- Initial API release
- Reorganized routers into modular structure
- Added full CRUD for images and audio
- Refactored wordlists API for modularity
- Consistent pagination across all list endpoints
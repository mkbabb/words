# API Endpoints

## Words

```
GET    /api/v2/words/{word_id}
POST   /api/v2/words                      # Create new word
PATCH  /api/v2/words/{word_id}           # Update metadata
DELETE /api/v2/words/{word_id}           # Remove word and all data

# Word forms
GET    /api/v2/words/{word_id}/forms
POST   /api/v2/words/{word_id}/forms     # Add inflection/variant
```

## Synthesized Entries

```
GET    /api/v2/synthesized/{word_id}
POST   /api/v2/synthesized/{word_id}     # Create new synthesis
PATCH  /api/v2/synthesized/{id}          # Update synthesis metadata
DELETE /api/v2/synthesized/{id}

# Regeneration
POST   /api/v2/synthesized/{id}/regenerate
Body:  {"components": ["definitions", "examples", "facts", "pronunciation"]}
```

## Definitions

```
GET    /api/v2/definitions/{id}
POST   /api/v2/definitions                # Create definition
PATCH  /api/v2/definitions/{id}          # Update any field
DELETE /api/v2/definitions/{id}

# Batch operations
PATCH  /api/v2/definitions/batch
Body:  [{"id": "def1", "text": "new text"}, {"id": "def2", "synonyms": ["word1", "word2"]}]
```

## Examples

```
GET    /api/v2/examples/{id}
POST   /api/v2/examples                   # Create example
PATCH  /api/v2/examples/{id}             # Update example
DELETE /api/v2/examples/{id}

# Regenerate AI examples
POST   /api/v2/examples/{id}/regenerate
Body:  {"context": "user prompt", "style": "formal"}

# Bulk create
POST   /api/v2/examples/bulk
Body:  [{"definition_id": "def1", "text": "...", "type": "generated"}]
```

## Pronunciations

```
GET    /api/v2/pronunciations/{id}
POST   /api/v2/pronunciations             # Create pronunciation
PATCH  /api/v2/pronunciations/{id}        # Update pronunciation
DELETE /api/v2/pronunciations/{id}

# Add audio
POST   /api/v2/pronunciations/{id}/audio
Body:  {"url": "...", "accent": "us", "format": "mp3"}
```

## Facts

```
GET    /api/v2/facts/{id}
POST   /api/v2/facts                      # Create fact
PATCH  /api/v2/facts/{id}                # Update fact
DELETE /api/v2/facts/{id}

# Generate facts
POST   /api/v2/facts/generate
Body:  {"word_id": "...", "categories": ["etymology", "usage"], "count": 3}
```

## Provider Data

```
GET    /api/v2/providers/{id}
POST   /api/v2/providers                  # Store provider data
PATCH  /api/v2/providers/{id}            # Update provider data
DELETE /api/v2/providers/{id}

# Refresh from provider
POST   /api/v2/providers/{id}/refresh
Body:  {"force": true}

# Bulk sync
POST   /api/v2/providers/sync
Body:  {"word_ids": ["word1", "word2"], "providers": ["oxford", "wiktionary"]}
```

## Media

```
# Images
GET    /api/v2/images/{id}
POST   /api/v2/images                     # Upload image
DELETE /api/v2/images/{id}

# Audio
GET    /api/v2/audio/{id}
POST   /api/v2/audio                      # Upload audio
DELETE /api/v2/audio/{id}
```

## Search & Lookup

```
GET    /api/v2/search?q={query}&method={exact|fuzzy|semantic}
POST   /api/v2/lookup/{word}              # Full lookup with synthesis
```

## Phrasal Expressions

```
GET    /api/v2/phrasal/{id}
POST   /api/v2/phrasal                    # Create phrasal verb/idiom
PATCH  /api/v2/phrasal/{id}              # Update expression
DELETE /api/v2/phrasal/{id}

# Find by base word
GET    /api/v2/words/{word_id}/phrasal
```

## Word Relationships

```
GET    /api/v2/relationships/{word_id}?type={synonym|antonym|related}
POST   /api/v2/relationships             # Create relationship
DELETE /api/v2/relationships/{id}
```

## Collocations

```
GET    /api/v2/words/{word_id}/collocations
POST   /api/v2/definitions/{id}/collocations
Body:  {"text": "strong coffee", "type": "adjective", "frequency": 0.8}
```

## Grammar Patterns

```
GET    /api/v2/definitions/{id}/grammar
PATCH  /api/v2/definitions/{id}/grammar
Body:  {"patterns": [{"pattern": "[Tn]", "description": "transitive + noun"}]}
```

## Batch Operations

```
POST   /api/v2/batch
Body:  {
  "operations": [
    {"method": "PATCH", "endpoint": "/definitions/{id}", "data": {...}},
    {"method": "POST", "endpoint": "/examples", "data": {...}},
    {"method": "DELETE", "endpoint": "/facts/{id}"}
  ]
}
```

## Common Query Parameters

- `fields`: Comma-separated field projection (e.g., `?fields=text,synonyms`)
- `expand`: Include related objects (e.g., `?expand=definitions,examples`)
- `version`: Specific version (e.g., `?version=3`)

## Headers

```
If-Match: "{version}"          # Optimistic locking
X-Regenerate: "true"          # Force regeneration
```

## Response Format

```json
{
  "data": {...},
  "meta": {
    "version": 1,
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

## Error Format

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Definition not found",
    "field": "id"
  }
}
```
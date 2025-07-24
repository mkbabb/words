# Floridify AI Regeneration API Design

## Overview

This document maps out all regeneration entry points for AI-synthesized components in the Floridify system. The regeneration system allows selective refresh of individual components without regenerating entire entries.

## Current Regeneration Capabilities

### 1. Component-Level Regeneration Functions

Located in `synthesis_functions.py`, these functions handle individual component synthesis:

#### Word-Level Components
- **`synthesize_pronunciation`**: Generate/regenerate pronunciation
- **`synthesize_etymology`**: Extract/regenerate etymology
- **`synthesize_word_forms`**: Generate word forms (plural, tense, etc.)
- **`generate_facts`**: Create interesting facts about words

#### Definition-Level Components
- **`synthesize_synonyms`**: Generate synonyms with efflorescence ranking
- **`synthesize_examples`**: Create contextual example sentences
- **`synthesize_antonyms`**: Generate antonyms
- **`assess_definition_cefr`**: Assess CEFR level (A1-C2)
- **`assess_definition_frequency`**: Determine frequency band (1-5)
- **`classify_definition_register`**: Classify language register
- **`identify_definition_domain`**: Identify specialized domain
- **`extract_grammar_patterns`**: Extract grammatical patterns
- **`identify_collocations`**: Find common word combinations
- **`generate_usage_notes`**: Create usage guidance
- **`detect_regional_variants`**: Identify regional variations

#### Synthesis Utilities
- **`synthesize_definition_text`**: Synthesize definition from clusters
- **`cluster_definitions`**: Group definitions by meaning

### 2. Batch Processing Functions

#### `enhance_definitions_parallel`
- Enhances multiple definitions with specified components in parallel
- Supports selective component regeneration via `components` parameter
- Handles `force_refresh` flag to regenerate existing data
- Tracks progress via `StateTracker`

#### `enhance_synthesized_entry`
- Enhances a complete synthesized entry
- Supports arbitrary component selection
- Handles both word-level and definition-level enhancements

### 3. Template-Based Prompt System

All AI operations use Jinja2 templates located in `/prompts/`:
- Each component has a dedicated prompt template
- Templates ensure consistent, high-quality AI responses
- Easy to modify prompts without changing code

## Existing API Endpoints

### Definition-Level Endpoints (`/api/v1/definitions/`)

1. **Update Definition Fields**
   - `PATCH /{word}/definitions/{index}`
   - Updates specific fields without AI regeneration

2. **Regenerate Examples**
   - `POST /{word}/definitions/{index}/examples/regenerate`
   - Regenerates example sentences with customizable parameters
   - Supports style (modern/formal/casual/technical) and context

3. **Generate Collocations**
   - `POST /{word}/definitions/{index}/collocations`
   - Generates common word combinations
   - Cached for 48 hours

4. **Generate Grammar Patterns**
   - `POST /{word}/definitions/{index}/grammar-patterns`
   - Extracts grammatical constructions
   - Cached for 48 hours

5. **Assess CEFR Level**
   - `POST /{word}/definitions/{index}/cefr-level`
   - Determines language proficiency level
   - Cached for 72 hours

6. **Generate Usage Notes**
   - `POST /{word}/definitions/{index}/usage-notes`
   - Creates usage guidance and warnings
   - Cached for 48 hours

## Proposed New API Endpoints

### 1. Component Regeneration Endpoint
```
POST /api/v1/synthesis/{word}/regenerate
```

**Request Body:**
```json
{
  "components": [
    "pronunciation",
    "etymology", 
    "facts",
    "synonyms",
    "examples",
    "antonyms",
    "cefr_level",
    "frequency_band",
    "register",
    "domain",
    "grammar_patterns",
    "collocations",
    "usage_notes",
    "regional_variants"
  ],
  "definition_indices": [0, 1],  // Optional: specific definitions to update
  "force": false,  // Force regeneration even if data exists
  "options": {
    "examples_count": 3,
    "facts_count": 5,
    "synonyms_count": 10
  }
}
```

**Response:**
```json
{
  "status": "success",
  "word": "serendipity",
  "regenerated": {
    "word_level": ["pronunciation", "facts"],
    "definition_level": {
      "0": ["synonyms", "examples"],
      "1": ["synonyms", "examples"]
    }
  },
  "errors": [],
  "entry_id": "..."
}
```

### 2. Batch Component Regeneration
```
POST /api/v1/synthesis/batch/regenerate
```

**Request Body:**
```json
{
  "words": ["serendipity", "ephemeral", "petrichor"],
  "components": ["examples", "synonyms"],
  "force": false
}
```

### 3. Provider Data Refresh
```
POST /api/v1/providers/{word}/refresh
```

**Request Body:**
```json
{
  "providers": ["wiktionary", "wordnik"],
  "cascade_synthesis": true  // Regenerate AI components after refresh
}
```

### 4. Component Status Endpoint
```
GET /api/v1/synthesis/{word}/status
```

**Response:**
```json
{
  "word": "serendipity",
  "components": {
    "pronunciation": {
      "exists": true,
      "last_generated": "2025-01-24T10:30:00Z",
      "model": "gpt-4o",
      "confidence": 0.95
    },
    "etymology": {
      "exists": true,
      "last_generated": "2025-01-24T10:30:00Z",
      "sources": ["wiktionary", "etymonline"]
    },
    "definitions": [
      {
        "index": 0,
        "components": {
          "synonyms": {"exists": true, "count": 10},
          "examples": {"exists": true, "count": 3},
          "antonyms": {"exists": false},
          "cefr_level": {"exists": true, "value": "C1"}
        }
      }
    ]
  }
}
```

### 5. Quality Assessment Endpoint
```
POST /api/v1/synthesis/{word}/assess-quality
```

**Response:**
```json
{
  "word": "serendipity",
  "quality_score": 0.85,
  "completeness": {
    "score": 0.9,
    "missing_components": ["antonyms", "regional_variants"]
  },
  "freshness": {
    "score": 0.8,
    "stale_components": ["examples"]
  },
  "recommendations": [
    "Regenerate examples (last updated 30 days ago)",
    "Add missing antonyms for definition 0"
  ]
}
```

## Implementation Strategy

### 1. Create Synthesis Router
Create `/api/routers/synthesis.py` with:
- Component regeneration endpoints
- Batch processing endpoints
- Status and quality assessment

### 2. Enhance Existing Functions
- Add progress tracking to all synthesis functions
- Implement proper error handling and rollback
- Add component-level caching with TTL

### 3. Add WebSocket Support
- Real-time progress updates during regeneration
- Stream results as components complete
- Handle long-running batch operations

### 4. Implement Rate Limiting
- Per-user rate limits for AI operations
- Priority queue for batch operations
- Cost tracking for OpenAI API usage

## Component Registry

All available components are registered in `SYNTHESIS_COMPONENTS`:

```python
SYNTHESIS_COMPONENTS = {
    # Word-level components
    "pronunciation": synthesize_pronunciation,
    "etymology": synthesize_etymology,
    "word_forms": synthesize_word_forms,
    "facts": generate_facts,
    
    # Definition-level components
    "synonyms": synthesize_synonyms,
    "examples": synthesize_examples,
    "antonyms": synthesize_antonyms,
    "cefr_level": assess_definition_cefr,
    "frequency_band": assess_definition_frequency,
    "register": classify_definition_register,
    "domain": identify_definition_domain,
    "grammar_patterns": extract_grammar_patterns,
    "collocations": identify_collocations,
    "usage_notes": generate_usage_notes,
    "regional_variants": detect_regional_variants,
    
    # Synthesis utilities
    "definition_text": synthesize_definition_text,
    "cluster_definitions": cluster_definitions,
}
```

## Error Handling

### Graceful Degradation
- If a component fails, log error but continue with others
- Return partial results with error details
- Never fail entire operation due to single component

### Rollback Strategy
- Track changes during regeneration
- Implement atomic updates where possible
- Provide rollback endpoint for reverting changes

## Caching Strategy

### Component-Level Caching
- Each component has independent cache TTL
- Examples: 24 hours
- CEFR levels: 72 hours
- Collocations: 48 hours

### Force Refresh Options
- `force`: Bypass all caches
- `force_components`: List of specific components to force refresh
- `max_age`: Only refresh components older than specified time

## Security Considerations

### Rate Limiting
- Implement per-user quotas
- Higher limits for authenticated users
- Exponential backoff for repeated requests

### Cost Control
- Track OpenAI API usage per user
- Implement daily/monthly limits
- Provide usage statistics endpoint

### Input Validation
- Validate component names against registry
- Limit batch sizes
- Sanitize user-provided context/options

## Future Enhancements

### 1. Component Dependencies
- Define dependencies between components
- Automatically regenerate dependent components
- Optimize regeneration order

### 2. Quality Metrics
- Track component quality scores
- Implement automatic quality checks
- Suggest regeneration based on quality

### 3. User Preferences
- Allow users to customize generation parameters
- Save preferred styles/counts
- Personalized component selection

### 4. A/B Testing
- Test different prompts/models
- Track user satisfaction
- Optimize based on feedback

## Conclusion

The regeneration system provides fine-grained control over AI-synthesized content, allowing selective updates without full regeneration. The modular design supports easy addition of new components and flexible API patterns for various use cases.
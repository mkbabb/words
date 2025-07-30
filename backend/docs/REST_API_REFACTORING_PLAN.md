# REST API Refactoring Plan

## Naming Convention Updates

### 1. Corpus Endpoints
- **Current**: `GET /corpus-stats`
- **Updated**: `GET /corpus/stats`

### 2. Word of the Day
- **Current**: All under `/word-of-the-day/*`
- **Updated**: Rename to `/wotd/*` for consistency

### 3. Synth Entries
- **Current**: `/synth-entries/*`
- **Updated**: `/synthesized-entries/*` (more descriptive)

### 4. Search Endpoints Consolidation
- **Remove**: `GET /words/search/{query}` (duplicate of main search)
- **Keep**: `GET /search` with query params

### 5. Resource Naming
- All resources should use plural forms consistently:
  - ✓ `/words`
  - ✓ `/definitions`
  - ✓ `/examples`
  - ✓ `/facts`
  - ✓ `/wordlists`
  - ✗ `/audio` → `/audio-files`
  - ✗ `/images` → `/image-files`

## Query Parameter Standardization

### Completed:
- ✓ definitions.py - DefinitionQueryParams
- ✓ examples.py - ExampleQueryParams
- ✓ facts.py - FactQueryParams
- ✓ words.py - WordQueryParams
- ✓ wordlists.py - WordListQueryParams (already exists)

### Remaining:
- corpus.py - needs query param models
- ai.py - needs standardized request/response models
- lookup.py - needs query param models

## Import Organization

### Completed:
- ✓ Moved all nested imports to top level
- ✓ Added missing imports (PIL, json, asyncio, etc.)

## Model Organization

### Completed:
- ✓ Moved SearchResultResponse to search.py
- ✓ Moved HealthCheckResponse to health.py
- ✓ Moved BatchOperationResponse to batch.py
- ✓ Removed unused models (AIGenerationResponse, etc.)

## Generic Updates

### Completed:
- ✓ Replaced bind_image_to_definition with generic PATCH endpoint
- ✓ Removed unused batch definition update

## Next Steps:
1. Update corpus-stats endpoint path
2. Standardize audio/images endpoint names
3. Remove duplicate search endpoints
4. Create missing query param models
# Frontend API Usage Analysis Report

## Overview
This report analyzes the frontend codebase to identify API usage patterns, type definitions, and potential mismatches between frontend expectations and backend responses.

## Key Findings

### 1. API Call Patterns

#### Main API Endpoints Used:
- `/api/v1/search` - Word search with fuzzy/semantic matching
- `/api/v1/lookup/{word}` - Get word definition (non-streaming)
- `/api/v1/lookup/{word}/stream` - Get word definition with SSE progress
- `/api/v1/ai/synthesize/synonyms` - Get AI-generated synonyms
- `/api/v1/suggestions` - Get vocabulary suggestions
- `/api/v1/lookup/{word}/regenerate-examples` - Regenerate examples for a definition
- `/api/v1/health` - Health check

#### API Parameters:
- **Search**: `q` (query), `max_results`, `min_score`
- **Lookup**: `force_refresh`, `providers[]`, `languages[]`
- **Suggestions**: `words[]`, `count`

### 2. Type Definitions vs API Usage

#### Example Type Mismatch Issue

**Frontend expects nested structure:**
```typescript
interface Definition {
  examples?: {
    generated: Example[];
    literature: Example[];
  };
}
```

**But API returns flat array:**
```json
{
  "examples": [
    { "type": "generated", "text": "...", ... },
    { "type": "literature", "text": "...", ... }
  ]
}
```

**Solution implemented:** `transformDefinitionExamples()` function transforms flat array to nested structure.

### 3. Data Transformation Points

#### api.ts transformations:
1. **Example transformation** (lines 84-122): Converts flat examples array to grouped structure
2. **Definition transformation** (lines 150-154): Applied to all definitions in response
3. **SSE result extraction** (line 220): Extracts result from `data.details?.result || data`

### 4. Type Safety Issues

#### Potential null/undefined access patterns found:
1. **Optional chaining used correctly:**
   - `entry.value?.word`
   - `entry.value?.definitions`
   - `definition.examples?.generated?.[0]`

2. **Areas with proper null checks:**
   - Provider extraction from source_attribution
   - Pronunciation data (`entry.pronunciation?.phonetic`)
   - Meaning cluster handling

### 5. Error Handling Patterns

#### Consistent error handling:
```typescript
try {
  // API call
} catch (error) {
  console.error('Context-specific error message', error);
  // Fallback behavior (empty arrays, default values)
}
```

#### Graceful degradation:
- Search returns empty array on error
- Synonyms fallback to empty thesaurus entry
- Suggestions fallback to recent lookup history

### 6. API Response Assumptions

#### Store (index.ts) assumptions:
1. **Definition response always has `definitions` array**
2. **Examples are pre-grouped** (after transformation)
3. **Streaming endpoint returns progress events** with `stage`, `progress`, `message`, `details`
4. **Complete event contains result** in `details.result` or root

#### Component assumptions:
1. **DefinitionDisplay.vue:**
   - Expects `meaning_cluster` with `id` and `name`
   - Expects `relevancy` score for sorting
   - Expects `source_attribution` for provider icons

2. **SearchBar.vue:**
   - Expects search results with `word`, `score`, `method`
   - Handles streaming with progress callback

### 7. Data Flow

1. **Search Flow:**
   ```
   SearchBar input → dictionaryApi.searchWord() → store.search() → SearchResult[]
   ```

2. **Definition Lookup Flow:**
   ```
   SearchBar enter/select → store.getDefinition() → dictionaryApi.getDefinitionStream()
   → SSE progress events → transform examples → store.currentEntry
   ```

3. **Regeneration Flow:**
   ```
   DefinitionDisplay regenerate → store.regenerateExamples() → dictionaryApi.regenerateExamples()
   → Update currentEntry.definitions[index].examples.generated
   ```

### 8. Streaming Implementation

**SSE Connection handling:**
- 5-second timeout for initial connection
- Progress events update loading state
- Complete event extracts result from `details.result`
- Error handling for connection loss

### 9. Caching and Persistence

**Persisted data:**
- UI state (mode, sources, languages, theme)
- Session state (current query, entry, thesaurus)
- Search/lookup history
- Suggestions cache (1-hour TTL)

**Cache invalidation:**
- Force refresh mode bypasses cache
- New word lookup refreshes suggestions
- Suggestions refresh on lookup history change

### 10. Type Mismatches Summary

1. **Examples structure** - Handled by transformation
2. **No explicit mismatches found** - Types align after transformations
3. **Defensive coding used** - Optional chaining, null checks, fallbacks

## Recommendations

1. **Type Generation**: Consider generating TypeScript types from backend OpenAPI/schemas
2. **Error Types**: Add typed error responses for better error handling
3. **Response Validation**: Add runtime validation for API responses
4. **Loading States**: Enhance loading progress granularity
5. **Offline Support**: Add service worker for caching API responses
6. **Type Guards**: Add type guard functions for API responses

## Conclusion

The frontend codebase demonstrates good defensive programming practices with proper null checks, error handling, and data transformations. The main area of complexity is the example transformation from flat to nested structure, which is handled correctly. No critical type mismatches were found that would cause runtime errors.
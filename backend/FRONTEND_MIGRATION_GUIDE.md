# Frontend Migration Guide

## Overview
This guide helps migrate the Floridify frontend to use the new API structure with minimal disruption.

## Breaking Changes

### 1. Response Structure Changes

#### Old Format
```typescript
// Direct data response
const definition: Definition = await api.getDefinition(word);
```

#### New Format
```typescript
// Wrapped in ResourceResponse
const response: ResourceResponse<Definition> = await api.getDefinition(id);
const definition = response.data;
```

### 2. Endpoint Changes

#### Word Operations
```typescript
// Old
GET /words/{word_id}
PATCH /words/{word_id}

// New
GET /words/{word_id}
PUT /words/{word_id}?version=1
```

#### Definition Operations
```typescript
// Old
GET /definitions/{word}/definitions/{index}
POST /definitions/{word}/definitions/{index}/examples/regenerate

// New  
GET /definitions/{definition_id}
POST /definitions/{definition_id}/regenerate
```

#### Synthesis (formerly Lookup)
```typescript
// Old
GET /lookup/{word}

// New
POST /synthesis
{
  "word": "example",
  "language": "english",
  "providers": ["oxford", "webster"]
}
```

## Type Updates

### 1. Update Base Types
```typescript
// types/api.ts
export interface ResourceResponse<T> {
  data: T;
  metadata?: Record<string, any>;
  links?: Record<string, string>;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface ErrorDetail {
  field?: string;
  message: string;
  code?: string;
}

export interface ErrorResponse {
  error: string;
  details?: ErrorDetail[];
  timestamp: string;
  request_id?: string;
}
```

### 2. Update API Client

```typescript
// utils/api.ts
import { ResourceResponse, ListResponse, ErrorResponse } from '@/types/api';

class DictionaryAPI {
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new APIError(error);
    }
    
    // Handle 304 Not Modified
    if (response.status === 304) {
      throw new NotModifiedError();
    }
    
    return response.json();
  }

  async searchWord(query: string, options?: SearchOptions): Promise<ListResponse<Word>> {
    const params = new URLSearchParams({
      limit: '10',
      ...options
    });
    
    const response = await fetch(`/api/words/search/${query}?${params}`);
    return this.handleResponse<ListResponse<Word>>(response);
  }

  async getDefinition(
    id: string, 
    options?: { include?: string[]; expand?: string[] }
  ): Promise<ResourceResponse<Definition>> {
    const params = new URLSearchParams();
    
    if (options?.include) {
      params.set('include', options.include.join(','));
    }
    
    if (options?.expand) {
      params.set('expand', options.expand.join(','));
    }
    
    const response = await fetch(`/api/definitions/${id}?${params}`);
    return this.handleResponse<ResourceResponse<Definition>>(response);
  }

  async synthesizeWord(word: string, options?: SynthesisOptions): Promise<ResourceResponse<SynthesizedEntry>> {
    const response = await fetch('/api/synthesis', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        word,
        language: options?.language || 'english',
        providers: options?.providers || ['oxford', 'webster'],
        force_refresh: options?.forceRefresh || false,
      }),
    });
    
    return this.handleResponse<ResourceResponse<SynthesizedEntry>>(response);
  }

  async regenerateComponents(
    definitionId: string,
    components: string[]
  ): Promise<ResourceResponse<Definition>> {
    const response = await fetch(`/api/definitions/${definitionId}/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        components,
        force: false,
      }),
    });
    
    return this.handleResponse<ResourceResponse<Definition>>(response);
  }
}
```

### 3. Update Store Actions

```typescript
// stores/index.ts
export const useAppStore = defineStore('app', {
  actions: {
    async searchWord(query: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await dictionaryApi.searchWord(query);
        this.searchResults = response.items; // Extract items from ListResponse
        this.totalResults = response.total;
      } catch (error) {
        if (error instanceof APIError) {
          this.error = error.response.error;
          console.error('API Error:', error.response.details);
        } else {
          this.error = 'Search failed';
        }
      } finally {
        this.loading = false;
      }
    },

    async getDefinition(wordText: string, forceRefresh = false) {
      this.loading = true;
      this.error = null;
      
      try {
        // Use synthesis endpoint instead of lookup
        const response = await dictionaryApi.synthesizeWord(wordText, {
          forceRefresh,
          providers: this.selectedProviders,
        });
        
        this.currentDefinition = response.data;
        
        // Store metadata
        this.definitionMetadata = response.metadata;
        
        // Update cache with ETag
        if (response.headers?.etag) {
          this.etagCache[wordText] = response.headers.etag;
        }
      } catch (error) {
        if (error instanceof NotModifiedError) {
          // Use cached data
          return;
        }
        
        this.error = 'Failed to load definition';
      } finally {
        this.loading = false;
      }
    },

    async regenerateExamples(definitionId: string) {
      try {
        const response = await dictionaryApi.regenerateComponents(
          definitionId,
          ['examples']
        );
        
        // Update the specific definition in state
        const definition = response.data;
        this.updateDefinition(definitionId, definition);
        
        return definition;
      } catch (error) {
        console.error('Failed to regenerate examples:', error);
        throw error;
      }
    }
  }
});
```

## Component Updates

### 1. DefinitionDisplay.vue
```vue
<script setup lang="ts">
import { computed } from 'vue';
import type { Definition } from '@/types';

const props = defineProps<{
  definition: Definition;
  canRegenerate?: boolean;
}>();

const emit = defineEmits<{
  regenerate: [components: string[]];
}>();

// Handle component regeneration
const handleRegenerateExamples = async () => {
  emit('regenerate', ['examples']);
};

const handleRegenerateSynonyms = async () => {
  emit('regenerate', ['synonyms', 'antonyms']);
};

// Use optional chaining for new fields
const cefrLevel = computed(() => props.definition.cefr_level || 'Unknown');
const frequencyBand = computed(() => props.definition.frequency_band || null);
</script>
```

### 2. SearchBar.vue
```vue
<script setup lang="ts">
const searchWord = async () => {
  if (!searchQuery.value.trim()) return;
  
  const response = await store.searchWord(searchQuery.value);
  
  // Response is now wrapped in ListResponse
  if (response && response.items.length > 0) {
    // Navigate or display results
    await router.push(`/word/${response.items[0].text}`);
  }
};
</script>
```

## Caching Strategy

### 1. Implement ETag Support
```typescript
class CacheManager {
  private etags: Map<string, string> = new Map();
  
  async fetchWithETag(url: string, options?: RequestInit): Promise<Response> {
    const etag = this.etags.get(url);
    
    const headers = new Headers(options?.headers);
    if (etag) {
      headers.set('If-None-Match', etag);
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    // Store new ETag
    const newEtag = response.headers.get('ETag');
    if (newEtag) {
      this.etags.set(url, newEtag);
    }
    
    return response;
  }
}
```

### 2. Handle 304 Responses
```typescript
if (response.status === 304) {
  // Use cached data
  const cached = this.cache.get(cacheKey);
  if (cached) {
    return cached;
  }
}
```

## Performance Optimizations

### 1. Use Field Selection
```typescript
// Only fetch needed fields
const response = await api.getWord(wordId, {
  include: ['text', 'language', 'definitions'],
  exclude: ['created_at', 'updated_at'],
});
```

### 2. Implement Pagination
```typescript
const loadMoreResults = async () => {
  const response = await api.listWords({
    offset: currentOffset,
    limit: 20,
    filter: currentFilter,
  });
  
  results.value.push(...response.items);
  hasMore.value = response.has_more;
  currentOffset += response.items.length;
};
```

### 3. Batch Operations
```typescript
// Update multiple definitions at once
const response = await api.batchUpdate('/batch/v2/definitions/update', {
  updates: definitions.map(def => ({
    id: def.id,
    quality_score: calculateScore(def),
  })),
});
```

## Testing Migration

### 1. Update API Mocks
```typescript
// Mock new response format
vi.mock('@/utils/api', () => ({
  dictionaryApi: {
    searchWord: vi.fn().mockResolvedValue({
      items: [mockWord],
      total: 1,
      offset: 0,
      limit: 20,
      has_more: false,
    }),
    
    synthesizeWord: vi.fn().mockResolvedValue({
      data: mockSynthesizedEntry,
      metadata: { version: 1 },
      links: { self: '/synthesis/123' },
    }),
  },
}));
```

### 2. Update Test Assertions
```typescript
// Old
expect(result).toEqual(mockDefinition);

// New
expect(result.data).toEqual(mockDefinition);
expect(result.metadata).toBeDefined();
```

## Rollout Strategy

### Phase 1: Type Updates
1. Add new type definitions
2. Update API client with backward compatibility
3. Deploy type changes

### Phase 2: Endpoint Migration
1. Update one endpoint at a time
2. Test thoroughly
3. Monitor for errors

### Phase 3: Feature Adoption
1. Implement field selection
2. Add component regeneration UI
3. Enable batch operations

### Phase 4: Cleanup
1. Remove legacy code
2. Update documentation
3. Final testing

## Common Issues and Solutions

### Issue: Undefined data property
```typescript
// Problem
const word = response.text; // undefined

// Solution
const word = response.data.text;
```

### Issue: Missing pagination info
```typescript
// Problem
const hasMore = results.length < total; // total undefined

// Solution
const hasMore = response.has_more;
```

### Issue: Component regeneration fails
```typescript
// Problem
await api.regenerateExamples(word, index);

// Solution
await api.regenerateComponents(definitionId, ['examples']);
```

## Support

For questions or issues during migration:
1. Check API documentation
2. Review error details in responses
3. Enable debug logging
4. Contact backend team
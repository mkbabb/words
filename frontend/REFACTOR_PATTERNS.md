# Frontend Refactoring Implementation Patterns

## Component Extraction Pattern

### Before (Monolithic)
```vue
<!-- SearchBar.vue (740 lines) -->
<template>
  <div class="search-container">
    <!-- 200 lines of template -->
    <input v-model="query" @keydown.enter="handleSearch" />
    <div v-if="showControls">
      <!-- 150 lines of controls -->
    </div>
    <div v-if="showResults">
      <!-- 100 lines of results -->
    </div>
  </div>
</template>

<script setup lang="ts">
// 300 lines of logic
</script>
```

### After (Modular)
```vue
<!-- SearchBar.vue (100 lines) -->
<template>
  <div class="search-container">
    <SearchInput 
      v-model="query"
      @search="handleSearch"
    />
    <SearchControls 
      v-if="showControls"
      :mode="mode"
    />
    <SearchResults 
      v-if="showResults"
      :results="results"
    />
  </div>
</template>

<script setup lang="ts">
const { query, results, mode } = useSearchContext()
const handleSearch = () => searchService.search(query.value, mode.value)
</script>
```

## Store Consolidation Pattern

### Before (Multiple Stores)
```typescript
// search-bar.ts
const useSearchBarStore = defineStore('searchBar', () => {
  const searchMode = ref('lookup')
  const searchQuery = ref('')
  // Delegates to mode stores
})

// content.ts  
const useContentStore = defineStore('content', () => {
  // Delegates to mode content stores
})

// modes/lookup.ts
const useLookupMode = defineStore('lookupMode', () => {
  const results = ref([])
  const selectedSources = ref([])
})
```

### After (Unified Store)
```typescript
// search.ts
const useSearchStore = defineStore('search', () => {
  // Direct state management
  const mode = ref<SearchMode>('lookup')
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const currentEntry = ref<Entry | null>(null)
  
  // Direct actions
  const search = async (q: string) => {
    results.value = await searchService.search(q, mode.value)
  }
  
  return { mode, query, results, currentEntry, search }
})
```

## API Client Pattern

### Before (Mixed Concerns)
```typescript
// api/dictionary.ts
export const dictionaryApi = {
  async search(query: string) { /* ... */ },
  async searchByPath(query: string) { /* ... */ },
  async lookup(word: string) { /* ... */ },
  async lookupStream(word: string, options) { 
    // 200 lines of SSE handling
  },
  // 10+ more methods
}
```

### After (Focused Clients)
```typescript
// api/clients/SearchClient.ts
export class SearchClient {
  constructor(private http: AxiosInstance, private sse: SSEClient) {}
  
  async search(query: string, options?: SearchOptions): Promise<SearchResult[]> {
    const { data } = await this.http.get('/search', { params: { q: query, ...options } })
    return data.results
  }
}

// api/clients/LookupClient.ts
export class LookupClient {
  constructor(private http: AxiosInstance, private sse: SSEClient) {}
  
  async lookup(word: string): Promise<Entry> {
    const { data } = await this.http.get(`/lookup/${word}`)
    return data.entry
  }
  
  async stream(word: string, handlers: StreamHandlers): Promise<Entry> {
    return this.sse.stream(`/lookup/${word}/stream`, handlers)
  }
}
```

## Service Layer Pattern

### Before (Direct API Calls)
```vue
<script setup lang="ts">
import { dictionaryApi } from '@/api'

const handleSearch = async () => {
  try {
    loading.value = true
    const results = await dictionaryApi.search(query.value)
    if (results.length === 0) {
      const generated = await dictionaryApi.generateEntry(query.value)
      results.push(generated)
    }
    store.setResults(results)
  } catch (error) {
    // Handle error
  } finally {
    loading.value = false
  }
}
</script>
```

### After (Service Layer)
```vue
<script setup lang="ts">
const lookupService = inject<LookupService>('lookupService')

const handleSearch = async () => {
  const result = await lookupService.performLookup(query.value, {
    fallbackToGeneration: true
  })
  // Service handles loading, errors, store updates
}
</script>
```

## Mode Component Pattern

### Before (Conditional Rendering)
```vue
<template>
  <div class="content">
    <div v-if="mode === 'lookup'">
      <!-- Lookup UI -->
    </div>
    <div v-else-if="mode === 'wordlist'">
      <!-- Wordlist UI -->
    </div>
    <div v-else-if="mode === 'stage'">
      <!-- Stage UI -->
    </div>
  </div>
</template>
```

### After (Dynamic Components)
```vue
<template>
  <component :is="modeComponent" v-bind="modeProps" />
</template>

<script setup lang="ts">
const modeComponents = {
  lookup: () => import('./modes/LookupMode.vue'),
  wordlist: () => import('./modes/WordlistMode.vue'),
  stage: () => import('./modes/StageMode.vue')
}

const modeComponent = computed(() => modeComponents[mode.value])
</script>
```

## Context Provider Pattern

### Before (Props Drilling)
```vue
<!-- Parent -->
<SearchBar 
  :mode="mode"
  :query="query"
  :results="results"
  @search="handleSearch"
  @mode-change="handleModeChange"
/>

<!-- Child -->
<SearchControls
  :mode="mode"
  :query="query"
  @search="$emit('search')"
/>

<!-- Grandchild -->
<LookupControls
  :query="query"
  @search="$emit('search')"
/>
```

### After (Context Injection)
```vue
<!-- Provider -->
<script setup lang="ts">
provide('search', {
  mode: readonly(mode),
  query: readonly(query),
  search: (q: string) => searchService.search(q)
})
</script>

<!-- Any descendant -->
<script setup lang="ts">
const { mode, query, search } = inject('search')
// Direct access, no props needed
</script>
```

## Edit Mode Pattern

### Before (Duplicate Components)
```vue
<!-- ExampleList.vue -->
<template>
  <ul>
    <li v-for="example in examples">{{ example }}</li>
  </ul>
</template>

<!-- ExampleListEditable.vue -->
<template>
  <ul>
    <li v-for="example in examples">
      <input v-model="example.text" />
    </li>
  </ul>
</template>
```

### After (Single Component)
```vue
<!-- Examples.vue -->
<template>
  <ul>
    <li v-for="example in examples">
      <span v-if="!editable">{{ example.text }}</span>
      <input v-else v-model="example.text" @blur="save" />
    </li>
  </ul>
</template>

<script setup lang="ts">
defineProps<{
  examples: Example[]
  editable?: boolean
}>()
</script>
```

## Performance Pattern

### Before (Render Everything)
```vue
<template>
  <div v-for="word in words" :key="word.id">
    <WordCard :word="word" />
  </div>
</template>
```

### After (Virtual Scrolling)
```vue
<template>
  <RecycleScroller
    :items="words"
    :item-size="120"
    key-field="id"
  >
    <template #default="{ item }">
      <WordCard :word="item" />
    </template>
  </RecycleScroller>
</template>
```

## Error Handling Pattern

### Before (Inline Try-Catch)
```typescript
const handleAction = async () => {
  try {
    loading.value = true
    const result = await api.doSomething()
    // Handle success
  } catch (error) {
    console.error(error)
    toast.error('Something went wrong')
  } finally {
    loading.value = false
  }
}
```

### After (Centralized Error Handler)
```typescript
// composables/useAsyncAction.ts
export function useAsyncAction<T>(
  action: () => Promise<T>,
  options?: AsyncOptions
) {
  const loading = ref(false)
  const error = ref<Error | null>(null)
  
  const execute = async () => {
    loading.value = true
    error.value = null
    
    try {
      const result = await action()
      options?.onSuccess?.(result)
      return result
    } catch (e) {
      error.value = e as Error
      errorHandler.handle(e, options?.context)
      options?.onError?.(e)
    } finally {
      loading.value = false
    }
  }
  
  return { execute, loading, error }
}

// Usage
const { execute: handleAction, loading } = useAsyncAction(
  () => api.doSomething(),
  { context: 'action_name' }
)
```

## Type Safety Pattern

### Before (Loose Types)
```typescript
const handleData = (data: any) => {
  store.setData(data.items || [])
}
```

### After (Type Guards)
```typescript
import { z } from 'zod'

const DataSchema = z.object({
  items: z.array(ItemSchema)
})

type Data = z.infer<typeof DataSchema>

const handleData = (data: unknown) => {
  const parsed = DataSchema.safeParse(data)
  if (!parsed.success) {
    throw new ValidationError('Invalid data', parsed.error)
  }
  store.setData(parsed.data.items)
}
```

## Testing Pattern

### Component Test
```typescript
// SearchInput.test.ts
describe('SearchInput', () => {
  it('emits search on enter', async () => {
    const wrapper = mount(SearchInput, {
      props: { modelValue: 'test' }
    })
    
    await wrapper.find('input').trigger('keydown.enter')
    
    expect(wrapper.emitted('search')).toBeTruthy()
    expect(wrapper.emitted('search')?.[0]).toEqual(['test'])
  })
})
```

### Store Test
```typescript
// search.test.ts
describe('SearchStore', () => {
  it('performs search', async () => {
    const store = useSearchStore()
    
    await store.search('test')
    
    expect(store.results).toHaveLength(3)
    expect(store.loading).toBe(false)
  })
})
```
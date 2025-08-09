# Frontend Refactoring Plans

## 🎯 Grand Architectural Plan

### Core Principles
- **Mode-First Architecture**: Each mode (lookup, wordlist, stage, wotd) becomes a first-class citizen with dedicated routes, stores, and components
- **Single Source of Truth**: One store per domain, one component per responsibility  
- **Server-Side Processing**: Move filtering, sorting, search to backend
- **Composable Components**: Small, focused components that compose into views
- **Isomorphic Types**: Mirror backend structure exactly

### Execution Order
1. API Layer → Service Layer → Store Consolidation
2. Component Decomposition → Mode Separation  
3. Performance Optimization → Type Harmonization

---

## 📦 Component Architecture Plan

### Route Restructure
```
/routes
  ├── LookupRoute.vue      # /lookup/:word?
  ├── WordlistRoute.vue    # /wordlist/:id
  ├── StageRoute.vue       # /stage
  └── WotdRoute.vue        # /word-of-the-day
```

### Home.vue Becomes App.vue
```vue
<template>
  <AppLayout>
    <RouterView />
  </AppLayout>
</template>
<!-- 50 lines max -->
```

### Extract Layout Components
- `AppLayout.vue` - Shell with sidebar slot
- `ModeProvider.vue` - Provide/inject mode context
- `ContentArea.vue` - Main content wrapper

---

## 🔍 SearchBar Modularization Plan

### Component Hierarchy
```
SearchBar.vue (100 lines)
├── SearchInput.vue
├── SearchControls/
│   ├── index.vue (router)
│   ├── LookupControls.vue
│   ├── WordlistControls.vue
│   └── shared/
│       ├── SourceSelector.vue
│       └── FilterBuilder.vue
└── SearchResults.vue
```

### Context System
```typescript
// useSearchContext.ts
const context = {
  mode: readonly(mode),
  query: readonly(query),
  results: readonly(results),
  execute: (q: string) => api.search(q, mode.value)
}
provide('search', context)
```

### Control Components
- Each mode gets dedicated controls
- Controls compose from shared primitives
- No v-if chains, use dynamic components

---

## 🗄️ Store Consolidation Plan

### New Store Architecture
```
stores/
├── search.ts       # Unified search + content
├── ui.ts          # Theme, sidebar only  
├── history.ts     # Keep as-is
└── modes/
    ├── lookup.ts   # Config only
    └── wordlist.ts # Config only
```

### SearchStore Unification
```typescript
const useSearchStore = defineStore('search', () => {
  // Mode state
  const mode = ref<'lookup'|'wordlist'|'stage'|'wotd'>('lookup')
  const query = ref('')
  
  // Content state  
  const currentEntry = ref<Entry | null>(null)
  const results = ref<SearchResult[]>([])
  
  // One search method
  const search = async (q: string) => {
    const handler = modeHandlers[mode.value]
    results.value = await handler.search(q)
  }
})
```

### Delete ContentStore
- Move content to SearchStore
- Move mode delegation to route components

---

## 📐 Sidebar Unification Plan  

### Single Sidebar System
```
sidebar/
├── Sidebar.vue           # Main container
├── SidebarMode.vue       # Mode router
├── modes/
│   ├── LookupSidebar.vue
│   └── WordlistSidebar.vue  
└── ProgressiveSidebar.vue # Simplified
```

### Context-Aware Logic
```typescript
// useSidebarContext.ts
const shouldShow = computed(() => ({
  main: true,
  progressive: mode === 'lookup' && hasContent
}))
```

### Progressive Sidebar Simplification
- Remove complex composables
- Direct scroll-to-element implementation
- 50% code reduction

---

## 📖 Definition Display Decomposition Plan

### Component Hierarchy
```
DefinitionContainer.vue (100 lines)
├── DefinitionHeader.vue
├── DefinitionContent.vue
│   ├── ClusterList.vue
│   │   └── Cluster.vue
│   │       └── Definition.vue
│   │           ├── DefinitionText.vue
│   │           ├── Examples.vue
│   │           └── Synonyms.vue
└── DefinitionActions.vue
```

### Unified Edit Mode
```vue
<!-- Single component with mode prop -->
<Examples 
  :items="examples"
  :editable="editMode"
  @update="handleUpdate"
/>
```

### Extract Skeletons
```vue
<DefinitionSkeleton v-if="loading" />
<DefinitionContent v-else :entry="entry" />
```

---

## 📚 WordList Mode Separation Plan

### Mode Components
```
wordlist/
├── WordlistContainer.vue
├── modes/
│   ├── OverviewMode.vue
│   │   ├── StatsCards.vue
│   │   └── ProgressChart.vue
│   └── LearnMode.vue
│       ├── ReviewQueue.vue
│       └── StudyCard.vue
```

### Server-Side Processing
```typescript
// Move to API
interface WordlistQuery {
  filters: Filters
  sort: SortCriteria[]
  pagination: { offset: number, limit: number }
}

// Client just displays
const { data } = useQuery(['wordlist', query])
```

### Virtual Scrolling
```vue
<RecycleScroller
  :items="words"
  :item-size="120"
>
  <template #default="{ item }">
    <WordCard :word="item" />
  </template>
</RecycleScroller>
```

---

## 🔌 API Layer Simplification Plan

### Unified SSE Client
```typescript
class SSEClient {
  stream<T>(url: string, handlers: Handlers): Promise<T>
}
```

### Focused API Clients
```typescript
// One client per domain
const lookupClient = new LookupClient(axios)
const searchClient = new SearchClient(axios)  
const wordlistClient = new WordlistClient(axios)
```

### Service Layer
```typescript
// Business logic here, not in API
class LookupService {
  async lookup(word: string, options: Options) {
    // Orchestration logic
    const results = await searchClient.search(word)
    if (!results.length) {
      return lookupClient.generate(word, options)
    }
    return lookupClient.get(results[0].id)
  }
}
```

---

## ⚡ Performance Optimization Plan

### Lazy Loading
```typescript
// Route-level splitting
const LookupRoute = () => import('./routes/LookupRoute.vue')
const WordlistRoute = () => import('./routes/WordlistRoute.vue')
```

### Virtual Lists
- RecycleScroller for wordlists
- Virtual scrolling for search results
- Intersection observer for progressive loading

### Optimized Reactivity
```typescript
// Shallow refs for arrays
const words = shallowRef<Word[]>([])

// Computed caching
const filtered = computed(() => {
  // Cache key includes filter state
  return cache.get(filterKey) || computeFiltered()
})
```

---

## 🔄 Type System Harmonization Plan

### Mirror Backend Types
```typescript
// types/api.ts - Exact backend match
interface DictionaryEntry {
  word: string
  clusters: DefinitionCluster[]
  // Exactly as backend defines
}
```

### Shared Type Definitions
```typescript
// types/shared.ts
export * from '@floridify/shared/types'
```

### Type Guards Everywhere
```typescript
// Every API response validated
const isEntry = (x: unknown): x is Entry => {
  return z.object({
    word: z.string(),
    clusters: z.array(ClusterSchema)
  }).safeParse(x).success
}
```

---

## Implementation Notes

- **No Breaking Changes**: All refactors maintain existing functionality
- **Incremental Migration**: Each plan executable independently
- **Testing First**: Write tests before refactoring
- **Performance Metrics**: Measure before/after each change
- **Type Safety**: Never use `any`, always explicit types
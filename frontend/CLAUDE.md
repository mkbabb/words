# Floridify Frontend - Vue 3 TypeScript SPA

**Modern Vue 3.5.17 application** with TypeScript strict mode, Pinia state management, shadcn/ui components, and Tailwind CSS.

## Architecture

**Stack**: Vue 3 Composition API + TypeScript 5.8.3 + Pinia 3.0.3 + Vite 7.0.3
**UI**: shadcn/ui (123 components) + Tailwind CSS 4.1.11 + Radix Vue primitives
**State**: Mode-based Pinia stores with localStorage persistence
**API**: Axios client with SSE streaming support

## Directory Structure

```
src/
├── components/          # 173 total components
│   ├── ui/             # 123 shadcn/ui components (Radix Vue-based)
│   │   ├── accordion/, alert/, button/, card/, dialog/, ...
│   │   └── ... (comprehensive accessible component library)
│   └── custom/         # 50 application-specific components
│       ├── search/     # Search bar and functionality
│       │   ├── SearchBar.vue (500+ lines, mode-aware)
│       │   ├── components/  # Autocomplete, results, input
│       │   ├── composables/ # useSearchOrchestrator (411 lines)
│       │   ├── types/       # TypeScript interfaces
│       │   └── utils/       # Search utilities
│       ├── definition/  # Definition display system
│       │   ├── DefinitionDisplay.vue
│       │   ├── components/  # Clusters, items, images
│       │   ├── composables/ # Image management, providers
│       │   └── skeletons/   # Loading states
│       ├── wordlist/    # Wordlist management views
│       ├── sidebar/     # Navigation and progressive sidebar
│       ├── loading/     # Loading modals with progress
│       └── pwa/         # PWA install prompts
├── stores/              # 12 Pinia stores (mode-based delegation)
│   ├── index.ts        # Unified useStores() aggregator
│   ├── search/
│   │   ├── search-bar.ts (507 lines) # Main search state with mode delegation
│   │   └── modes/      # lookup.ts, wordlist.ts (mode-specific stores)
│   ├── content/
│   │   ├── content.ts (328 lines)  # Content display state
│   │   ├── history.ts (381 lines)  # Search/lookup history with caching
│   │   └── modes/      # lookup.ts, wordlist.ts
│   ├── ui/             # Theme, sidebar, loading states
│   ├── composables/    # useUIState, useNotifications, useRouterSync
│   ├── providers/      # State persistence (localStorage)
│   └── types/          # Mode types, constants
├── api/                 # API integration (10 modules)
│   ├── core.ts         # Axios instance, interceptors
│   ├── lookup.ts       # Word lookup (standard + streaming)
│   ├── search.ts       # Multi-method search
│   ├── ai.ts           # AI synthesis endpoints
│   ├── wordlists.ts    # Wordlist operations (288 lines)
│   └── sse/            # Server-Sent Events client (299 lines)
├── composables/         # 20+ reusable composables
│   ├── useSearchOrchestrator.ts (411 lines) # Central search logic
│   ├── useAutocomplete.ts      # Autocomplete functionality
│   ├── useIOSPWA.ts            # iOS PWA features
│   └── useTextureSystem.ts     # Paper texture management
├── types/               # TypeScript type definitions
│   ├── api.ts (360 lines)      # Isomorphic types (mirrors backend)
│   ├── index.ts (275 lines)    # Frontend-specific types
│   └── modes.ts                # Centralized mode types
├── router/              # Vue Router configuration
│   └── index.ts        # SPA routing with deep linking
├── assets/              # Styles and static assets
│   └── index.css       # Tailwind base + custom CSS variables
└── views/
    └── Home.vue        # Single-page application main view
```

## Key Design Principles

**Isomorphic Types**: Frontend TypeScript types (`types/api.ts`, 360 lines) mirror backend Pydantic models exactly—no drift, full type safety.

**Mode-Based State**: SearchBarStore delegates to mode-specific stores (lookup, wordlist, WOTD) with onEnter/onExit lifecycle hooks—no monolithic store.

**Composable-First**: Logic reuse through composables, not mixins. **No API calls in stores**—all network operations in `useSearchOrchestrator`.

**Component Isolation**: Each feature has own directory with components, composables, types, and utils—co-location of related functionality.

**Strict TypeScript**: 100% TypeScript strict mode, no `any` types, comprehensive type coverage across stack.

## Core Components

### 1. SearchBar (`components/custom/search/SearchBar.vue`)

**500+ lines** demonstrating complex stateful component:

**Features**:
- Mode-aware rendering (lookup, wordlist, word-of-the-day, stage)
- Autocomplete with keyboard navigation
- Scroll-responsive sizing and opacity
- AI mode toggle with sparkle animations
- Error states with retry mechanisms
- Streaming search progress integration

**Scroll Behavior**:
```typescript
const scrollProgress = computed(() => {
  const progress = Math.min(y.value / (scrollThreshold.value * 2), 1)
  return 1 - Math.pow(1 - progress, 3) // Eased progress
})

const shrinkPercentage = computed(() => {
  const baseline = searchBar.isFocused ? 0 : 0.35
  return Math.max(baseline, Math.min(scrollProgress.value * 0.85, 0.85))
})
```

**Integration**:
- Uses `useSearchOrchestrator` for all search operations
- Delegates to `useAutocomplete` for suggestions
- Syncs with `SearchBarStore` (507 lines)

### 2. DefinitionDisplay (`components/custom/definition/DefinitionDisplay.vue`)

**Features**:
- Modular cluster-based rendering
- Separate components for etymology, examples, synonyms, images
- Streaming data support with skeleton loading
- Editable fields with inline editing
- Progressive sidebar navigation

**Cluster Rendering**:
- Groups definitions by meaning (AI clustering)
- Unicode superscripts (¹²³) for meaning differentiation
- Accordion-based navigation for multiple meanings

## State Management (Pinia)

### 1. SearchBarStore (`stores/search/search-bar.ts` - 507 lines)

**Mode Router** delegating to mode-specific stores:

```typescript
const searchBar = defineStore('search-bar', () => {
  // Mode state
  const searchMode = ref<SearchMode>('lookup')
  const searchSubMode = ref<SearchSubMode>('dictionary')

  // Delegate to mode stores
  const lookupStore = useLookupSearchStore()
  const wordlistStore = useWordlistSearchStore()

  // Mode switching with lifecycle
  const setMode = (mode: SearchMode) => {
    const previousStore = getCurrentModeStore()
    previousStore.onExit() // Lifecycle hook

    searchMode.value = mode

    const newStore = getCurrentModeStore()
    newStore.onEnter() // Lifecycle hook
  }

  // Results delegation
  const results = computed(() => {
    switch (searchMode.value) {
      case 'lookup': return lookupStore.results
      case 'wordlist': return wordlistStore.results
      // ... other modes
    }
  })

  return { searchMode, setMode, results, ... }
})
```

**Persistence** (via pinia-plugin-persistedstate):
```typescript
{
  persist: {
    key: 'search-bar',
    pick: ['searchMode', 'searchSubMode', 'previousMode', 'searchQuery']
  }
}
```

### 2. ContentStore (`stores/content/content.ts` - 328 lines)

**Manages displayed content** with mode-aware delegation:

**Features**:
- Definition error states with retry logic
- Streaming data support (`setPartialEntry`)
- Progressive sidebar navigation
- Accordion state management

```typescript
const content = defineStore('content', () => {
  const currentEntry = ref<SynthesizedDictionaryEntry | null>(null)
  const isLoading = ref(false)
  const definitionError = ref<string | null>(null)

  // Mode-specific content stores
  const lookupContent = useLookupContentStore()
  const wordlistContent = useWordlistContentStore()

  // Delegates to active mode store
  const setEntry = (entry: SynthesizedDictionaryEntry) => {
    const activeStore = getActiveModeStore()
    activeStore.setEntry(entry)
    currentEntry.value = entry
  }

  return { currentEntry, isLoading, setEntry, ... }
})
```

### 3. HistoryStore (`stores/content/history.ts` - 381 lines)

**Intelligent caching** with timestamp validation:

```typescript
const history = defineStore('history', () => {
  // Recent searches/lookups
  const recentSearches = ref<string[]>([])
  const recentLookups = ref<string[]>([])

  // Vocabulary suggestions (1-hour cache)
  const vocabularySuggestions = ref<string[]>([])
  const lastSuggestionFetch = ref<number | null>(null)

  // Throttled refresh (5-minute minimum)
  const refreshVocabularySuggestions = async () => {
    const now = Date.now()
    if (lastSuggestionFetch.value && now - lastSuggestionFetch.value < 5 * 60 * 1000) {
      return // Skip refresh
    }

    const suggestions = await api.suggestions.getVocabularySuggestions()
    vocabularySuggestions.value = suggestions
    lastSuggestionFetch.value = now
  }

  return { recentSearches, vocabularySuggestions, refreshVocabularySuggestions, ... }
})
```

## Composables

### 1. useSearchOrchestrator (`composables/useSearchOrchestrator.ts` - 411 lines)

**Central orchestration** for all search operations—**NO API calls in stores**:

```typescript
export function useSearchOrchestrator(options: Options) {
  const searchBar = useSearchBarStore()
  const content = useContentStore()

  // Main search dispatcher
  const performSearch = async () => {
    switch (searchBar.searchMode) {
      case 'lookup':
        return await executeLookupSearch(searchBar.searchQuery)
      case 'wordlist':
        return await executeWordlistSearch(searchBar.searchQuery)
      // ... other modes
    }
  }

  // Lookup operations
  const getDefinition = async (word: string, options?: LookupOptions) => {
    if (options?.onProgress) {
      // Streaming with SSE
      return lookupApi.lookupStream(word, {
        onProgress: (event) => {
          // Update UI with progress
        },
        onPartialResult: (partial) => {
          content.setPartialEntry(partial)
        }
      })
    }
    // Standard lookup
    return lookupApi.lookup(word, apiOptions)
  }

  // Thesaurus, AI suggestions, etc.
  const getThesaurusData = async (word: string) => { ... }
  const getAISuggestions = async (prompt: string) => { ... }

  return {
    performSearch,
    getDefinition,
    getThesaurusData,
    getAISuggestions,
    // ... all search operations
  }
}
```

**Key Design**: Separates network logic from state management—stores only manage UI state.

### 2. useAutocomplete

**Autocomplete functionality** with caching and throttling:
- Debounced API calls (300ms)
- Result caching (in-memory)
- Keyboard navigation support

### 3. useIOSPWA

**iOS-specific PWA features**:
- Standalone mode detection
- Swipe navigation prevention
- Safe area insets handling
- Viewport adjustments

## API Integration

### 1. API Client (`api/core.ts`)

**Axios Configuration**:
```typescript
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

// Request/response interceptors for logging
api.interceptors.request.use(config => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
  return config
})
```

**Vite Proxy** (proxies to backend):
```typescript
proxy: {
  '/api': {
    target: process.env.VITE_API_URL || 'http://localhost:8000',
    changeOrigin: true,
    timeout: 120000,
  }
}
```

### 2. SSE Client (`api/sse/SSEClient.ts` - 299 lines)

**Sophisticated streaming** implementation:

```typescript
export async function stream<T>(
  url: string,
  options: SSEOptions,
  handlers: {
    onProgress?: (event: ProgressEvent) => void
    onPartialResult?: (partial: Partial<T>) => void
    onComplete?: (result: T) => void
    onError?: (error: Error) => void
  }
): Promise<T> {
  const eventSource = new EventSource(url)

  // Progress events
  eventSource.addEventListener('progress', (e) => {
    const event = JSON.parse(e.data)
    handlers.onProgress?.(event)
  })

  // Chunked completion assembly
  let completionChunks: any[] = []
  eventSource.addEventListener('completion_chunk', (e) => {
    completionChunks.push(JSON.parse(e.data))
  })

  // Complete event
  eventSource.addEventListener('complete', (e) => {
    const result = JSON.parse(e.data)
    handlers.onComplete?.(result)
    eventSource.close()
  })

  // Error handling
  eventSource.onerror = (error) => {
    handlers.onError?.(new Error('SSE connection failed'))
    eventSource.close()
  }
}
```

**Stage Mapping** (for progress):
```typescript
const STAGE_CATEGORY_MAP = {
  'SEARCH_START': 'SEARCH',
  'PROVIDER_FETCH_START': 'FETCH',
  'AI_SYNTHESIS': 'SYNTHESIZE',
  'COMPLETE': 'COMPLETE'
}
```

## TypeScript & Type Safety

### 1. Isomorphic Types (`types/api.ts` - 360 lines)

**Exact mirrors of backend Pydantic models**:

```typescript
export interface Definition extends BaseMetadata {
  id: string
  word_id: string
  part_of_speech: string
  text: string
  meaning_cluster?: MeaningCluster
  examples?: Example[]
  images?: ImageMedia[]
  synonyms: string[]
  antonyms: string[]
  cefr_level?: string
  frequency_band?: number
  // ... 30+ fields matching backend
}

export interface SynthesizedDictionaryEntry extends BaseMetadata {
  id: string
  word_id: string
  word: string
  pronunciation?: Pronunciation
  definitions?: Definition[]
  etymology?: Etymology
  images?: ImageMedia[]
  // ... backend-aligned fields
}
```

### 2. Centralized Mode Types (`types/modes.ts`)

**Replaces 76+ inline union type instances**:

```typescript
export type LookupMode = 'dictionary' | 'thesaurus' | 'suggestions'
export type SearchMode = 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage'
export type SearchSubMode<T extends SearchMode> = SearchSubModeMap[T]
export type LoadingMode = 'lookup' | 'suggestions' | 'wordlist'
export type ErrorType = 'network' | 'not-found' | 'server' | 'ai-failed' | 'unknown'

// Type guards
export function isSearchMode(mode: string): mode is SearchMode {
  return ['lookup', 'wordlist', 'word-of-the-day', 'stage'].includes(mode)
}
```

## UI/UX & Styling

### 1. Tailwind Configuration (`tailwind.config.ts` - 389 lines)

**Custom Design System**:

**Fonts**:
```typescript
fontFamily: {
  sans: ['Fraunces', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
  serif: ['Fraunces', ...],
  mono: ['Fira Code', 'Consolas', 'Monaco', 'monospace']
}
```

**Paper Textures** (45 keyframe animations):
```typescript
backgroundImage: {
  'paper-clean': 'url("data:image/svg+xml,...")',
  'paper-aged': 'url("data:image/svg+xml,...")',
  'paper-handmade': 'url("data:image/svg+xml,...")',
  'paper-kraft': 'url("data:image/svg+xml,...")'
}
```

**Apple-Inspired Easings**:
```typescript
transitionTimingFunction: {
  'apple-default': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  'apple-smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
  'apple-spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  'apple-elastic': 'cubic-bezier(0.68, -0.6, 0.32, 1.6)'
}
```

### 2. CSS Variables (`assets/index.css`)

**Theme System**:
```css
/* Light theme (paper-like) */
--color-background: hsl(48 15% 98%);  /* Warm off-white */
--color-card: hsl(48 12% 99%);

/* Dark theme */
.dark {
  --color-background: hsl(24 8% 6%);   /* Dark warm tone */
  --color-card: hsl(24 6% 7%);
}
```

### 3. shadcn/ui Integration

**123 components** based on Radix Vue:
- Fully accessible (ARIA-compliant)
- Themed with custom Tailwind variables
- TypeScript support throughout
- Composition API-based

**Example Component**:
```vue
<script setup lang="ts">
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const props = defineProps<{
  variant?: 'default' | 'destructive' | 'outline'
  size?: 'default' | 'sm' | 'lg'
}>()
</script>

<template>
  <button :class="cn(buttonVariants({ variant, size }), $attrs.class)">
    <slot />
  </button>
</template>
```

## Routing & Navigation

**Vue Router** with SPA deep linking:

```typescript
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/search/:query?', name: 'Search', component: Home, props: true },
    { path: '/definition/:word', name: 'Definition', component: Home, props: true },
    { path: '/wordlist/:wordlistId', name: 'Wordlist', component: Home, props: true },
  ]
})
```

**Route-Store Synchronization** (`Home.vue`):
```typescript
watch(() => route.name, async (routeName) => {
  if (routeName === 'Definition' && route.params.word) {
    searchBar.setMode('lookup')
    searchBar.setSubMode('lookup', 'dictionary')
    await orchestrator.getDefinition(word)
  }
})
```

## Development Workflow

**Setup**:
```bash
cd frontend
npm install
npm run dev  # Port 3000
```

**Build**:
```bash
npm run build  # TypeScript check + Vite build
npm run preview  # Preview production build
```

**Quality Checks**:
```bash
npm run type-check  # TypeScript compilation (strict mode)
prettier --write .  # Code formatting
```

**Testing** (TO BE IMPLEMENTED):
```bash
npm test  # Vitest (configured but unused)
```

## Performance Optimizations

**Bundle Splitting**:
```typescript
manualChunks: {
  'vue-vendor': ['vue', 'vue-router', 'pinia']
}
```

**Lazy Loading**:
- Dynamic imports for large components
- Route-based code splitting
- Async component loading

**Caching**:
- History store: 1-hour vocabulary cache
- 5-minute throttle on suggestion refreshes
- Image caching with CDN support
- localStorage persistence

## Critical Gaps

**Testing Infrastructure** (IDENTIFIED GAP):
- ✗ Zero test coverage despite Vitest configuration
- ✗ No component tests
- ✗ No composable tests
- ✗ No store tests

**Recommendation**:
```bash
npm install -D vitest @vue/test-utils @vitest/ui jsdom
# Create vitest.config.ts
# Add tests co-located with components
```

---

**Key Files**:
- Core: `/frontend/src/`
- Components: `/frontend/src/components/`
- Stores: `/frontend/src/stores/`
- API: `/frontend/src/api/`
- Types: `/frontend/src/types/`
- Composables: `/frontend/src/composables/`

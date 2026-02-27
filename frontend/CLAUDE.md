# Floridify Frontend

Vue 3.5 TypeScript SPA. Pinia state management. shadcn/ui + Tailwind CSS. ~34K LOC.

## Structure

```
frontend/src/
├── App.vue                         # Root: theme init, PWA setup, error handlers
├── main.ts                         # Vue init, Pinia + router + service worker
├── views/
│   ├── Home.vue (326)              # SPA root: sidebar, search bar, content area
│   └── NotFound.vue (12)           # 404
│
├── components/
│   ├── ui/                         # 123 shadcn/ui components (Radix Vue)
│   │   ├── accordion/, alert/, avatar/, badge/, button/, card/
│   │   ├── carousel/, collapsible/, combobox/, command/, dialog/
│   │   ├── dropdown-menu/, hover-card/, input/, label/
│   │   ├── multi-select/, notification/, popover/, progress/
│   │   ├── select/, separator/, sheet/, skeleton/, slider/
│   │   ├── tabs/, textarea/, toast/, tooltip/
│   │   └── infinite-scroll.vue, infinite-scroll-improved.vue
│   │
│   └── custom/                     # 50 application components
│       ├── search/                 # Search bar system (28 files, 2,739 LOC)
│       │   ├── SearchBar.vue (735) # Primary interface, scroll-responsive
│       │   ├── SearchHistoryContent.vue
│       │   ├── components/         # SearchInput, SearchControls, SearchResults
│       │   │                       # ActionsRow, ExpandModal, AutocompleteOverlay
│       │   │                       # ModeToggle, RegenerateButton, progress bars
│       │   ├── composables/        # useSearchOrchestrator (371), useAutocomplete
│       │   │                       # useSearchBarNavigation, useSearchBarScroll
│       │   │                       # useFocusManagement, useModalManagement
│       │   ├── constants/          # Stage config, provider sources
│       │   ├── types/              # SearchBar-specific interfaces
│       │   └── utils/              # Keyboard handlers, scroll, AI query
│       │
│       ├── definition/             # Definition display (39 files, 3,297 LOC)
│       │   ├── DefinitionDisplay.vue (605) # Main presenter
│       │   ├── WordSuggestionDisplay.vue
│       │   ├── components/         # DefinitionCluster, DefinitionItem, WordHeader
│       │   │                       # EditableField, ImageCarousel, ImageUploader
│       │   │                       # AddToWordlistModal, Etymology, ExampleList
│       │   │                       # SynonymList, ProviderIcons, ThemeSelector
│       │   ├── composables/        # useDefinitionEditMode (317), useImageManagement
│       │   ├── skeletons/          # Loading placeholders
│       │   └── utils/              # Clustering, formatting, provider helpers
│       │
│       ├── wordlist/               # Wordlist management (9 files, 3,088 LOC)
│       │   ├── WordListView.vue (586)
│       │   ├── WordListCard.vue, CreateWordListModal.vue
│       │   ├── WordListUploadModal.vue (760) # File upload + parsing
│       │   ├── WordListSortBuilder.vue, WordlistSelectionModal.vue
│       │   └── composables/        # useWordlistOperations, useWordlistFiltering
│       │
│       ├── sidebar/                # App sidebar (13 files, 1,493 LOC)
│       │   ├── SidebarContent.vue (329), SidebarHeader.vue, SidebarFooter.vue
│       │   ├── SidebarLookupView.vue, SidebarWordListView.vue
│       │   ├── SidebarWordListItem.vue, SidebarRecentItem.vue
│       │   └── RecentItem.vue, RecentLookupItem.vue, RecentSearchItem.vue
│       │
│       ├── navigation/             # Progressive sidebar (8 files, 617 LOC)
│       │   ├── ProgressiveSidebar.vue # Definition cluster navigation
│       │   ├── components/         # SidebarCluster, SidebarPartOfSpeech
│       │   └── composables/        # useScrollTracking, useActiveTracking
│       │
│       ├── loading/                # Progress display
│       │   ├── LoadingModal.vue, LoadingProgress.vue
│       │   └── pipeline-stages.ts
│       ├── pwa/                    # PWAInstallPrompt, PWANotificationPrompt
│       ├── animation/              # AnimatedText, BorderShimmer, BouncyToggle
│       ├── icons/                  # FloridifyIcon, provider icons (8 files)
│       ├── texture/                # TextureBackground, TextureCard, TextureOverlay
│       ├── typewriter/             # TypewriterText + composable
│       ├── card/                   # Card, ThemedCard, GradientBorder
│       ├── dark-mode-toggle/       # DarkModeToggle
│       └── common/                 # RefreshButton, ConfirmDialog, ErrorBoundary
│
├── stores/                         # 12 Pinia stores
│   ├── index.ts                    # useStores() aggregator
│   ├── search/
│   │   ├── search-bar.ts (507)     # Mode router: delegates to lookup/wordlist
│   │   └── modes/
│   │       ├── lookup.ts (525)     # Lookup search ops, provider/language selection
│   │       ├── wordlist.ts (564)   # Wordlist search, sort, filter
│   │       ├── word-of-the-day.ts  # WOTD mode
│   │       └── stage.ts            # Debug/test mode
│   ├── content/
│   │   ├── content.ts (328)        # Displayed content, streaming support
│   │   ├── history.ts (374)        # Recent searches/lookups, vocab suggestions
│   │   └── modes/                  # lookup.ts, wordlist.ts
│   ├── ui/
│   │   ├── ui-state.ts (109)       # Theme, sidebar collapse
│   │   └── loading.ts (155)        # Global loading + progress
│   ├── composables/                # useNotifications, useRouterSync
│   └── types/                      # Mode types, theme constants
│
├── api/                            # 14 API modules
│   ├── core.ts (70)                # Axios instance, interceptors, 60s timeout
│   ├── index.ts                    # Unified export
│   ├── lookup.ts (126)             # Standard + SSE streaming lookup
│   ├── search.ts (140)             # Multi-method search
│   ├── ai.ts (414)                 # 40+ AI synthesis endpoints
│   ├── wordlists.ts (289)          # Wordlist CRUD + reviews
│   ├── entries.ts (177)            # Dictionary entry ops
│   ├── definitions.ts, media.ts, examples.ts, suggestions.ts
│   ├── health.ts, versions.ts
│   └── sse/SSEClient.ts (300)      # EventSource: config, progress, complete events
│
├── composables/                    # Global composables
│   ├── useIOSPWA.ts (346)          # Standalone mode, swipe nav, safe areas
│   ├── usePWA.ts (299)             # Service worker, install prompt, notifications
│   ├── useTextureSystem.ts (162)   # Paper texture variant selection
│   └── useSlugGeneration.ts (51)   # URL slug generation
│
├── types/                          # TypeScript definitions
│   ├── api.ts (405)                # Isomorphic: mirrors backend Pydantic exactly
│   ├── index.ts (274)              # Frontend-specific: SearchResult, error types
│   ├── modes.ts (336)              # Centralized: SearchMode, LookupMode, ErrorType
│   └── wordlist.ts (288)           # Wordlist, MasteryLevel, ReviewData
│
├── router/
│   └── index.ts (67)               # 7 routes: /, /search/:q, /definition/:word,
│                                    #   /thesaurus/:word, /wordlist/:id, 404
├── utils/
│   ├── index.ts (71)               # cn(), debounce(), formatDate(), normalizeWord()
│   ├── logger.ts, guards.ts, time.ts, textToPath.ts
│   └── animations/                 # Spring, easing, keyframe utilities
│
├── services/
│   └── pwa.service.ts (318)        # PWA: install, notifications, push subscription
│
├── assets/
│   └── index.css                   # Tailwind base + CSS vars (light/dark themes)
│
└── styles/
    └── ios-pwa.css                 # iOS-specific safe areas, viewport
```

## Design Principles

- **Isomorphic types**: `types/api.ts` mirrors backend Pydantic models exactly
- **Mode-based state**: SearchBarStore delegates to mode-specific stores with onEnter/onExit lifecycle
- **No API calls in stores**: All network operations in composables (useSearchOrchestrator)
- **Component co-location**: Each feature groups components, composables, types, utils together
- **Strict TypeScript**: 100% strict mode, no `any` types

## State Architecture

```
useStores()
├── useSearchBarStore → useLookupMode / useWordlistMode (mode delegation)
├── useContentStore → useLookupContent / useWordlistContent
├── useHistoryStore (recent searches, vocab suggestions with 1h cache)
├── useUIStore (theme, sidebar)
└── useLoadingState (progress, stages)
```

**Persistence**: pinia-plugin-persistedstate → localStorage for searchMode, history, theme.

## SSE Streaming

```
EventSource(/api/v1/lookup/{word}/stream)
├── event: config   → stage weights
├── event: progress → { stage, progress, message }
├── event: completion_chunk → partial results (>32KB)
└── event: complete → final SynthesizedDictionaryEntry
```

## Design System

**Fonts**: Fraunces (display), Fira Code (mono)
**Textures**: 4 SVG noise patterns (clean, aged, handmade, kraft)
**Easings**: Apple-inspired (default, smooth, spring, elastic)
**Colors**: Warm off-white light, warm dark. CSS variables throughout.
**Animations**: 45+ keyframes. Apple-inspired transition durations.

## Config

| File | Purpose |
|------|---------|
| `vite.config.ts` | Port 3000, API proxy to :8000, Vue + Tailwind plugins |
| `tsconfig.json` | Strict mode, 7 path aliases (`@/*` → `src/*`) |
| `tailwind.config.ts` | 389 LOC: design system, textures, animations, easings |
| `components.json` | shadcn/ui: default style, slate base, Radix Vue |
| `nginx.conf` | Production: rate limiting, SSE buffering off, security headers |
| `Dockerfile` | 6-stage: base → deps → dev → build → production (nginx:alpine) |

## Routes

| Path | Name | Notes |
|------|------|-------|
| `/` | Home | SPA root |
| `/search/:query?` | Search | Multi-method |
| `/definition/:word` | Definition | Deep link |
| `/thesaurus/:word` | Thesaurus | Synonym view |
| `/wordlist/:wordlistId` | Wordlist | List detail |
| `/:pathMatch(.*)*` | NotFound | 404 |

## Development

```bash
cd frontend
npm install
npm run dev          # Port 3000, hot reload
npm run build        # vue-tsc --noEmit && vite build
npm run type-check   # TypeScript strict
prettier --write .   # Format
```

## Gap

Frontend tests: Vitest configured but zero tests written. No component, composable, or store tests.

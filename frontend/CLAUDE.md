# Floridify Frontend

Vue 3.5 TypeScript SPA. Pinia state management. shadcn/ui + Tailwind CSS. ~36K LOC.

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
│   ├── PWAInstallPrompt.vue        # Legacy PWA prompt (root-level)
│   │
│   ├── ui/                         # 123 shadcn/ui .vue components (Radix Vue)
│   │   ├── accordion/, alert/, avatar/, badge/, button/, card/
│   │   ├── carousel/, collapsible/, combobox/, command/, dialog/
│   │   ├── dropdown-menu/, hover-card/, input/, label/
│   │   ├── multi-select/, notification/, popover/, progress/
│   │   ├── select/, separator/, sheet/, skeleton/, slider/
│   │   ├── tabs/, textarea/, toast/, tooltip/
│   │   └── infinite-scroll.vue, infinite-scroll-improved.vue
│   │
│   └── custom/                     # 105 application .vue components
│       ├── ConfirmDialog.vue, ErrorBoundary.vue, Modal.vue
│       ├── NotificationToast.vue, Sidebar.vue
│       │
│       ├── search/                 # Search bar system (32 files, 4,814 LOC)
│       │   ├── SearchBar.vue (737) # Primary interface, scroll-responsive
│       │   ├── SearchHistoryContent.vue
│       │   ├── components/         # SearchInput, SearchControls, SearchResults
│       │   │                       # ActionsRow, ExpandModal, AutocompleteOverlay
│       │   │                       # ModeToggle, RegenerateButton, ActionButton
│       │   │                       # HamburgerButton, SparkleIndicator
│       │   │                       # RainbowProgressBar, ThinLoadingProgress
│       │   ├── composables/        # useSearchOrchestrator (371), useAutocomplete
│       │   │                       # useSearchBarNavigation, useSearchBarScroll
│       │   │                       # useFocusManagement, useModalManagement
│       │   │                       # useSearchBarUI
│       │   ├── constants/          # Stage config, provider sources
│       │   ├── types/              # SearchBar-specific interfaces
│       │   └── utils/              # Keyboard handlers, scroll, AI query
│       │
│       ├── definition/             # Definition display (42 files, 4,880 LOC)
│       │   ├── DefinitionDisplay.vue (732) # Main presenter
│       │   ├── DefinitionSkeleton.vue
│       │   ├── WordSuggestionDisplay.vue
│       │   ├── components/         # DefinitionCluster, DefinitionItem, WordHeader
│       │   │                       # EditableField, ImageCarousel, ImageUploader
│       │   │                       # AddToWordlistModal, Etymology, ExampleList
│       │   │                       # ExampleListEditable, SynonymList, SynonymListEditable
│       │   │                       # ProviderIcons, ProviderTabs, ProviderDataTab
│       │   │                       # ThemeSelector, ThesaurusView, AnimatedTitle
│       │   │                       # EmptyState, ErrorState, EntryImage
│       │   │                       # VersionBadge, VersionHistory
│       │   ├── composables/        # useDefinitionEditMode (317), useImageManagement
│       │   │                       # useDefinitionGroups, useProviders
│       │   ├── constants/          # Provider configuration
│       │   ├── skeletons/          # DefinitionClusterSkeleton, DefinitionItemSkeleton
│       │   ├── types/              # Definition-specific interfaces
│       │   └── utils/              # Clustering, formatting, provider helpers
│       │
│       ├── wordlist/               # Wordlist management (12 files, 3,516 LOC)
│       │   ├── WordListView.vue (586)
│       │   ├── WordListView-simplified.vue
│       │   ├── WordListCard.vue, CreateWordListModal.vue
│       │   ├── WordListUploadModal.vue (760) # File upload + parsing
│       │   ├── WordListSortBuilder.vue, WordlistSelectionModal.vue
│       │   ├── EditWordNotesModal.vue
│       │   └── composables/        # useWordlistOperations, useWordlistFiltering
│       │                           # useWordlistStats
│       │
│       ├── sidebar/                # App sidebar (16 files, 1,873 LOC)
│       │   ├── SidebarContent.vue (329), SidebarHeader.vue, SidebarFooter.vue
│       │   ├── SidebarLookupView.vue, SidebarWordListView.vue
│       │   ├── SidebarWordListItem.vue, SidebarRecentItem.vue
│       │   ├── SidebarSection.vue, GoldenSidebarSection.vue
│       │   ├── RecentItem.vue, RecentItemWithHover.vue
│       │   ├── RecentLookupItem.vue, RecentSearchItem.vue
│       │   ├── VocabularySuggestionItem.vue, YoshiAvatar.vue
│       │
│       ├── navigation/             # Progressive sidebar (14 files, 923 LOC)
│       │   ├── ProgressiveSidebar.vue, ProgressiveSidebarBase.vue
│       │   ├── components/         # SidebarCluster, SidebarPartOfSpeech
│       │   │                       # SidebarHoverCard, PartOfSpeechPreview
│       │   ├── composables/        # useScrollTracking, useActiveTracking
│       │   │                       # useSidebarNavigation, useSidebarState
│       │   └── types/              # Navigation-specific interfaces
│       │
│       ├── loading/                # Progress display
│       │   ├── LoadingModal.vue, LoadingProgress.vue
│       │   └── pipeline-stages.ts
│       ├── pwa/                    # PWAInstallPrompt, PWANotificationPrompt
│       ├── animation/              # AnimatedText, AnimationControls, BorderShimmer
│       │                           # BouncyToggle, ShimmerText
│       ├── icons/                  # FloridifyIcon, FancyF + 6 provider icons (8 files)
│       ├── texture/                # TextureBackground, TextureCard, TextureOverlay
│       ├── typewriter/             # TypewriterText + composable + utils
│       ├── text-animations/        # TypewriterText (alternate)
│       ├── latex/                  # LaTeX rendering component
│       ├── card/                   # Card, ThemedCard, GradientBorder
│       ├── dark-mode-toggle/       # DarkModeToggle
│       └── common/                 # RefreshButton
│
├── stores/                         # 7 Pinia stores + composables + mode configs
│   ├── index.ts                    # useStores() aggregator
│   ├── auth.ts (21)               # Auth store
│   ├── search/
│   │   ├── search-bar.ts (508)     # Mode router: delegates to lookup/wordlist
│   │   └── modes/
│   │       ├── lookup.ts (574)     # Lookup search ops, provider/language selection
│   │       ├── wordlist.ts (564)   # Wordlist search, sort, filter
│   │       ├── word-of-the-day.ts (98)  # WOTD mode config
│   │       └── stage.ts (93)       # Debug/test mode config
│   ├── content/
│   │   ├── content.ts (324)        # Displayed content, streaming support
│   │   ├── history.ts (374)        # Recent searches/lookups, vocab suggestions
│   │   └── modes/                  # lookup.ts (257), wordlist.ts (118)
│   ├── ui/
│   │   ├── ui-state.ts (107)       # Theme, sidebar collapse
│   │   └── loading.ts (155)        # Global loading + progress
│   ├── composables/                # useNotifications (103), useRouterSync (21)
│   └── types/                      # mode-types.ts (192), constants.ts (175)
│
├── api/                            # 13 modules
│   ├── core.ts (70)                # Axios instance, interceptors, 60s timeout
│   ├── index.ts                    # Unified export
│   ├── lookup.ts (126)             # Standard + SSE streaming lookup
│   ├── search.ts (146)             # Multi-method search
│   ├── ai/                         # AI synthesis endpoints (split from ai.ts)
│   │   ├── index.ts                # Barrel assembling aiApi object
│   │   ├── synthesize.ts           # synthesize namespace (synonyms, antonyms, pronunciation)
│   │   ├── generate.ts             # generate namespace (examples, facts, wordForms)
│   │   ├── assess.ts               # assess namespace (7 assessment methods)
│   │   └── suggestions.ts          # validateQuery, suggestWords, synthesizeEntry, etc.
│   ├── wordlists.ts (289)          # Wordlist CRUD + reviews
│   ├── entries.ts (177)            # Dictionary entry ops
│   ├── definitions.ts, media.ts, examples.ts, suggestions.ts
│   ├── health.ts, versions.ts
│   └── sse/                        # SSE streaming (types extracted)
│       ├── index.ts                # Barrel export
│       ├── types.ts                # ProgressEvent, ConfigEvent, SSEOptions, SSEHandlers
│       └── SSEClient.ts (300)      # EventSource: config, progress, complete events
│
├── composables/                    # Global composables
│   ├── useIOSPWA.ts (346)          # Standalone mode, swipe nav, safe areas
│   ├── usePWA.ts (299)             # Service worker, install prompt, notifications
│   ├── useTextureSystem.ts (162)   # Paper texture variant selection
│   └── useSlugGeneration.ts (51)   # URL slug generation
│
├── types/                          # TypeScript definitions
│   ├── api/                        # Isomorphic: mirrors backend Pydantic (split from api.ts)
│   │   ├── index.ts                # Barrel: re-exports all sub-modules
│   │   ├── models.ts               # Enums, core entities (Word, Definition, etc.)
│   │   ├── responses.ts            # API envelopes (ListResponse, ErrorResponse, etc.)
│   │   ├── guards.ts               # Type guard functions (isWord, isDefinition, etc.)
│   │   └── versions.ts             # Version history types (VersionSummary, etc.)
│   ├── index.ts (274)              # Frontend-specific: SearchResult, error types
│   ├── modes.ts (336)              # Centralized: SearchMode, LookupMode, ErrorType
│   └── wordlist.ts (288)           # Wordlist, MasteryLevel, ReviewData
│
├── router/
│   └── index.ts (67)               # 7 routes (see Routes table below)
│
├── utils/
│   ├── index.ts (71)               # cn(), debounce(), formatDate(), normalizeWord()
│   ├── animations.ts, logger.ts, guards.ts, time.ts, textToPath.ts
│   └── animations/                 # animations.ts, constants.ts
│
├── services/
│   └── pwa.service.ts (318)        # PWA: install, notifications, push subscription
│
├── assets/
│   ├── index.css                   # Tailwind base + CSS vars (light/dark themes)
│   ├── themed-cards.css            # Card theme styles
│   ├── images/, yoshi/             # Static assets
│
└── styles/
    └── ios-pwa.css                 # iOS-specific safe areas, viewport
```

## Design Principles

- **Isomorphic types**: `types/api/` directory mirrors backend Pydantic models exactly
- **Mode-based state**: SearchBarStore delegates to mode-specific stores with onEnter/onExit lifecycle
- **No API calls in stores**: All network operations in composables (useSearchOrchestrator)
- **Component co-location**: Each feature groups components, composables, types, utils together
- **Strict TypeScript**: strict mode, 7 path aliases (`@/*` -> `src/*`)

## State Architecture

```
useStores()
├── useSearchBarStore → useLookupMode / useWordlistMode (mode delegation)
├── useContentStore → useLookupContentState / useWordlistContentState
├── useHistoryStore (recent searches, vocab suggestions with 1h cache)
├── useUIStore (theme, sidebar)
├── useLoadingState (progress, stages)
└── useLookupMode (provider/language selection)
```

7 actual Pinia stores (defineStore): auth, search-bar, lookup, wordlist, content, history, ui-state. The remaining modules (loading, stage, word-of-the-day, content modes) are composable-style state functions.

**Persistence**: pinia-plugin-persistedstate -> localStorage for searchMode, history, theme.

## SSE Streaming

Uses `fetch()` with `ReadableStream`, not `EventSource`. Implements retry with exponential backoff (max 3 retries, 1s base delay). Progressive timeout resets on each received event.

```
fetch(/api/v1/lookup/{word}/stream, Accept: text/event-stream)
├── event: config            → stage weights (ConfigEvent)
├── event: progress          → { stage, progress, message, is_complete }
├── event: completion_start  → begins chunked mode
├── event: completion_chunk  → { chunk_type, definition_index, data }
├── event: partial           → partial results (onPartialResult callback)
├── event: complete          → final SynthesizedDictionaryEntry
└── event: error             → { message }
```

Chunked completion assembles basic_info + definition + examples chunks into a final result. Heartbeat pings (lines starting with `:`) are skipped.

## Design System

**Fonts**: Fraunces (sans + serif), Fira Code (mono)
**Textures**: 4 SVG noise patterns (paper-clean, paper-aged, paper-handmade, paper-kraft) + 3 intensity levels (subtle, medium, strong)
**Easings**: 8 Apple-inspired cubic-beziers (apple-default, apple-smooth, apple-spring, apple-elastic, apple-ease-in, apple-ease-out, apple-bounce-in, apple-bounce-out)
**Colors**: Warm off-white light, warm dark. CSS variables throughout.
**Keyframes**: 30 `@keyframes` across 15 files.

## Config

| File | Purpose |
|------|---------|
| `vite.config.ts` | Port 3000, API proxy to :8000, Vue + Tailwind plugins |
| `tsconfig.json` | Strict mode, 7 path aliases (`@/*` -> `src/*`) |
| `tailwind.config.ts` | 388 LOC: design system, textures, animations, easings |
| `components.json` | shadcn/ui: default style, slate base, Radix Vue |
| `nginx.conf` | Production: rate limiting, SSE buffering off, security headers |
| `Dockerfile` | 6-stage: base -> dependencies -> dev-dependencies -> development -> build -> production (nginx:alpine) |

## Routes

| Path | Name | Notes |
|------|------|-------|
| `/` | Home | SPA root |
| `/search/:query?` | Search | Multi-method |
| `/definition/:word` | Definition | Deep link |
| `/thesaurus/:word` | Thesaurus | Synonym view |
| `/wordlist/:wordlistId` | Wordlist | List detail |
| `/wordlist/:wordlistId/search/:query?` | WordlistSearch | Scoped search within wordlist |
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

No frontend tests. Vitest is configured in package.json (`"test": "vitest"`) but no vitest config file exists and zero test files have been written.

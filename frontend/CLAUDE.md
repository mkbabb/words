# Floridify Frontend

Vue 3.5 TypeScript SPA. Pinia state management. shadcn/ui (Reka UI) + Tailwind CSS 4. Clerk authentication.

## Structure

```
frontend/src/
├── components/
│   ├── ui/                     # shadcn/ui primitives (Reka UI-based)
│   │   ├── accordion/, alert/, avatar/, badge/, button/, card/
│   │   ├── carousel/, collapsible/, combobox/, command/, dialog/
│   │   ├── dropdown-menu/, hover-card/, input/, label/, multi-select/
│   │   ├── notification/, popover/, progress/, select/, separator/
│   │   ├── sheet/, skeleton/, slider/, tabs/, textarea/
│   │   ├── toast/, tooltip/, infinite-scroll/
│   │   └── index.ts
│   └── custom/                 # Application components
│       ├── search/             # SearchBar, SearchInput, AutocompleteOverlay, ModeToggle
│       │   ├── components/     # SearchControls, SearchResults, ActionsRow, RainbowProgressBar
│       │   ├── composables/    # useSearchOrchestrator, useAutocomplete, useFocusManagement
│       │   └── utils/          # keyboard, scroll, ai-query helpers
│       ├── definition/         # DefinitionDisplay, DefinitionSkeleton
│       │   ├── components/     # DefinitionCluster, WordHeader, Etymology, ThesaurusView
│       │   │                   # ImageCarousel, AudioPlaybackButton, ProviderVersionSelector
│       │   │                   # TimeMachineOverlay, VersionHistory, VersionDiffViewer
│       │   │                   # InlineDiff, TextDiffBlock, AnimatedTitle, EmptyState, ErrorState
│       │   ├── composables/    # useDefinitionEditMode, useImageManagement, useProviders
│       │   │                   # useDefinitionGroups, useAudioPlayback, useTimeMachine
│       │   └── skeletons/      # Loading state skeletons
│       ├── wordlist/           # WordListView, WordListCard, CreateWordListModal
│       │   │                   # WordListUploadModal, WordListSortBuilder, WordlistStatsBar
│       │   ├── composables/    # useWordlistOperations, useWordlistFiltering
│       │   │                   # useWordlistFileParser, useWordlistUpload
│       │   └── modals/         # EditWordNotesModal
│       ├── sidebar/            # SidebarContent, SidebarHeader, SidebarFooter
│       │   │                   # SidebarLookupView, SidebarWordListView
│       │   └── items/          # RecentLookupItem, VocabularySuggestionItem, YoshiAvatar
│       ├── progressive-sidebar/ # ProgressiveSidebar, SidebarCluster, SidebarHoverCard
│       │   ├── composables/    # useScrollTracking, useActiveTracking, useSidebarNavigation
│       │   └── types.ts
│       ├── auth/               # AuthGate, RoleBadge, UserMenu
│       ├── loading/            # LoadingModal, LoadingProgress, pipeline-stages
│       ├── icons/              # FloridifyIcon, FancyF, AppleIcon, OxfordIcon, etc.
│       ├── animation/          # AnimatedText, BorderShimmer, BouncyToggle, ShimmerText
│       ├── texture/            # TextureBackground, TextureCard, TextureOverlay
│       ├── typewriter/         # TypewriterText + useTypewriter composable
│       ├── latex/              # LaTeX rendering (KaTeX)
│       ├── card/               # Card, ThemedCard, GradientBorder
│       ├── dark-mode/          # DarkModeToggle
│       ├── pwa/                # PWAInstallPrompt, PWANotificationPrompt
│       └── Sidebar.vue, ConfirmDialog.vue, ErrorBoundary.vue, Modal.vue
│
├── stores/                     # Pinia state management
│   ├── auth.ts                 # Clerk auth state
│   ├── search/
│   │   ├── search-bar.ts       # SearchBarStore: mode delegation
│   │   └── modes/              # lookup.ts, wordlist.ts, word-of-the-day.ts, stage.ts
│   ├── content/
│   │   ├── content.ts          # ContentStore: word display state
│   │   ├── history.ts          # Lookup history
│   │   └── modes/              # lookup.ts, wordlist.ts
│   ├── ui/
│   │   ├── ui-state.ts         # UI state (sidebar, dark mode)
│   │   └── loading.ts          # Loading states
│   ├── types/                  # Mode type definitions, constants
│   └── composables/            # useNotifications, useRouterSync
│
├── api/                        # Backend communication
│   ├── core.ts                 # Axios client, interceptors, base URL
│   ├── lookup.ts, search.ts, entries.ts, definitions.ts
│   ├── wordlists.ts, suggestions.ts, versions.ts, providers.ts
│   ├── media.ts, audio.ts, examples.ts, health.ts, users.ts
│   ├── ai/                     # synthesize.ts, generate.ts, assess.ts, suggestions.ts
│   └── sse/                    # SSEClient.ts, types.ts — fetch-based streaming
│
├── composables/                # Global composables
│   ├── useIOSPWA.ts            # iOS PWA detection + safe area
│   ├── usePWA.ts               # PWA install/notification prompts
│   ├── useTextureSystem.ts     # Paper texture management
│   ├── useSlugGeneration.ts    # URL slug generation
│   └── useStateSync.ts         # Cross-tab state synchronization
│
├── types/                      # Isomorphic types mirroring backend Pydantic
│   ├── index.ts                # Re-exports
│   ├── modes.ts                # Mode type definitions
│   ├── wordlist.ts             # Wordlist types
│   └── api/                    # Backend model mirrors
│       ├── models.ts           # Word, Definition, DictionaryEntry, etc.
│       ├── responses.ts        # LookupResponse, SearchResponse
│       ├── guards.ts           # Type guard functions
│       └── versions.ts         # Version/diff types
│
├── views/                      # Route views
│   ├── Home.vue                # SPA root (lookup, wordlist, wotd modes)
│   ├── Admin.vue               # Admin panel
│   ├── Login.vue               # Clerk sign-in
│   ├── Signup.vue              # Clerk sign-up
│   └── NotFound.vue            # 404
│
├── router/index.ts             # Vue Router: /, /admin, /login, /signup, /word/:slug, /search/:query, 404
│
├── lib/utils.ts                # cn() utility (clsx + tailwind-merge)
├── plugins/toast.ts            # Toast notification plugin (sonner)
├── services/index.ts           # Service layer
│
├── utils/
│   ├── animations/             # Animation utilities, constants
│   ├── wordDiff.ts             # Word-level LCS diff for TimeMachine
│   ├── guards.ts               # Runtime type guards
│   ├── logger.ts               # Frontend logging
│   ├── textToPath.ts           # SVG text path generation
│   ├── time.ts                 # Time formatting
│   └── validatePersistedState.ts # Pinia persistence validation
│
├── assets/                     # CSS, images, sprites
│   ├── index.css, theme.css, transitions.css, typography.css, utilities.css
│   └── images/                 # Yoshi sprites, themed card backgrounds
│
└── styles/ios-pwa.css          # iOS PWA-specific styles
```

## Design Principles

- **Isomorphic types**: `types/api/` mirrors backend Pydantic models exactly
- **Mode-based state**: SearchBarStore delegates to mode-specific stores (lookup, wordlist, wotd) with `onEnter`/`onExit` lifecycle
- **No API calls in stores**: Network operations live in composables and API modules
- **Component co-location**: Each feature subsystem has its own `components/`, `composables/`, `utils/`, `types/`

## State Architecture

```
SearchBarStore (search-bar.ts)
  ├── delegates to → LookupModeStore | WordlistModeStore | WotdModeStore
  └── manages: query, mode, search state

ContentStore (content.ts)
  ├── delegates to → LookupContentStore | WordlistContentStore
  └── manages: displayed word, definitions, versions

UIStateStore (ui-state.ts)
  └── manages: sidebar, dark mode, texture settings

AuthStore (auth.ts)
  └── manages: Clerk auth state, user role
```

## SSE Streaming

Fetch-based streaming (not `EventSource`—supports POST and custom headers). [`SSEClient`](src/api/sse/SSEClient.ts) with retry and exponential backoff. Event types: `progress`, `stage`, `result`, `error`, `complete`.

## Dependencies

| Package | Purpose |
|---------|---------|
| `vue` 3.5 | Framework |
| `pinia` 3.0 | State management |
| `reka-ui` | shadcn/ui component primitives |
| `@clerk/vue` | Authentication |
| `tailwind-merge` + `clsx` | CSS class merging |
| `gsap` | Animations |
| `sonner` | Toast notifications |
| `katex` | LaTeX rendering |
| `axios` | HTTP client |

## Routes

| Path | View | Notes |
|------|------|-------|
| `/` | Home | SPA root—lookup, wordlist, wotd modes |
| `/word/:slug` | Home | Deep link to word definition |
| `/search/:query` | Home | Deep link to search results |
| `/admin` | Admin | Admin panel (auth-gated) |
| `/login` | Login | Clerk sign-in |
| `/signup` | Signup | Clerk sign-up |
| `/:pathMatch(.*)*` | NotFound | 404 catch-all |

## Development

```bash
npm install && npm run dev       # Dev server on port 3000
npm run type-check               # vue-tsc --noEmit
npm run build                    # Production build
prettier --write .               # Format
```

## Config Files

| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite config, SSE proxy plugin, API proxy |
| `tsconfig.json` | TypeScript strict mode |
| `tailwind.config.ts` | Design system: paper textures, easings |
| `nginx.conf` | Production: rate limiting, SSE proxy, security headers |
| `Dockerfile` | 6-stage: base → deps → dev-deps → dev → build → production (nginx) |

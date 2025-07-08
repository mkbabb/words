# Frontend Design Specification

## Visual Hierarchy

**Landing State**: Search bar centered vertically, LaTeX F logo (𝓕) at 6xl scale, minimal UI
**Search State**: Search bar animated to top, logo scaled to 4xl, results display below

## Typography System

- **Headers**: Fraunces (elegant serif for word titles)
- **Technical**: Fira Code (phonetic, IPA notation)
- **Body**: System fonts (definitions, interface text)
- **Logo**: KaTeX-rendered \mathscr{F} with subscript d/t

## Layout Architecture

```
┌─────────────────────────────────────────┐
│ [🌙] Dark Toggle                       │
│                                         │
│         𝓕d  [━━━━━━━━━━━━━━━━] 🔍         │ Landing
│                                         │
│     [serendipity] [ephemeral] [...]     │
│                                         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [🌙] 𝓕d [━━━━━━━━━━━━━━━━] 🔍            │ Search
│                                         │
│ ╭─ word /wɜrd/ ──────────────────────╮   │
│ │ noun¹                              │   │
│ │   A unit of language...            │   │
│ │   synonyms: term, expression       │   │
│ ╰────────────────────────────────────╯   │
└─────────────────────────────────────────┘
```

## Animation Specifications

- **Search Transition**: 0.6s cubic-bezier(0.4, 0, 0.2, 1)
- **Logo Scale**: 6xl → 4xl with synchronized movement
- **Dark Mode**: 650ms ease-out with pulse animation
- **Results**: Staggered fade-in with 100ms delays

## Component System

**SearchBar**: Debounced input, suggestion dropdown, animated logo
**DefinitionDisplay**: Hierarchical meanings, pronunciation toggle, clickable synonyms
**ThesaurusView**: Heatmap visualization, similarity-based color coding
**DarkModeToggle**: Animated sun/moon with CSS transforms

## Color Psychology

- **Base**: High contrast black/white foundation
- **Accents**: Semantic purple for primary actions
- **Heatmap**: Red intensity gradient (10 levels)
- **States**: Muted grays for secondary information

## Interaction Patterns

- **Universal Linking**: Click any word → new search
- **Smooth Transitions**: Zero page loads, component swapping
- **Contextual UI**: F_d ⟷ F_t based on current mode
- **Persistent History**: Infinite scroll with lazy loading

## Technical Implementation

- **Framework**: Vue 3 Composition API
- **Styling**: Tailwind CSS with shadcn-vue components
- **Animations**: CSS transforms, GPU-accelerated
- **State**: Pinia with localStorage persistence
- **Typography**: Web fonts with fallbacks
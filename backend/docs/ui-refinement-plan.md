# UI Refinement Implementation Plan

## Phase 1: Core Layout & Logo
1. **LaTeX Logo Refinement**
   - Use `katex` display mode for crisp rendering
   - Add LaTeX subscript: `\mathscr{F}_{\text{d/t}}`
   - Implement proper padding/margins to prevent cut-off

2. **Logo Repositioning**
   - Create rounded square container with background
   - Position left of search bar in flexbox layout
   - Apply subtle gradient/shadow for depth

3. **Search Icon Integration**
   - Import `lucide-vue-next` search icon
   - Replace button text with `<Search />` component
   - Scale appropriately with button size

## Phase 2: Sidebar Implementation
1. **Desktop Sidebar Structure**
   - Fixed positioned aside element
   - Collapsible state with width transitions
   - Ribbon mode: 60px width, icon-only

2. **Mobile Horizontal Sidebar**
   - Transform to horizontal layout using CSS transforms
   - Sticky positioning with `top: 0`
   - Search bar sticky below with `top: [sidebar-height]`

3. **Toggle Mechanism**
   - Pinia store state for sidebar open/closed
   - Smooth CSS transitions with `transition-all duration-300 ease-in-out`
   - Click outside to close functionality

## Phase 3: Enhanced Styling
1. **Value.js Card Shadow System**
   - Extract shadow classes from value.js codebase
   - Apply to cards: `shadow-[0_8px_30px_rgb(0,0,0,0.12)]`
   - Implement hover shadow increases

2. **Interactive Element Enhancements**
   - Hover states: `hover:scale-105 hover:shadow-lg`
   - Button darkening: `hover:brightness-95`
   - Transition all: `transition-all duration-200 ease-out`

3. **Border Radius Standardization**
   - Base radius: `rounded-xl` (12px)
   - Interactive elements: `rounded-lg` (8px)
   - Small components: `rounded-md` (6px)

## Phase 4: Search Functionality
1. **Progress Bar Implementation**
   - Linear progress spanning search bar width
   - Indeterminate animation during API calls
   - Position absolute within search container

2. **Async State Management**
   - Loading skeletons using `pulse` animation
   - Skeleton components for definition cards
   - Error boundaries with retry mechanisms

3. **Autocomplete System**
   - Debounced input with 200ms delay
   - Dropdown positioned with `z-50` minimum
   - Portal rendering to avoid z-index conflicts

## Phase 5: Advanced Features
1. **Definition Preview**
   - Watch first autocomplete result
   - Fetch definition in background
   - Display in floating preview card

2. **Enhanced Text Formatting**
   - Regex replacement in example sentences
   - Bold matching word/phrase using `<strong>`
   - Support multiple examples per definition

3. **Phonetic Toggle Fix**
   - Debug store pronunciation mode state
   - Ensure proper reactivity in display component
   - Add visual indicator for current mode

## Phase 6: Performance & Polish
1. **Animation Implementation**
   - Spring physics using CSS `cubic-bezier(0.68, -0.55, 0.265, 1.55)`
   - Staggered animations for list items
   - Intersection Observer for scroll-triggered animations

2. **Document Meta Updates**
   - Title: `floridify`
   - Favicon implementation
   - Meta description and keywords

3. **Mobile Responsiveness**
   - Breakpoint-specific layouts using Tailwind
   - Touch-friendly interactive areas (44px minimum)
   - Swipe gestures for sidebar toggle
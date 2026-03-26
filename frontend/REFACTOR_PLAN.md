# Glassmorphism & Paper Cohesion Plan

Visual design system consolidation. The metaphor: **content written on textured paper, viewed through glass**. Paper texture is omnipresent at varying intensities. Glass blur increases with elevation. Cartoon shadows give depth without realism. Typography is bold, serif-forward (Fraunces). Color palette is warm (hsl(48) backgrounds, amber AI accents).

---

## Phase 1: Typography Semantic Migration (Mechanical)

### Goal
Replace all raw `text-Nxl font-serif font-bold/semibold` combos with the semantic typography scale defined in `utilities.css`. The semantic classes already exist but have **zero consumers** — every component still uses raw Tailwind.

### Semantic Scale (already defined in `@layer components` of `utilities.css`)

| Class | Resolves To | Use Case |
|-------|------------|----------|
| `text-display` | `text-3xl font-serif font-bold tracking-tight; line-height: 1.2` | Page titles, hero text |
| `text-title` | `text-2xl font-serif font-bold` | Section heads, wordlist names |
| `text-heading` | `text-xl font-serif font-semibold` | Subsection headers, modal titles |
| `text-subheading` | `text-lg font-medium` | Card subtitles, toolbar labels |
| `text-body` | `text-sm leading-relaxed` | Body copy |
| `text-caption` | `text-xs text-muted-foreground` | Labels, hints, timestamps |

### Replacements (~35 occurrences across 21 files)

**`text-display` candidates** (page-level titles):
- `WordHeader.vue` — main word heading (currently inline font-serif styles)
- `AnimatedTitle.vue` — animated page title
- `WordlistDashboard.vue` lines 25/31/37 — stat numbers (`text-4xl font-serif font-bold` — keep `text-4xl` override, add `text-display` base)

**`text-title` candidates** (section heads):
- `WordListView.vue:18` — `<h1 class="text-2xl font-serif font-bold">`
- `WordListView.vue:60,63` — tab triggers (`font-serif text-2xl font-bold`)
- `WordlistDashboard.vue:6` — `<h2 class="font-serif text-2xl font-bold tracking-tight">`
- `WordDetailModal.vue:23` — `text-2xl sm:text-3xl font-serif font-bold`
- `ReviewCard.vue:39` — `text-2xl font-serif font-bold`
- `ReviewModal.vue:39` — `text-xl font-serif font-bold` (bump to title or keep heading)

**`text-heading` candidates** (subsections):
- `ProviderDataView.vue:110` — `font-serif text-xl font-semibold` (etymology header)
- `UploadDropZone.vue:50` — `font-serif text-xl font-semibold`
- `WordPreviewList.vue:16` — `font-serif text-lg font-semibold`

**`text-subheading` candidates** (card-level labels):
- `ReviewModal.vue:74` — `text-lg font-medium`
- `WordlistDashboard.vue:76` — `font-serif text-lg font-semibold`
- Various sidebar section headers

### Cleanup: Remove Unused `heading-1` through `heading-6`

The `heading-1` through `heading-6` utilities in `tailwind.config.ts` (lines 428-433) have **zero consumers** across all `.vue` and `.ts` files. Remove them entirely — the semantic scale in `utilities.css` supersedes them.

**Files touched:**
- `tailwind.config.ts` — delete `.heading-1` through `.heading-6` (6 lines)
- ~21 `.vue` files — find/replace raw typography combos with semantic classes

### Verification
`npx vue-tsc --noEmit && npx vite build` — zero regressions. Visual diff: no change (semantic classes resolve to identical styles).

---

## Phase 2: Surface Hierarchy with Paper Texture

### Goal
Establish a 5-level elevation system where every level gets paper texture. Currently `card-surface`, `popover-surface`, and `dialog-surface` exist and are used, but there is no Level 1 (`paper-surface`) for non-elevated content panels.

### Elevation Table

| Level | Class | Blur | BG Opacity | Texture | Shadow | Use Case |
|-------|-------|------|------------|---------|--------|----------|
| 0 | `body` | none | 100% | none | none | Page background (already set in `@layer base`) |
| 1 | `paper-surface` **(new)** | none | 98% | clean, subtle | `elevation-1` | Definition panels, sidebar content areas, stats bars |
| 2 | `card-surface` (existing) | `blur-sm` | 92% | clean | `elevation-2` | Cards, ThemedCard base, search bar shell |
| 3 | `popover-surface` (existing) | `blur-xl` | 95% | clean | `xl` | Dropdowns, popovers, hover cards, autocomplete |
| 4 | `dialog-surface` (existing) | `blur-xl` | 94% | clean | `2xl` | Modals, dialogs, sheets |
| G | `glass-*` (existing) | varies | 80% | none | none | Floating UI without paper (pills, overlay buttons, nav chrome) |

### New: `paper-surface` (Level 1)

Add to `index.css` `@layer components`:

```css
.paper-surface {
  @apply bg-background/98 shadow-elevation-1;
  background-image: var(--paper-clean-texture);
  background-blend-mode: multiply;
}
```

No blur, no rounded corners (inherits from context), minimal shadow. This is the "flat panel" layer — content resting on the page surface with just enough texture to distinguish it from the bare background.

### Existing surfaces — minor tuning

- `card-surface` — already correct (`bg-background/92 backdrop-blur-sm`). No changes needed.
- `popover-surface` — already correct (`bg-background/95 backdrop-blur-xl`). No changes needed.
- `dialog-surface` — already correct (`bg-background/94 backdrop-blur-xl`). No changes needed.

### Files touched
- `frontend/src/assets/index.css` — add `.paper-surface` to `@layer components` block

---

## Phase 3: Root shadcn Component Paper Integration

### Goal
Ensure the base shadcn primitives default to the paper texture system so every consumer inherits texture without per-component overrides.

### Changes

**`Card.vue`** (`components/ui/card/Card.vue`)
Current:
```
bg-card text-card-foreground flex flex-col gap-6 rounded-xl border p-6 shadow-elevation-2 transition-shadow duration-200
```
Change to:
```
card-surface text-card-foreground flex flex-col gap-6 rounded-xl p-6 transition-shadow duration-200
```
The `card-surface` class already provides `bg-background/92`, `backdrop-blur-sm`, `shadow-card`, `border border-border/35`, and paper texture. Removes redundant `bg-card`, `border`, and `shadow-elevation-2`.

**`DialogContent.vue`** (`components/ui/dialog/DialogContent.vue`)
Already uses `dialog-surface`. No change needed.

**`PopoverContent.vue`** (`components/ui/popover/PopoverContent.vue`)
Already uses `popover-surface`. No change needed.

**`SelectContent.vue`** (`components/ui/select/SelectContent.vue`)
Already uses `popover-surface`. No change needed.

**`DropdownMenuContent.vue`** (`components/ui/dropdown-menu/DropdownMenuContent.vue`)
Already uses `popover-surface`. No change needed.

**`HoverCardContent.vue`** (`components/ui/hover-card/HoverCardContent.vue`)
Already uses `popover-surface`. No change needed.

**`TooltipContent.vue`** (`components/ui/tooltip/TooltipContent.vue`)
Current: `bg-primary backdrop-blur-sm`. Tooltips are inverted (dark bg, light text) — paper texture would look wrong. **Leave as-is.**

**`TabsList.vue`** (`components/ui/tabs/TabsList.vue`)
The pill variant already uses `glass-light`. The underline variant is transparent. No change needed.

### Accordion panels
Accordion content areas should inherit `paper-surface` when used as content containers. This is contextual — add `paper-surface` in the consuming components (e.g., sidebar sections that use accordion), not in the base AccordionContent primitive.

### Files touched
- `frontend/src/components/ui/card/Card.vue` — swap to `card-surface`

### Estimated scope
1 file changed, ~2 lines modified.

---

## Phase 4: Component-Level Paper Suffusion

### Goal
Apply paper texture to all significant content areas that currently lack it. These are components that show content on plain backgrounds where the "paper" metaphor should be visible.

### 4.1 — SearchBar shell

**File:** `frontend/src/components/custom/search/SearchBar.vue`

The search bar container (line ~23) already uses `shadow-cartoon-sm`, `backdrop-blur-xl`, and `bg-background/90`. Add paper texture overlay:
- Add `background-image: var(--paper-clean-texture); background-blend-mode: multiply;` via the existing `card-surface` class or a targeted style.
- The search bar is effectively a Level 2 surface — it should use `card-surface` styling (but keeps its cartoon shadow).

### 4.2 — Sidebar content area

**Files:**
- `frontend/src/components/custom/Sidebar.vue` — main sidebar panel
- `frontend/src/components/custom/sidebar/SidebarContent.vue`
- `frontend/src/components/custom/sidebar/GoldenSidebarSection.vue`

The sidebar already has `bg-background/95 backdrop-blur-xl`. Add paper texture:
- Add `paper-surface` to the inner content scroll area (not the outer fixed shell, which is glass).
- `GoldenSidebarSection.vue` containers (line 22) already use `backdrop-blur-sm` — add paper texture.

### 4.3 — Definition panels

**Files:**
- `frontend/src/components/custom/definition/DefinitionDisplay.vue`
- `frontend/src/components/custom/definition/components/content/DefinitionCluster.vue`
- `frontend/src/components/custom/definition/components/content/DefinitionContentView.vue`

The main definition content area has no paper texture. Add `paper-surface` to:
- The cluster containers (definition groupings)
- The overall definition panel wrapper

### 4.4 — Stats bars

**Files:**
- `frontend/src/components/custom/wordlist/WordlistStatsBar.vue`
- `frontend/src/components/custom/wordlist/MasteryBar.vue`

Stats containers use `bg-muted` or similar. Swap to `paper-surface` for consistency.

### 4.5 — Loading skeletons

**Files:**
- `frontend/src/components/ui/skeleton/Skeleton.vue`
- `frontend/src/components/custom/definition/skeletons/DefinitionStreamingSkeleton.vue`
- `frontend/src/components/custom/definition/DefinitionSkeleton.vue`

Skeleton pulse animations currently use `bg-muted`. Consider adding subtle paper texture to skeleton containers (not the pulse bars themselves) so the loading state feels continuous with the loaded state.

### 4.6 — Empty states

**Files:**
- `frontend/src/components/custom/definition/components/EmptyState.vue`
- `frontend/src/components/custom/definition/components/ErrorState.vue`
- `frontend/src/components/custom/wordlist/views/WordlistDashboard.vue` (empty wordlist state, line ~71-93)

Empty state containers should use `paper-surface` instead of bare backgrounds to maintain the "paper" feel even when there is no content.

### Estimated scope
~12 files, ~15-20 class additions/modifications.

---

## Phase 5: Interactive Glass Depth

### Goal
Add micro-interactions that reinforce the glass depth metaphor through blur, opacity, and shadow transitions.

### 5.1 — Card hover: blur intensification

Add a utility or modify `card-surface` to increase blur on hover:

```css
.card-surface {
  /* existing styles */
  transition: backdrop-filter 200ms var(--ease-apple-smooth),
              box-shadow 200ms var(--ease-apple-smooth);
}

.card-surface:hover {
  backdrop-filter: blur(8px); /* up from blur-sm (4px) */
  box-shadow: var(--shadow-card-hover); /* 0 8px 24px rgba(0,0,0,0.12) */
}
```

### 5.2 — Active press: opacity shift

For interactive cards (word cards, wordlist cards), on `:active`:
- Increase background opacity slightly (e.g., `bg-background/95`) for a "pressed into surface" feel
- Already partially implemented via `active:scale-[0.98]` in many components

Add to `utilities.css`:
```css
.press-depth {
  @apply active:bg-background/96 active:shadow-elevation-1;
  transition: background-color 100ms var(--ease-apple-smooth),
              box-shadow 100ms var(--ease-apple-smooth);
}
```

### 5.3 — Focus ring: glass-tinted

Current focus ring: `focus-visible:ring-2 focus-visible:ring-primary/50`. Enhance with slight backdrop blur for a glass-tinted appearance:

```css
.focus-ring-glass {
  @apply focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2;
  &:focus-visible {
    box-shadow: 0 0 0 2px var(--color-background), 0 0 0 4px color-mix(in srgb, var(--color-primary) 40%, transparent);
  }
}
```

### 5.4 — Dropdown open: animate blur

When popovers/dropdowns open, animate the blur intensity from 0 to full:

```css
.popover-surface[data-state='open'] {
  animation: blur-in 200ms var(--ease-apple-smooth) forwards;
}

@keyframes blur-in {
  from { backdrop-filter: blur(0px); }
  to { backdrop-filter: blur(16px); /* blur-xl */ }
}
```

This gives the glass "materializing out of thin air" effect.

### Files touched
- `frontend/src/assets/index.css` — update `card-surface` hover states
- `frontend/src/assets/utilities.css` — add `press-depth`, `focus-ring-glass` utilities
- `frontend/src/assets/theme.css` — add `blur-in` keyframe

### Estimated scope
3 CSS files, ~30 lines added.

---

## Phase 6: Cartoon Shadow Consistency Audit

### Goal
Standardize shadow usage across the app. Currently cartoon shadows (`shadow-cartoon-*`) are used inconsistently — some cards have them, others use standard `shadow-xl`, and some have both (`shadow-2xl shadow-cartoon-lg` in `TimeMachineExpandedView.vue`).

### Rules

| Surface Type | Shadow | Hover Shadow |
|-------------|--------|-------------|
| Word cards, wordlist cards, themed cards | `shadow-cartoon-sm` | `shadow-cartoon-sm-hover` |
| Search bar | `shadow-cartoon-sm` | `shadow-cartoon-sm-hover` |
| Progressive sidebar | `shadow-cartoon-lg` | (none — not interactive) |
| Dropdowns, popovers, hover cards | `shadow-xl` (standard) | (none) |
| Modals, dialogs | `shadow-2xl` (standard) | (none) |
| Tooltips | `shadow-lg` (standard) | (none) |
| Notification toasts | `shadow-cartoon-sm` | (none) |
| PWA prompts | `shadow-cartoon-md` | (none) |
| Login/signup form | `shadow-cartoon-sm` | (none) |

### Issues to fix

1. **Double shadow** — `TimeMachineExpandedView.vue:36` and `TimeMachineVersionCard.vue:10` both use `shadow-2xl shadow-cartoon-lg`. These conflict (both set `box-shadow`). Pick one:
   - TimeMachine overlay panels are Level 4 (dialog-like) — use `shadow-2xl` only, drop `shadow-cartoon-lg`
   - Or keep `shadow-cartoon-lg` only if the cartoon aesthetic is desired there

2. **`shadow-cartoon-lg backdrop-blur-xl`** combo on `WordHeader.vue:132` (admin dropdown), `ProviderIcons.vue:66,166`, `SearchResultItem.vue:88` — these are popovers. Standardize to `popover-surface` class (which includes `shadow-xl`) instead of per-component shadow declarations.

3. **Missing cartoon shadow** — `ThemedCard.vue` and `TextureCard.vue` both apply `shadow-cartoon-lg` at the component level. But `BaseWordCard.vue` applies `hover:shadow-cartoon-sm-hover` only on hover, with no default shadow. Consider adding `shadow-cartoon-sm` as default to BaseWordCard.

### Files to audit (~18 files with `shadow-cartoon-*`)

```
ThemedCard.vue              — shadow-cartoon-lg (correct)
TextureCard.vue             — shadow-cartoon-lg (correct)
BaseWordCard.vue            — hover:shadow-cartoon-sm-hover (add default?)
WordListCard.vue            — via parent ThemedCard
WordlistGrid.vue            — hover:shadow-cartoon-sm-hover
SearchBar.vue               — shadow-cartoon-sm (correct)
ProgressiveSidebar.vue      — shadow-cartoon-lg (correct)
WordlistProgressiveSidebar  — shadow-cartoon-lg (correct)
SidebarHoverCard.vue        — shadow-cartoon-lg (correct)
SidebarPartOfSpeech.vue     — shadow-cartoon-lg / shadow-cartoon-sm (correct)
NotificationToast.vue       — shadow-cartoon-sm (correct)
PWAInstallPrompt.vue        — shadow-cartoon-md (correct)
Login.vue / Signup.vue      — shadow-cartoon-sm (correct)
WordLookupPopover.vue       — shadow-cartoon-sm (correct)
TimeMachineVersionCard.vue  — shadow-2xl shadow-cartoon-lg (FIX: pick one)
TimeMachineExpandedView.vue — shadow-2xl shadow-cartoon-lg (FIX: pick one)
WordHeader.vue              — shadow-cartoon-lg on admin dropdown (FIX: use popover-surface)
ProviderIcons.vue           — shadow-cartoon-lg on popovers (FIX: use popover-surface)
SearchResultItem.vue        — shadow-cartoon-lg on popover (FIX: use popover-surface)
UploadDropZone.vue          — shadow-cartoon-sm on drag active (correct)
```

### Estimated scope
~8 files, ~12 line changes.

---

## Key Principle: The Visual Stack

```
Layer 4  ─ Dialog   ─ blur-xl  ─ 94% opaque ─ paper ─ shadow-2xl    ─ Modals
Layer 3  ─ Popover  ─ blur-xl  ─ 95% opaque ─ paper ─ shadow-xl     ─ Dropdowns
Layer 2  ─ Card     ─ blur-sm  ─ 92% opaque ─ paper ─ cartoon-sm    ─ Cards, search bar
Layer 1  ─ Panel    ─ none     ─ 98% opaque ─ paper ─ elevation-1   ─ Definition, sidebar
Layer 0  ─ Body     ─ none     ─ 100%       ─ none  ─ none          ─ Page background
  Glass  ─ Float    ─ varies   ─ 80% opaque ─ none  ─ none          ─ Pills, overlay buttons
```

Every layer above 0 carries the paper texture at the intensity defined by its background opacity. Lower opacity = more texture bleed-through. The glass variants (`glass-light`, `glass-medium`, `glass-heavy`) are for chrome elements that intentionally skip paper texture — navigation pills, overlay buttons, control surfaces.

---

## Execution Order & Estimates

| Phase | Risk | Files | Est. Changes | Dependencies |
|-------|------|-------|-------------|-------------|
| 1. Typography semantic migration | Low | ~22 | ~35 find/replace | None |
| 2. `paper-surface` definition | Low | 1 | 5 lines | None |
| 3. Card.vue paper integration | Low | 1 | 2 lines | Phase 2 |
| 4. Component paper suffusion | Medium | ~12 | ~20 class additions | Phase 2 |
| 5. Interactive glass depth | Low | 3 | ~30 lines CSS | Phase 2 |
| 6. Shadow consistency audit | Low | ~8 | ~12 line changes | None |

Phases 1, 2, and 6 are independent and can be executed in parallel. Phase 3 depends on 2. Phase 4 depends on 2. Phase 5 depends on 2.

### Verification per phase

1. `npx vue-tsc --noEmit` — zero new type errors
2. `npx vite build` — successful production build
3. Visual inspection in browser (light + dark mode)
4. Check `prefers-reduced-motion` still disables animations

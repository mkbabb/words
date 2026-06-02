# WC — Atmosphere, Depth & a11y refinement spec (words/floridify)

Lens: **Atmosphere, visual depth & a11y polish.** Refinement, not redesign. The app is stable and
built on glass-ui (`@mkbabb/glass-ui@^3.0.0` — the 5-rung glass ladder, aurora/paper backdrops,
`--shadow-cartoon-*` stack, `glass-floating`/`glass-wash` surfaces, `focus-ring`). Every recommendation
grounds in a real file:line and a specific glass-ui primitive already reachable through the caret.

---

## § Aesthetic direction — "the lit reading room"

floridify's soul is the **printed page under a warm lamp**: Fraunces throughout
(`theme.css:5-8`), KaTeX math, warm paper palette (`--background: hsl(48 15% 98%)`), SVG paper-grain
texture (`App.vue:88-97`). The type and palette commit hard. But the **depth language is inverted**:
the peripheral chrome — Sidebar (`Sidebar.vue:7` `glass-floating`), popovers, the Time Machine
(`TimeMachineVersionCard.vue:10` `glass-floating`) — uses the glass ladder richly, while the **hero
surface, the definition card, is the flattest thing on screen**: `ThemedCard.vue:4` renders opaque
`bg-card` + `shadow-cartoon-lg` with zero glass tier. The most important object reads as cardboard
while the furniture floats.

The thesis: **the definition is a lit page resting ON the reading room, not a sticker pasted over it.**
Give the hero card a real glass tier so the paper backdrop lives *behind and through* it; let the page
itself have atmosphere (a faint warm aurora wash) so glass has something to refract; and make the
depth honest in forced-colors / focus modes so the room stays legible when the lamp is off.

### Why the current depth undersells the room

| Surface | Current depth | Problem |
|---|---|---|
| Definition hero (`ThemedCard.vue:4`) | opaque `bg-card` + `shadow-cartoon-lg`, no glass | The headline object is the only flat surface; ignores the ladder its own chrome uses. |
| Page backdrop (`App.vue:88-97`) | fixed `::before` paper-texture at `opacity:.9`, flat | Static grain, no atmosphere/light — glass has nothing to refract, so floating chrome reads pasted-on. |
| Landmarks (`Home.vue:8-94`, `DefinitionDisplay.vue`) | bare `<div>` tree; only `Admin.vue` + sidebars carry roles | No `<main>`/`<article>`/`<nav>`/`<h2>` — screen readers get one undifferentiated blob; the etymology `<h3>` (`Etymology.vue:6`) floats headless. |
| Hairlines (`DefinitionDisplay.vue:130`, `Etymology.vue:4`) | `border-border/50`, `divider-h-tapered` | Inconsistent rung weights; the warm-paper border never softens to a true hairline (`--border-soft`). |
| Focus / forced-colors | `focus-ring` mixed with hand-rolled `focus-visible:ring` (`SynonymListEditable.vue:71`, `RecentItem.vue:69`); **zero** `forced-colors` blocks | Inconsistent focus vocab; glass surfaces vanish entirely in Windows High Contrast (no border fallback). |

The fix is not more decoration — it is **honest tiers** (hero gets glass, page gets light) and
**honest structure** (landmarks, one focus vocab, a forced-colors floor).

---

## § Refinement 1 — the hero card joins the glass ladder

**Surface:** `ThemedCard.vue:2-12` / `Card.vue:4`. The definition card is the visual anchor and the
only flat surface on screen.

**glass-ui lever:** the 5-rung ladder — promote the resting card body to **`glass-resting`** (the
canonical content-surface rung) instead of opaque `bg-card`, keeping `shadow-cartoon-lg` as the
lift. The paper grain (`--paper-clean-texture`) then layers *over* a translucent substrate so the
backdrop reads faintly through the page edges, exactly the "lit page on a desk" gestalt. Themed
variants (gold/silver/bronze) keep their `data-theme` accent + `BorderShimmer`; only the default
substrate swaps. Gate behind `textureIntensity`/variant so virtualized wordlist cards
(`index.css:182` `.word-card`, deliberately blur-free for Safari perf) stay opaque — glass goes on
the *one* hero, not the 100-card grid.

**Why idiomatic:** the ladder already ships and the app already uses `glass-floating`/`glass-wash`
elsewhere; this just stops exempting the headline surface from the system it lives in.

---

## § Refinement 2 — a warm aurora wash behind the room

**Surface:** `App.vue:82-98` `.app-shell::before` (flat paper grain, `z-index:-1`).

**glass-ui lever:** mount **`<Aurora>`** (`@mkbabb/glass-ui/aurora` — standalone ≈16 KiB WebGL
chunk, never dragged in by the root barrel) as a fixed, `z-index:-2` page backdrop *beneath* the
existing paper-grain `::before`, tuned to the warm palette (low-saturation `--color-gold` /
`--background` nuclei, slow drift, ~6% intensity). This gives glass something to refract: the
`glass-resting` hero (R1) and the `glass-floating` sidebar now sit over a living-light field instead
of dead grain. Honor `prefers-reduced-motion` — `useAurora` exposes a suspend source; freeze to a
static first-frame gradient (the spec's reduced-motion grammar at `index.css:103-120` already
establishes the pattern). Atmosphere over flat fill, on the compositor, payload-isolated.

---

## § Refinement 3 — semantic landmarks + heading hierarchy

**Surface:** `Home.vue:8` (page shell), `DefinitionDisplay.vue:81` (the entry wrapper),
`Sidebar.vue:6` (already `<aside>`), `Etymology.vue:6` (headless `<h3>`).

**glass-ui lever:** glass-ui ships a **`Section`** sectioning-landmark primitive
(`ui/section` — composes the typography ladder) for exactly this. Wrap `Home.vue:8`'s main column in
`<main>`, give `DefinitionDisplay.vue:81`'s entry the role of `<article aria-labelledby>` keyed to
the word title (`WordHeader` `AnimatedTitle`), and make each definition region (definitions /
etymology / phrases / thesaurus inside `DefinitionContentView`) a `<Section>` with a real `<h2>`
landmark so the etymology `<h3>` (`Etymology.vue:6`) nests under a parent rather than floating. Add a
visually-hidden skip-link to `<main>`. The Sidebar's `<aside>` gains `role="navigation"` +
`aria-label`. Zero visual change; a screen reader gains the whole document outline.

---

## § Refinement 4 — one hairline + focus vocabulary

**Surface:** dividers/borders at `DefinitionDisplay.vue:130`, `Etymology.vue:4,8`,
`Home.vue:21`; focus rings split between `focus-ring` and hand-rolled `focus-visible:ring`
(`SynonymListEditable.vue:71`, `RecentItem.vue:69`, `CreateWordListModal.vue:78`).

**glass-ui lever:** standardize on glass-ui's **`--border-soft` hairline token** + the **`focus-ring`
utility** as the single focus vocabulary. Replace ad-hoc `border-border/50` and `border-border/30`
inside the definition card with the soft-hairline rung so warm-paper edges read as one deliberate
weight; replace every hand-rolled `focus-visible:ring-2 ring-primary` with `focus-ring` so keyboard
focus is uniform across inputs, sidebar items, and the word header's pill buttons
(`WordHeader.vue:24,149` currently have hover affordances but no visible focus state on the bare
`<button>`s — a coarse-target + keyboard gap). One border weight, one focus ring, app-wide.

---

## § Refinement 5 — forced-colors floor + coarse targets

**Surface:** all glass surfaces (`Sidebar.vue`, `ThemedCard`, popovers, `TimeMachineOverlay.vue:22`);
the 32px (`h-8 w-8`) header buttons (`WordHeader.vue:24`) and 40px stacked language badges.

**glass-ui lever:** glass-ui's coarse-target floor pattern (`[data-density]` 44px coarse floor —
the DockIconButton precedent) + a **`forced-colors`** fallback layer. In Windows High Contrast /
forced-colors, `backdrop-blur` + translucent `glass-*` surfaces collapse to invisible; add a
`@media (forced-colors: active)` block (sibling to the `prefers-reduced-motion` block at
`index.css:103`) that gives every `glass-*` rung a `1px solid CanvasText` border and opaque `Canvas`
background, and pins focus to `outline: 2px solid Highlight`. Promote the 32px `h-8 w-8` header
buttons (`WordHeader.vue:24`) and pronunciation pill (`WordHeader.vue:149`) to a ≥44px coarse-pointer
floor via `@media (pointer: coarse)` so touch targets clear WCAG 2.5.5 on the hero header. Depth that
survives the lamp going off.

---

## FILE WRITTEN

`/Users/mkbabb/Programming/words/docs/tranches/A/design/WC-design-atmosphere-a11y.md`

# WC — Layout, Spatial Composition & glass-ui Component Idioms

LENS: spatial composition + glass-ui compound idioms (GlassDock / Card / InstrumentChassis / Configurator / the 5-rung tier ladder).
Scope: REFINEMENT of a stable app already on `@mkbabb/glass-ui@^3.0.0`. Spec only — no src edits.

---

## AESTHETIC DIRECTION

**"The lexicographer's bench."** floridify already owns a strong editorial identity — Fraunces display + Fira Code mono + KaTeX, a clean-paper texture wash (`App.vue:88` `--paper-clean-texture`), and `shadow-cartoon-lg` ThemedCards. The problem is not the *skin*, it's the *spatial grammar*: the entire reading surface is one predictable top-to-bottom column inside a single `ThemedCard` (`DefinitionDisplay.vue:83`) — WordHeader → tapered `<hr>` → tabs → CardContent clusters → Etymology → Phrases, every block full-bleed and stacked. It reads like a document, not an *instrument*. The direction: keep the warm-paper editorial tone, but break the monolithic stack into a **deliberately composed instrument panel** — an asymmetric header that treats the word as a masthead, glass-tier depth that separates "the word artifact" (resting/floating) from "the workbench chrome" (wash/quiet), and one orchestrated page-load reveal instead of the current scattered per-cluster fade (`DefinitionContentView` `animate-cluster-in` stagger). Atmosphere already present (paper, aurora-capable, cartoon shadows) is under-leveraged for *hierarchy*; right now every surface sits at the same z-depth.

The app reinvents several glass-ui compounds with raw divs: the TimeMachine timeline is hand-built (`TimeMachineTimeline.vue:1` — raw flex + absolute connecting line + `animate-ping` dots) when glass-ui ships `GlassTimeline`; the WordHeader's pronunciation/language/provider cluster is three bespoke pill recipes (`WordHeader.vue:24,69,149`) duplicating `glass-pill`/`MetricBadge`/`StackedIcons`; the admin toolbar is the *only* idiomatic GlassDock use (`ThemeSelector.vue:6`) and it's hidden behind admin. The tier ladder is used 36× but almost entirely as `glass-wash` (17×) — the depth range is collapsed.

---

## TOP REFINEMENTS  (surface → glass-ui lever)

### 1. Break the monolithic column — masthead header + tier-separated body
`DefinitionDisplay.vue:81-177` nests everything in one `ThemedCard` at one z-plane. **Refine:** treat the word artifact and the workbench chrome as two tiers. Keep `ThemedCard` (resting/floating tier) for the *definition body*, but lift `WordHeader` out as an **asymmetric masthead** — the word set huge and left-anchored in Fraunces (it's currently `inline` inside a wrapping flex row, `WordHeader.vue:5-9`, so the masthead collapses to body scale), with pronunciation/audio/providers as a right-gravity satellite cluster on a `glass-quiet` rung floating *over* the card's top edge (overlap, not stack). Lever: glass tier ladder (`glass-floating` card body, `glass-quiet` header chrome) + intentional negative space above the masthead. This is the single highest-impact change — it converts a document into a composed page.

### 2. Replace the hand-rolled TimeMachine timeline with `GlassTimeline`
`TimeMachineTimeline.vue:1-50` reinvents a timeline from raw flex + an absolute `h-px` connecting line + bespoke `animate-ping` selected-dot — ~120 lines duplicating a shipped primitive. **Refine:** mount `GlassTimeline` (glass-ui `/timeline`) for the version rail; it brings the connecting-line, active-node, and node-transition grammar for free and stays visually consistent with the rest of the system. Frees the bespoke CSS and makes versioning read as a first-class instrument, not a one-off widget.

### 3. Promote the WordHeader satellite cluster to glass-ui pill/badge primitives
`WordHeader.vue:24` (add button), `:69` (language badge), `:149` (pronunciation pill) are three separately hand-rolled `rounded-full border bg-background/96 shadow-cartoon-sm` recipes — the exact `glass-pill` / `MetricBadge` recipe re-implemented inline three times. **Refine:** re-express as `MetricBadge` (`/metric-badge`) for the language/IPA chips and the `glass-pill` utility for the pronunciation trigger; keep `StackedIcons` (already used `:84`) for the multi-language stack. Removes ~40 lines of duplicated pill styling, unifies hover/press states with the system's four-state contract, and makes the cluster legibly *dense* (controlled density) rather than incidentally crowded.

### 4. Surface the editing chrome as a real dock, not an admin-only overlay
`ThemeSelector.vue:6` is the app's one idiomatic `GlassDock` — but it's `absolute top-2 right-2`, admin-gated, and collapsed by default. Meanwhile the *public* reading toolbar (mode tabs, source provider tabs) is scattered: `ProviderViewTabs.vue:2` is a `<Tabs>` with **no `TabsList`** (source switching is bolted onto ProviderIcons in the header). **Refine:** consolidate the public reading controls (dictionary/thesaurus/etymology submode switch + source toggle) into a single bottom-anchored `GlassDock` with `DockLayerGroup`/`DockLayer` — the canonical "instrument chrome over a live surface" idiom. The reading column then carries *only* content; all verbs live in one floating glass instrument. This also fixes the dangling no-`TabsList` pattern: panel-nav belongs in a dock rail, not an invisible tab strip.

### 5. One orchestrated page-load reveal over scattered per-cluster fades
Today the reveal is fragmented: `Home.vue:207` `cardFadeIn`, `DefinitionContentView` per-cluster `animate-cluster-in` stagger, `ThemedCard` random sparkle delays (`ThemedCard.vue:81`), `TimeMachineTimeline` `animate-ping`. **Refine:** replace the ad-hoc keyframes with glass-ui's `useStaggerReveal` / `useSpringOrchestrator` driving ONE masthead-down cascade — word → satellite cluster → divider → first content cluster — on entry of a new word. Lever: motion composables already in the dependency. High-impact single moment > four competing micro-animations; also retires the `Math.random()` sparkle timing (`ThemedCard.vue:74-97`) that currently fights any coherent rhythm.

### Density/negative-space note
The body is dense-but-flat; the *margins* are generous (`max-w-5xl mx-auto`, `space-y-8`). Push the asymmetry: let the masthead bleed wider than the body column and let the satellite cluster overlap the card's top-right corner (refinement 1). The progressive sidebar (`Home.vue:27-35`, `14rem`) is the right negative-space lever — pair its `glass-wash` rail visually with the new bottom dock so chrome frames content on two edges.

---

## FILE WRITTEN
`/Users/mkbabb/Programming/words/docs/tranches/A/design/WC-design-layout.md`

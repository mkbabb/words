# WC — Motion & Micro-interactions refinement spec (words/floridify)

Lens: **Motion & micro-interactions.** Refinement, not redesign. The app is stable and built on
glass-ui (golden-ratio type, the 5-rung glass ladder, `@mkbabb/keyframes.js`, the AQ.W5 motion
substrate). This spec makes its glass-ui motion usage **more distinctive, more idiomatic, and more
compositor-driven** — every recommendation grounds in a real file:line and a specific glass-ui lever
already reachable through the `^3.0.0` caret (`@mkbabb/glass-ui@3.1.0`).

---

## § Aesthetic direction — "the printing press wakes up"

floridify is a dictionary: a reference object whose soul is the **printed page**. The type already
commits hard — **Fraunces** (a characterful high-contrast display serif, NOT Inter/Roboto/Space-Grotesk)
across the whole app (`src/assets/theme.css:5-8`), KaTeX math, paper-texture cards. That is a real,
non-generic point of view, and the motion does not yet serve it.

The motion thesis: **a word arrives like ink hitting paper.** One memorable, orchestrated reveal —
the **word-lookup → definition cross-fade morph** — should anchor every lookup, with the title, the
pronunciation pill, and the definition clusters settling in a single coordinated beat rather than the
current scatter of independent animations (a typewriter on the title, a `setTimeout`-gated CSS stagger
on the clusters, a hand-rolled JS scroll number on the search bar). The aesthetic is **editorial and
unhurried**: spring-eased, compositor-only, weighty but quick. Nothing bounces for its own sake.

### Why the current motion undersells the type

| Surface | Current motion | Problem |
|---|---|---|
| Word title (`AnimatedTitle.vue:19`) | `TypewriterText` keystroke sim, 120ms/char, 1.5% error rate | A typewriter is a *generic* "AI is typing" trope — it fights the printed-page identity and adds 1-2s of latency to the most important glyph on the page. |
| Definition clusters (`DefinitionContentView.vue:23,246-257`) | `setTimeout`-gated `.animate-cluster-in` class, only fires when `oldWord && newWord !== oldWord` | Stagger never plays on first paint (the highest-value moment); the `setTimeout` is main-thread and PRM-blind. |
| Search-bar shrink (`Home.vue:174-189`) | `useScroll` + hand-computed `scrollProgress`/`shrinkPercentage` cubic | A bespoke JS rAF/scroll number doing exactly what glass-ui's `useScrollProgress` / `.scroll-progress` ships, on the main thread. |
| Word → word navigation (`useRouteOrchestration.ts:60-92`) | instant store swap, no transition | The *named* A.md candidate site (§Successor "the word-lookup → definition transition") with **zero** motion. |

The fix is not more motion — it is **one orchestrated reveal** done on the compositor, and the
*removal* of the scattered, main-thread pieces that currently compete with it.

---

## § The one memorable reveal — word morph via View Transitions

**Surface:** the word-lookup → definition swap, owned by `useRouteOrchestration.ts:60-92`
(`handleDefinitionRoute`) and rendered by `DefinitionDisplay.vue` / `WordHeader.vue`.

**glass-ui lever:** `startViewTransition` + `supportsViewTransitions` from `@mkbabb/glass-ui/motion-core`
(`useViewTransition.ts`), paired with the `view-transition.css` substrate (`.gl-list-item` group recipe,
`--vt-*` tokens) — both shipped at AQ.W5 and reachable today via the `^3.0.0` caret. A.md §Spine-mapping
REFUTED motion/VT "for lack of a named consumer site"; **this is the named site.** WC promotes it from
named-forward to consumer.

**Design:**

1. **Tag the morphing elements.** In `WordHeader.vue` (the `<AnimatedTitle>` host, line 7-10) set
   `view-transition-name: word-title` on the title element, and on the pronunciation pill
   (`WordHeader.vue:148`) set `view-transition-name: word-pron`. On the definition card root
   (`DefinitionDisplay.vue:81`) set `view-transition-name: definition-card`. Names must be page-unique
   (the runtime MANDATORY) — one element per name per state.

2. **Wrap the swap.** In `handleDefinitionRoute` (`useRouteOrchestration.ts:74-80`), wrap the
   `content.setCurrentEntry(definition)` mutation:
   ```ts
   import { startViewTransition } from '@mkbabb/glass-ui/motion-core';
   // ...
   startViewTransition(() => content.setCurrentEntry(definition));
   ```
   The helper degrades to an instant synchronous call when `document.startViewTransition` is absent
   (≤20-LOC fallback already inside the helper) — no words-side branch needed. Because both the old and
   new card carry `view-transition-name: word-title`, the browser **morphs** the outgoing word's title
   into the incoming word's title on the compositor: the old definition cross-fades out, the new title
   slides in from its tagged position. This is the "ink hitting paper" beat — one coordinated reveal that
   ties title, pronunciation, and card together.

3. **Tune the look via tokens, not new CSS.** Override `--vt-duration` / `--vt-ease` on the card scope to
   land an editorial, unhurried morph (e.g. `--vt-duration: var(--duration-smooth)` ≈500ms,
   `--vt-ease: var(--ease-apple-spring)`). For the definition card add
   `view-transition-class: gl-list-item` so the slide-in/out keyframes (`gl-vt-slide-in`) apply.

4. **Reduced-motion is free.** `view-transition.css:27-33` already zeroes every VT pseudo under PRM — the
   swap still runs (state mutates instantly), just without motion. The correct degrade, no words code.

5. **a11y MANDATORY:** the helper returns `finished`; after a word morph, route focus to the new title
   (`await startViewTransition(...).finished; titleEl.focus()`) so screen-reader/keyboard users land on
   the new content. Wire this in `DefinitionDisplay` once the entry settles.

This single change makes the most-trafficked interaction in the app — looking up the next word — feel
like a designed object turning a page, and it runs entirely on the compositor.

---

## § Retire the typewriter on the title

**Surface:** `AnimatedTitle.vue` (consumed once, `WordHeader.vue:7`).

The `TypewriterText` keystroke simulation (120ms/char + correction passes) is the single most
**generic-AI** gesture in the app and it directly delays the page's hero glyph. Once the word-morph VT
(above) owns the title's entrance, the typewriter is redundant *and* counter-aesthetic.

**glass-ui lever:** delete the typewriter; let `view-transition-name: word-title` + `view-transition.css`
own the entrance. If a non-VT engine needs an entrance, fall back to a single `useSpringMount`
(`@mkbabb/glass-ui` motion) opacity+rise on the title element — one spring, terminal in ~350ms, PRM-aware
via the composable's own gate. Net: a faster, more characterful, more idiomatic reveal and one fewer
bespoke component. (Keep `TypewriterText` for the *loading* surfaces where a typing metaphor is on-theme,
e.g. the `LoadingModal` "efflorescing" text — that is a legitimate use; the *title* is not.)

---

## § Replace the hand-rolled scroll number with the native scroll timeline

**Surface:** `Home.vue:174-189` — `useScroll(window)` → `scrollProgress` (cubic ease) →
`shrinkPercentage`, threaded into `SearchBar` to drive the sticky-shrink.

**glass-ui lever:** `useScrollProgress` (`@mkbabb/glass-ui` motion) for the reactive number, OR — preferred
— the pure-CSS `.scroll-progress` recipe (`scroll-driven.css`) when the search-bar shrink can be expressed
as a `scroll()` timeline. The composable **feature-detects native `scroll()` and does not attach any
scroll/resize/RO listeners when the compositor can own it** (`useScrollProgress.ts` `NATIVE_SCROLL_TIMELINE`
gate) — exactly the INP win A.W2 is chasing. Today `Home.vue` runs a main-thread `useScroll` + cubic on
every scroll frame for a purely visual axis.

**Design:** swap the bespoke `scrollProgress` computed for `useScrollProgress({ target: searchBarEl })`,
or bind `shrinkPercentage` off a `.scroll-progress`-driven custom property. The shrink stays identical;
the work moves off the main thread on supporting engines (Chromium/Safari TP) and degrades to the
composable's JS path elsewhere. This also dovetails with A.W2's `useYieldToMain` adoption — same INP lens.

---

## § Promote the cluster stagger to the native view() timeline

**Surface:** `DefinitionContentView.vue:18-31` (the `v-for` over `DefinitionCluster`) + the
`clusterAnimReady` `setTimeout` machinery (`:246-257`) + the scoped `@keyframes clusterSlideIn` (`:272-281`).

**Two problems:** (a) the stagger only fires on a *word change* (`oldWord && newWord !== oldWord`), so the
**first** lookup — the most important reveal — gets no stagger at all; (b) the `setTimeout(600ms)`
class-toggle is main-thread and PRM-blind.

**glass-ui lever:** the `[data-scroll-reveal]` recipe from `scroll-driven.css` — fade+lift on entry, **one
`view()` timeline per child, stagger implicit** (no `setTimeout` cascade), compositor-driven, and gated
under `@media (prefers-reduced-motion: no-preference)` so PRM is automatic. Add `data-scroll-reveal` to the
`clusterContainerRef` wrapper (`DefinitionContentView.vue:13`); each `<DefinitionCluster>` child then reveals
on entry with no JS. For the *initial* coordinated beat (clusters already in-viewport on first paint), pair
with `useStaggerReveal` (`@mkbabb/glass-ui` motion) as the feature-detected fallback — it reveals immediately
under native `view()` (single-writer rule) and runs the IO-gated stagger otherwise. Delete `clusterAnimReady`,
the `setTimeout`, the `STAGGER` import, and the scoped keyframe.

This makes the cluster cascade play on **every** lookup (including the first), on the compositor, with PRM
honored by the platform — strictly more, and cheaper, than today.

---

## § Micro-interactions — make them surprising + spring-physical, not generic

The app's hover/press micro-interactions are already decent (cartoon-shadow lifts, `ease-spring-snappy`,
`scale-press` — e.g. `WordHeader.vue:24,149`). Two targeted upgrades:

1. **TimeMachine timeline scrub** (`TimeMachineTimeline.vue:20-36`) — dot selection is a CSS
   `transition-normal` size jump + an `animate-ping`. Upgrade the selected-dot travel and the connecting
   line to a **spring** via `useSpring` (`@mkbabb/glass-ui` motion / `@mkbabb/keyframes.js` runtime) so
   scrubbing versions feels like a physical detent slider, not a CSS lerp. The version-card swap
   (`TimeMachineVersionCard.vue`, already `<Transition>`-wrapped) can additionally use `startViewTransition`
   to morph between versions — the same lever as the word morph, reused (no new substrate).

2. **Audio + add-to-wordlist affordances** (`WordHeader.vue:13-30`) — these are the moments of delight in a
   reference app. The add-button lift is fine; give the audio-play button a `useSpringPress`
   (`@mkbabb/glass-ui` motion) so the press has real overshoot, and confirm the add-to-wordlist success
   with a one-shot `sparkle-sweep` (glass-ui `animations.css` keyframe) rather than a silent modal close.

All three are idiomatic glass-ui composables/keyframes already in the dependency graph — zero new runtime.

---

## § Reduced-motion — close the JS gaps

CSS PRM coverage is good (`transitions.css:80,113,174`; `index.css:102-121`; glass-ui's own VT/scroll-driven
blocks). **But the JS-timed animations are PRM-blind:**

- the cluster `setTimeout` stagger (`DefinitionContentView.vue:254`) — fixed for free by moving to
  `[data-scroll-reveal]` / `useStaggerReveal` (both PRM-gated).
- the `TimeMachineTimeline` `scrollIntoView({ behavior: 'smooth' })` (`:97`) — should read
  `prefers-reduced-motion` and pass `'auto'` under PRM.
- the new VT swaps — already PRM-correct via `view-transition.css` (no action).

**Standard:** every motion lever WC adds is either CSS-gated (`scroll-driven.css`, `view-transition.css`)
or composable-gated (the glass-ui motion composables read PRM internally). No new main-thread `setTimeout`
animation is introduced; the existing one is *deleted*.

---

## § Typography fix (motion-adjacent, one line)

`theme.css:6` sets `--font-sans: "Fraunces"` — a *serif* aliased as sans. Fraunces-everywhere is a bold,
coherent choice for the body and display, but a reference app benefits from a refined sans for dense UI
chrome (badges, the version `font-mono` labels' siblings, stat pills). **Optional refinement:** pair
Fraunces (display + body) with a characterful grotesque for chrome — but NOT Inter/Roboto/Space-Grotesk.
Candidates: **Söhne**, **格 /格Plex (IBM Plex Sans)**, or keep the all-Fraunces commitment if the
all-serif identity is intentional. This is a one-line `@theme` change, no component edits. Lowest priority;
flagged only because the sans/serif alias is almost certainly an oversight.

---

## § Implementation order (when A authorizes impl)

1. **Word morph VT** (`useRouteOrchestration.ts` + `WordHeader.vue` + `DefinitionDisplay.vue`) — the headline.
2. **Retire typewriter on title** (`AnimatedTitle.vue` → delete; `WordHeader.vue` entrance via VT/spring).
3. **Cluster stagger → `[data-scroll-reveal]`** (`DefinitionContentView.vue`) — delete the `setTimeout`.
4. **Scroll number → `useScrollProgress`/`.scroll-progress`** (`Home.vue`) — INP, dovetails with A.W2.
5. **Micro-interaction springs** (TimeMachine, audio/add buttons) — `useSpring`/`useSpringPress`/sparkle.
6. **PRM JS gaps + font alias** — cleanup.

Every item consumes an **already-shipped** glass-ui primitive (the AQ.W5 motion substrate via the `^3.0.0`
caret). Net: one new words-side artefact count of **zero** (no new substrate — pure consumption + deletion),
which keeps WC inside A.md's "adopt-not-build" and substrate-without-consumer invariants. The deletions
(typewriter title, `clusterAnimReady` setTimeout, the hand-rolled scroll cubic) are net-negative LOC.

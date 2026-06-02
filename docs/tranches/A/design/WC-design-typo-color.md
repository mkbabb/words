# WC — Typography & Color/Theme Refinement Spec

**Lens:** Typography & color/theme cohesion · dark-mode fidelity
**Scope:** REFINEMENT of glass-ui usage in the floridify dictionary SPA. No redesign — leverage glass-ui's existing golden-ratio ladder, Fraunces display axes, section-color tokens, and `light-dark()` dark mode better. Spec only.

---

## AESTHETIC DIRECTION

**"Editorial lexicon — a printed dictionary that breathes."** The app already commits to the right substrate: Fraunces (a wonky, optical-sizing variable serif), warm paper backgrounds (`hsl(48 15% 98%)`), paper-grain texture, KaTeX. That's a genuinely distinctive base — but it executes timidly. The word IS the hero of a dictionary, yet the headword renders at `text-pane-title` (a non-canonical ~`text-2xl`) and the palette is near-monochrome (`--primary: hsl(0 0% 9%)` pure neutral grey — the "timid" failure the methodology warns against). The direction: lean into **antiquarian-editorial** — make the headword a true display register with Fraunces' WONK/SOFT/opsz axes engaged, restore a **dominant ink + one warm scholarly accent** (the existing `--color-gold hsl(43 90% 55%)` / aged-ink), and use glass-ui's **section-color ladder** to color-code parts-of-speech the way a real lexicon color-codes entries. Refined, not loud: restraint executed precisely. Dark mode is already first-class (full hand-tuned `.dark` palette + texture variants) — preserve it, and route the new accents through `light-dark()` so they stay native.

---

## CURRENT STATE (grounded)

**Typography**
- `src/assets/theme.css:5-7` — Fraunces mapped to `--font-serif`/`--font-sans`/`--font-display`. Good face. But glass-ui's `--font-display-variation-settings: "WONK" 1, "SOFT" 0` and `font-optical-sizing: auto` are **never engaged** — the app sets `font-variation-settings` exactly once, in `AnimatedText.vue:158`. The headword paints as flat-weight Fraunces with default WONK, losing the face's whole character.
- `AnimatedTitle.vue:6` — headword uses `text-pane-title font-bold`, a non-canonical utility, NOT glass-ui's `text-display-*` ladder (`--type-display-1..5`, φ-scaled clamps). The display ladder (`docs`/`typography.css`) is **entirely unused** by the dictionary surface.
- `Etymology.vue:5` — `text-3xl font-semibold tracking-wide`; `DefinitionItem.vue:29` part-of-speech is `text-subheading text-muted-foreground`; body is `text-base leading-relaxed font-serif` (`:86`). Heading sizes are ad-hoc Tailwind steps (`text-3xl/4xl/2xl`) rather than the golden-ratio semantic rungs (`text-title`/`text-heading`/`text-subheading`), so vertical rhythm drifts off the √φ grid glass-ui provides.

**Color/theme**
- `theme.css:70` — `--primary: hsl(0 0% 9%)` is **pure achromatic grey**, divorced from the warm `hsl(48 …)` paper. Result: a timid, evenly-distributed palette — no dominant tone, no sharp accent. `--color-gold` exists (`:15`) but is used only for mastery bars, never as the entry/UI accent.
- glass-ui ships a 10+-rung `--section-color-*` ladder (rose/purple/indigo/teal…), each `light-dark()`-resolved (`tokens.css:439`, `:1295`). The dictionary **does not consume a single section color** — parts-of-speech, etymology, thesaurus all read `text-muted-foreground`. Maximum opportunity for "dominant-with-accents."
- Dark mode (`theme.css:100-172`) is exemplary and first-class — keep as the reference; new accents must route through `light-dark()` (the pattern glass-ui already uses at `tokens.css:1295`) so they don't regress it.

---

## TOP 5 REFINEMENTS (surface → glass-ui lever)

### 1. Promote the headword to a true display register with Fraunces axes engaged
**Surface:** `AnimatedTitle.vue:6` (`text-pane-title font-bold`).
**Lever:** glass-ui `text-display-2`/`text-display-3` utility (`typography.css` — `--type-display-2/3`, φ-scaled clamp, `font-optical-sizing: auto`, `font-variation-settings: var(--font-display-variation-settings)`, `text-wrap: balance`).
**Do:** swap `text-pane-title font-bold` → `text-display-3` (long words clamp down gracefully; opsz pushes Fraunces toward its high-contrast display cut). The headword goes from ~`text-2xl` flat to a φ²-scaled, optically-sized, WONK=1 serif — the single most memorable change. Pair with a tightened `--type-tracking-tight` (already the utility default). For a printed-dictionary touch, render the part-of-speech `<sup>` (`DefinitionItem.vue:41`) in `font-mono text-caption` italic — a typographic counterpoint the face supports.

### 2. Re-key `--primary` from achromatic grey to warm scholarly ink
**Surface:** `theme.css:70` `--primary: hsl(0 0% 9%)`; dark `:111`.
**Lever:** the token IS the lever — `--primary` is the J-invariant "token-first" entry point; consumers retune it (memory: presets in consumers).
**Do:** shift to a warm near-black aligned with the paper hue, e.g. `--primary: hsl(28 22% 12%)` (light) / keep the warm-cream dark value. This gives the whole UI (buttons, rings, active pills in `WordHeader.vue:98,137`) a dominant **warm-ink** tone instead of dead neutral grey — cohesive with `--background hsl(48 15% 98%)`. Zero structural change; it cascades through every `bg-primary`/`text-primary`/`ring-primary` already in use.

### 3. Color-code parts-of-speech via the section-color ladder (the sharp accent)
**Surface:** `DefinitionItem.vue:29` (`text-subheading text-muted-foreground`), `Etymology.vue` heading, `ThesaurusView.vue`.
**Lever:** glass-ui `--section-color-*` (`theme.css`/`tokens.css:439`, each `light-dark()`-resolved; exposed as `text-section-N` via `--color-section-N`).
**Do:** map a stable section color per part-of-speech (noun→`section-color-2` indigo, verb→`section-color-3` teal, adj→`section-color-0` rose, …) and apply to the POS label + its `border-l-2` rail (`DefinitionItem.vue:64` currently `border-accent`). A dictionary that color-keys its grammatical categories reads as *designed*, and because the ladder is `light-dark()`-native, dark mode comes free. This is the "dominant-with-sharp-accents" move — ink body, jewel-toned POS markers.

### 4. Re-base the heading hierarchy onto the golden-ratio semantic rungs
**Surface:** `Etymology.vue:5` (`text-3xl`), and the ~6 ad-hoc `text-2xl/3xl/4xl` sites surfaced in the heading grep across definition/wordlist views.
**Lever:** glass-ui semantic classes `text-title` (φ^3/2), `text-heading` (φ), `text-subheading` (√φ) — all on the √φ grid (`typography.css` scale tokens).
**Do:** replace ad-hoc Tailwind sizes with the semantic rungs so every heading lands on a φ-harmonic step. "Etymology" → `text-heading`, section labels → `text-subheading`. Restores the deliberate vertical rhythm the golden-ratio scale was built to give, which the dictionary currently bypasses. Add `text-balance` to multi-word headings (the display utilities already carry it).

### 5. Make the accent dark-mode-native via light-dark(), and warm the gold
**Surface:** `theme.css:15` `--color-gold`/`--ai-accent`; the `.dark` accent block `:135-137`.
**Lever:** glass-ui's `light-dark()` convergence pattern (`tokens.css:1264` `@supports` guard + per-mode pair).
**Do:** collapse the duplicated light/dark accent declarations into single `light-dark(light, dark)` expressions for `--color-gold`/`--color-info`/`--color-success` (matching glass-ui's own `--section-color-N: light-dark(…)` shape). One source of truth per accent, guaranteed parity, and the dictionary's accent system inherits glass-ui's dark-mode fidelity by construction rather than by hand-maintained mirror blocks. Slightly warm the gold's light value (`hsl(41 88% 50%)`) so it reads as aged-brass against paper, not amber-on-white.

---

## NOTES / GUARDRAILS

- All changes are **token + utility-class swaps** — no component-structure edits, consistent with the stable-app constraint and glass-ui's token-first invariant.
- Preserve the instant theme-swap discipline (`index.css:145-154` `.no-transition`); the accent re-key is paint-only and does not reintroduce transition jank.
- Keep accents routed through `light-dark()` so the exemplary hand-tuned `.dark` palette stays first-class — do not fork accent values into a parallel `.dark` mirror.
- Fraunces opsz/WONK engagement (Ref 1) is the highest-impact, lowest-risk single change: the face is already loaded with the full `opsz 9..144` / italic axes (`index.html:62`); the app simply isn't using them.

---

## FILE WRITTEN
`/Users/mkbabb/Programming/words/docs/tranches/A/design/WC-design-typo-color.md`

# Tranche A — the modern-web baseline (words/floridify)

A is words/floridify's first tranche. The app is a mature Vue 3.5 + vue-router 4 + Pinia + Clerk
frontend over a FastAPI + MongoDB + AI-synthesis backend (`floridify`), with a separate
`notification-server` for web-push. The constellation modern-web arc closed
(`docs/constellation/.../MODERN-WEB-CLOSE.md`) with glass-ui 3.0.0 + 3.1.0 and keyframes 2.2.0
published; words' R-CONSUME landed (20 root-barrel sites at HEAD; value.js off the eager graph via
the keyframes dynamic boundary). A picks up the **n+1** state the A5 audit surfaced: a hand-rolled
PWA that hash-rots every build, the glass-ui 3.1.0 INP/CWV substrate sitting unadopted, and a FastAPI
that ships no response-header policy. A earns words its modern-web baseline on top of the landed
R-CONSUME — adopting, not building — and the one piece of genuinely words-local substrate (the
security-header layer) mirrors muster J's server pattern without creating shared substrate.

A runs **frontend-only + backend-security**. The Python/FastAPI backend is in scope for **W3 only**
(the security-header + Fetch-Metadata middleware); every other wave is frontend.

A is in DEVELOPMENT now. W0 (scaffold + format adoption) and W1 (the Workbox PWA design) are DEV;
W2-W4 are authored-now-run-later — the implementation phase opens only on explicit user
authorization. The dev/impl boundary sits between W1 and W2.

## § Thesis

The A5 audit (`docs/constellation/next/audit/A5-keyframes-words-bbnf.md` §3) found words carrying a
**248-LOC hand-rolled service worker** (`frontend/public/service-worker.js`, `floridify-v3` cache) whose
`STATIC_ASSETS` precache list is hard-coded to UN-hashed paths (`/assets/index.css`,
`/assets/themed-cards.css`) — vite emits content-hashed asset names, so the precache list rots every
build and the listed paths 404 post-build. The corroborating smoking gun is
`frontend/public/dev-sw-cleanup.js` (36 LOC) — a shim that runs on every dev page load to UN-register
the SW and nuke all caches, because the hand-rolled SW caused real cache-staleness pain. A hand-rolled
SW that needs a per-load cleanup shim is a SW that does not work; the fix is to replace it, not patch it.

Beyond the PWA, three modern-web levers the close shipped sit unadopted in words:

- **No `content-visibility`** anywhere (`grep` → 0). words renders large lists via `@tanstack/vue-virtual`
  + custom `useVirtualGrid`/`useVirtualSectionWindow`/`useWindowedStore` (785 LOC across
  `src/composables/virtual/`), but off-screen definition cards and admin tables skip nothing.
  glass-ui 3.1.0's `.deferred-section` utility (the constellation's de-duped `content-visibility:auto`
  home) is available via the `^3.0.0` caret and unconsumed.
- **INP under the virtual-scroll + AI-synthesis render.** Word lookup → multi-definition synthesis and
  wordlist windowing are classic INP long-task sites. glass-ui 3.1.0's `useYieldToMain`
  (`scheduler.yield()` wrapper, the adopt-not-build lever) is unadopted; the client-side re-rank/filter
  paths run unbroken.
- **FastAPI ships no response-header policy.** `backend/src/floridify/api/main.py` has scoped CORS, Clerk
  auth, rate-limiting, cache-headers, structured logging, exception handlers — a solid baseline. The gap
  (`grep Strict-Transport|Content-Security-Policy|X-Content-Type|Permissions-Policy|Cross-Origin|Sec-Fetch`
  across `src/floridify/` → 0): no HSTS, no `X-Content-Type-Options: nosniff`, no `Referrer-Policy`, no
  `Permissions-Policy`, no CSP, no COOP/CORP, no Fetch-Metadata resource isolation.

A closes each lever against its real consumer site. **The PWA migration is a net deletion** (the 248-LOC
SW + the 36-LOC cleanup shim retire for `vite-plugin-pwa`/Workbox's generated, content-hash-aware SW);
the CWV/INP adoptions are pure consumption of the published glass-ui substrate (no new words-side
primitive); the security layer is one words-local FastAPI middleware that mirrors muster J's Hono pattern
without becoming shared substrate (FastAPI ≠ Hono — the stacks differ).

## § Binding question

Can words earn its modern-web baseline — a content-hash-correct Workbox PWA (retiring the hash-rotting
hand-rolled SW + the dev-cleanup shim), the glass-ui 3.1.0 `.deferred-section` + `useYieldToMain` levers
adopted on the virtual-list/synthesis hot paths, and a FastAPI security-header + report-only-CSP +
Fetch-Metadata layer (words-local, mirroring muster J) — on top of the landed 3.0.0 R-CONSUME, with the
Newly/Limited features feature-detected and the current path kept as the fallback, without regressing the
Clerk-auth, web-push, or iOS-PWA install flows, and proven by honest AFTER measurement?

## § Goal criterion

A succeeds when the modern-web baseline is earned, adopted, and measured:

- **Scaffold + format (W0)** — `docs/tranches/A/` stands up; the precepts submodule pointer is committed
  at the constellation-canonical commit (the only true precepts sync debt in the slice — §0.1 of the A5
  audit); words adopts the bbnf tranche format (this plan + PROGRESS + a close FINAL).
- **PWA → Workbox (W1 design → W2 impl)** — `vite-plugin-pwa` (Workbox under it) replaces the hand-rolled
  SW with a content-hash-aware generated precache + a real offline route + an update flow; the 248-LOC SW
  AND the 36-LOC dev-cleanup shim are deleted; the push-subscribe, install-prompt, and iOS-PWA flows are
  re-homed on the plugin's `injectManifest` (custom SW retained) or `generateSW` (config-driven) surface
  with no behavioural regression. **Net LOC deletion.**
- **CWV/INP adoption (W2)** — glass-ui's `.deferred-section` lands on the off-screen definition-card +
  admin-table surfaces; `useYieldToMain` lands on the client-side re-rank/filter + synthesis-render hot
  paths. Both are consumed-from-the-published-glass-ui, no words-side re-implementation.
- **Security baseline (W3)** — a FastAPI security-headers middleware (HSTS · `X-Content-Type-Options` ·
  `Referrer-Policy` · `Permissions-Policy` · COOP/CORP) + a **report-only** CSP (Phase 2 path to enforce)
  + Fetch-Metadata resource isolation (`Sec-Fetch-*` deny cross-site navigations to API routes) lands in
  the existing middleware stack; CORS `allow_credentials` + the scoped origin list are preserved.
- **Measure (W4)** — honest AFTER numbers: a Lighthouse/PWA-audit pass confirming the installable,
  offline-capable, no-404-precache PWA; an INP/long-task trace on the virtual-scroll + synthesis paths
  showing the yield breaking >50ms tasks; the security headers verified present on a live response.
- **Gates green, fallbacks kept** — typecheck + build + e2e green throughout; every Newly/Limited feature
  feature-detected with the current path as the ≤20-LOC fallback; the overfitting audit clean (the only
  new words-side artefact is the security middleware — words-local, single-consumer-by-nature, not shared
  substrate; everything else is adopt-or-delete).

## § Completion criterion

The development half (W0-W1) completes when the scaffold exists, the precepts pointer is committed at the
canonical commit, and the W1 Workbox design slice verifies — the `injectManifest`-vs-`generateSW`
decision, the push/install/iOS-PWA re-homing map, the offline-route + update-flow design, and the
deletion inventory (the exact 248 + 36 LOC slated to go). The implementation half (W2-W4) completes when
every wave's hard gate verifies (the build-emitted hashed precache manifest with zero 404 entries, the
deletion proof, the `.deferred-section`/`useYieldToMain` consumer sites wired, the live security-header
response capture, the INP long-task trace) and the close ceremony — overfitting audit (the security
middleware is the only new artefact; words-local, not shared substrate) + `A/FINAL.md` + honest AFTER
measurement — lands.

## § Wave sequence

The work maps onto the canonical 6-wave modern-web spine selectively — only the waves with a real,
consumer-backed lever ship; the inapplicable spine waves are refuted in-record (§ Spine mapping below).

| Wave | Disposition | Contents |
|---|---|---|
| **W0** | DEV | Scaffold + format adoption — stand up `docs/tranches/A/`; adopt the bbnf tranche format; commit the precepts submodule pointer at the canonical commit (the slice's only true precepts sync debt, A5 §0.1). |
| **W1** | DEV — boundary | Workbox PWA design slice — `vite-plugin-pwa` `injectManifest` vs `generateSW` decision; the push-subscribe + install-prompt + iOS-PWA re-homing map; the offline-route + update-flow design; the SW + cleanup-shim deletion inventory. **END OF DEV BOUNDARY.** |
| **W2** | IMPL | PWA migration + CWV/INP adoption — land the Workbox SW (retire the 248-LOC hand-roll + the 36-LOC dev-cleanup shim, a net deletion); adopt glass-ui `.deferred-section` on the off-screen card/table surfaces + `useYieldToMain` on the re-rank/filter/synthesis hot paths. |
| **W3** | IMPL | FastAPI security baseline — security-headers middleware (HSTS · nosniff · Referrer-Policy · Permissions-Policy · COOP/CORP) + report-only CSP + Fetch-Metadata, words-local, mirroring muster J's pattern; the FastAPI backend is in scope HERE ONLY. |
| **W4** | IMPL | Measure — Lighthouse/PWA audit (installable + offline + no-404 precache); INP/long-task trace on the virtual-scroll + synthesis paths; live security-header response capture; the overfitting audit + `A/FINAL.md`. |

Ordering rationale: W0 stands up the format + closes the precepts debt (the prerequisite for any
committed work). W1 designs the Workbox migration before touching the SW (the push/install/iOS-PWA flows
must be re-homed without regression — a design-first wave). W2 lands the PWA net-deletion alongside the
zero-cost glass-ui CWV/INP adoptions (they share the frontend write scope and no consumer overlap). W3 is
the only backend wave — isolated write scope (Python middleware), isolated review surface. W4 measures
AFTER, honestly, and closes. The dev/impl boundary sits at W1|W2 — implementation opens on explicit user
authorization.

### Spine mapping (canonical 6-wave modern-web spine — applicable waves only)

The constellation modern-web spine is W1 perf/INP · W2 CWV/content-visibility · W3 forms/a11y · W4
CSS-platform · W5 motion/VT · W6 security/PWA. words binds the spine where a real, consumer-backed lever
exists and **refutes the rest in-record** (no wave is invented for a feature with no consumer):

| Spine wave | Lever in words | Disposition |
|---|---|---|
| perf/INP | `useYieldToMain` on the re-rank/filter/synthesis hot paths | **BOUND** — folded into A.W2 |
| CWV/content-visibility | `.deferred-section` on off-screen cards/tables | **BOUND** — folded into A.W2 |
| forms/a11y | — | **REFUTED** — the R-CONSUME already pulled glass-ui's `:user-invalid`/`useUserInvalidAria` form vocabulary (AQ.W4); words consumes the form substrate as-shipped. No words-local forms/a11y gap the audit surfaced rises to a wave; a standalone a11y wave with no named axe-failure site is substrate-without-consumer. Re-open only if a measured axe regression surfaces. |
| CSS-platform | — | **REFUTED** — the platform-CSS substrate (`light-dark()`, `:has()`, individual transforms, tokenized scrollbars, anchor positioning) lives in glass-ui (AQ.W2/W3/W6) and reaches words through `/styles`. words has no words-local CSS-platform lever the audit named; inventing one is overfit. |
| motion/VT | — | **REFUTED** — `useViewTransition` shipped in glass-ui (AQ.W5) and is available to words via the caret, but the A5 audit named NO words consumer site for a view-transition reveal (unlike muster's verdict-reveal / fourier's route-morph). A VT adoption with no identified surface is substrate-without-consumer; named-forward to a future tranche if a route-morph or reveal surface emerges. |
| security/PWA | Workbox PWA migration (W2) + FastAPI security layer (W3) | **BOUND** — the spine's security/PWA wave splits across A.W2 (PWA) + A.W3 (security) because words' two security/PWA levers have disjoint write scopes (frontend SW vs backend middleware) and warrant separate hard gates + review surfaces. |

The spine's perf + CWV + security/PWA waves bind; forms/a11y + CSS-platform + motion/VT refute because
the substrate already shipped in glass-ui and words has no named local consumer site. A.W4 (measure) is
words' addition to the spine — the honest-AFTER discipline the constellation close demanded.

## § Inherited invariants

words inherits the constellation precepts (now in-tree via the committed submodule). Load-bearing for A:

- **No backwards-compat alias** — the Workbox migration RETIRES the hand-rolled SW + the dev-cleanup shim;
  it does not keep both live. The generated SW is the sole path; the deleted files do not linger as dead
  fallbacks.
- **Substrate-without-consumer is binary** — A creates exactly ONE new words-side artefact (the FastAPI
  security middleware), and it is words-local by nature (a server's own response-header policy, not
  shareable substrate — FastAPI ≠ Hono ≠ nginx). The CWV/INP levers are consumed FROM glass-ui (zero new
  words primitive). No cross-repo substrate is created. The bbnf-playground PWA was refused on this exact
  bar (A5 §4); words' PWA is NOT refused because words has a real install + offline + push consumer base.
- **The overfitting audit runs at close** — `docs/precepts/audits/overfitting-audit.md` against every A
  artefact. Every new artefact has ≥2 consumers OR is a demo OR is not shipped; the security middleware
  meets the bar as the single legitimate consumer of its own policy (a server-wide middleware is not an
  overfit — it is the response path for every route).
- **Baseline browser policy binds** — Widely → native; Newly → feature-detected fallback ≤20 LOC; Limited
  → progressive-only with the current path defaulted. The SW itself is Widely; Fetch-Metadata
  (`Sec-Fetch-*`) is Widely on modern browsers and degrades safe (absent headers fail-open to the
  existing CORS+auth gate); the CSP ships report-only first (the no-enforcement progressive path) before
  any enforce flip.
- **No quick solutions, no workarounds; gestalt over patch** — the dev-cleanup shim is the canonical
  workaround being deleted; A does not add another. The Workbox migration is the gestalt fix (replace the
  broken precache mechanism) over the patch (hand-edit the `STATIC_ASSETS` list to chase hashes).
- **Writing style** — precise, no grandiloquence, no editorializing; em dashes without spaces.

## § Cross-repo perimeter

A is almost entirely words-internal. The one cross-repo touch is **inward**: words consumes glass-ui
3.1.0's `.deferred-section` + `useYieldToMain` (W2) through the published package via the contract-v2
dev-resolution (the built `dist/`, not a source reach-around) — the `^3.0.0` caret already in
`frontend/package.json` resolves 3.1.0. No outward publish is required (words is a leaf SPA, not a
publisher). The FastAPI security layer (W3) is words-local and creates no cross-repo substrate; it
MIRRORS muster J's Hono security pattern as a reference, but the implementation is FastAPI-native and
shared with no one. The precepts submodule commit (W0) advances words' own gitlink to the
constellation-canonical commit — a sync INTO words, not a publish out.

Push/npm/commit authority stays the user's per the standing agent git clause; the orchestrator owns the
index and the gates; agents are edit-only / read-only-git.

## § Successor

A closes words' first modern-web baseline. Named-forward contingencies (each an exact destination, not a
vague "future tranche"):

- **CSP report-only → enforce** — the W3 CSP ships report-only; the enforce flip lands in a successor
  wave once the report endpoint has collected a clean violation window (no false-positive blocks of the
  Clerk/Stripe/CDN origins). Named-forward to **A.W3's own Phase 2** or the next words tranche.
- **`useViewTransition` adoption** — refuted at A for lack of a named consumer site; re-opens IF a
  route-morph or reveal surface emerges (the word-lookup → definition transition is the candidate). Named
  successor: the next words tranche's motion wave.
- **iOS-PWA push parity** — if the Workbox migration surfaces an iOS-Safari push-subscribe gap (the
  `useIOSPWA` flow is the fragile surface), it converges in a W2 follow-up, not a new tranche.

No A successor tranche is opened here; the named-forwards are watched conditions, not committed work.

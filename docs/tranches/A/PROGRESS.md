# Tranche A — PROGRESS

Execution log for tranche A (words/floridify's first tranche — the modern-web baseline). Updated at wave
boundaries. Plan basis — `docs/tranches/A/A.md`; the W1 Workbox design slice will land at
`design/W1-workbox-pwa.md`; the close at `FINAL.md`.

Status vocabulary — PLANNED / IN-PROGRESS / DONE / MET / MISS / NAMED-FORWARD (watched condition) /
USER-DOMAIN (cross-repo perimeter; user's push/commit authority).

## Top-line status

**A in DEVELOPMENT — plan authored; W0-W1 are DEV, W2-W4 authored-now-run-later (impl opens on explicit
user authorization).** A is words/floridify's first bbnf tranche. It earns words its modern-web baseline
on top of the landed 3.0.0 R-CONSUME: a content-hash-correct Workbox PWA replacing the 248-LOC
hash-rotting hand-rolled SW + the 36-LOC dev-cleanup shim (a NET DELETION); the glass-ui 3.1.0
`.deferred-section` + `useYieldToMain` CWV/INP levers ADOPTED on the virtual-list/synthesis hot paths
(consumed from the published substrate, no words-side re-build); and a words-local FastAPI security-header
+ report-only-CSP + Fetch-Metadata layer mirroring muster J. Frontend-only + backend-security; the
FastAPI backend is in scope for W3 only. The dev/impl boundary sits at W1|W2.

## Wave status table

| Wave | Title | Phase | Status | Evidence |
|---|---|---|---|---|
| A.W0 | Scaffold + format adoption (precepts already in-tree) | DEV | IN-PROGRESS | this scaffold (`A.md` + `PROGRESS.md`); precepts submodule pointer commit pending (USER-DOMAIN — A5 §0.1, the slice's only true sync debt) |
| A.W1 | Workbox PWA design slice. **END OF DEV BOUNDARY.** | DEV (boundary) | PLANNED | `design/W1-workbox-pwa.md` (pending) — `injectManifest` vs `generateSW`; push/install/iOS-PWA re-homing map; offline-route + update-flow; the 248+36 LOC deletion inventory |
| A.W2 | PWA migration + CWV/INP adoption | IMPL | PLANNED | Workbox SW lands; 248-LOC SW + 36-LOC dev-cleanup shim deleted; `.deferred-section` + `useYieldToMain` wired |
| A.W3 | FastAPI security baseline (backend in scope HERE ONLY) | IMPL | PLANNED | security-headers middleware + report-only CSP + Fetch-Metadata in `backend/src/floridify/api/middleware/` |
| A.W4 | Measure + close | IMPL (LAST) | PLANNED | Lighthouse/PWA audit + INP long-task trace + live security-header capture + overfitting audit + `FINAL.md` |

**Wave count: 5 (A.W0-A.W4)** — 2 DEVELOPMENT (W0 scaffold + W1 design) + 3 IMPLEMENTATION. Dev/impl
boundary at W1|W2.

## Spine mapping (record)

The canonical 6-wave modern-web spine binds selectively in words (consumer-backed levers only):

| Spine wave | Disposition in A |
|---|---|
| perf/INP | BOUND → A.W2 (`useYieldToMain`) |
| CWV/content-visibility | BOUND → A.W2 (`.deferred-section`) |
| forms/a11y | REFUTED — form vocabulary shipped in glass-ui AQ.W4, consumed as-shipped; no named words-local axe-failure site |
| CSS-platform | REFUTED — platform-CSS substrate lives in glass-ui AQ, reaches words via `/styles`; no words-local lever |
| motion/VT | REFUTED — `useViewTransition` available but NO named words consumer site; named-forward |
| security/PWA | BOUND → split A.W2 (PWA) + A.W3 (security) — disjoint write scopes warrant separate gates |

## Hard gates (per wave — verified at each close)

| Wave | Hard gate (evidence-bearing) |
|---|---|
| A.W0 | Scaffold exists (`A.md` + `PROGRESS.md` authored); the precepts submodule pointer is committed into the words parent tree at the constellation-canonical commit (`git ls-tree HEAD docs/` shows the `160000 commit` entry — today it shows none, A5 §0.1). |
| A.W1 | The Workbox design slice verifies: the `injectManifest`/`generateSW` decision is recorded with rationale; the push/install/iOS-PWA re-homing map names every current `usePWA`/`useIOSPWA` surface and its Workbox destination; the deletion inventory names the exact 248 + 36 LOC. Design reviewed; no source written. |
| A.W2 | Build-emitted `dist/sw.js` precache manifest contains ONLY content-hashed entries, ZERO 404-prone hardcoded paths (the hash-rot is gone — diff the generated manifest against the build's hashed asset list). The 248-LOC `service-worker.js` + the 36-LOC `dev-sw-cleanup.js` are deleted (deletion proof). `.deferred-section` + `useYieldToMain` appear at their named consumer sites (grep + a focused render assertion). Push-subscribe + install-prompt + iOS-PWA flows pass their existing e2e with no regression. |
| A.W3 | A live response capture (curl/e2e on a running FastAPI) shows the security headers present (HSTS · `X-Content-Type-Options: nosniff` · `Referrer-Policy` · `Permissions-Policy` · COOP/CORP) + a `Content-Security-Policy-Report-Only` header + Fetch-Metadata enforcement (a cross-site `Sec-Fetch-Site: cross-site` navigation to an API route is denied). The existing CORS scoped-origin list + `allow_credentials` are preserved (the CORS e2e still passes). |
| A.W4 | A Lighthouse/PWA audit run confirms installable + offline-capable + no-404 precache. An INP/long-task trace (the existing Playwright e2e harness) on the virtual-scroll + synthesis paths shows the yield breaking >50ms tasks. The security headers verified present on a live response. Overfitting audit clean (the security middleware is the only new artefact; words-local). `FINAL.md` authored. |

## Deferred items folded (from the A5 audit §3.1)

| A5 deferred / gap | Folded into | Disposition |
|---|---|---|
| Hand-rolled 248-LOC SW (hash-rotting precache; brittle `STATIC_ASSETS`) | A.W1 design → A.W2 impl | net-deletion via Workbox |
| `dev-sw-cleanup.js` shim (signals real staleness pain) | A.W2 | deleted alongside the SW (the shim's reason-to-exist disappears) |
| No `content-visibility` (`.deferred-section` unadopted) | A.W2 | adopt glass-ui 3.1.0 substrate |
| INP under virtual-scroll + AI-synthesis (`useYieldToMain` unadopted) | A.W2 | adopt glass-ui 3.1.0 substrate |
| FastAPI no security-headers / no CSP / no Fetch-Metadata | A.W3 | words-local middleware, mirrors muster J |
| Precepts submodule pointer uncommitted (A5 §0.1 — the only true sync debt) | A.W0 | commit the gitlink at the canonical commit |
| Honest AFTER measurement (the constellation close discipline) | A.W4 | Lighthouse + INP trace + header capture |

## Named-forward / open

- **CSP report-only → enforce** — the W3 CSP ships report-only first; the enforce flip is named-forward to
  A.W3 Phase 2 (after a clean violation window confirms no false-positive blocks of Clerk/Stripe/CDN
  origins). Watched condition, not committed-here work.
- **`useViewTransition` adoption** — REFUTED at A (no named words consumer site); re-opens if a
  route-morph / reveal surface emerges (word-lookup → definition transition is the candidate). Named
  successor: the next words tranche's motion wave.
- **iOS-PWA push parity** — if the Workbox migration surfaces an iOS-Safari push-subscribe gap (the
  `useIOSPWA` flow is the fragile surface), it converges in a W2 follow-up, not a new tranche.

## Cross-repo perimeter (USER-DOMAIN — recorded)

A is almost entirely words-internal. The one cross-repo touch is INWARD — words consumes glass-ui 3.1.0's
`.deferred-section` + `useYieldToMain` (W2) through the published package (contract-v2 dev-resolution; the
`^3.0.0` caret resolves 3.1.0). No outward publish (words is a leaf SPA). The precepts submodule commit
(W0) and any git push stay the user's authority per the standing agent git clause; the orchestrator owns
the index and the gates, agents are edit-only / read-only-git.

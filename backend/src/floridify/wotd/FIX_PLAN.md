# WOTD Streamlining and Fix Plan (Granular)

This plan enumerates concrete, incremental fixes to make `backend/src/floridify/wotd` a working, end‑to‑end pipeline that trains on synthetically generated literature data from the NEW providers module (`backend/src/floridify/providers/literature`) rather than the deprecated `wotd/literature` package. No heavy rewrite — just a careful, KISS‑forward refactor to remove hacks, fix broken codepaths, and align imports.

Status baseline from tools:
- Ruff (autofix): surfaced at least one unused variable in `embeddings.py` and did not complete due to syntax errors in deprecated `wotd/literature` code.
- MyPy: blocked by syntax errors in `wotd/literature/corpus_builder.py` (broken f-string/triple-quote); further typing checks halted.

Note: This document is an action plan only. It does not modify code.

---

## 0) High-level targets

- Train: WOTD pipeline runs fully using synthetic corpora from `providers/literature` corpus builder APIs; no network calls to the deprecated `wotd/literature` module.
- Encode: FSQ/HVQ encoders train with batched data; consistent embedding backbone across train/infer.
- Infer: Inference uses the same embedding model as training from checkpoint config.
- Deploy: SageMaker entrypoints import valid symbols and run end-to-end without NameError/ImportError.

---

## 1) Tooling and blockers to address first

- Remove/stop referencing `backend/src/floridify/wotd/literature` (deprecated and currently syntactically invalid). This directory breaks MyPy and Ruff, blocking useful feedback on the rest of the codebase.
  - Replace all imports of `.literature` or `..literature` (that refer to `wotd/literature`) with `..providers.literature` equivalents.
  - If any file still requires types/constants from the old package, port only the imports (no code duplication).
- After imports are fixed, re-run Ruff and MyPy; address:
  - Unused variable in `embeddings.py` (`actual_dim`), either remove or use.
  - Add missing type hints where trivial, especially for public APIs in `encoders.py`, `trainer.py`, `generator.py`, `inference.py`.

Deliverable: repo lints (Ruff) and type checks (MyPy) run successfully across `wotd/` after adjustments.

---

## 2) Granular fixes by file

### A) `wotd/trainer.py`
- Imports:
  - Replace any `from .literature ...` and `from ..literature ...` with `from ..providers.literature import ...` (e.g., `LiteratureCorpusBuilder`, `build_literature_training_set`), matching the new providers API.
  - Remove legacy `get_openai_connector()` paths for synthetic generation used in this module; synthetic corpora should come from providers/literature.
- Orchestration:
  - Ensure there is a single orchestrator entrypoint (function) that SageMaker can call, e.g., `train_wotd_pipeline(config: TrainingConfig, output_dir: str) -> TrainingResults`.
  - The existing class `WOTDTrainer` should be the implementation detail; the top-level function should instantiate it and return `TrainingResults`.
- Data flow:
  - Use providers/literature corpus builder to construct corpora with stable semantic labels (style/complexity/era/variation). Stop using hash‑based fallback targets; derive labels directly from corpora metadata.
  - Implement a Dataset/DataLoader for batching embeddings to the encoder (batch size configurable), replacing per-vector training loops.
- Loss plumbing:
  - Keep current reconstruction + entropy + diversity losses, but ensure they aggregate per-batch (means) with gradient clipping.
  - Provide clean hooks for optional supervised CE heads and/or InfoNCE later; do not wire by default in this sprint.
- Save/Load:
  - Confirm `semantic_encoder.pt` includes `encoder_type` and `config` as currently written; ensure `semantic_ids.json` persists tuples as lists.

### B) `wotd/encoders.py`
- Public interface:
  - `get_semantic_encoder(input_dim: int, use_fsq: bool | None = None)` already returns `UnifiedSemanticEncoder`; verify callers only use `.encode()` and `.train_step()` methods exposed by the wrapper, not the internal modules directly.
- HVQ stability:
  - If trivial, add codebook usage/perplexity logging (no deep EMA codebook update in this pass). At minimum, avoid returning lists in `indices` where ints are expected; normalize outputs to int tuples.
- FSQ minor tidy:
  - Ensure latent z normalization bounds are respected; keep bounds buffers as is.

### C) `wotd/embeddings.py`
- Remove/resolve the unused `actual_dim` assignment (or use it to set an attribute if required by callers).
- Enforce L2 renormalization after truncation (already present). Keep device fallback logic as is but simplify logs where noisy.

### D) `wotd/generator.py`
- If this module still depends on `get_openai_connector()`, convert it to use `providers/literature` synthetic generation routines or delete unused paths.
- Ensure `SyntheticGenerator.generate_complete_training_set()` pulls from providers/literature builders; unify corpus IDs to match `WOTDCorpus` expectations.

### E) `wotd/inference.py`
- Embedding parity:
  - Replace hard-coded `MiniLM` with the embedding model saved in the checkpoint `config` (use `MODEL_DIMENSIONS` to set `input_dim`).
  - Create the semantic encoder with the correct `input_dim` from `config.embedding_model`.
- Functional parity:
  - Remove mock generation if it confuses users; keep a minimal stub that clearly states “LM generation not wired in this run,” returning placeholder words.

### F) `wotd/deployment/train.py`
- Imports:
  - Replace `from wotd.trainer import train_wotd_pipeline` with the real symbol (ensure it exists post‑trainer cleanup).
- Behavior:
  - Confirm it constructs `TrainingConfig` correctly and calls the entrypoint, writing `training_results.json` to `SM_OUTPUT_DIR`.

### G) `wotd/deployment/inference.py`
- Imports:
  - Replace `from wotd.trainer import SemanticEncoder` (nonexistent) with `from wotd.encoders import get_semantic_encoder` (and use checkpoint `config` to set input dim and type).
- Serving stack:
  - If staying with Flask for now, ensure the process manager is configured (gunicorn/nginx); otherwise switch to sagemaker-inference (next phase) — keep this file minimal and correct.

### H) `wotd/sagemaker.py`
- This orchestrator looks fine; just ensure the images used actually exist in ECR. Align with DLCs in the next iteration (Dockerfiles) — not code changes here.

### I) `wotd/constants.py`
- Clarify comments: references to “BGE” while defaults are GTE-Qwen2; update docstrings/comments to avoid confusion. Keep values as is.

---

## 3) Providers integration (NEW source of truth)

- Replace all training/literature data sources with `backend/src/floridify/providers/literature`:
  - `providers/literature/corpus_builder.py` to generate synthetic corpora with explicit metadata.
  - `providers/literature/models.py` and `mappings.py` for enum/value normalization.
- Ensure the resulting corpora map cleanly to `WOTDCorpus` fields and produce deterministic semantic IDs.

---

## 4) Minimal acceptance tests (manual)

- Lint/type:
  - Ruff + MyPy pass on `wotd/` without referencing deprecated `wotd/literature`.
- Train:
  - Run training locally on a small sample (e.g., 20 corpora × 50 words), confirm artifacts saved: `semantic_encoder.pt`, `semantic_ids.json`.
- Infer:
  - Load artifacts with `WOTDInference`, encode a text snippet, produce a semantic ID, and list similar corpora.
- Deploy:
  - `deployment/train.py` runs in a container and writes `training_results.json`.

---

## 5) Streamlining sequence (no heavy refactor)

1) Remove deprecated import usages of `wotd/literature`; point to `providers/literature` across trainer/generator.
2) Add/verify `train_wotd_pipeline()` entrypoint in trainer and fix deployment train script import.
3) Enforce embedding parity in `inference.py`; create encoder with correct `input_dim` from checkpoint config.
4) Batch training in trainer (DataLoader) and maintain current loss components; add gradient clipping and early stopping (existing hooks).
5) Clean up ruff/mypy issues (unused variables, trivial hints) once syntax errors are gone.
6) Sanity test and document how to run end-to-end.

---

## 6) Known hacks/partial fixes to retire

- Hash-based semantic targets in `trainer.py` — replace with real labels from corpora metadata.
- Hard-coded MiniLM in inference — replace with checkpoint `config.embedding_model`.
- Nonexistent imports in deployment (`SemanticEncoder`, `train_wotd_pipeline`) — align with real symbols.
- Deprecated `wotd/literature` module — stop importing; do not fix it. Use `providers/literature` instead.

---

## 7) Risks and mitigations

- Providers API drift: Pin a minimal interface for corpus generation and add a thin adapter in `wotd` if needed.
- CPU/GPU variance: Keep current device fallback logic in embeddings; document small-batch defaults for MPS.
- SageMaker serving: Keep Flask in this pass; migrate to sagemaker-inference/DLCs in a subsequent, contained change.

---

## 8) Next iteration (optional)

- Add supervised multi-head CE heads (4 outputs) and optional InfoNCE (contrastive) for better ID separability.
- HVQ codebook EMA updates and perplexity/usage metrics.
- TorchScript/ONNX export for encoder and int8 PTQ for CPU.


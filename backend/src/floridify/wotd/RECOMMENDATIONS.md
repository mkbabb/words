# WOTD Semantic ID Pipeline — KISS Recommendations (2025)

This simplified plan focuses on practical wins to improve loss, speed, and overall performance without redesigning the system. It assumes we streamline imports to use the new providers-based literature pipeline and that Ruff/MyPy can run cleanly.

---

## Highest-Value Changes

- Same embeddings at train and infer: Always load the embedding model saved in the checkpoint config; stop hard-coding MiniLM in inference. Create the semantic encoder with `input_dim` derived from `MODEL_DIMENSIONS[config.embedding_model]`.
- Batch the encoder training: Use a DataLoader (64–128) with gradient clipping. Keep the current reconstruction + entropy + diversity losses, but compute on batches and early-stop on validation loss.
- Clean labels from providers: Build synthetic corpora via `providers/literature` and derive deterministic `(style, complexity, era, variation)` from corpus metadata (no hash fallbacks). Persist mappings in `semantic_ids.json`.
- Minimal HVQ hygiene: Log per-level codebook usage/perplexity to detect collapse; keep the rest of HVQ as-is for now.
- SageMaker import sanity: Ensure `deployment/train.py` calls a real `train_wotd_pipeline()` entrypoint and `deployment/inference.py` imports the encoder from `wotd.encoders`.

---

## Optional but Safe

- Cosine schedule + warmup: Use cosine LR with 10% warmup and early stopping; improves convergence without complexity.
- AMP on GPU: Enable autocast + GradScaler on CUDA; keep CPU/MPS fallbacks unchanged.
- `torch.compile`: Try compiling the encoder during training for a 5–20% speedup; keep a flag to disable if unstable.

---

## Quick Checklist

- [ ] Switch all training data to `providers/literature` (remove deprecated `wotd/literature` imports).
- [ ] Add/verify a `train_wotd_pipeline(config, output_dir)` entrypoint used by SageMaker `train.py`.
- [ ] Batch training + gradient clipping + early stopping + cosine schedule.
- [ ] Inference uses checkpoint’s embedding model and correct `input_dim`.
- [ ] Log HVQ usage/perplexity per level (detect collapse early).

---

## Expected Results

- Less training time and more stable convergence (no per-sample loops).
- Better reconstruction loss and more consistent semantic IDs from clean labels.
- Working end-to-end train → artifacts → inference with consistent embeddings.


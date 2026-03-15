"""Embedding model management and encoding for semantic search.

Handles model loading, caching, and text encoding with multiprocessing support.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np

from ...utils.logging import get_logger

logger = get_logger(__name__)


def _encode_chunk_worker(
    chunk: list[str],
    model_name: str,
    batch_size: int,
    worker_id: int,
) -> np.ndarray:
    """Worker function for multiprocessing encoding.

    Must be at module level for pickling. Each worker loads its own model instance
    to avoid shared state and GIL contention.

    Args:
        chunk: List of texts to encode
        model_name: Name/path of sentence transformer model
        batch_size: Batch size for encoding
        worker_id: Worker process ID for logging

    Returns:
        Numpy array of embeddings for the chunk
    """
    from sentence_transformers import SentenceTransformer

    # Each worker loads its own model to avoid shared state
    model = SentenceTransformer(model_name)

    # Encode the chunk (single-process within this worker)
    embeddings = model.encode(
        sentences=chunk,
        batch_size=batch_size,
        show_progress_bar=False,  # Disable to avoid clutter from multiple workers
        output_value="sentence_embedding",
        precision="float32",
        convert_to_numpy=True,
        convert_to_tensor=False,
        normalize_embeddings=True,
    )

    return embeddings


# Global model cache using asyncio lock for thread-safety
# Lazy import optimization: sentence_transformers loaded only when semantic search is used
_model_cache: dict[str, Any] = {}  # Values are SentenceTransformer instances
_model_cache_lock = asyncio.Lock()


async def get_cached_model(
    model_name: str,
    device: str = "cpu",
    use_onnx: bool = False,
) -> Any:  # Returns SentenceTransformer
    """Get or create cached sentence transformer model using global cache.

    Models are cached in-memory with a singleton pattern to avoid reloading
    the same model multiple times (critical performance optimization).

    OPTIMIZATION: sentence_transformers is imported lazily only when this function
    is called, reducing CLI boot time by ~1.3s (45% reduction).

    Args:
        model_name: HuggingFace model name
        device: Device to load model on (cpu, cuda, mps)
        use_onnx: Whether to use ONNX backend

    Returns:
        Cached or newly loaded SentenceTransformer model
    """
    cache_key = f"{model_name}:{device}:{use_onnx}"

    # Fast path: check without lock
    if cache_key in _model_cache:
        logger.debug(f"✅ Model cache HIT: {model_name} on {device}")
        return _model_cache[cache_key]

    # Slow path: load model with lock (double-check pattern)
    async with _model_cache_lock:
        # Double-check after acquiring lock
        if cache_key in _model_cache:
            logger.debug(f"✅ Model cache HIT (after lock): {model_name} on {device}")
            return _model_cache[cache_key]

        logger.info(f"⏳ Loading model {model_name} on {device} (one-time load, will be cached)")
        start_time = time.perf_counter()

        # CRITICAL FIX: Offload blocking model loading to a thread pool.
        # SentenceTransformer() loads ~600MB of weights from disk (or downloads
        # them), which blocks the event loop for 1-3s and stalls HTTP requests.
        def _load_model() -> Any:  # Returns SentenceTransformer
            from sentence_transformers import SentenceTransformer

            if use_onnx:
                try:
                    m = SentenceTransformer(model_name, backend="onnx", trust_remote_code=True)
                    logger.info("✅ ONNX backend enabled")
                    return m
                except Exception as e:
                    logger.warning(f"Failed to load ONNX model: {e}. Falling back to PyTorch")
            return SentenceTransformer(model_name, trust_remote_code=True)

        # Use a dedicated executor so loading ~600MB of weights doesn't
        # saturate the default thread pool and starve HTTP request handlers.
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-load") as executor:
            model = await loop.run_in_executor(executor, _load_model)

        # Set device for GPU acceleration (fast, no I/O)
        model = model.to(device)

        # NOTE: torch.set_num_threads() is UNSAFE when multiple OpenMP runtimes
        # are loaded (PyTorch + FAISS + scikit-learn via floridify import chain).
        # Increasing threads causes SIGSEGV in the OpenMP runtime on macOS.
        # The batch_size increase (32→128) provides the main throughput gain instead.

        # Cache the model
        _model_cache[cache_key] = model

        elapsed = time.perf_counter() - start_time
        logger.info(f"✅ Model loaded and cached in {elapsed:.2f}s: {model_name} on {device}")

        return model


def get_cached_model_sync(
    model_name: str,
    device: str = "cpu",
) -> Any:  # Returns SentenceTransformer
    """Synchronous model load, shares _model_cache with async get_cached_model().

    Used by WOTD embeddings and other sync contexts that need the same model.

    Args:
        model_name: HuggingFace model name
        device: Device to load model on (cpu, cuda, mps)

    Returns:
        Cached or newly loaded SentenceTransformer model
    """
    cache_key = f"{model_name}:{device}:False"

    if cache_key in _model_cache:
        logger.debug(f"✅ Model cache HIT (sync): {model_name} on {device}")
        return _model_cache[cache_key]

    logger.info(f"⏳ Loading model {model_name} on {device} (sync, will be cached)")
    start_time = time.perf_counter()

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, trust_remote_code=True).to(device)
    _model_cache[cache_key] = model

    elapsed = time.perf_counter() - start_time
    logger.info(f"✅ Model loaded and cached in {elapsed:.2f}s: {model_name} on {device}")

    return model

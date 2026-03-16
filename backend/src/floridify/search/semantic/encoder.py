"""Semantic encoding: text-to-embedding with quantization, multiprocessing, and Matryoshka truncation."""

from __future__ import annotations

import math
import multiprocessing as mp
import os
import platform
import time
from typing import Any, Literal

import numpy as np

from ...utils.logging import get_logger
from .constants import (
    ENABLE_GPU_ACCELERATION,
    MATRYOSHKA_DIM,
    MATRYOSHKA_DIMENSIONS,
    QUANTIZATION_PRECISION,
    USE_QUANTIZATION,
)
from .embedding import _encode_chunk_worker, get_cached_model

logger = get_logger(__name__)


class SemanticEncoder:
    """Handles text encoding to embeddings with optimizations.

    Encapsulates model initialization, device detection, quantization,
    multiprocessing orchestration, and Matryoshka truncation.

    This class is used by SemanticSearch and SemanticEmbeddingBuilder
    to encode texts into embeddings.
    """

    def __init__(self) -> None:
        self.sentence_model: Any | None = None  # SentenceTransformer
        self.device: str = "cpu"

    def detect_optimal_device(self) -> str:
        """Detect the optimal device for model execution."""
        if not ENABLE_GPU_ACCELERATION:
            return "cpu"

        import torch

        if torch.cuda.is_available():
            device_name = f"cuda:{torch.cuda.current_device()}"
            logger.info(f"GPU acceleration enabled: {torch.cuda.get_device_name()}")
            return device_name
        logger.info("Using CPU for embedding generation")
        return "cpu"

    async def initialize_model(self, model_name: str, device: str | None = None) -> Any:
        """Initialize sentence transformer with standard optimizations using cached model.

        Args:
            model_name: HuggingFace model name/path
            device: Device to load on (auto-detected if None)

        Returns:
            SentenceTransformer model instance
        """
        if device:
            self.device = device
        elif not self.device or self.device == "cpu":
            self.device = self.detect_optimal_device()

        # Get cached model (critical performance optimization - avoids reloading)
        model = await get_cached_model(
            model_name=model_name,
            device=self.device,
            use_onnx=False,
        )

        # Log quantization configuration
        quantization_status = (
            f"quantization={QUANTIZATION_PRECISION}"
            if USE_QUANTIZATION
            else "quantization=disabled"
        )

        logger.debug(f"Model ready: {model_name} on {self.device} ({quantization_status})")

        self.sentence_model = model
        return model

    def encode(
        self,
        texts: list[str],
        model_name: str,
        batch_size: int,
        use_multiprocessing: bool = True,
    ) -> np.ndarray:
        """Encode texts with optimizations (quantization + GPU acceleration + multiprocessing).

        Quantization significantly reduces memory usage and improves speed:
        - int8: 75% memory reduction, ~2-3x speedup, <2% quality loss
        - binary: 97% memory reduction, ~10x speedup, ~5-10% quality loss

        Multiprocessing provides linear speedup with CPU cores for large corpora.
        Uses sentence-transformers' native multi-process pool (process-based, not threading).

        Args:
            texts: List of texts to encode
            model_name: Model name (used for multiprocessing workers)
            batch_size: Batch size for encoding
            use_multiprocessing: Whether to use multiprocessing for large corpora

        Returns:
            Numpy array of embeddings
        """
        if not self.sentence_model:
            raise ValueError("Model required for encoding - call initialize_model() first")

        # Determine precision based on configuration and corpus size
        # INT8 quantization needs at least 100 embeddings for stable quantization ranges
        use_quantization = USE_QUANTIZATION and len(texts) >= 100

        # CRITICAL: Multi-process encoding requires float32 precision
        # Int8 quantization causes shared state issues across processes
        will_use_multiprocessing = (
            use_multiprocessing and len(texts) > 5000 and self.device == "cpu"
        )
        precision: Literal["float32", "int8", "uint8", "binary", "ubinary"] = (
            "float32"
            if will_use_multiprocessing
            # Process-safe precision
            else (QUANTIZATION_PRECISION if use_quantization else "float32")
        )

        # Multi-process encoding for large corpora on CPU
        # Uses custom multiprocessing.Pool for reliable cross-platform support
        # Each worker loads its own model to avoid shared state and GIL contention
        if will_use_multiprocessing:
            return self._encode_multiprocess(texts, model_name, batch_size, precision)
        else:
            embeddings = self._encode_single(texts, batch_size, precision)
            return self.truncate_matryoshka(embeddings, model_name)

    def _encode_multiprocess(
        self,
        texts: list[str],
        model_name: str,
        batch_size: int,
        precision: str,
    ) -> np.ndarray:
        """Encode texts using multiprocessing for large corpora on CPU.

        Args:
            texts: List of texts to encode
            model_name: Model name for worker processes
            batch_size: Batch size within each worker
            precision: Encoding precision

        Returns:
            Numpy array of embeddings
        """
        # Docker-compatible CPU detection: use sched_getaffinity for container CPU limits
        # Falls back to cpu_count() if sched_getaffinity unavailable (Windows)
        try:
            available_cpus = len(os.sched_getaffinity(0))
        except AttributeError:
            available_cpus = os.cpu_count() or 8

        # Use 2 workers to avoid OOM (each worker loads ~600MB model with spawn method)
        # With spawn, each worker gets its own copy (no memory sharing)
        # 2 workers x 600MB + main process = ~2GB total (safe under 7GB limit)
        num_workers = 2

        logger.info(
            f"Encoding {len(texts)} texts with {num_workers} parallel processes "
            f"(Docker-aware CPU detection: {available_cpus} cores, precision={precision})"
        )

        # Split texts into chunks for parallel processing
        chunk_size = math.ceil(len(texts) / num_workers)
        chunks = [texts[i : i + chunk_size] for i in range(0, len(texts), chunk_size)]

        logger.info(
            f"Split into {len(chunks)} chunks of ~{chunk_size} texts each "
            f"(batch_size={batch_size} within each worker)"
        )

        # Create worker arguments
        worker_args = [(chunk, model_name, batch_size, i) for i, chunk in enumerate(chunks)]

        # Use spawn on macOS (fork is unsafe with threads/CoreFoundation)
        # Use fork on Linux (efficient copy-on-write memory sharing)
        mp_method = "spawn" if platform.system() == "Darwin" else "fork"
        ctx = mp.get_context(mp_method)

        logger.info(
            f"Starting multiprocessing.Pool with {num_workers} workers ({mp_method} method)..."
        )
        start_time = time.perf_counter()

        with ctx.Pool(processes=num_workers) as pool:
            logger.info("Pool started, encoding chunks in parallel...")

            # Map chunks to workers and collect results
            results = pool.starmap(_encode_chunk_worker, worker_args)

        # Concatenate results from all workers
        embeddings = np.vstack(results)
        elapsed = time.perf_counter() - start_time

        logger.info(
            f"Multi-process encoding complete: {embeddings.shape} in {elapsed:.1f}s "
            f"({len(texts) / elapsed:.0f} words/sec, {num_workers} workers)"
        )

        return self.truncate_matryoshka(embeddings, model_name)

    def _encode_single(
        self,
        texts: list[str],
        batch_size: int,
        precision: str,
    ) -> np.ndarray:
        """Encode texts in single process (small batches or GPU).

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            precision: Encoding precision

        Returns:
            Numpy array of embeddings
        """
        if USE_QUANTIZATION and len(texts) > 100:
            logger.debug(
                f"Encoding {len(texts)} texts with {precision} quantization "
                f"(~{self._get_compression_ratio(precision):.0%} compression)"
            )

        embeddings = self.sentence_model.encode(
            sentences=texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 1000,
            output_value="sentence_embedding",
            precision=precision,
            convert_to_numpy=True,
            convert_to_tensor=False,
            device=self.device,
            normalize_embeddings=True,
        )
        # Model name not available here, but truncate_matryoshka handles None gracefully
        return embeddings

    @staticmethod
    def _get_compression_ratio(precision: str) -> float:
        """Calculate compression ratio for different precisions."""
        ratios = {
            "float32": 1.0,
            "int8": 0.25,
            "uint8": 0.25,
            "binary": 0.03125,  # 1/32
            "ubinary": 0.03125,
        }
        return ratios.get(precision, 1.0)

    @staticmethod
    def truncate_matryoshka(embeddings: np.ndarray, model_name: str | None = None) -> np.ndarray:
        """Truncate embeddings using Matryoshka Representation Learning.

        Only applies to MRL-capable models (Qwen3) when MATRYOSHKA_DIM is set.
        Truncated embeddings are re-normalized to maintain unit length.

        Args:
            embeddings: Embeddings to truncate
            model_name: Model name to check MRL support

        Returns:
            Truncated and re-normalized embeddings, or original if not applicable
        """
        if MATRYOSHKA_DIM is None or model_name is None:
            return embeddings

        supported_dims = MATRYOSHKA_DIMENSIONS.get(model_name)
        if not supported_dims or MATRYOSHKA_DIM not in supported_dims:
            return embeddings

        if embeddings.ndim == 1:
            truncated = embeddings[:MATRYOSHKA_DIM]
        else:
            truncated = embeddings[:, :MATRYOSHKA_DIM]

        # Re-normalize to unit length after truncation
        norms = np.linalg.norm(truncated, axis=-1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        truncated = truncated / norms

        if embeddings.shape[-1] != MATRYOSHKA_DIM:
            logger.debug(f"Matryoshka truncation: {embeddings.shape[-1]}D -> {MATRYOSHKA_DIM}D")

        return truncated

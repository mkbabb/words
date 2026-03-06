"""Centralized parallelism config. Must run before torch/faiss/numpy imports.

macOS triple-libomp problem: PyTorch + FAISS + scikit-learn each vendor
separate libomp.dylib. When OMP_NUM_THREADS > 1, competing OpenMP runtimes
cause SIGSEGV. Fix: OMP_NUM_THREADS=1, throughput via batch_size instead.
"""

from __future__ import annotations

import os
import platform

_configured = False


def configure_threading() -> None:
    """Set all parallelism env vars. Idempotent (no-op after first call)."""
    global _configured
    if _configured:
        return
    _configured = True

    is_macos = platform.system() == "Darwin"
    if is_macos:
        # Triple-libomp fix: suppress abort + force single-threaded OpenMP
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        # Apple Accelerate threading (GCD, separate from OpenMP)
        os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
        # HuggingFace tokenizers: Rayon deadlocks on fork()
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        # Prevent joblib/loky from spawning workers with broken libomp
        os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
        # MPS fallback for Apple Silicon — intentionally disabled (CPU is faster for this model size)
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    else:
        # Linux/Docker: enable parallelism (single system libomp, no conflict)
        os.environ["TOKENIZERS_PARALLELISM"] = "true"

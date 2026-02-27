#!/usr/bin/env python3
"""Run the Floridify REST API server."""

from __future__ import annotations

import os
import platform

# CRITICAL: Prevent libomp conflict on macOS (PyTorch + scikit-learn + FAISS each load separate libomp)
# OMP_NUM_THREADS=1 at import time prevents segfault; parallelism restored via torch.set_num_threads()
if platform.system() == "Darwin":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.floridify.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )

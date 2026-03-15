"""FAISS index construction with tiered optimization strategies.

Builds optimized FAISS indices based on corpus size, choosing from:
Flat L2, IVF-Flat, INT8 ScalarQuantizer, HNSW, IVF-PQ, and OPQ+IVF-PQ.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ...utils.logging import get_logger
from .constants import (
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_SEARCH,
    HNSW_M,
    LARGE_CORPUS_THRESHOLD,
    MASSIVE_CORPUS_THRESHOLD,
    MEDIUM_CORPUS_THRESHOLD,
    SMALL_CORPUS_THRESHOLD,
    USE_HNSW,
)

logger = get_logger(__name__)


def configure_faiss_threading() -> None:
    """Configure FAISS OpenMP threading for optimal performance.

    Threading is controlled via environment variables (OMP_NUM_THREADS, etc.)
    set before library initialization. No runtime calls needed.
    """
    # Environment variables (OMP_NUM_THREADS) handle threading
    # No faiss.omp_set_num_threads() call to avoid OpenMP library conflicts
    logger.debug("FAISS threading controlled by environment variables")


def calculate_optimal_nlist(vocab_size: int) -> int:
    """Calculate optimal number of IVF clusters.

    Rule of thumb: sqrt(N) to 4*sqrt(N) clusters
    More clusters = faster search but slower indexing
    """
    sqrt_n = int(math.sqrt(vocab_size))
    if vocab_size <= 100000:
        return min(1024, max(sqrt_n, vocab_size // 50))
    if vocab_size <= 250000:
        return min(2048, max(sqrt_n, vocab_size // 50))
    return min(4096, max(sqrt_n * 2, vocab_size // 50))


def build_optimized_index(
    dimension: int,
    vocab_size: int,
    sentence_embeddings: np.ndarray | None,
) -> Any:  # Returns faiss.Index
    """Build optimized FAISS index with model-aware quantization strategies.

    Quantization strategies by corpus size:

    SMALL (<10k): Exact search - no compression
      - 10k @ BGE-M3: 40MB  |  10k @ MiniLM: 15MB

    MEDIUM (10-25k): FP16 - 50% compression, <0.5% quality loss
      - 25k @ BGE-M3: 100MB->50MB  |  25k @ MiniLM: 38MB->19MB

    LARGE (25-50k): INT8 - 75% compression, ~1-2% quality loss
      - 50k @ BGE-M3: 200MB->50MB  |  50k @ MiniLM: 75MB->19MB

    MASSIVE (50-250k): HNSW (if enabled) or IVF-PQ
      HNSW: Graph-based navigation, 3-5x speedup, ~2-3% quality loss
      - 100k @ BGE-M3: 400MB->450MB  |  100k @ MiniLM: 150MB->165MB
      - 250k @ BGE-M3: 1GB->1.1GB  |  250k @ MiniLM: 375MB->410MB
      IVF-PQ: 90% compression, ~5-10% quality loss
      - 100k @ BGE-M3: 400MB->40MB  |  100k @ MiniLM: 150MB->15MB
      - 250k @ BGE-M3: 1GB->100MB  |  250k @ MiniLM: 375MB->38MB

    EXTREME (>250k): OPQ+IVF-PQ - 97% compression, ~10-15% quality loss
      - 500k @ BGE-M3: 2GB->60MB  |  500k @ MiniLM: 750MB->23MB
      - 1M @ BGE-M3: 4GB->120MB  |  1M @ MiniLM: 1.5GB->45MB

    FAISS parameters:
    - nlist: Number of IVF clusters (sqrt(N) to 4*sqrt(N))
    - nprobe: Clusters searched at query time (nlist/16 to nlist/32)
    - m: PQ subquantizers dividing vector into subspaces
    - nbits: Bits per subquantizer (8 for quality/size balance)
    - M: HNSW connections per node (bidirectional links)
    - efConstruction: HNSW build-time search depth
    - efSearch: HNSW query-time search depth (tunable)

    Args:
        dimension: Embedding vector dimension
        vocab_size: Number of vocabulary items
        sentence_embeddings: The embedding vectors to index

    Returns:
        Built and populated FAISS index
    """
    import faiss

    # Handle empty corpus
    if vocab_size == 0 or sentence_embeddings is None or sentence_embeddings.size == 0:
        logger.warning("No embeddings to index - creating empty index")
        return faiss.IndexFlatL2(dimension)

    # Memory baseline: FP32 vectors
    base_memory_mb = (vocab_size * dimension * 4) / (1024 * 1024)
    model_type = "BGE-M3" if dimension == 1024 else "MiniLM" if dimension == 384 else "Custom"

    logger.info(
        f"🔄 Building {model_type} optimized index (dim: {dimension}, vocab: {vocab_size:,}, baseline: {base_memory_mb:.1f}MB)",
    )

    if vocab_size <= SMALL_CORPUS_THRESHOLD:
        # Exact L2 search - no compression
        sentence_index = faiss.IndexFlatL2(dimension)
        sentence_index.add(sentence_embeddings)
        actual_memory_mb = base_memory_mb
        logger.info(
            f"✅ IndexFlatL2: exact search, {actual_memory_mb:.1f}MB (100% of baseline)",
        )

    elif vocab_size <= MEDIUM_CORPUS_THRESHOLD:
        # IVF-Flat - 3-5x faster than FlatL2, minimal quality loss (<0.1%)
        nlist = max(64, int(math.sqrt(vocab_size)))  # 70-122 clusters for 5k-15k
        quantizer = faiss.IndexFlatL2(dimension)
        sentence_index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)

        logger.info(f"🔄 Training IVF-Flat index (nlist={nlist} clusters)...")
        sentence_index.train(sentence_embeddings)
        sentence_index.add(sentence_embeddings)

        # Optimize for latency: search 25% of clusters
        sentence_index.nprobe = max(16, nlist // 4)

        expected_memory_mb = base_memory_mb * 1.05  # 5% overhead for index structure
        logger.info(
            f"✅ IVF-Flat: {expected_memory_mb:.1f}MB (~100% of {base_memory_mb:.1f}MB), "
            f"nlist={nlist}, nprobe={sentence_index.nprobe}, <0.1% quality loss, 3-5x speedup"
        )

    elif vocab_size <= LARGE_CORPUS_THRESHOLD:
        # INT8 quantization - 4x compression, small quality loss
        sentence_index = faiss.IndexScalarQuantizer(
            dimension,
            faiss.ScalarQuantizer.QT_8bit,
        )
        sentence_index.train(sentence_embeddings)
        sentence_index.add(sentence_embeddings)
        expected_memory_mb = base_memory_mb * 0.25
        logger.info(
            f"✅ INT8 Quantization: {expected_memory_mb:.1f}MB (25% of {base_memory_mb:.1f}MB), ~1-2% quality loss",
        )

    elif vocab_size <= MASSIVE_CORPUS_THRESHOLD:
        # Choose between HNSW and IVF-PQ based on configuration
        if USE_HNSW:
            # HNSW - faster than IVF-PQ with minimal quality loss
            # 3-5x speedup with graph-based navigation
            sentence_index = faiss.IndexHNSWFlat(dimension, HNSW_M)

            # Set build-time search depth
            sentence_index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION

            logger.info(
                f"🔄 Building HNSW index (M={HNSW_M}, efConstruction={HNSW_EF_CONSTRUCTION})..."
            )
            sentence_index.add(sentence_embeddings)

            # Set query-time search depth (tunable for latency/quality)
            sentence_index.hnsw.efSearch = HNSW_EF_SEARCH

            # HNSW memory: ~(4 + M * 2) bytes per connection
            # For M=32: ~68 bytes per vector + original vectors
            hnsw_overhead_per_vec = 4 + HNSW_M * 2
            hnsw_overhead_mb = (vocab_size * hnsw_overhead_per_vec) / (1024 * 1024)
            expected_memory_mb = base_memory_mb + hnsw_overhead_mb
            compression_ratio = expected_memory_mb / base_memory_mb

            logger.info(
                f"✅ HNSW: {expected_memory_mb:.1f}MB ({compression_ratio * 100:.0f}% of {base_memory_mb:.1f}MB), "
                f"efSearch={HNSW_EF_SEARCH}, ~2-3% quality loss, 3-5x speedup"
            )
        else:
            # IVF with Product Quantization - high compression
            nlist = calculate_optimal_nlist(vocab_size)
            # Adjust m based on dimension: more subquantizers for higher dims
            m = 64 if dimension >= 1024 else 32 if dimension >= 512 else 16
            nbits = 8  # 8 bits per subquantizer for quality

            quantizer = faiss.IndexFlatL2(dimension)
            sentence_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

            logger.info(f"🔄 Training IVF-PQ (nlist={nlist} clusters, m={m} subquantizers)...")
            sentence_index.train(sentence_embeddings)
            sentence_index.add(sentence_embeddings)

            # nprobe: search top k% of clusters
            sentence_index.nprobe = min(nlist // 16, 128)
            compression_ratio = (m * nbits) / (dimension * 32)
            expected_memory_mb = base_memory_mb * compression_ratio
            logger.info(
                f"✅ IVF-PQ: {expected_memory_mb:.1f}MB ({compression_ratio * 100:.0f}% of {base_memory_mb:.1f}MB), ~5-10% quality loss",
            )

    else:
        # OPQ + IVF-PQ - maximum compression for huge corpora
        nlist = min(8192, vocab_size // 25)
        m = 64 if dimension >= 768 else 32
        nbits = 8

        # OPQ: Optimized Product Quantization - rotates space for better quantization
        quantizer = faiss.IndexFlatL2(dimension)
        opq_transform = faiss.OPQMatrix(dimension, m)
        pq_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)
        sentence_index = faiss.IndexPreTransform(opq_transform, pq_index)

        logger.info(f"🔄 Training OPQ+IVF-PQ (nlist={nlist}, m={m})...")
        sentence_index.train(sentence_embeddings)
        sentence_index.add(sentence_embeddings)

        # More aggressive nprobe for large indices
        base_index = faiss.downcast_index(sentence_index.index)
        base_index.nprobe = min(nlist // 32, 256)
        compression_ratio = 0.03  # ~3% of original size
        expected_memory_mb = base_memory_mb * compression_ratio
        logger.info(
            f"✅ OPQ+IVF-PQ: {expected_memory_mb:.1f}MB ({compression_ratio * 100:.0f}% of {base_memory_mb:.1f}MB), ~10-15% quality loss",
        )

    return sentence_index

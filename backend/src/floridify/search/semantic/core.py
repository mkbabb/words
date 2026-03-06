"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import asyncio
import hashlib
import math
import multiprocessing as mp
import os
import platform
import time
from typing import Any, Literal

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ...caching.core import get_global_cache
from ...caching.models import CacheNamespace, VersionConfig
from ...corpus.core import Corpus
from ...corpus.manager import get_tree_corpus_manager
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..result import SearchResult
from .constants import (
    DEFAULT_SENTENCE_MODEL,
    ENABLE_GPU_ACCELERATION,
    L2_DISTANCE_NORMALIZATION,
    QUANTIZATION_PRECISION,
    USE_QUANTIZATION,
    SemanticModel,
)
from .embedding import _encode_chunk_worker, get_cached_model
from .index_builder import build_optimized_index, configure_faiss_threading
from .models import SemanticIndex
from .persistence import (
    load_embeddings_from_binary_data,
    load_faiss_index_from_binary_data,
    save_embeddings_and_index,
)

logger = get_logger(__name__)


class SemanticSearch:
    def __init__(
        self,
        index: SemanticIndex | None = None,
        corpus: Corpus | None = None,
        query_cache_size: int = 100,
    ):
        """Initialize semantic search with index and optional corpus.

        Args:
            index: Pre-loaded SemanticIndex containing all data
            corpus: Optional corpus for runtime operations
            query_cache_size: Size of LRU cache for query embeddings (default: 100)

        """
        # Data model
        self.index = index
        self.corpus = corpus

        # Runtime objects (built from index)
        self.sentence_model: SentenceTransformer | None = None
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None
        self.device: str = "cpu"

        # Query embedding cache (LRU)
        self.query_cache: dict[str, np.ndarray] = {}
        self.query_cache_size = query_cache_size
        self.query_cache_order: list[str] = []  # For LRU tracking

        # Result cache (LRU) - cache final search results
        self.result_cache: dict[str, list[SearchResult]] = {}
        self.result_cache_order: list[str] = []
        self.result_cache_size = 500  # Cache up to 500 unique searches

        # Debounced flush tasks for persisting caches to L2
        self._flush_task: asyncio.Task[None] | None = None
        self._result_flush_task: asyncio.Task[None] | None = None

        # Note: _load_from_index is now async, caller must await it after construction
        # This is handled in from_corpus() and from_index() class methods

    @classmethod
    async def from_corpus(
        cls,
        corpus: Corpus,
        model_name: SemanticModel = DEFAULT_SENTENCE_MODEL,
        config: VersionConfig | None = None,
        batch_size: int | None = None,
    ) -> SemanticSearch:
        """Create SemanticSearch from a corpus.

        Args:
            corpus: Corpus to build semantic index from
            model_name: Sentence transformer model to use
            config: Version configuration
            batch_size: Batch size for embedding generation

        Returns:
            SemanticSearch instance with loaded index

        """
        # Get or create index (no longer saves immediately)
        index = await SemanticIndex.get_or_create(
            corpus=corpus,
            model_name=model_name,
            batch_size=batch_size,
            config=config or VersionConfig(),
        )

        # Create search with index
        search = cls(index=index, corpus=corpus)

        # FIX: Check if embeddings actually exist (not just the fields)
        # Require both num_embeddings > 0 AND actual data present
        # binary_data is properly typed as dict[str, str] | None
        has_embeddings = index.num_embeddings > 0 and index.binary_data is not None

        if has_embeddings:
            logger.info(
                f"Loading semantic index from cache for '{corpus.corpus_name}' "
                f"({index.num_embeddings:,} embeddings)"
            )
            await search._load_from_index()
        else:
            logger.info(
                f"Building new semantic embeddings for '{corpus.corpus_name}' "
                f"({len(corpus.vocabulary):,} words)"
            )
            await search.initialize()

            # Verify embeddings were built (empty corpora are valid - they just have 0 embeddings)
            if search.sentence_embeddings is not None and search.sentence_embeddings.size > 0:
                logger.info(
                    f"✅ Built semantic index: {search.index.num_embeddings:,} embeddings, "
                    f"{search.index.embedding_dimension}D"
                )
            else:
                logger.info(
                    f"✅ Created semantic index for empty corpus '{corpus.corpus_name}' (0 embeddings)"
                )

        return search

    async def _load_from_index(self) -> None:
        """Load data from the index model with proper binary_data handling."""
        if not self.index:
            logger.warning("No index to load from")
            return

        # FIX: Check if embeddings exist before trying to load
        if self.index.num_embeddings == 0:
            logger.warning(
                f"Index for '{self.index.corpus_name}' has 0 embeddings, cannot load. "
                f"Will need to rebuild."
            )
            return

        # Set device from index
        self.device = self.index.device

        # Initialize model if needed
        if not self.sentence_model:
            self.sentence_model = await self._initialize_optimized_model()

        # FIX: Load from binary_data (external storage) instead of inline fields
        # The embeddings and index_data fields are not populated when loading from cache
        # binary_data is properly typed as dict[str, str] | None in SemanticIndex
        binary_data = self.index.binary_data

        if not binary_data:
            logger.error(
                f"No binary data found for index '{self.index.corpus_name}' "
                f"(num_embeddings={self.index.num_embeddings})"
            )
            raise RuntimeError(
                f"Semantic index missing binary data - cache corrupted for '{self.index.corpus_name}'"
            )

        # Load embeddings and FAISS index - current format only, no legacy support
        # CRITICAL FIX: Offload blocking gzip decompression and FAISS deserialization
        # to a thread pool so the event loop stays responsive. For 278K-word corpora
        # this can take several seconds of CPU-bound decompression.
        try:
            corpus_name = self.index.corpus_name
            self.sentence_embeddings = await asyncio.to_thread(
                load_embeddings_from_binary_data, binary_data, corpus_name
            )
            self.sentence_index = await asyncio.to_thread(
                load_faiss_index_from_binary_data, binary_data, corpus_name
            )

            # Restore persisted caches from L2
            await self._load_query_cache_from_l2()
            await self._load_result_cache_from_l2()

        except Exception as e:
            logger.error(f"Failed to load embeddings/index from cache: {e}", exc_info=True)
            # Reset to trigger rebuild
            self.sentence_embeddings = None
            self.sentence_index = None
            raise RuntimeError(
                f"Corrupted semantic index for '{self.index.corpus_name}': {e}"
            ) from e

    def _detect_optimal_device(self) -> str:
        """Detect the optimal device for model execution."""
        if not ENABLE_GPU_ACCELERATION:
            return "cpu"

        if torch.cuda.is_available():
            device_name = f"cuda:{torch.cuda.current_device()}"
            logger.info(f"🚀 GPU acceleration enabled: {torch.cuda.get_device_name()}")
            return device_name
        logger.info("💻 Using CPU for embedding generation")
        return "cpu"

    async def _initialize_optimized_model(self) -> SentenceTransformer:
        """Initialize sentence transformer with standard optimizations using cached model."""
        if not self.index:
            raise ValueError("Index required to initialize model")

        # Detect optimal device if not set
        if not self.device or self.device == "cpu":
            self.device = self._detect_optimal_device()
            self.index.device = self.device

        # Get cached model (critical performance optimization - avoids reloading)
        model = await get_cached_model(
            model_name=self.index.model_name,
            device=self.device,
            use_onnx=False,
        )

        # Log quantization configuration
        quantization_status = (
            f"quantization={QUANTIZATION_PRECISION}"
            if USE_QUANTIZATION
            else "quantization=disabled"
        )

        logger.debug(
            f"Model ready: {self.index.model_name} on {self.device} ({quantization_status})"
        )
        return model

    def _get_cached_query_embedding(self, query: str) -> np.ndarray | None:
        """Get cached query embedding using LRU eviction.

        Args:
            query: Normalized query string

        Returns:
            Cached embedding if available, None otherwise

        """
        # Generate cache key from query (use hash for consistent keys)
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if cache_key in self.query_cache:
            # Move to end of LRU order (most recently used)
            if cache_key in self.query_cache_order:
                self.query_cache_order.remove(cache_key)
            self.query_cache_order.append(cache_key)
            return self.query_cache[cache_key]

        return None

    def _cache_query_embedding(self, query: str, embedding: np.ndarray) -> None:
        """Cache query embedding with LRU eviction and L2 persistence.

        Args:
            query: Normalized query string
            embedding: Query embedding to cache

        """
        cache_key = hashlib.md5(query.encode()).hexdigest()

        # LRU eviction if cache is full
        if len(self.query_cache) >= self.query_cache_size:
            if self.query_cache_order:
                # Remove least recently used
                oldest_key = self.query_cache_order.pop(0)
                self.query_cache.pop(oldest_key, None)

        # Add to cache
        self.query_cache[cache_key] = embedding
        self.query_cache_order.append(cache_key)

        # Schedule debounced flush to L2
        self._schedule_query_cache_flush()

    def _get_result_cache_key(self, query: str) -> str:
        """Generate cache key for search results (query-only for max reuse)."""
        return hashlib.md5(query.encode()).hexdigest()

    def _get_cached_results(
        self, query: str, max_results: int, min_score: float
    ) -> list[SearchResult] | None:
        """Get cached search results using LRU eviction. Truncates from full cache."""
        cache_key = self._get_result_cache_key(query)

        if cache_key in self.result_cache:
            # Move to end of LRU order (most recently used)
            if cache_key in self.result_cache_order:
                self.result_cache_order.remove(cache_key)
            self.result_cache_order.append(cache_key)
            # Filter and truncate from cached full result set
            cached = self.result_cache[cache_key]
            return [r for r in cached if r.score >= min_score][:max_results]

        return None

    def _cache_results(
        self, query: str, max_results: int, min_score: float, results: list[SearchResult]
    ) -> None:
        """Cache search results with LRU eviction. Stores full result set."""
        cache_key = self._get_result_cache_key(query)

        # LRU eviction if cache is full
        if len(self.result_cache) >= self.result_cache_size:
            if self.result_cache_order:
                # Remove least recently used
                oldest_key = self.result_cache_order.pop(0)
                self.result_cache.pop(oldest_key, None)

        # Add to cache
        self.result_cache[cache_key] = results
        self.result_cache_order.append(cache_key)

        # Schedule debounced flush to L2
        self._schedule_result_cache_flush()

    def _query_cache_l2_key(self) -> str:
        """L2 cache key for this index's query embedding cache."""
        return f"query_embed_cache:{self.index.corpus_uuid}:{self.index.model_name}"

    async def _load_query_cache_from_l2(self) -> None:
        """Load persisted query embeddings from L2 cache on startup."""
        if not self.index:
            return
        cache = await get_global_cache()
        cached = await cache.get(
            namespace=CacheNamespace.SEMANTIC,
            key=self._query_cache_l2_key(),
        )
        if not isinstance(cached, dict):
            return
        count = 0
        for key, emb_bytes in cached.items():
            if isinstance(emb_bytes, bytes):
                self.query_cache[key] = np.frombuffer(emb_bytes, dtype=np.float32).copy()
                self.query_cache_order.append(key)
                count += 1
        if count > 0:
            logger.debug(f"Loaded {count} cached query embeddings from L2")

    def _schedule_query_cache_flush(self) -> None:
        """Schedule a debounced (5s) flush of query cache to L2."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        try:
            loop = asyncio.get_running_loop()
            self._flush_task = loop.create_task(self._debounced_flush())
        except RuntimeError:
            # TODO[MEDIUM]: Replace no-loop flush skip with explicit initialization/lifecycle invariant.
            pass

    async def _debounced_flush(self) -> None:
        """Wait 5s then persist query cache to L2."""
        await asyncio.sleep(5.0)
        if not self.index or not self.query_cache:
            return
        cache = await get_global_cache()
        serializable = {k: v.tobytes() for k, v in self.query_cache.items()}
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=self._query_cache_l2_key(),
            value=serializable,
        )
        logger.debug(f"Flushed {len(serializable)} query embeddings to L2")

    # --- Result cache L2 persistence ---

    def _result_cache_l2_key(self) -> str:
        """L2 cache key for this index's result cache."""
        return f"result_cache:{self.index.corpus_uuid}:{self.index.model_name}"

    async def _load_result_cache_from_l2(self) -> None:
        """Load persisted search results from L2 cache on startup."""
        if not self.index:
            return
        cache = await get_global_cache()
        cached = await cache.get(
            namespace=CacheNamespace.SEMANTIC,
            key=self._result_cache_l2_key(),
        )
        if not isinstance(cached, dict):
            return
        count = 0
        for key, results_data in cached.items():
            if isinstance(results_data, list):
                self.result_cache[key] = [SearchResult.model_validate(r) for r in results_data]
                self.result_cache_order.append(key)
                count += 1
        if count > 0:
            logger.debug(f"Loaded {count} cached search results from L2")

    def _schedule_result_cache_flush(self) -> None:
        """Schedule a debounced (5s) flush of result cache to L2."""
        if self._result_flush_task and not self._result_flush_task.done():
            self._result_flush_task.cancel()
        try:
            loop = asyncio.get_running_loop()
            self._result_flush_task = loop.create_task(self._debounced_result_flush())
        except RuntimeError:
            # TODO[MEDIUM]: Replace no-loop flush skip with explicit initialization/lifecycle invariant.
            pass

    async def _debounced_result_flush(self) -> None:
        """Wait 5s then persist result cache to L2."""
        await asyncio.sleep(5.0)
        if not self.index or not self.result_cache:
            return
        cache = await get_global_cache()
        serializable = {
            k: [r.model_dump(mode="json") for r in results]
            for k, results in self.result_cache.items()
        }
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=self._result_cache_l2_key(),
            value=serializable,
        )
        logger.debug(f"Flushed {len(serializable)} search result sets to L2")

    def _encode(self, texts: list[str], use_multiprocessing: bool = True) -> np.ndarray:
        """Encode texts with optimizations (quantization + GPU acceleration + multiprocessing).

        Quantization significantly reduces memory usage and improves speed:
        - int8: 75% memory reduction, ~2-3x speedup, <2% quality loss
        - binary: 97% memory reduction, ~10x speedup, ~5-10% quality loss

        Multiprocessing provides linear speedup with CPU cores for large corpora.
        Uses sentence-transformers' native multi-process pool (process-based, not threading).
        """
        if not self.sentence_model or not self.index:
            raise ValueError("Model and index required for encoding")

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
                f"(batch_size={self.index.batch_size} within each worker)"
            )

            # Create worker arguments
            worker_args = [
                (chunk, self.index.model_name, self.index.batch_size, i)
                for i, chunk in enumerate(chunks)
            ]

            # Use spawn on macOS (fork is unsafe with threads/CoreFoundation)
            # Use fork on Linux (efficient copy-on-write memory sharing)
            mp_method = "spawn" if platform.system() == "Darwin" else "fork"
            ctx = mp.get_context(mp_method)

            logger.info(
                f"Starting multiprocessing.Pool with {num_workers} workers ({mp_method} method)..."
            )
            start_time = time.perf_counter()

            with ctx.Pool(processes=num_workers) as pool:
                logger.info("✅ Pool started, encoding chunks in parallel...")

                # Map chunks to workers and collect results
                results = pool.starmap(_encode_chunk_worker, worker_args)

            # Concatenate results from all workers
            embeddings = np.vstack(results)
            elapsed = time.perf_counter() - start_time

            logger.info(
                f"✅ Multi-process encoding complete: {embeddings.shape} in {elapsed:.1f}s "
                f"({len(texts) / elapsed:.0f} words/sec, {num_workers} workers)"
            )

            return embeddings
        else:
            # Single-process for small batches or GPU
            if USE_QUANTIZATION and len(texts) > 100:
                logger.debug(
                    f"Encoding {len(texts)} texts with {precision} quantization "
                    f"(~{self._get_compression_ratio(precision):.0%} compression)"
                )

            return self.sentence_model.encode(
                sentences=texts,
                batch_size=self.index.batch_size,
                show_progress_bar=len(texts) > 1000,
                output_value="sentence_embedding",
                precision=precision,
                convert_to_numpy=True,
                convert_to_tensor=False,
                device=self.device,
                normalize_embeddings=True,
            )

    def _get_compression_ratio(self, precision: str) -> float:
        """Calculate compression ratio for different precisions."""
        ratios = {
            "float32": 1.0,
            "int8": 0.25,
            "uint8": 0.25,
            "binary": 0.03125,  # 1/32
            "ubinary": 0.03125,
        }
        return ratios.get(precision, 1.0)

    async def initialize(self) -> None:
        """Initialize semantic search by building embeddings."""
        if not self.index:
            raise ValueError("Index required for initialization")

        if not self.corpus:
            # Try to load corpus from index - use corpus_uuid for lookup
            # CRITICAL: use_cache=False to avoid loading stale corpus after test modifications
            manager = get_tree_corpus_manager()
            self.corpus = await manager.get_corpus(
                corpus_uuid=self.index.corpus_uuid,
                corpus_name=self.index.corpus_name,
                config=VersionConfig(use_cache=False),
            )

        if not self.corpus:
            raise ValueError(
                f"Could not load corpus '{self.index.corpus_name}' (UUID: {self.index.corpus_uuid})"
            )

        # CRITICAL FIX: Validate UUID consistency between index and corpus
        if self.corpus.corpus_uuid != self.index.corpus_uuid:
            raise ValueError(
                f"UUID MISMATCH: SemanticIndex references corpus_uuid={self.index.corpus_uuid}, "
                f"but loaded corpus has corpus_uuid={self.corpus.corpus_uuid}. "
                f"This indicates index corruption or stale cache. "
                f"Solution: Rebuild semantic index for corpus '{self.corpus.corpus_name}'."
            )

        logger.info(
            f"Initializing semantic search for corpus '{self.index.corpus_name}' using {self.index.model_name}",
        )

        # Initialize model if not already done
        if not self.sentence_model:
            self.device = self._detect_optimal_device()
            self.index.device = self.device
            self.sentence_model = await self._initialize_optimized_model()

        await self._build_embeddings_from_corpus()

    async def update_corpus(self, corpus: Corpus) -> None:
        """Update corpus and reinitialize if vocabulary hash has changed.

        Args:
            corpus: New corpus instance

        """
        if not self.index:
            raise ValueError("Index required for corpus update")

        if corpus.vocabulary_hash != self.index.vocabulary_hash:
            logger.info(
                f"Vocabulary hash changed for corpus '{corpus.corpus_name}', reinitializing semantic search",
            )
            self.corpus = corpus

            # Create new index with updated corpus
            self.index = await SemanticIndex.create(
                corpus=corpus,
                model_name=self.index.model_name,
                batch_size=self.index.batch_size,
            )

            # Clear existing runtime data to force rebuild
            self.sentence_embeddings = None
            self.sentence_index = None
            self.result_cache.clear()
            self.result_cache_order.clear()

            await self._build_embeddings_from_corpus()
        else:
            # Just update the corpus reference
            self.corpus = corpus

    async def _build_embeddings_from_corpus(self) -> None:
        """Build or load embeddings using corpus instance."""
        if not self.corpus or not self.index:
            raise ValueError("Corpus and index required")

        vocabulary_hash = self.corpus.vocabulary_hash

        # Check if vocabulary has changed to avoid unnecessary rebuilding
        if (
            self.index.vocabulary_hash == vocabulary_hash
            and self.sentence_embeddings is not None
            and self.sentence_embeddings.size > 0
        ):
            logger.debug("Vocabulary unchanged and embeddings exist, skipping rebuild")
            return

        self.index.vocabulary_hash = vocabulary_hash

        # Build embeddings using pre-computed lemma mappings from Corpus
        logger.info("Building new semantic embeddings using pre-computed lemmas")

        start_time = time.perf_counter()
        # CRITICAL FIX: Offload blocking embedding work to a thread pool so
        # the async event loop stays responsive for HTTP requests while the
        # (potentially minutes-long) encoding runs in background.
        await asyncio.to_thread(self._build_embeddings)
        build_time_seconds = time.perf_counter() - start_time

        logger.info(f"Built semantic embeddings in {build_time_seconds * 1000:.1f}ms")

        # Save embeddings to index
        await save_embeddings_and_index(
            index=self.index,
            sentence_embeddings=self.sentence_embeddings,
            sentence_index=self.sentence_index,
            build_time=build_time_seconds,
            corpus_uuid=self.corpus.corpus_uuid if self.corpus else self.index.corpus_uuid,
        )

    def _build_embeddings(self) -> None:
        """Build streamlined semantic embeddings - sentence transformers only."""
        if not self.corpus or not self.index:
            raise ValueError("Corpus and index required")

        # Check if lemmatized vocabulary is available
        if not self.corpus.lemmatized_vocabulary:
            logger.warning(
                f"Corpus '{self.corpus.corpus_name}' has empty lemmatized vocabulary - no embeddings to build"
            )
            # Set empty embeddings and index for consistency
            self.sentence_embeddings = np.array([], dtype=np.float32).reshape(
                0, 1024
            )  # BGE-M3 dimension
            self.index.variant_mapping = {}
            return

        # Process entire vocabulary at once for better performance
        vocab_count = len(self.corpus.lemmatized_vocabulary)
        logger.info(f"🔄 Starting embedding generation: {vocab_count:,} lemmas")

        embedding_start = time.time()

        # Use lemmatized vocabulary directly - it's already normalized/processed
        embedding_vocabulary = self.corpus.lemmatized_vocabulary

        # Create trivial identity mapping since we're using lemmas directly
        variant_mapping = {i: i for i in range(len(embedding_vocabulary))}

        # Store int→int variant mapping directly (no str conversion)
        self.index.variant_mapping = variant_mapping

        logger.info(
            f"🔄 Using {len(embedding_vocabulary)} lemmatized embeddings directly (no re-normalization)",
        )

        # Process in batches for large vocabularies with progress tracking
        # Batching provides visibility into progress while multiprocessing provides speed
        # CRITICAL: Batch size must exceed 5000 to trigger multiprocessing in _encode()
        # Larger batches = better throughput with cpu_count()-1 workers
        if len(embedding_vocabulary) > 100000:
            batch_size = 15000  # Massive corpora: maximize throughput
        elif len(embedding_vocabulary) > 50000:
            batch_size = 12000  # Large corpora: balance speed & memory
        else:
            batch_size = 8000  # Medium corpora: conservative

        if len(embedding_vocabulary) > batch_size:
            logger.info(
                f"🔄 Processing {len(embedding_vocabulary):,} lemmas in batches of {batch_size:,}"
            )
            embeddings_list = []
            total_batches = (len(embedding_vocabulary) + batch_size - 1) // batch_size

            for i in range(0, len(embedding_vocabulary), batch_size):
                batch = embedding_vocabulary[i : i + batch_size]
                batch_num = i // batch_size + 1
                progress_pct = (batch_num / total_batches) * 100

                # Log every 5th batch or first/last batch (reduces 36+ logs to ~8 logs)
                if batch_num % 5 == 0 or batch_num == 1 or batch_num == total_batches:
                    logger.info(
                        f"  📊 Batch {batch_num}/{total_batches} ({progress_pct:.0f}% complete)"
                    )
                else:
                    logger.debug(
                        f"  📊 Batch {batch_num}/{total_batches} ({progress_pct:.0f}% complete)"
                    )

                batch_start = time.time()
                try:
                    # Use thread-based parallel encoding (implemented in _encode)
                    batch_embeddings = self._encode(batch, use_multiprocessing=True)
                    batch_time = time.time() - batch_start

                    # Log completion only for logged start batches
                    if batch_num % 5 == 0 or batch_num == 1 or batch_num == total_batches:
                        logger.debug(
                            f"    ✅ Batch {batch_num} complete in {batch_time:.1f}s "
                            f"({len(batch) / batch_time:.0f} words/sec)"
                        )

                    embeddings_list.append(batch_embeddings)

                except Exception as e:
                    logger.error(f"Failed to encode batch {batch_num}: {e}")
                    raise

            # Concatenate all batches
            self.sentence_embeddings = np.vstack(embeddings_list)
            logger.info(
                f"✅ Completed {len(embeddings_list)} batches - {len(embedding_vocabulary):,} lemmas encoded"
            )
        else:
            # Small vocabulary - use thread-based parallel encoding
            logger.info(
                f"🔄 Processing {len(embedding_vocabulary):,} lemmas (small corpus, no batching)"
            )
            self.sentence_embeddings = self._encode(embedding_vocabulary, use_multiprocessing=True)

        # Safety check for empty embeddings
        if self.sentence_embeddings.size == 0:
            raise ValueError("No valid embeddings generated from vocabulary")

        # CRITICAL FIX: Explicitly normalize embeddings to unit length
        # Some models (e.g., GTE-Qwen2) don't normalize despite normalize_embeddings=True
        norms_before = np.linalg.norm(self.sentence_embeddings, axis=1, keepdims=True)
        logger.info(
            f"Embedding norms before normalization - min: {norms_before.min():.6f}, max: {norms_before.max():.6f}, mean: {norms_before.mean():.6f}"
        )

        # Normalize to unit length (L2 norm = 1.0)
        self.sentence_embeddings = self.sentence_embeddings / norms_before

        # Verify normalization
        norms_after = np.linalg.norm(self.sentence_embeddings, axis=1)
        is_normalized = np.allclose(norms_after, 1.0, atol=0.01)
        logger.info(
            f"Embedding norms after normalization - min: {norms_after.min():.6f}, max: {norms_after.max():.6f}, mean: {norms_after.mean():.6f}"
        )
        logger.info(f"✅ Embeddings normalized: {is_normalized}")

        if not is_normalized:
            logger.warning(
                "⚠️ Embeddings not properly normalized after normalization step - L2 distances may be inaccurate"
            )

        # Ensure C-contiguous memory layout for optimal FAISS performance
        if not self.sentence_embeddings.flags.c_contiguous:
            self.sentence_embeddings = np.ascontiguousarray(self.sentence_embeddings)
            logger.debug("✅ Memory layout optimized: C-contiguous array")

        # Log memory usage
        memory_mb = self.sentence_embeddings.nbytes / (1024 * 1024)
        logger.info(f"✅ Embeddings optimized: {memory_mb:.1f}MB")

        # Build FAISS index for sentence embeddings with dynamic optimization
        dimension = self.sentence_embeddings.shape[1]
        vocab_size = len(self.corpus.lemmatized_vocabulary)

        logger.info(
            f"🔄 Building FAISS index (dimension: {dimension}, vocab_size: {vocab_size:,})...",
        )

        # Configure FAISS threading before building index
        configure_faiss_threading()

        # Model-aware optimized quantization strategy
        self.sentence_index = build_optimized_index(dimension, vocab_size, self.sentence_embeddings)

        total_time = time.time() - embedding_start
        embeddings_per_sec = vocab_count / total_time if total_time > 0 else 0

        # Update index statistics
        self.index.num_embeddings = vocab_count
        self.index.embedding_dimension = dimension

        logger.info(
            f"✅ Semantic embeddings complete: {vocab_count:,} embeddings, dim={dimension} ({total_time:.1f}s, {embeddings_per_sec:.0f} emb/s)",
        )

    def _load_index_from_data(self, index_data: SemanticIndex) -> None:
        """Load index from data object - current format only."""
        binary_data = index_data.binary_data

        if not binary_data:
            raise RuntimeError(
                f"Semantic index for '{self.index.corpus_name}' missing binary_data - "
                f"cache corrupted or invalid format"
            )

        self.sentence_embeddings = load_embeddings_from_binary_data(
            binary_data, self.index.corpus_name
        )
        self.sentence_index = load_faiss_index_from_binary_data(binary_data, self.index.corpus_name)

    def _lookup_vocab_embedding(self, normalized_query: str) -> np.ndarray | None:
        """Look up pre-computed embedding for in-vocabulary queries.

        Three O(1) lookups: vocabulary_to_index → word_to_lemma_indices → sentence_embeddings.
        Returns None for out-of-vocabulary queries (which fall through to transformer encoding).
        """
        if self.corpus is None or self.sentence_embeddings is None:
            return None

        # Corpus vocabulary_to_index uses batch_normalize → normalize_comprehensive
        # (lowercased + diacritics stripped + contractions expanded). Apply the same
        # normalization here so "café", "CAFÉ", "Café" all match the "cafe" key.
        from floridify.text.normalize import normalize

        lookup_key = normalize(normalized_query)

        # O(1) dict lookup: normalized word → vocabulary index
        word_idx = self.corpus.vocabulary_to_index.get(lookup_key)
        if word_idx is None:
            return None

        # O(1) dict lookup: word index → lemma index
        lemma_idx = self.corpus.word_to_lemma_indices.get(word_idx)
        if lemma_idx is None:
            return None

        # O(1) array access: lemma index → pre-computed embedding
        # variant_mapping is embedding_idx→lemma_idx, but currently always identity.
        # Use lemma_idx directly as embedding index (embeddings are stored in lemma order).
        if lemma_idx < 0 or lemma_idx >= len(self.sentence_embeddings):
            return None

        return self.sentence_embeddings[lemma_idx]

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform semantic similarity search using sentence embeddings.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results with scores

        """
        if self.sentence_index is None:
            logger.warning("Semantic search not initialized - no index")
            return []

        if self.sentence_embeddings is None or self.sentence_embeddings.size == 0:
            logger.warning("Semantic search not initialized - no embeddings")
            return []

        if not self.corpus:
            logger.warning("Semantic search not initialized - no corpus")
            return []

        try:
            # Normalize query to match corpus normalization
            normalized_query = query.strip() if query else ""
            if not normalized_query:
                return []

            # Check result cache first (fastest path)
            cached_results = self._get_cached_results(normalized_query, max_results, min_score)
            if cached_results is not None:
                return cached_results

            # Fast path: look up pre-computed embedding for in-vocabulary words (~0.001ms)
            query_embedding = self._lookup_vocab_embedding(normalized_query)

            if query_embedding is None:
                # Check embedding cache
                query_embedding = self._get_cached_query_embedding(normalized_query)

            if query_embedding is None:
                # Cache miss - generate embedding asynchronously (releases GIL)
                query_embedding = await asyncio.to_thread(self._encode, [normalized_query])
                query_embedding = query_embedding[0]

                if query_embedding is None:
                    return []

                # Cache the embedding for future queries
                self._cache_query_embedding(normalized_query, query_embedding)

            # Search using FAISS asynchronously (releases GIL)
            distances, indices = await asyncio.to_thread(
                self.sentence_index.search,
                query_embedding.astype("float32").reshape(1, -1),
                max_results + min(max_results, 10),  # Adaptive buffer for score filtering
            )

            # Convert distances to similarity scores (1 - normalized_distance)
            # L2 distance range is [0, 2] for normalized vectors
            similarities = 1 - (distances[0] / L2_DISTANCE_NORMALIZATION)

            # Pre-filter valid indices and scores for batch processing
            embedding_vocab_size = len(self.sentence_embeddings)
            valid_mask = (
                (indices[0] >= 0)
                & (similarities >= min_score)
                & (indices[0] < embedding_vocab_size)
            )
            valid_embedding_indices = indices[0][valid_mask]
            valid_similarities = similarities[valid_mask]

            # Create results directly - no complex mapping needed since we use lemmas directly
            results = []
            lemma_to_word_indices = self.corpus.lemma_to_word_indices

            # Get variant mapping from index if available (already int→int)
            variant_mapping = self.index.variant_mapping if self.index else {}

            for embedding_idx, similarity in zip(
                valid_embedding_indices,
                valid_similarities,
                strict=False,
            ):
                # Use variant mapping from index or direct mapping
                lemma_idx = variant_mapping.get(embedding_idx, embedding_idx)

                if lemma_idx >= len(self.corpus.lemmatized_vocabulary):
                    continue  # Skip invalid indices

                lemma = self.corpus.lemmatized_vocabulary[lemma_idx]

                # Map lemma index to original word
                if lemma_idx < len(lemma_to_word_indices):
                    original_word_indices = lemma_to_word_indices[lemma_idx]
                    # Use first index if multiple mappings exist
                    if isinstance(original_word_indices, list) and original_word_indices:
                        word = self.corpus.get_original_word_by_index(original_word_indices[0])
                    elif isinstance(original_word_indices, int):
                        word = self.corpus.get_original_word_by_index(original_word_indices)
                    else:
                        word = lemma
                else:
                    word = lemma  # Direct use if mapping unavailable

                # Only add result if we have a valid word
                if word:
                    results.append(
                        SearchResult(
                            word=word,
                            lemmatized_word=lemma,
                            score=float(similarity),
                            method=SearchMethod.SEMANTIC,
                            language=None,
                            metadata=None,
                        ),
                    )

                if len(results) >= max_results:
                    break

            # Cache results for future queries
            self._cache_results(normalized_query, max_results, min_score, results)

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise RuntimeError(f"Semantic search failed for query '{normalized_query}': {e}") from e

    def model_dump(self) -> dict[str, Any]:
        """Serialize semantic search to dictionary for caching."""
        if not self.index:
            return {}

        # Delegate to index model for serialization
        return self.index.model_dump()

    @classmethod
    async def model_load(cls, data: dict[str, Any]) -> SemanticSearch:
        """Deserialize semantic search from cached dictionary."""
        # Load index from data
        index = SemanticIndex.model_load(data)

        # Create instance with loaded index
        instance = cls(index=index)

        # Load runtime objects from index
        await instance._load_from_index()

        return instance

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the semantic search index."""
        if not self.index:
            return {
                "initialized": False,
                "vocabulary_size": 0,
                "embedding_dim": 0,
                "model_name": "",
                "corpus_name": "",
                "semantic_metadata_id": None,
                "batch_size": 0,
            }

        return {
            "initialized": self.sentence_index is not None,
            "vocabulary_size": self.index.num_embeddings,
            "embedding_dim": self.index.embedding_dimension,
            "model_name": self.index.model_name,
            "corpus_name": self.index.corpus_name,
            "semantic_metadata_id": f"{self.index.corpus_name}:{self.index.model_name}",
            "batch_size": self.index.batch_size,
        }

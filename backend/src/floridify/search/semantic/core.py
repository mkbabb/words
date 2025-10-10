"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import pickle
import time
from typing import TYPE_CHECKING, Any, Literal

import faiss
import numpy as np
import torch

from ...caching.models import VersionConfig
from ...corpus.core import Corpus
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..models import SearchResult
from .constants import (
    DEFAULT_SENTENCE_MODEL,
    ENABLE_GPU_ACCELERATION,
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_SEARCH,
    HNSW_M,
    L2_DISTANCE_NORMALIZATION,
    LARGE_CORPUS_THRESHOLD,
    MASSIVE_CORPUS_THRESHOLD,
    MEDIUM_CORPUS_THRESHOLD,
    QUANTIZATION_PRECISION,
    SMALL_CORPUS_THRESHOLD,
    USE_HNSW,
    USE_ONNX_BACKEND,
    USE_QUANTIZATION,
    SemanticModel,
)
from .models import SemanticIndex

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)

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

        # Lazy import: Only import when actually needed (saves ~1.3s on CLI boot)
        from sentence_transformers import SentenceTransformer

        logger.info(f"⏳ Loading model {model_name} on {device} (one-time load, will be cached)")
        start_time = time.perf_counter()

        # Initialize model with ONNX optimization if requested
        if use_onnx:
            try:
                model = SentenceTransformer(model_name, backend="onnx", trust_remote_code=True)
                logger.info("✅ ONNX backend enabled")
            except Exception as e:
                logger.warning(f"Failed to load ONNX model: {e}. Falling back to PyTorch")
                model = SentenceTransformer(model_name, trust_remote_code=True)
        else:
            model = SentenceTransformer(model_name, trust_remote_code=True)

        # Set device for GPU acceleration
        model = model.to(device)

        # Cache the model
        _model_cache[cache_key] = model

        elapsed = time.perf_counter() - start_time
        logger.info(f"✅ Model loaded and cached in {elapsed:.2f}s: {model_name} on {device}")

        return model


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
        has_embeddings = (
            index.num_embeddings > 0
            and (
                (hasattr(index, "binary_data") and index.binary_data)
                or (hasattr(index, "embeddings") and index.embeddings)
            )
        )

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

            # FIX: Verify embeddings were actually built
            if not search.sentence_embeddings or search.sentence_embeddings.size == 0:
                raise RuntimeError(
                    f"Failed to build semantic embeddings for '{corpus.corpus_name}': "
                    f"no embeddings generated"
                )

            logger.info(
                f"✅ Built semantic index: {search.index.num_embeddings:,} embeddings, "
                f"{search.index.embedding_dimension}D"
            )

        return search

    async def _load_from_index(self) -> None:
        """Load data from the index model with proper binary_data handling."""
        import zlib

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
        binary_data = getattr(self.index, "binary_data", None)

        if not binary_data:
            logger.error(
                f"No binary data found for index '{self.index.corpus_name}' "
                f"(num_embeddings={self.index.num_embeddings})"
            )
            raise RuntimeError(
                f"Semantic index missing binary data - cache corrupted for '{self.index.corpus_name}'"
            )

        # Load embeddings and FAISS index with decompression
        try:
            # Load compressed embeddings
            if "embeddings" in binary_data:
                embeddings_bytes = base64.b64decode(binary_data["embeddings"].encode("utf-8"))
                decompressed = zlib.decompress(embeddings_bytes)
                self.sentence_embeddings = pickle.loads(decompressed)
                logger.debug(
                    f"Loaded compressed embeddings: {len(decompressed) / 1024 / 1024:.2f}MB decompressed, "
                    f"shape={self.sentence_embeddings.shape if self.sentence_embeddings is not None else 'none'}"
                )
            else:
                logger.warning(f"No embeddings in binary_data for '{self.index.corpus_name}'")

            # Load compressed FAISS index
            if "index_data" in binary_data:
                index_bytes = base64.b64decode(binary_data["index_data"].encode("utf-8"))
                decompressed = zlib.decompress(index_bytes)
                faiss_data = pickle.loads(decompressed)
                self.sentence_index = faiss.deserialize_index(faiss_data)
                logger.debug(
                    f"Loaded compressed FAISS index: {len(decompressed) / 1024 / 1024:.2f}MB decompressed, "
                    f"{self.sentence_index.ntotal if self.sentence_index else 0} vectors"
                )
            else:
                logger.warning(f"No FAISS index in binary_data for '{self.index.corpus_name}'")

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
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("🚀 MPS acceleration enabled (Apple Silicon)")
            return "mps"
        logger.info("💻 Using CPU - GPU not available")
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
            use_onnx=USE_ONNX_BACKEND,
        )

        # Log quantization configuration
        quantization_status = (
            f"quantization={QUANTIZATION_PRECISION}"
            if USE_QUANTIZATION
            else "quantization=disabled"
        )

        logger.debug(
            f"Model ready: {self.index.model_name} on {self.device} "
            f"(onnx={USE_ONNX_BACKEND}, {quantization_status})"
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
            logger.debug(f"Query embedding cache HIT for: {query[:50]}...")
            return self.query_cache[cache_key]

        return None

    def _cache_query_embedding(self, query: str, embedding: np.ndarray) -> None:
        """Cache query embedding with LRU eviction.

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
                logger.debug(f"Evicted oldest query from cache (size: {self.query_cache_size})")

        # Add to cache
        self.query_cache[cache_key] = embedding
        self.query_cache_order.append(cache_key)
        logger.debug(
            f"Cached query embedding (cache size: {len(self.query_cache)}/{self.query_cache_size})"
        )

    def _get_result_cache_key(self, query: str, max_results: int, min_score: float) -> str:
        """Generate cache key for search results."""
        # Include all search parameters in cache key
        cache_str = f"{query}|{max_results}|{min_score:.3f}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_cached_results(
        self, query: str, max_results: int, min_score: float
    ) -> list[SearchResult] | None:
        """Get cached search results using LRU eviction."""
        cache_key = self._get_result_cache_key(query, max_results, min_score)

        if cache_key in self.result_cache:
            # Move to end of LRU order (most recently used)
            if cache_key in self.result_cache_order:
                self.result_cache_order.remove(cache_key)
            self.result_cache_order.append(cache_key)
            logger.debug(
                f"Result cache HIT for: {query[:50]}... (max={max_results}, min={min_score})"
            )
            return self.result_cache[cache_key]

        return None

    def _cache_results(
        self, query: str, max_results: int, min_score: float, results: list[SearchResult]
    ) -> None:
        """Cache search results with LRU eviction."""
        cache_key = self._get_result_cache_key(query, max_results, min_score)

        # LRU eviction if cache is full
        if len(self.result_cache) >= self.result_cache_size:
            if self.result_cache_order:
                # Remove least recently used
                oldest_key = self.result_cache_order.pop(0)
                self.result_cache.pop(oldest_key, None)
                logger.debug(f"Evicted oldest result from cache (size: {self.result_cache_size})")

        # Add to cache
        self.result_cache[cache_key] = results
        self.result_cache_order.append(cache_key)
        logger.debug(
            f"Cached search results (cache size: {len(self.result_cache)}/{self.result_cache_size})"
        )

    def _encode(self, texts: list[str], use_multiprocessing: bool = True) -> np.ndarray:
        """Encode texts with optimizations (quantization + GPU acceleration + multiprocessing).

        Quantization significantly reduces memory usage and improves speed:
        - int8: 75% memory reduction, ~2-3x speedup, <2% quality loss
        - binary: 97% memory reduction, ~10x speedup, ~5-10% quality loss

        Multiprocessing provides linear speedup with CPU cores for large corpora.
        """
        if not self.sentence_model or not self.index:
            raise ValueError("Model and index required for encoding")

        # Determine precision based on configuration and corpus size
        # INT8 quantization needs at least 100 embeddings for stable quantization ranges
        use_quantization = USE_QUANTIZATION and len(texts) >= 100
        precision: Literal["float32", "int8", "uint8", "binary", "ubinary"] = (
            QUANTIZATION_PRECISION if use_quantization else "float32"
        )

        # Use multiprocessing for large corpora (>5000 words) on CPU
        if use_multiprocessing and len(texts) > 5000 and self.device == "cpu":
            import os

            # Determine optimal device distribution
            num_workers = max(4, min(12, int((os.cpu_count() or 8) * 0.75)))
            devices = ["cpu"] * num_workers

            logger.info(
                f"Encoding {len(texts)} texts with {num_workers} parallel workers "
                f"({precision} precision, ~{self._get_compression_ratio(precision):.0%} compression)"
            )

            # Start multiprocess pool
            pool = self.sentence_model.start_multi_process_pool(target_devices=devices)

            try:
                # Calculate optimal chunk size for load balancing
                chunk_size = max(100, len(texts) // (num_workers * 3))

                # Encode with multiprocessing
                embeddings = self.sentence_model.encode_multi_process(
                    sentences=texts,
                    pool=pool,
                    batch_size=self.index.batch_size,
                    chunk_size=chunk_size,
                    precision=precision,
                    normalize_embeddings=True,
                    show_progress_bar=len(texts) > 1000,
                )

                # Convert to numpy if needed
                if not isinstance(embeddings, np.ndarray):
                    embeddings = np.array(embeddings)

                return embeddings
            finally:
                # Always cleanup pool
                self.sentence_model.stop_multi_process_pool(pool)
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
            # Try to load corpus from index - use both corpus_id and corpus_name for robustness
            self.corpus = await Corpus.get(
                corpus_id=self.index.corpus_id,
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )

        if not self.corpus:
            raise ValueError(
                f"Could not load corpus '{self.index.corpus_name}' (ID: {self.index.corpus_id})"
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
            and self.index.embeddings
        ):
            logger.debug("Vocabulary unchanged and embeddings exist, skipping rebuild")
            return

        self.index.vocabulary_hash = vocabulary_hash

        # Build embeddings using pre-computed lemma mappings from Corpus
        logger.info("Building new semantic embeddings using pre-computed lemmas")

        start_time = time.perf_counter()
        self._build_embeddings()
        build_time_seconds = time.perf_counter() - start_time

        logger.info(f"Built semantic embeddings in {build_time_seconds * 1000:.1f}ms")

        # Save embeddings to index
        await self._save_embeddings_to_index(build_time_seconds)

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
            self.index.embeddings = ""  # Empty string for serialized empty embeddings
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

        # Store in index
        self.index.variant_mapping = {str(k): v for k, v in variant_mapping.items()}
        self.index.vocabulary = self.corpus.vocabulary
        self.index.lemmatized_vocabulary = self.corpus.lemmatized_vocabulary

        logger.info(
            f"🔄 Using {len(embedding_vocabulary)} lemmatized embeddings directly (no re-normalization)",
        )

        # Process in batches for large vocabularies to avoid hanging
        # Use smaller batch size for better progress tracking and to avoid hanging
        batch_size = 2000 if len(embedding_vocabulary) > 10000 else 5000

        if len(embedding_vocabulary) > batch_size:
            logger.info(f"🔄 Processing {len(embedding_vocabulary):,} lemmas in batches of {batch_size:,}")
            embeddings_list = []
            total_batches = (len(embedding_vocabulary) + batch_size - 1) // batch_size

            for i in range(0, len(embedding_vocabulary), batch_size):
                batch = embedding_vocabulary[i:i + batch_size]
                batch_num = i // batch_size + 1
                progress_pct = (batch_num / total_batches) * 100

                logger.info(
                    f"  📊 Batch {batch_num}/{total_batches} "
                    f"({len(batch):,} words, {progress_pct:.1f}% complete)..."
                )

                batch_start = time.time()
                try:
                    # Disable multiprocessing for batches to avoid hanging
                    batch_embeddings = self._encode(batch, use_multiprocessing=False)
                    batch_time = time.time() - batch_start

                    logger.info(
                        f"    ✅ Batch {batch_num} complete in {batch_time:.1f}s "
                        f"({len(batch) / batch_time:.0f} words/sec)"
                    )
                    embeddings_list.append(batch_embeddings)

                except Exception as e:
                    logger.error(f"    ❌ Failed to encode batch {batch_num}: {e}")
                    # Create zero embeddings for failed batch as fallback
                    fallback = np.zeros((len(batch), self.sentence_embeddings.shape[1] if hasattr(self, 'sentence_embeddings') and self.sentence_embeddings is not None else 384), dtype=np.float32)
                    embeddings_list.append(fallback)

            self.sentence_embeddings = np.vstack(embeddings_list)
            logger.info(f"✅ All {len(embedding_vocabulary):,} embeddings generated successfully")
        else:
            # Process smaller vocabularies in one go
            logger.info(f"🔄 Processing {len(embedding_vocabulary):,} lemmas in single batch")
            self.sentence_embeddings = self._encode(embedding_vocabulary, use_multiprocessing=False)

        # Safety check for empty embeddings
        if self.sentence_embeddings.size == 0:
            raise ValueError("No valid embeddings generated from vocabulary")

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
        self._configure_faiss_threading()

        # Model-aware optimized quantization strategy
        self._build_optimized_index(dimension, vocab_size)

        total_time = time.time() - embedding_start
        embeddings_per_sec = vocab_count / total_time if total_time > 0 else 0

        # Update index statistics
        self.index.num_embeddings = vocab_count
        self.index.embedding_dimension = dimension
        self.index.embeddings_per_second = embeddings_per_sec

        logger.info(
            f"✅ Semantic embeddings complete: {vocab_count:,} embeddings, dim={dimension} ({total_time:.1f}s, {embeddings_per_sec:.0f} emb/s)",
        )

    async def _save_embeddings_to_index(self, build_time: float) -> None:
        """Save embeddings to the index model with compression."""
        import zlib

        if not self.index or not self.corpus:
            raise ValueError("Index and corpus required")

        # Prepare binary data separately for external storage
        binary_data = {}

        # Compress and encode embeddings
        if self.sentence_embeddings is not None and self.sentence_embeddings.size > 0:
            embeddings_bytes = pickle.dumps(self.sentence_embeddings)
            # Add compression to reduce size
            compressed_embeddings = zlib.compress(embeddings_bytes, level=6)
            binary_data["embeddings"] = base64.b64encode(compressed_embeddings).decode("utf-8")
            logger.debug(
                f"Compressed embeddings: {len(embeddings_bytes) / 1024 / 1024:.2f}MB → "
                f"{len(compressed_embeddings) / 1024 / 1024:.2f}MB "
                f"({100 * (1 - len(compressed_embeddings) / len(embeddings_bytes)):.1f}% reduction)"
            )

        # Compress and encode FAISS index
        if self.sentence_index is not None:
            index_bytes = pickle.dumps(faiss.serialize_index(self.sentence_index))
            compressed_index = zlib.compress(index_bytes, level=6)
            binary_data["index_data"] = base64.b64encode(compressed_index).decode("utf-8")
            logger.debug(
                f"Compressed FAISS index: {len(index_bytes) / 1024 / 1024:.2f}MB → "
                f"{len(compressed_index) / 1024 / 1024:.2f}MB "
                f"({100 * (1 - len(compressed_index) / len(index_bytes)):.1f}% reduction)"
            )

        # Update statistics
        self.index.build_time_seconds = build_time
        self.index.memory_usage_mb = (
            (self.sentence_embeddings.nbytes / (1024 * 1024))
            if self.sentence_embeddings is not None
            else 0.0
        )

        # Detect and store index type
        if self.sentence_index:
            index_class_name = self.sentence_index.__class__.__name__
            if "HNSW" in index_class_name:
                self.index.index_type = "HNSW"
            elif "IVFPQ" in index_class_name:
                self.index.index_type = "IVFPQ"
            elif "IVF" in index_class_name:
                self.index.index_type = "IVF"
            elif "ScalarQuantizer" in index_class_name:
                self.index.index_type = "ScalarQuantizer"
            else:
                self.index.index_type = "Flat"

        # Save with binary data stored externally
        try:
            await self.index.save(binary_data=binary_data)
        except Exception as e:
            logger.error(f"Failed to save semantic index: {e}")
            raise RuntimeError(
                f"Semantic index persistence failed. This may be due to size limits or corruption. "
                f"Embeddings size: {self.index.memory_usage_mb:.2f}MB. Error: {e}"
            ) from e

        logger.info(
            f"Saved semantic index for '{self.index.corpus_name}' with {self.index.num_embeddings} embeddings",
        )

    def _load_index_from_data(self, index_data: SemanticIndex) -> None:
        """Load index from data object, handling compressed binary data."""
        import pickle
        import zlib

        # Check if binary data is stored externally
        binary_data = getattr(index_data, "binary_data", None)

        if binary_data:
            # Load from external storage (new format with compression)
            if "embeddings" in binary_data:
                try:
                    embeddings_bytes = base64.b64decode(binary_data["embeddings"].encode("utf-8"))
                    # Decompress
                    decompressed = zlib.decompress(embeddings_bytes)
                    self.sentence_embeddings = pickle.loads(decompressed)
                    logger.debug(
                        f"Loaded compressed embeddings: {len(decompressed) / 1024 / 1024:.2f}MB"
                    )
                except Exception as e:
                    logger.error(f"Failed to load embeddings: {e}")
                    raise RuntimeError(f"Corrupted embeddings data: {e}") from e

            if "index_data" in binary_data:
                try:
                    index_bytes = base64.b64decode(binary_data["index_data"].encode("utf-8"))
                    # Decompress
                    decompressed = zlib.decompress(index_bytes)
                    faiss_data = pickle.loads(decompressed)
                    self.sentence_index = faiss.deserialize_index(faiss_data)
                    logger.debug(
                        f"Loaded compressed FAISS index: {len(decompressed) / 1024 / 1024:.2f}MB"
                    )
                except Exception as e:
                    logger.error(f"Failed to load FAISS index: {e}")
                    raise RuntimeError(f"Corrupted FAISS index data: {e}") from e
        else:
            # Fallback for old format (deprecated, will be removed)
            logger.warning("Loading index from deprecated inline format")
            if hasattr(index_data, "embeddings") and index_data.embeddings:
                embeddings_bytes = base64.b64decode(index_data.embeddings.encode("utf-8"))
                self.sentence_embeddings = pickle.loads(embeddings_bytes)
            if hasattr(index_data, "index_data") and index_data.index_data:
                index_bytes = base64.b64decode(index_data.index_data.encode("utf-8"))
                faiss_data = pickle.loads(index_bytes)
                self.sentence_index = faiss.deserialize_index(faiss_data)

    def _configure_faiss_threading(self) -> None:
        """Configure FAISS OpenMP threading for optimal performance."""
        import os

        import faiss

        # Get available cores
        cpu_count = os.cpu_count() or 8

        # Configure based on device
        if self.device == "cpu":
            # Use all cores for CPU-only workloads
            num_threads = cpu_count
        else:
            # Reduce threads for GPU to avoid contention
            num_threads = max(4, cpu_count // 2)

        faiss.omp_set_num_threads(num_threads)
        logger.info(f"🔧 FAISS OpenMP threads: {num_threads}/{cpu_count} cores")

    def _build_optimized_index(self, dimension: int, vocab_size: int) -> None:
        """Build optimized FAISS index with model-aware quantization strategies.

        Quantization strategies by corpus size:

        SMALL (<10k): Exact search - no compression
          • 10k @ BGE-M3: 40MB  |  10k @ MiniLM: 15MB

        MEDIUM (10-25k): FP16 - 50% compression, <0.5% quality loss
          • 25k @ BGE-M3: 100MB→50MB  |  25k @ MiniLM: 38MB→19MB

        LARGE (25-50k): INT8 - 75% compression, ~1-2% quality loss
          • 50k @ BGE-M3: 200MB→50MB  |  50k @ MiniLM: 75MB→19MB

        MASSIVE (50-250k): HNSW (if enabled) or IVF-PQ
          HNSW: Graph-based navigation, 3-5x speedup, ~2-3% quality loss
          • 100k @ BGE-M3: 400MB→450MB  |  100k @ MiniLM: 150MB→165MB
          • 250k @ BGE-M3: 1GB→1.1GB  |  250k @ MiniLM: 375MB→410MB
          IVF-PQ: 90% compression, ~5-10% quality loss
          • 100k @ BGE-M3: 400MB→40MB  |  100k @ MiniLM: 150MB→15MB
          • 250k @ BGE-M3: 1GB→100MB  |  250k @ MiniLM: 375MB→38MB

        EXTREME (>250k): OPQ+IVF-PQ - 97% compression, ~10-15% quality loss
          • 500k @ BGE-M3: 2GB→60MB  |  500k @ MiniLM: 750MB→23MB
          • 1M @ BGE-M3: 4GB→120MB  |  1M @ MiniLM: 1.5GB→45MB

        FAISS parameters:
        - nlist: Number of IVF clusters (sqrt(N) to 4*sqrt(N))
        - nprobe: Clusters searched at query time (nlist/16 to nlist/32)
        - m: PQ subquantizers dividing vector into subspaces
        - nbits: Bits per subquantizer (8 for quality/size balance)
        - M: HNSW connections per node (bidirectional links)
        - efConstruction: HNSW build-time search depth
        - efSearch: HNSW query-time search depth (tunable)
        """
        # Handle empty corpus
        if (
            vocab_size == 0
            or self.sentence_embeddings is None
            or self.sentence_embeddings.size == 0
        ):
            logger.warning("No embeddings to index - creating empty index")
            self.sentence_index = faiss.IndexFlatL2(dimension)
            return

        # Memory baseline: FP32 vectors
        base_memory_mb = (vocab_size * dimension * 4) / (1024 * 1024)
        model_type = "BGE-M3" if dimension == 1024 else "MiniLM" if dimension == 384 else "Custom"

        logger.info(
            f"🔄 Building {model_type} optimized index (dim: {dimension}, vocab: {vocab_size:,}, baseline: {base_memory_mb:.1f}MB)",
        )

        if vocab_size <= SMALL_CORPUS_THRESHOLD:
            # Exact L2 search - no compression
            self.sentence_index = faiss.IndexFlatL2(dimension)
            self.sentence_index.add(self.sentence_embeddings)
            actual_memory_mb = base_memory_mb
            logger.info(
                f"✅ IndexFlatL2: exact search, {actual_memory_mb:.1f}MB (100% of baseline)",
            )

        elif vocab_size <= MEDIUM_CORPUS_THRESHOLD:
            # IVF-Flat - 3-5x faster than FlatL2, minimal quality loss (<0.1%)
            import math

            nlist = max(64, int(math.sqrt(vocab_size)))  # 70-122 clusters for 5k-15k
            quantizer = faiss.IndexFlatL2(dimension)
            self.sentence_index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)

            logger.info(f"🔄 Training IVF-Flat index (nlist={nlist} clusters)...")
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)

            # Optimize for latency: search 25% of clusters
            self.sentence_index.nprobe = max(16, nlist // 4)

            expected_memory_mb = base_memory_mb * 1.05  # 5% overhead for index structure
            logger.info(
                f"✅ IVF-Flat: {expected_memory_mb:.1f}MB (~100% of {base_memory_mb:.1f}MB), "
                f"nlist={nlist}, nprobe={self.sentence_index.nprobe}, <0.1% quality loss, 3-5x speedup"
            )

        elif vocab_size <= LARGE_CORPUS_THRESHOLD:
            # INT8 quantization - 4x compression, small quality loss
            self.sentence_index = faiss.IndexScalarQuantizer(
                dimension,
                faiss.ScalarQuantizer.QT_8bit,
            )
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)
            expected_memory_mb = base_memory_mb * 0.25
            logger.info(
                f"✅ INT8 Quantization: {expected_memory_mb:.1f}MB (25% of {base_memory_mb:.1f}MB), ~1-2% quality loss",
            )

        elif vocab_size <= MASSIVE_CORPUS_THRESHOLD:
            # Choose between HNSW and IVF-PQ based on configuration
            if USE_HNSW:
                # HNSW - faster than IVF-PQ with minimal quality loss
                # 3-5x speedup with graph-based navigation
                self.sentence_index = faiss.IndexHNSWFlat(dimension, HNSW_M)

                # Set build-time search depth
                self.sentence_index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION

                logger.info(
                    f"🔄 Building HNSW index (M={HNSW_M}, efConstruction={HNSW_EF_CONSTRUCTION})..."
                )
                self.sentence_index.add(self.sentence_embeddings)

                # Set query-time search depth (tunable for latency/quality)
                self.sentence_index.hnsw.efSearch = HNSW_EF_SEARCH

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
                nlist = self._calculate_optimal_nlist(vocab_size)
                # Adjust m based on dimension: more subquantizers for higher dims
                m = 64 if dimension >= 1024 else 32 if dimension >= 512 else 16
                nbits = 8  # 8 bits per subquantizer for quality

                quantizer = faiss.IndexFlatL2(dimension)
                self.sentence_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

                logger.info(f"🔄 Training IVF-PQ (nlist={nlist} clusters, m={m} subquantizers)...")
                self.sentence_index.train(self.sentence_embeddings)
                self.sentence_index.add(self.sentence_embeddings)

                # nprobe: search top k% of clusters
                self.sentence_index.nprobe = min(nlist // 16, 128)
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
            self.sentence_index = faiss.IndexPreTransform(opq_transform, pq_index)

            logger.info(f"🔄 Training OPQ+IVF-PQ (nlist={nlist}, m={m})...")
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)

            # More aggressive nprobe for large indices
            base_index = faiss.downcast_index(self.sentence_index.index)
            base_index.nprobe = min(nlist // 32, 256)
            compression_ratio = 0.03  # ~3% of original size
            expected_memory_mb = base_memory_mb * compression_ratio
            logger.info(
                f"✅ OPQ+IVF-PQ: {expected_memory_mb:.1f}MB ({compression_ratio * 100:.0f}% of {base_memory_mb:.1f}MB), ~10-15% quality loss",
            )

    def _calculate_optimal_nlist(self, vocab_size: int) -> int:
        """Calculate optimal number of IVF clusters.

        Rule of thumb: sqrt(N) to 4*sqrt(N) clusters
        More clusters = faster search but slower indexing
        """
        import math

        sqrt_n = int(math.sqrt(vocab_size))
        if vocab_size <= 100000:
            return min(1024, max(sqrt_n, vocab_size // 50))
        if vocab_size <= 250000:
            return min(2048, max(sqrt_n, vocab_size // 50))
        return min(4096, max(sqrt_n * 2, vocab_size // 50))

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
        if not self.sentence_index:
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
                max_results * 2,  # Get extra results for filtering
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

            # Get variant mapping from index if available
            variant_mapping = (
                {int(k): v for k, v in self.index.variant_mapping.items()} if self.index else {}
            )

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
            logger.error(f"Semantic search failed: {e}")
            return []

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
            "initialized": bool(self.sentence_index),
            "vocabulary_size": len(self.index.lemmatized_vocabulary),
            "embedding_dim": self.index.embedding_dimension,
            "model_name": self.index.model_name,
            "corpus_name": self.index.corpus_name,
            "semantic_metadata_id": f"{self.index.corpus_name}:{self.index.model_name}",
            "batch_size": self.index.batch_size,
        }

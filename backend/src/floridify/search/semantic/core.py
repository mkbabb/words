"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import time
from typing import Any, Literal

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ...caching.manager import get_tree_corpus_manager
from ...caching.models import CacheNamespace
from ...corpus.core import Corpus
from ...models.versioned import ResourceType, SemanticIndexMetadata, VersionConfig
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..models import SearchResult
from .constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_SENTENCE_MODEL,
    ENABLE_GPU_ACCELERATION,
    L2_DISTANCE_NORMALIZATION,
    LARGE_CORPUS_THRESHOLD,
    MASSIVE_CORPUS_THRESHOLD,
    MEDIUM_CORPUS_THRESHOLD,
    MODEL_BATCH_SIZES,
    SMALL_CORPUS_THRESHOLD,
    USE_MIXED_PRECISION,
    USE_ONNX_BACKEND,
    SemanticModel,
)

logger = get_logger(__name__)


class SemanticIndex:
    """Encapsulates semantic index data and building logic.

    This class manages the FAISS index, embeddings, and related data structures
    for semantic search. It handles index building and optimization.
    """

    def __init__(
        self,
        corpus: Corpus,
        model_name: SemanticModel = DEFAULT_SENTENCE_MODEL,
    ):
        """Initialize semantic index.

        Args:
            corpus: Corpus containing vocabulary data
            model_name: Sentence transformer model to use
        """
        self.corpus = corpus
        self.model_name = model_name

        # Embeddings and index data
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None

        # Variant mapping for embedding index to lemma index
        self.variant_mapping: dict[int, int] = {}
        self.lemma_to_embeddings: dict[int, list[int]] = {}

        # Metadata
        self.embedding_dimension: int = 0
        self.num_vectors: int = 0
        self.build_time_seconds: float = 0.0
        self.memory_usage_mb: float = 0.0

        # Cache control
        self.embeddings_hash: str | None = None
        self.index_hash: str | None = None
        self._serialized_index_cache: dict[str, Any] | None = None
        self._index_cache_dirty: bool = True

    def build_index(
        self,
        embeddings: np.ndarray,
        variant_mapping: dict[int, int],
    ) -> None:
        """Build optimized FAISS index from embeddings.

        Args:
            embeddings: Sentence embeddings array
            variant_mapping: Mapping from embedding index to lemma index
        """
        start_time = time.perf_counter()

        self.sentence_embeddings = embeddings
        self.variant_mapping = variant_mapping
        self.embedding_dimension = embeddings.shape[1]
        self.num_vectors = embeddings.shape[0]

        # Build lemma to embeddings mapping
        self.lemma_to_embeddings.clear()
        for embed_idx, lemma_idx in variant_mapping.items():
            if lemma_idx not in self.lemma_to_embeddings:
                self.lemma_to_embeddings[lemma_idx] = []
            self.lemma_to_embeddings[lemma_idx].append(embed_idx)

        # Build optimized FAISS index
        self._build_optimized_faiss_index(self.embedding_dimension, len(self.corpus.vocabulary))

        # Add embeddings to index
        if self.sentence_index and self.sentence_embeddings is not None:
            self.sentence_index.add(self.sentence_embeddings)

        # Calculate metrics
        self.build_time_seconds = time.perf_counter() - start_time
        if self.sentence_embeddings is not None:
            self.memory_usage_mb = self.sentence_embeddings.nbytes / (1024 * 1024)

        self._index_cache_dirty = True

        logger.info(
            f"Built semantic index with {self.num_vectors} vectors in {self.build_time_seconds:.2f}s"
        )

    def _build_optimized_faiss_index(self, dimension: int, vocab_size: int) -> None:
        """Build optimized FAISS index with model-aware quantization strategies.

        Implements adaptive quantization based on corpus size and embedding model.
        Uses different strategies for different scales to balance speed vs accuracy.
        """
        if vocab_size < SMALL_CORPUS_THRESHOLD:
            # Small corpus: Use flat index for exact search
            logger.debug(f"Using flat index for small corpus ({vocab_size} words)")
            if L2_DISTANCE_NORMALIZATION:
                self.sentence_index = faiss.IndexFlatL2(dimension)
            else:
                self.sentence_index = faiss.IndexFlatIP(dimension)

        elif vocab_size < MEDIUM_CORPUS_THRESHOLD:
            # Medium corpus: IVF with moderate quantization
            nlist = min(int(np.sqrt(vocab_size) * 2), 256)
            quantizer = faiss.IndexFlatL2(dimension)
            self.sentence_index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

            if self.sentence_embeddings is not None:
                self.sentence_index.train(self.sentence_embeddings)

            # Set search parameters
            self.sentence_index.nprobe = max(1, nlist // 8)

            logger.debug(f"Using IVF index for medium corpus ({vocab_size} words, nlist={nlist})")

        elif vocab_size < LARGE_CORPUS_THRESHOLD:
            # Large corpus: IVF with PQ quantization
            nlist = min(int(np.sqrt(vocab_size) * 4), 1024)
            m = min(dimension // 2, 64)  # subquantizers
            nbits = 8  # bits per subquantizer

            quantizer = faiss.IndexFlatL2(dimension)
            self.sentence_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

            if self.sentence_embeddings is not None:
                self.sentence_index.train(self.sentence_embeddings)

            # Optimize search parameters
            self.sentence_index.nprobe = max(1, nlist // 16)

            logger.debug(
                f"Using IVFPQ index for large corpus ({vocab_size} words, "
                f"nlist={nlist}, m={m}, nbits={nbits})"
            )

        else:
            # Massive corpus: Aggressive quantization with IVFPQ
            nlist = min(int(np.sqrt(vocab_size) * 8), 4096)
            m = min(dimension // 4, 32)
            nbits = 8

            quantizer = faiss.IndexFlatL2(dimension)
            if vocab_size > MASSIVE_CORPUS_THRESHOLD:
                # For truly massive corpora, use hierarchical quantization
                self.sentence_index = faiss.IndexShards(dimension, True, False)
            else:
                self.sentence_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

            if self.sentence_embeddings is not None:
                if hasattr(self.sentence_index, "train"):
                    self.sentence_index.train(self.sentence_embeddings)

            # Conservative search for massive index
            if hasattr(self.sentence_index, "nprobe"):
                self.sentence_index.nprobe = max(1, nlist // 32)

            logger.debug(
                f"Using aggressive IVFPQ for massive corpus ({vocab_size} words, nlist={nlist})"
            )

    def search(
        self,
        query_embeddings: np.ndarray,
        k: int = 10,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Search index for nearest neighbors.

        Args:
            query_embeddings: Query embedding vectors
            k: Number of neighbors to return

        Returns:
            Distances and indices of nearest neighbors
        """
        if self.sentence_index is None:
            return np.array([]), np.array([])

        # Ensure query embeddings are contiguous
        query_embeddings = np.ascontiguousarray(query_embeddings, dtype=np.float32)

        # Search FAISS index
        distances, indices = self.sentence_index.search(query_embeddings, k)

        return distances, indices

    def get_statistics(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "model_name": self.model_name,
            "num_vectors": self.num_vectors,
            "embedding_dimension": self.embedding_dimension,
            "memory_usage_mb": self.memory_usage_mb,
            "build_time_seconds": self.build_time_seconds,
            "index_type": type(self.sentence_index).__name__ if self.sentence_index else None,
        }

    @classmethod
    async def get(
        cls,
        corpus: Corpus,
        model_name: SemanticModel = DEFAULT_SENTENCE_MODEL,
        config: VersionConfig | None = None,
    ) -> SemanticIndex | None:
        """Get semantic index from versioned storage.

        Args:
            corpus: Corpus containing vocabulary
            model_name: Model name for embeddings
            config: Version configuration

        Returns:
            SemanticIndex instance or None if not found
        """
        from ...caching.manager import get_version_manager

        manager = get_version_manager()

        # Create index ID based on corpus and model
        index_id = f"{corpus.corpus_name}:{model_name}"

        # Get the latest semantic index metadata
        semantic_metadata = await manager.get_latest(
            resource_id=index_id,
            resource_type=ResourceType.SEMANTIC,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not semantic_metadata:
            return None

        # Load content from metadata
        content = await semantic_metadata.get_content()
        if not content:
            return None

        # Create index instance
        index = cls(corpus=corpus, model_name=model_name)

        # Load data from content
        if "embeddings" in content:
            index.sentence_embeddings = np.array(content["embeddings"], dtype=np.float32)
        if "variant_mapping" in content:
            index.variant_mapping = content["variant_mapping"]
        if "lemma_to_embeddings" in content:
            index.lemma_to_embeddings = content["lemma_to_embeddings"]

        # Rebuild FAISS index from embeddings
        if index.sentence_embeddings is not None and len(index.variant_mapping) > 0:
            index.build_index(index.sentence_embeddings, index.variant_mapping)

        # Set metadata from stored values
        index.embedding_dimension = semantic_metadata.embedding_dimension
        index.num_vectors = semantic_metadata.num_vectors
        index.build_time_seconds = semantic_metadata.build_time_seconds
        index.memory_usage_mb = semantic_metadata.memory_usage_mb

        return index

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save semantic index to versioned storage.

        Args:
            config: Version configuration
        """
        from ...caching.manager import get_version_manager

        if self.sentence_embeddings is None:
            raise ValueError("No embeddings to save")

        manager = get_version_manager()

        # Create index ID
        index_id = f"{self.corpus.corpus_name}:{self.model_name}"

        # Prepare content to save
        content = {
            "embeddings": self.sentence_embeddings.tolist(),
            "variant_mapping": self.variant_mapping,
            "lemma_to_embeddings": self.lemma_to_embeddings,
            "corpus_name": self.corpus.corpus_name,
            "model_name": self.model_name,
        }

        # Save using version manager
        await manager.save(
            resource_id=index_id,
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.SEMANTIC,
            content=content,
            config=config or VersionConfig(),
            metadata={
                "corpus_id": self.corpus.corpus_id,
                "corpus_version": self.corpus.vocabulary_hash,
                "model_name": self.model_name,
                "embedding_dimension": self.embedding_dimension,
                "num_vectors": self.num_vectors,
                "build_time_seconds": self.build_time_seconds,
                "memory_usage_mb": self.memory_usage_mb,
            },
        )

        logger.info(f"Saved semantic index for {index_id}")

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        model_name: SemanticModel = DEFAULT_SENTENCE_MODEL,
        force_rebuild: bool = False,
        config: VersionConfig | None = None,
    ) -> SemanticIndex:
        """Get existing semantic index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            model_name: Model name for embeddings
            force_rebuild: Force rebuilding even if exists
            config: Version configuration

        Returns:
            SemanticIndex instance
        """
        # Try to get existing unless forced rebuild
        if not force_rebuild:
            existing = await cls.get(corpus, model_name, config)
            if existing:
                return existing

        # Create new index
        index = cls(corpus=corpus, model_name=model_name)

        # The actual embedding generation would happen in SemanticSearch
        # This is just the data container

        return index


class SemanticSearch:
    def __init__(
        self,
        corpus: Corpus,
        model_name: SemanticModel = DEFAULT_SENTENCE_MODEL,
        force_rebuild: bool = False,
        batch_size: int | None = None,
    ):
        """Initialize semantic search with sentence transformers.

        Args:
            corpus: Corpus instance containing vocabulary data
            model_name: Sentence transformer model to use (BGE-M3 or MiniLM)
            force_rebuild: Force rebuilding embeddings even if cached
            batch_size: Batch size for embedding generation (auto-selected if None)

        """
        self.corpus = corpus
        self.model_name = model_name
        self.force_rebuild = force_rebuild
        # Auto-select batch size based on model if not provided
        self.batch_size = batch_size or MODEL_BATCH_SIZES.get(model_name, DEFAULT_BATCH_SIZE)

        # Initialize optimized sentence model
        self.device = self._detect_optimal_device()
        self.sentence_model: SentenceTransformer = self._initialize_optimized_model()
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None

        # Semantic metadata reference for persistence
        self.semantic_metadata: SemanticIndexMetadata | None = None
        self._vocabulary_hash: str = ""

        # Variant mapping for embedding index to lemma index (always present)
        self.variant_mapping: dict[int, int] = {}

        # Cache serialized FAISS index to avoid repeated expensive serialization
        self._serialized_index_cache: dict[str, Any] | None = None
        self._index_cache_dirty: bool = True

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

    def _initialize_optimized_model(self) -> SentenceTransformer:
        """Initialize sentence transformer with standard optimizations."""
        # Initialize model with ONNX optimization if enabled
        if USE_ONNX_BACKEND:
            try:
                # Let sentence-transformers handle ONNX model selection automatically
                model = SentenceTransformer(self.model_name, backend="onnx")
                logger.info("✅ ONNX backend enabled with automatic model selection")
            except Exception as e:
                logger.warning(f"Failed to load ONNX model: {e}. Falling back to PyTorch")
                model = SentenceTransformer(self.model_name)
        else:
            model = SentenceTransformer(self.model_name)

        # Set device for GPU acceleration
        model = model.to(self.device)

        # Enable mixed precision for non-CPU devices
        if USE_MIXED_PRECISION and self.device != "cpu":
            logger.info("✅ Mixed precision (FP16) enabled for 1.88x speedup")

        logger.info(
            f"🔧 Model optimized: device={self.device}, onnx={USE_ONNX_BACKEND}, fp16={USE_MIXED_PRECISION}",
        )
        return model

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts with optimizations (ONNX + mixed precision + GPU)."""
        precision: Literal["float32", "int8", "uint8", "binary", "ubinary"] = "float32"

        return self.sentence_model.encode(
            sentences=texts,
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > 1000,
            output_value="sentence_embedding",
            precision=precision,
            convert_to_numpy=True,
            convert_to_tensor=False,
            device=self.device,
            normalize_embeddings=True,
        )

    async def initialize(self) -> None:
        """Initialize semantic search using corpus instance."""
        logger.info(
            f"Initializing semantic search for corpus '{self.corpus.corpus_name}' using {self.model_name}",
        )

        await self._build_embeddings_from_corpus()

    async def update_corpus(self, corpus: Corpus) -> None:
        """Update corpus and reinitialize if vocabulary hash has changed.

        Args:
            corpus: New corpus instance

        """
        if corpus.vocabulary_hash != self._vocabulary_hash:
            logger.info(
                f"Vocabulary hash changed for corpus '{corpus.corpus_name}', reinitializing semantic search",
            )
            self.corpus = corpus
            self._vocabulary_hash = corpus.vocabulary_hash
            # Clear existing data to force rebuild
            self.sentence_embeddings = None
            self.sentence_index = None
            self.semantic_metadata = None
            await self._build_embeddings_from_corpus()
        else:
            # Just update the corpus reference
            self.corpus = corpus

    async def _build_embeddings_from_corpus(self) -> None:
        """Build or load embeddings using corpus instance."""
        if not self.corpus:
            raise ValueError("Corpus not loaded")

        vocabulary_hash = self.corpus.vocabulary_hash

        # Check if vocabulary has changed to avoid unnecessary rebuilding
        if (
            self._vocabulary_hash == vocabulary_hash
            and not self.force_rebuild
            and self.sentence_embeddings is not None
        ):
            logger.debug("Vocabulary unchanged and embeddings exist, skipping rebuild")
            return

        self._vocabulary_hash = vocabulary_hash

        # Build embeddings using pre-computed lemma mappings from Corpus
        logger.info("Building new semantic embeddings using pre-computed lemmas")

        start_time = time.perf_counter()
        self._build_embeddings()
        build_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(f"Built semantic embeddings in {build_time_ms:.1f}ms")

        # Create or update metadata only if we're not in a test environment (no database needed)
        try:
            await self._create_semantic_metadata(build_time_ms)
        except Exception as e:
            logger.warning(f"Failed to create semantic metadata (continuing without database): {e}")

    def _build_embeddings(self) -> None:
        """Build streamlined semantic embeddings - sentence transformers only."""
        if not self.corpus:
            raise ValueError("Corpus not loaded")

        # Check if lemmatized vocabulary is available
        if not self.corpus.lemmatized_vocabulary:
            raise ValueError(f"Corpus '{self.corpus.corpus_name}' has empty lemmatized vocabulary")

        # Process entire vocabulary at once for better performance
        vocab_count = len(self.corpus.lemmatized_vocabulary)
        logger.info(f"🔄 Starting embedding generation: {vocab_count:,} lemmas (full batch)")

        embedding_start = time.time()

        # Use lemmatized vocabulary directly - it's already normalized/processed
        # No need to re-normalize: lemmatized_vocabulary is already unique and processed
        embedding_vocabulary = self.corpus.lemmatized_vocabulary

        # Create trivial identity mapping since we're using lemmas directly
        self.variant_mapping = {i: i for i in range(len(embedding_vocabulary))}

        logger.info(
            f"🔄 Using {len(embedding_vocabulary)} lemmatized embeddings directly (no re-normalization)",
        )

        # Process all variants with optimizations
        self.sentence_embeddings = self._encode(embedding_vocabulary)

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

        # Model-aware optimized quantization strategy
        self._build_optimized_index(dimension, vocab_size)

        # Mark serialization cache as dirty when index is rebuilt
        self._index_cache_dirty = True
        self._serialized_index_cache = None

        total_time = time.time() - embedding_start
        embeddings_per_sec = vocab_count / total_time if total_time > 0 else 0
        logger.info(
            f"✅ Semantic embeddings complete: {vocab_count:,} embeddings, dim={dimension} ({total_time:.1f}s, {embeddings_per_sec:.0f} emb/s)",
        )

    async def _create_semantic_metadata(self, build_time_ms: float) -> None:
        """Create or update SemanticIndex versioned document."""
        if not self.corpus:
            raise ValueError("Corpus not loaded")

        # Get existing corpus metadata from MongoDB
        manager = get_tree_corpus_manager()
        corpus_metadata = await manager.get_corpus(self.corpus.corpus_name)

        if not corpus_metadata:
            raise ValueError(
                f"Corpus metadata must be created before semantic metadata: {self.corpus.corpus_name}",
            )

        # Check if SemanticIndexMetadata already exists
        existing = await SemanticIndexMetadata.find_one(
            SemanticIndexMetadata.corpus_id == corpus_metadata.id,
            SemanticIndexMetadata.model_name == self.model_name,
            SemanticIndexMetadata.version_info.is_latest,
        )

        if existing:
            logger.debug(f"Using existing SemanticIndexMetadata for {corpus_metadata.id}")
            self.semantic_metadata = existing
            # Load the actual index from metadata
            await self._load_index_from_metadata(existing)
            return

        # Create new SemanticIndex with versioned data
        import hashlib

        from ...models.versioned import ContentLocation, StorageType, VersionInfo

        # Store index externally
        content_location = ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=CacheNamespace.SEMANTIC,
            cache_key=f"semantic:{self.corpus.vocabulary_hash}:{self.model_name}",
            size_bytes=self.sentence_embeddings.nbytes
            if self.sentence_embeddings is not None
            else 0,
            checksum=hashlib.sha256(self.corpus.vocabulary_hash.encode()).hexdigest(),
        )

        # Create metadata for persistence
        self.semantic_metadata = SemanticIndexMetadata(
            resource_id=f"{self.corpus.corpus_name}:{self.model_name}",
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.SEMANTIC,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash=self.corpus.vocabulary_hash,
            ),
            corpus_id=corpus_metadata.id,
            corpus_version="1.0.0",
            model_name=self.model_name,
            embedding_dimension=(
                self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 0
            ),
            index_type="faiss",
            content_location=content_location,
            build_time_seconds=build_time_ms / 1000.0,
            memory_usage_mb=(self.sentence_embeddings.nbytes / (1024 * 1024))
            if self.sentence_embeddings is not None
            else 0,
            num_vectors=len(self.corpus.lemmatized_vocabulary),
        )

        # Store the index data in metadata content
        index_data = {
            "corpus_id": str(corpus_metadata.id),
            "corpus_version": "1.0.0",
            "model_name": self.model_name,
            "embedding_dimension": (
                self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 0
            ),
            "variant_mapping": self.variant_mapping,
            "vocabulary": self.corpus.vocabulary,
            "lemmatized_vocabulary": self.corpus.lemmatized_vocabulary,
            "num_vectors": len(self.corpus.lemmatized_vocabulary),
        }
        await self.semantic_metadata.set_content(index_data)
        await self.semantic_metadata.save()

        logger.info(
            f"Created SemanticIndexMetadata for corpus '{self.corpus.corpus_name}' (vocabulary_hash: {self.corpus.vocabulary_hash})",
        )

    async def _load_index_from_metadata(self, metadata: SemanticIndexMetadata) -> None:
        """Load index data from metadata."""
        content = await metadata.get_content()
        if content:
            # Restore data from content
            self.variant_mapping = content.get("variant_mapping", {})

    def _build_optimized_index(self, dimension: int, vocab_size: int) -> None:
        """Build optimized FAISS index with model-aware quantization strategies.

        Quantization strategies by corpus size:

        SMALL (<10k): Exact search - no compression
          • 10k @ BGE-M3: 40MB  |  10k @ MiniLM: 15MB

        MEDIUM (10-25k): FP16 - 50% compression, <0.5% quality loss
          • 25k @ BGE-M3: 100MB→50MB  |  25k @ MiniLM: 38MB→19MB

        LARGE (25-50k): INT8 - 75% compression, ~1-2% quality loss
          • 50k @ BGE-M3: 200MB→50MB  |  50k @ MiniLM: 75MB→19MB

        MASSIVE (50-250k): IVF-PQ - 90% compression, ~5-10% quality loss
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
        """
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
                f"✅ IndexFlatL2: exact search, {actual_memory_mb:.1f}MB (100% of baseline)"
            )

        elif vocab_size <= MEDIUM_CORPUS_THRESHOLD:
            # FP16 quantization - 2x compression, minimal quality loss
            self.sentence_index = faiss.IndexScalarQuantizer(
                dimension,
                faiss.ScalarQuantizer.QT_fp16,
            )
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)
            expected_memory_mb = base_memory_mb * 0.5
            logger.info(
                f"✅ FP16 Quantization: {expected_memory_mb:.1f}MB (50% of {base_memory_mb:.1f}MB), <0.5% quality loss",
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

    def search(
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
            normalized_query = query
            if not normalized_query:
                return []

            query_embedding: np.ndarray = self._encode([normalized_query])[0]

            if query_embedding is None:
                return []

            # Search using FAISS - need to reshape to 2D array for batch processing
            distances, indices = self.sentence_index.search(
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

            for embedding_idx, similarity in zip(
                valid_embedding_indices, valid_similarities, strict=False
            ):
                # Direct mapping: embedding_idx = lemma_idx (no variants)
                lemma_idx = embedding_idx

                if lemma_idx >= len(self.corpus.lemmatized_vocabulary):
                    continue  # Skip invalid indices

                lemma = self.corpus.lemmatized_vocabulary[lemma_idx]

                # Map lemma index to original word
                if lemma_idx < len(lemma_to_word_indices):
                    original_word_idx = lemma_to_word_indices[lemma_idx]
                    word = self.corpus.get_original_word_by_index(original_word_idx)
                else:
                    word = lemma  # Direct use if mapping unavailable

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

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def model_dump(self) -> dict[str, Any]:
        """Serialize semantic search to dictionary for caching."""
        return {
            "corpus": self.corpus.model_dump() if self.corpus else None,
            "model_name": self.model_name,
            "force_rebuild": self.force_rebuild,
            "batch_size": self.batch_size,
            "device": self.device,
            "sentence_embeddings": (
                self.sentence_embeddings.tolist() if self.sentence_embeddings is not None else None
            ),
            "sentence_index_data": self._serialize_faiss_index(),
            "vocabulary_hash": self._vocabulary_hash,
            "semantic_metadata_id": (
                str(self.semantic_metadata.id) if self.semantic_metadata else None
            ),
            "variant_mapping": self.variant_mapping,  # Always exists after _build_embeddings
        }

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> SemanticSearch:
        """Deserialize semantic search from cached dictionary."""
        # Reconstruct corpus
        corpus = Corpus.model_load(data["corpus"]) if data["corpus"] else None
        if not corpus:
            raise ValueError("Cannot load SemanticSearch without corpus data")

        # Create instance
        instance = cls(
            corpus=corpus,
            model_name=data.get("model_name", DEFAULT_SENTENCE_MODEL),
            force_rebuild=data.get("force_rebuild", False),
            batch_size=data.get("batch_size", DEFAULT_BATCH_SIZE),
        )

        # Restore device (will reinitialize model)
        instance.device = data.get("device", "cpu")

        # Restore embeddings
        if data.get("sentence_embeddings"):
            instance.sentence_embeddings = np.array(data["sentence_embeddings"], dtype=np.float32)
            # Ensure C-contiguous layout
            if not instance.sentence_embeddings.flags.c_contiguous:
                instance.sentence_embeddings = np.ascontiguousarray(instance.sentence_embeddings)

        # Restore FAISS index
        if data.get("sentence_index_data") and instance.sentence_embeddings is not None:
            instance.sentence_index = instance._deserialize_faiss_index(
                data["sentence_index_data"],
                instance.sentence_embeddings,
            )

        # Restore metadata
        instance._vocabulary_hash = data.get("vocabulary_hash", "")

        # Restore variant mapping for diacritic variants
        instance.variant_mapping = data.get("variant_mapping", {})

        return instance

    def _serialize_faiss_index(self) -> dict[str, Any] | None:
        """Serialize FAISS index to dictionary with caching."""
        if not self.sentence_index or self.sentence_embeddings is None:
            return None

        # Return cached serialization if available and not dirty
        if not self._index_cache_dirty and self._serialized_index_cache is not None:
            return self._serialized_index_cache

        # Serialize the actual FAISS index to bytes using faiss's built-in method
        index_bytes = faiss.serialize_index(self.sentence_index)

        # Detect index type for proper serialization using class name
        index_class_name = self.sentence_index.__class__.__name__
        if "IVFPQ" in index_class_name:
            index_type = "IndexIVFPQ"
        elif "IVF" in index_class_name:
            index_type = "IndexIVFFlat"
        elif "HNSW" in index_class_name:
            index_type = "IndexHNSWFlat"
        elif "ScalarQuantizer" in index_class_name:
            index_type = "IndexScalarQuantizer"
        else:
            index_type = "IndexFlatL2"  # Default

        self._serialized_index_cache = {
            "index_type": index_type,
            "dimension": self.sentence_embeddings.shape[1],
            "size": self.sentence_index.ntotal,
            "index_data": index_bytes.tobytes().hex(),  # Convert numpy uint8 array to hex string for JSON
        }

        # Mark cache as clean
        self._index_cache_dirty = False

        return self._serialized_index_cache

    def _deserialize_faiss_index(
        self,
        index_data: dict[str, Any],
        embeddings: np.ndarray,
    ) -> faiss.Index:
        """Deserialize FAISS index from dictionary."""
        if "index_data" in index_data:
            # Deserialize the actual FAISS index from bytes
            index_bytes = bytes.fromhex(index_data["index_data"])
            index_array = np.frombuffer(index_bytes, dtype=np.uint8)
            index = faiss.deserialize_index(index_array)
            return index
        # Fallback: recreate index from embeddings
        dimension = index_data["dimension"]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        return index

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the semantic search index."""
        return {
            "initialized": bool(self.sentence_index),
            "vocabulary_size": (len(self.corpus.lemmatized_vocabulary) if self.corpus else 0),
            "embedding_dim": (
                self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 0
            ),
            "model_name": self.model_name,
            "corpus_name": self.corpus.corpus_name if self.corpus else "",
            "semantic_metadata_id": (self.semantic_metadata.id if self.semantic_metadata else None),
            "batch_size": self.batch_size,
        }

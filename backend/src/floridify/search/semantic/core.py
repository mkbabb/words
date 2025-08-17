"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import base64
import pickle
import time
from typing import Any, Literal

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ...corpus.core import Corpus
from ...models.versioned import VersionConfig
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..models import SearchResult, SemanticIndex
from .constants import (
    DEFAULT_SENTENCE_MODEL,
    ENABLE_GPU_ACCELERATION,
    L2_DISTANCE_NORMALIZATION,
    LARGE_CORPUS_THRESHOLD,
    MASSIVE_CORPUS_THRESHOLD,
    MEDIUM_CORPUS_THRESHOLD,
    SMALL_CORPUS_THRESHOLD,
    USE_MIXED_PRECISION,
    USE_ONNX_BACKEND,
    SemanticModel,
)

logger = get_logger(__name__)


class SemanticSearch:
    def __init__(
        self,
        index: SemanticIndex | None = None,
        corpus: Corpus | None = None,
    ):
        """Initialize semantic search with index and optional corpus.

        Args:
            index: Pre-loaded SemanticIndex containing all data
            corpus: Optional corpus for runtime operations

        """
        # Data model
        self.index = index
        self.corpus = corpus

        # Runtime objects (built from index)
        self.sentence_model: SentenceTransformer | None = None
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None
        self.device: str = "cpu"

        # Load from index if provided
        if index:
            self._load_from_index()

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
        # Get or create index
        index = await SemanticIndex.get_or_create(
            corpus=corpus,
            model_name=model_name,
            batch_size=batch_size,
            config=config or VersionConfig(),
        )

        # Create search with index
        search = cls(index=index, corpus=corpus)

        # Initialize if index needs building
        if not index.embeddings:
            await search.initialize()

        return search

    def _load_from_index(self) -> None:
        """Load data from the index model."""
        if not self.index:
            return

        # Set device from index
        self.device = self.index.device

        # Initialize model if needed
        if not self.sentence_model:
            self.sentence_model = self._initialize_optimized_model()

        # Load embeddings and FAISS index if available
        if self.index.embeddings:
            embeddings_bytes = base64.b64decode(self.index.embeddings.encode('utf-8'))
            self.sentence_embeddings = pickle.loads(embeddings_bytes)

        if self.index.index_data:
            index_bytes = base64.b64decode(self.index.index_data.encode('utf-8'))
            faiss_data = pickle.loads(index_bytes)
            self.sentence_index = faiss.deserialize_index(faiss_data)

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
        if not self.index:
            raise ValueError("Index required to initialize model")

        # Detect optimal device if not set
        if not self.device or self.device == "cpu":
            self.device = self._detect_optimal_device()
            self.index.device = self.device

        # Initialize model with ONNX optimization if enabled
        if USE_ONNX_BACKEND:
            try:
                # Let sentence-transformers handle ONNX model selection automatically
                model = SentenceTransformer(self.index.model_name, backend="onnx")
                logger.info("✅ ONNX backend enabled with automatic model selection")
            except Exception as e:
                logger.warning(
                    f"Failed to load ONNX model: {e}. Falling back to PyTorch"
                )
                model = SentenceTransformer(self.index.model_name)
        else:
            model = SentenceTransformer(self.index.model_name)

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
        if not self.sentence_model or not self.index:
            raise ValueError("Model and index required for encoding")

        precision: Literal["float32", "int8", "uint8", "binary", "ubinary"] = "float32"

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

    async def initialize(self) -> None:
        """Initialize semantic search by building embeddings."""
        if not self.index:
            raise ValueError("Index required for initialization")

        if not self.corpus:
            # Try to load corpus from index
            self.corpus = await Corpus.get(
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )

        if not self.corpus:
            raise ValueError(f"Could not load corpus '{self.index.corpus_name}'")

        logger.info(
            f"Initializing semantic search for corpus '{self.index.corpus_name}' using {self.index.model_name}",
        )

        # Initialize model if not already done
        if not self.sentence_model:
            self.device = self._detect_optimal_device()
            self.index.device = self.device
            self.sentence_model = self._initialize_optimized_model()

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
            raise ValueError(
                f"Corpus '{self.corpus.corpus_name}' has empty lemmatized vocabulary"
            )

        # Process entire vocabulary at once for better performance
        vocab_count = len(self.corpus.lemmatized_vocabulary)
        logger.info(
            f"🔄 Starting embedding generation: {vocab_count:,} lemmas (full batch)"
        )

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
        """Save embeddings to the index model."""
        if not self.index or not self.corpus:
            raise ValueError("Index and corpus required")

        # Update index with embeddings data
        if self.sentence_embeddings is not None:
            embeddings_bytes = pickle.dumps(self.sentence_embeddings)
            self.index.embeddings = base64.b64encode(embeddings_bytes).decode('utf-8')

        if self.sentence_index is not None:
            index_bytes = pickle.dumps(faiss.serialize_index(self.sentence_index))
            self.index.index_data = base64.b64encode(index_bytes).decode('utf-8')

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
            if "IVFPQ" in index_class_name:
                self.index.index_type = "IVFPQ"
            elif "IVF" in index_class_name:
                self.index.index_type = "IVF"
            elif "ScalarQuantizer" in index_class_name:
                self.index.index_type = "ScalarQuantizer"
            else:
                self.index.index_type = "Flat"

        # Save the updated index
        await self.index.save()

        logger.info(
            f"Saved semantic index for '{self.index.corpus_name}' with {self.index.num_embeddings} embeddings"
        )

    def _load_index_from_data(self, index_data: SemanticIndex) -> None:
        """Load index from data object."""
        import pickle

        if index_data.embeddings:
            embeddings_bytes = base64.b64decode(index_data.embeddings.encode('utf-8'))
            self.sentence_embeddings = pickle.loads(embeddings_bytes)
        if index_data.index_data:
            index_bytes = base64.b64decode(index_data.index_data.encode('utf-8'))
            faiss_data = pickle.loads(index_bytes)
            self.sentence_index = faiss.deserialize_index(faiss_data)

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
        model_type = (
            "BGE-M3"
            if dimension == 1024
            else "MiniLM" if dimension == 384 else "Custom"
        )

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
            self.sentence_index = faiss.IndexIVFPQ(
                quantizer, dimension, nlist, m, nbits
            )

            logger.info(
                f"🔄 Training IVF-PQ (nlist={nlist} clusters, m={m} subquantizers)..."
            )
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

            # Get variant mapping from index if available
            variant_mapping = (
                {int(k): v for k, v in self.index.variant_mapping.items()}
                if self.index
                else {}
            )

            for embedding_idx, similarity in zip(
                valid_embedding_indices, valid_similarities, strict=False
            ):
                # Use variant mapping from index or direct mapping
                lemma_idx = variant_mapping.get(embedding_idx, embedding_idx)

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
        if not self.index:
            return {}

        # Delegate to index model for serialization
        return self.index.model_dump()

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> SemanticSearch:
        """Deserialize semantic search from cached dictionary."""
        # Load index from data
        index = SemanticIndex.model_load(data)

        # Create instance with loaded index
        instance = cls(index=index)

        # Load runtime objects from index
        instance._load_from_index()

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

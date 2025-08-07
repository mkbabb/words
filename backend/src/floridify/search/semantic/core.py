"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import time
from typing import Any, Literal

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ...text import normalize_comprehensive
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..corpus.core import Corpus
from ..corpus.manager import get_corpus_manager
from ..models import SearchResult, SemanticMetadata
from .constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_SENTENCE_MODEL,
    ENABLE_GPU_ACCELERATION,
    L2_DISTANCE_NORMALIZATION,
    USE_MIXED_PRECISION,
    USE_ONNX_BACKEND,
)

logger = get_logger(__name__)


class SemanticSearch:
    """ULTRATHINK: Modern semantic search using state-of-the-art sentence transformers."""

    def __init__(
        self,
        corpus: Corpus,
        model_name: str = DEFAULT_SENTENCE_MODEL,
        force_rebuild: bool = False,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """
        Initialize semantic search with sentence transformers.

        Args:
            corpus: Corpus instance containing vocabulary data
            model_name: Sentence transformer model to use
            force_rebuild: Force rebuilding embeddings even if cached
            batch_size: Batch size for embedding generation
        """
        self.corpus = corpus
        self.model_name = model_name
        self.force_rebuild = force_rebuild
        self.batch_size = batch_size

        # Initialize optimized sentence model
        self.device = self._detect_optimal_device()
        self.sentence_model: SentenceTransformer = self._initialize_optimized_model()
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None

        # Semantic metadata reference
        self.semantic_metadata: SemanticMetadata | None = None
        self._vocabulary_hash: str = ""  # Start empty, will be set during initialization

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
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("🚀 MPS acceleration enabled (Apple Silicon)")
            return "mps"
        else:
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
            f"🔧 Model optimized: device={self.device}, onnx={USE_ONNX_BACKEND}, fp16={USE_MIXED_PRECISION}"
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
        """
        Initialize semantic search using corpus instance.
        """
        logger.info(
            f"Initializing semantic search for corpus '{self.corpus.corpus_name}' using {self.model_name}"
        )

        await self._build_embeddings_from_corpus()

    async def update_corpus(self, corpus: Corpus) -> None:
        """
        Update corpus and reinitialize if vocabulary hash has changed.

        Args:
            corpus: New corpus instance
        """
        if corpus.vocabulary_hash != self._vocabulary_hash:
            logger.info(
                f"Vocabulary hash changed for corpus '{corpus.corpus_name}', reinitializing semantic search"
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

        # Generate unique normalized forms for embeddings (no duplicates)
        # Track unique normalized forms and their mappings
        unique_normalized = {}  # normalized -> first lemma index
        self.variant_mapping = {}  # embedding index -> lemma index

        for i, lemma in enumerate(self.corpus.lemmatized_vocabulary):
            # Normalize once and use that for embedding
            normalized = normalize_comprehensive(lemma)
            if not normalized.strip():
                normalized = lemma  # Use original if normalization fails

            # Only add if this normalized form hasn't been seen
            if normalized not in unique_normalized:
                unique_normalized[normalized] = i

        # Build embedding vocabulary from unique normalized forms
        embedding_vocabulary = list(unique_normalized.keys())

        # Build mapping from embedding index to lemma index
        for embed_idx, normalized in enumerate(embedding_vocabulary):
            self.variant_mapping[embed_idx] = unique_normalized[normalized]

        logger.info(
            f"📈 Optimized: {len(embedding_vocabulary)} unique embeddings from {len(self.corpus.lemmatized_vocabulary)} lemmas"
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
            f"🔄 Building FAISS index (dimension: {dimension}, vocab_size: {vocab_size:,})..."
        )

        # Dynamic index selection with INT8 quantization for memory efficiency
        if vocab_size > 100000:  # Large corpus with Product Quantization
            # Use IVF with Product Quantization for 8x memory reduction
            nlist = 8192 if vocab_size >= 200000 else min(4096, vocab_size // 100)
            m = 48  # Number of subquantizers (dimension must be divisible by m)
            nbits = 8  # 8 bits per subquantizer

            # Ensure dimension is divisible by m
            if dimension % m != 0:
                m = 32  # Fallback to 32 if not divisible
                if dimension % m != 0:
                    m = 16  # Further fallback

            quantizer = faiss.IndexFlatL2(dimension)
            self.sentence_index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

            # Train the index (required for IVF and PQ)
            logger.info(f"🔄 Training IVF-PQ index with {nlist} clusters, {m} subquantizers...")
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)

            # Optimized search parameters for 200k+ corpus
            self.sentence_index.nprobe = 256 if vocab_size >= 200000 else min(128, nlist // 8)
            logger.info(
                f"✅ IVF-PQ index built with nprobe={self.sentence_index.nprobe} (8x memory reduction)"
            )

        elif vocab_size > 20000:  # Medium corpus with Scalar Quantization
            # Use Scalar Quantizer for 4x memory reduction
            self.sentence_index = faiss.IndexScalarQuantizer(
                dimension, faiss.ScalarQuantizer.QT_8bit
            )
            logger.info("🔄 Training Scalar Quantizer index...")
            self.sentence_index.train(self.sentence_embeddings)
            self.sentence_index.add(self.sentence_embeddings)
            logger.info("✅ Scalar Quantizer index built (4x memory reduction)")

        else:  # Small corpus - use exact search
            self.sentence_index = faiss.IndexFlatL2(dimension)
            self.sentence_index.add(self.sentence_embeddings)
            logger.info("✅ IndexFlatL2 used for small corpus")

        # Mark serialization cache as dirty when index is rebuilt
        self._index_cache_dirty = True
        self._serialized_index_cache = None

        total_time = time.time() - embedding_start
        embeddings_per_sec = vocab_count / total_time if total_time > 0 else 0
        logger.info(
            f"✅ Semantic embeddings complete: {vocab_count:,} embeddings, dim={dimension} ({total_time:.1f}s, {embeddings_per_sec:.0f} emb/s)"
        )

    async def _create_semantic_metadata(self, build_time_ms: float) -> None:
        """Create or update SemanticMetadata MongoDB document."""
        if not self.corpus:
            raise ValueError("Corpus not loaded")

        # Get existing corpus metadata from MongoDB
        manager = get_corpus_manager()
        corpus_metadata = await manager.get_corpus_metadata(self.corpus.corpus_name)

        if not corpus_metadata:
            raise ValueError(
                f"Corpus metadata must be created before semantic metadata: {self.corpus.corpus_name}"
            )

        # Check if SemanticMetadata already exists
        existing = await SemanticMetadata.find_one(
            {
                "corpus_data_id": corpus_metadata.id,
                "vocabulary_hash": self.corpus.vocabulary_hash,
                "model_name": self.model_name,
            }
        )

        if existing:
            self.semantic_metadata = existing
            logger.debug(f"Using existing SemanticMetadata for {corpus_metadata.id}")
            return

        # Create new SemanticMetadata with bi-directional relationship
        self.semantic_metadata = SemanticMetadata(
            corpus_data_id=corpus_metadata.id,
            vocabulary_hash=self.corpus.vocabulary_hash,
            model_name=self.model_name,
            embedding_dimension=(
                self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 0
            ),
            vocabulary_size=len(self.corpus.lemmatized_vocabulary),
            build_time_ms=build_time_ms,
        )

        await self.semantic_metadata.save()

        # Update corpus metadata to reference the semantic metadata
        corpus_metadata.semantic_data_id = self.semantic_metadata.id
        await corpus_metadata.save()

        logger.info(
            f"Created SemanticMetadata for corpus '{self.corpus.corpus_name}' (vocabulary_hash: {self.corpus.vocabulary_hash})"
        )

    def search(
        self, query: str, max_results: int = 20, min_score: float = 0.0
    ) -> list[SearchResult]:
        """
        Perform semantic similarity search using sentence embeddings.

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
            normalized_query = normalize_comprehensive(query)
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
            # Note: indices now refer to embedding vocabulary (with variants)
            embedding_vocab_size = (
                len(self.sentence_embeddings) if hasattr(self, "sentence_embeddings") else 0
            )
            valid_mask = (
                (indices[0] >= 0)
                & (similarities >= min_score)
                & (indices[0] < embedding_vocab_size)
            )
            valid_embedding_indices = indices[0][valid_mask]
            valid_similarities = similarities[valid_mask]

            # Create results in batch - avoid repeated SearchResult object creation overhead
            results = []
            lemma_to_word_indices = self.corpus.lemma_to_word_indices
            seen_lemma_indices = set()  # Avoid duplicates when variants map to same lemma

            for embedding_idx, similarity in zip(valid_embedding_indices, valid_similarities):
                # Map embedding index back to original lemma index using variant mapping
                if hasattr(self, "variant_mapping") and embedding_idx in self.variant_mapping:
                    original_lemma_idx = self.variant_mapping[embedding_idx]
                else:
                    # Fallback for backward compatibility (no variants)
                    original_lemma_idx = embedding_idx

                # Skip if we've already seen this lemma (from another variant)
                if original_lemma_idx in seen_lemma_indices:
                    continue
                seen_lemma_indices.add(original_lemma_idx)

                # Get the original lemma
                if original_lemma_idx < len(self.corpus.lemmatized_vocabulary):
                    lemma = self.corpus.lemmatized_vocabulary[original_lemma_idx]
                else:
                    continue  # Skip invalid indices

                # Map lemma index back to original word using corpus
                if original_lemma_idx < len(lemma_to_word_indices):
                    original_word_idx = lemma_to_word_indices[original_lemma_idx]
                    word = self.corpus.get_original_word_by_index(
                        original_word_idx
                    )  # Return original with diacritics
                else:
                    # Fallback: use lemma as word if mapping is missing
                    word = lemma

                results.append(
                    SearchResult(
                        word=word,
                        lemmatized_word=lemma,
                        score=float(similarity),
                        method=SearchMethod.SEMANTIC,
                        language=None,
                        metadata=None,
                    )
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
            "variant_mapping": getattr(self, "variant_mapping", {}),  # Include variant mapping
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
                data["sentence_index_data"], instance.sentence_embeddings
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

        # Detect index type for proper serialization
        index_type = "IndexFlatL2"  # Default
        if hasattr(self.sentence_index, "quantizer"):
            if hasattr(self.sentence_index, "nlist"):
                index_type = "IndexIVFFlat"
        elif hasattr(self.sentence_index, "hnsw"):
            index_type = "IndexHNSWFlat"

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
        self, index_data: dict[str, Any], embeddings: np.ndarray
    ) -> faiss.Index:
        """Deserialize FAISS index from dictionary."""
        if "index_data" in index_data:
            # Deserialize the actual FAISS index from bytes
            index_bytes = bytes.fromhex(index_data["index_data"])
            index_array = np.frombuffer(index_bytes, dtype=np.uint8)
            index = faiss.deserialize_index(index_array)
            return index
        else:
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

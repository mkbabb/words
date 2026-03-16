"""Semantic embedding builder: constructs embeddings and FAISS indices from corpus vocabulary."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import numpy as np

from ...utils.logging import get_logger
from .encoder import SemanticEncoder
from .index_builder import build_optimized_index, configure_faiss_threading
from .persistence import save_embeddings_and_index

if TYPE_CHECKING:
    from ...corpus.core import Corpus
    from .models import SemanticIndex

logger = get_logger(__name__)


class SemanticEmbeddingBuilder:
    """Builds semantic embeddings and FAISS indices from corpus vocabulary.

    Orchestrates the full embedding pipeline: vocabulary extraction,
    batched encoding, normalization, FAISS index construction, and persistence.
    """

    def __init__(self, encoder: SemanticEncoder) -> None:
        """Initialize with a SemanticEncoder for text-to-embedding conversion.

        Args:
            encoder: SemanticEncoder instance (must have model initialized)
        """
        self.encoder = encoder

    async def build_embeddings_from_corpus(
        self,
        corpus: Corpus,
        index: SemanticIndex,
    ) -> tuple[np.ndarray | None, object | None, dict[str, np.ndarray] | None]:
        """Build or load embeddings using corpus instance.

        Checks vocabulary hash to avoid unnecessary rebuilds, then delegates
        to _build_embeddings for the actual computation in a dedicated thread.

        Args:
            corpus: Corpus containing vocabulary and lemmas
            index: SemanticIndex to populate with results

        Returns:
            Tuple of (sentence_embeddings, sentence_index, word_embeddings_cache)
        """
        vocabulary_hash = corpus.vocabulary_hash

        # Build embeddings using pre-computed lemma mappings from Corpus
        logger.info("Building new semantic embeddings using pre-computed lemmas")

        start_time = time.perf_counter()
        # CRITICAL FIX: Use dedicated executor so embedding work (potentially
        # minutes-long) doesn't saturate the default thread pool and starve
        # HTTP request handlers.
        loop = asyncio.get_running_loop()

        # Capture results via mutable container for thread executor
        result_holder: dict[str, object] = {}

        def _run_build() -> None:
            embs, idx, word_cache = self._build_embeddings(corpus, index)
            result_holder["embeddings"] = embs
            result_holder["index"] = idx
            result_holder["word_cache"] = word_cache

        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="embed-build") as executor:
            await loop.run_in_executor(executor, _run_build)

        build_time_seconds = time.perf_counter() - start_time

        sentence_embeddings = result_holder.get("embeddings")
        sentence_index = result_holder.get("index")
        word_embeddings = result_holder.get("word_cache")

        logger.info(f"Built semantic embeddings in {build_time_seconds * 1000:.1f}ms")

        # Update index vocabulary hash
        index.vocabulary_hash = vocabulary_hash

        # Save embeddings to index
        await save_embeddings_and_index(
            index=index,
            sentence_embeddings=sentence_embeddings,
            sentence_index=sentence_index,
            build_time=build_time_seconds,
            corpus_uuid=corpus.corpus_uuid,
        )

        return sentence_embeddings, sentence_index, word_embeddings  # type: ignore[return-value]

    def _build_embeddings(
        self,
        corpus: Corpus,
        index: SemanticIndex,
    ) -> tuple[np.ndarray, object, dict[str, np.ndarray] | None]:
        """Build streamlined semantic embeddings - sentence transformers only.

        This is the core synchronous computation. It runs in a dedicated thread
        to avoid blocking the event loop.

        Args:
            corpus: Corpus containing vocabulary and lemmas
            index: SemanticIndex to populate with metadata

        Returns:
            Tuple of (sentence_embeddings, faiss_index, word_embeddings_cache)
        """
        # Check if lemmatized vocabulary is available
        if not corpus.lemmatized_vocabulary:
            logger.warning(
                f"Corpus '{corpus.corpus_name}' has empty lemmatized vocabulary - no embeddings to build"
            )
            # Set empty embeddings and index for consistency
            empty_embeddings = np.array([], dtype=np.float32).reshape(0, 1024)  # BGE-M3 dimension
            index.variant_mapping = {}
            index.num_embeddings = 0
            index.embedding_dimension = 1024
            return empty_embeddings, None, None

        # Process entire vocabulary at once for better performance
        vocab_count = len(corpus.lemmatized_vocabulary)
        logger.info(f"Starting embedding generation: {vocab_count:,} lemmas")

        embedding_start = time.time()

        # Use lemmatized vocabulary directly - it's already normalized/processed
        embedding_vocabulary = corpus.lemmatized_vocabulary

        # Create trivial identity mapping since we're using lemmas directly
        variant_mapping = {i: i for i in range(len(embedding_vocabulary))}

        # Store int->int variant mapping directly (no str conversion)
        index.variant_mapping = variant_mapping

        logger.info(
            f"Using {len(embedding_vocabulary)} lemmatized embeddings directly (no re-normalization)",
        )

        # Encode embeddings (with batching for large vocabularies)
        sentence_embeddings = self._encode_vocabulary(embedding_vocabulary, index)

        # Safety check for empty embeddings
        if sentence_embeddings.size == 0:
            raise ValueError("No valid embeddings generated from vocabulary")

        # CRITICAL FIX: Explicitly normalize embeddings to unit length
        # Some models (e.g., GTE-Qwen2) don't normalize despite normalize_embeddings=True
        sentence_embeddings = self._normalize_embeddings(sentence_embeddings)

        # Ensure C-contiguous memory layout for optimal FAISS performance
        if not sentence_embeddings.flags.c_contiguous:
            sentence_embeddings = np.ascontiguousarray(sentence_embeddings)
            logger.debug("Memory layout optimized: C-contiguous array")

        # Log memory usage
        memory_mb = sentence_embeddings.nbytes / (1024 * 1024)
        logger.info(f"Embeddings optimized: {memory_mb:.1f}MB")

        # Build per-word embedding cache for incremental updates (<50k words)
        word_embeddings: dict[str, np.ndarray] | None = None
        if vocab_count < 50000:
            word_embeddings = {
                word: sentence_embeddings[i] for i, word in enumerate(embedding_vocabulary)
            }
            logger.debug(f"Built per-word embedding cache: {vocab_count} entries")

        # Build FAISS index for sentence embeddings with dynamic optimization
        dimension = sentence_embeddings.shape[1]
        vocab_size = len(corpus.lemmatized_vocabulary)

        logger.info(
            f"Building FAISS index (dimension: {dimension}, vocab_size: {vocab_size:,})...",
        )

        # Configure FAISS threading before building index
        configure_faiss_threading()

        # Model-aware optimized quantization strategy
        sentence_index = build_optimized_index(dimension, vocab_size, sentence_embeddings)

        total_time = time.time() - embedding_start
        embeddings_per_sec = vocab_count / total_time if total_time > 0 else 0

        # Update index statistics
        index.num_embeddings = vocab_count
        index.embedding_dimension = dimension

        logger.info(
            f"Semantic embeddings complete: {vocab_count:,} embeddings, dim={dimension} ({total_time:.1f}s, {embeddings_per_sec:.0f} emb/s)",
        )

        return sentence_embeddings, sentence_index, word_embeddings

    def _encode_vocabulary(
        self,
        embedding_vocabulary: list[str],
        index: SemanticIndex,
    ) -> np.ndarray:
        """Encode vocabulary with batching for large corpora.

        Args:
            embedding_vocabulary: List of words/lemmas to encode
            index: SemanticIndex for model name and batch size

        Returns:
            Numpy array of embeddings
        """
        # Process in batches for large vocabularies with progress tracking
        # Batching provides visibility into progress while multiprocessing provides speed
        # CRITICAL: Batch size must exceed 5000 to trigger multiprocessing in encode()
        # Larger batches = better throughput with cpu_count()-1 workers
        if len(embedding_vocabulary) > 100000:
            batch_size = 15000  # Massive corpora: maximize throughput
        elif len(embedding_vocabulary) > 50000:
            batch_size = 12000  # Large corpora: balance speed & memory
        else:
            batch_size = 8000  # Medium corpora: conservative

        if len(embedding_vocabulary) > batch_size:
            return self._encode_batched(embedding_vocabulary, index, batch_size)
        else:
            # Small vocabulary - use thread-based parallel encoding
            logger.info(
                f"Processing {len(embedding_vocabulary):,} lemmas (small corpus, no batching)"
            )
            return self.encoder.encode(
                embedding_vocabulary,
                model_name=index.model_name,
                batch_size=index.batch_size,
                use_multiprocessing=True,
            )

    def _encode_batched(
        self,
        embedding_vocabulary: list[str],
        index: SemanticIndex,
        batch_size: int,
    ) -> np.ndarray:
        """Encode vocabulary in batches with progress logging.

        Args:
            embedding_vocabulary: List of words/lemmas to encode
            index: SemanticIndex for model name and batch size
            batch_size: Number of words per batch

        Returns:
            Concatenated numpy array of all batch embeddings
        """
        logger.info(f"Processing {len(embedding_vocabulary):,} lemmas in batches of {batch_size:,}")
        embeddings_list = []
        total_batches = (len(embedding_vocabulary) + batch_size - 1) // batch_size

        for i in range(0, len(embedding_vocabulary), batch_size):
            batch = embedding_vocabulary[i : i + batch_size]
            batch_num = i // batch_size + 1
            progress_pct = (batch_num / total_batches) * 100

            # Log every 5th batch or first/last batch (reduces 36+ logs to ~8 logs)
            if batch_num % 5 == 0 or batch_num == 1 or batch_num == total_batches:
                logger.info(f"  Batch {batch_num}/{total_batches} ({progress_pct:.0f}% complete)")
            else:
                logger.debug(f"  Batch {batch_num}/{total_batches} ({progress_pct:.0f}% complete)")

            batch_start = time.time()
            try:
                # Use thread-based parallel encoding (implemented in encoder.encode)
                batch_embeddings = self.encoder.encode(
                    batch,
                    model_name=index.model_name,
                    batch_size=index.batch_size,
                    use_multiprocessing=True,
                )
                batch_time = time.time() - batch_start

                # Log completion only for logged start batches
                if batch_num % 5 == 0 or batch_num == 1 or batch_num == total_batches:
                    logger.debug(
                        f"    Batch {batch_num} complete in {batch_time:.1f}s "
                        f"({len(batch) / batch_time:.0f} words/sec)"
                    )

                embeddings_list.append(batch_embeddings)

            except Exception as e:
                logger.error(f"Failed to encode batch {batch_num}: {e}")
                raise

        # Concatenate all batches
        result = np.vstack(embeddings_list)
        logger.info(
            f"Completed {len(embeddings_list)} batches - {len(embedding_vocabulary):,} lemmas encoded"
        )
        return result

    @staticmethod
    def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings to unit length (L2 norm = 1.0).

        Args:
            embeddings: Embeddings to normalize

        Returns:
            Normalized embeddings
        """
        norms_before = np.linalg.norm(embeddings, axis=1, keepdims=True)
        logger.info(
            f"Embedding norms before normalization - min: {norms_before.min():.6f}, max: {norms_before.max():.6f}, mean: {norms_before.mean():.6f}"
        )

        # Normalize to unit length (L2 norm = 1.0)
        embeddings = embeddings / norms_before

        # Verify normalization
        norms_after = np.linalg.norm(embeddings, axis=1)
        is_normalized = np.allclose(norms_after, 1.0, atol=0.01)
        logger.info(
            f"Embedding norms after normalization - min: {norms_after.min():.6f}, max: {norms_after.max():.6f}, mean: {norms_after.mean():.6f}"
        )
        logger.info(f"Embeddings normalized: {is_normalized}")

        if not is_normalized:
            logger.warning(
                "Embeddings not properly normalized after normalization step - L2 distances may be inaccurate"
            )

        return embeddings

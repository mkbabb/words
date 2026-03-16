"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from ...caching.models import VersionConfig
from ...corpus.core import Corpus
from ...corpus.manager import get_tree_corpus_manager
from ...utils.logging import get_logger
from ..constants import SearchMethod
from ..result import SearchResult
from .builder import SemanticEmbeddingBuilder
from .constants import (
    DEFAULT_SENTENCE_MODEL,
    L2_DISTANCE_NORMALIZATION,
    SemanticModel,
)
from .encoder import SemanticEncoder
from .index_builder import build_optimized_index, configure_faiss_threading
from .models import SemanticIndex
from .persistence import (
    load_embeddings_from_binary_data,
    load_faiss_index_from_binary_data,
    save_embeddings_and_index,
)
from .query_cache import SemanticQueryCache

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

        # Encoder handles model init, device detection, and text-to-embedding
        self._encoder = SemanticEncoder()

        # Runtime objects (built from index)
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: Any | None = None  # faiss.Index

        # Per-word embedding cache for incremental updates (<50k words)
        self._word_embeddings: dict[str, np.ndarray] | None = None

        # Query/result cache manager (LRU + L2 persistence)
        self._query_cache_manager = SemanticQueryCache(
            corpus_uuid=index.corpus_uuid if index else "",
            model_name=index.model_name if index else "",
            query_cache_size=query_cache_size,
        )

        # Note: _load_from_index is now async, caller must await it after construction
        # This is handled in from_corpus() and from_index() class methods

    # -- Public properties for backward compatibility --

    @property
    def sentence_model(self) -> Any | None:
        """SentenceTransformer model (delegated to encoder)."""
        return self._encoder.sentence_model

    @sentence_model.setter
    def sentence_model(self, value: Any) -> None:
        self._encoder.sentence_model = value

    @property
    def device(self) -> str:
        """Device for model execution (delegated to encoder)."""
        return self._encoder.device

    @device.setter
    def device(self, value: str) -> None:
        self._encoder.device = value

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
                    f"Built semantic index: {search.index.num_embeddings:,} embeddings, "
                    f"{search.index.embedding_dimension}D"
                )
            else:
                logger.info(
                    f"Created semantic index for empty corpus '{corpus.corpus_name}' (0 embeddings)"
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
        self._encoder.device = self.index.device

        # Initialize model if needed
        if not self._encoder.sentence_model:
            await self._encoder.initialize_model(
                model_name=self.index.model_name,
                device=self.index.device,
            )
            self.index.device = self._encoder.device

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
        # CRITICAL FIX: Use a dedicated ThreadPoolExecutor so decompression (601MB
        # embeddings + 392MB FAISS index) doesn't saturate the default executor
        # that asyncio.to_thread() uses—starving HTTP request handlers.
        try:
            corpus_name = self.index.corpus_name

            def _load_all():
                embeddings = load_embeddings_from_binary_data(binary_data, corpus_name)
                index = load_faiss_index_from_binary_data(binary_data, corpus_name)
                return embeddings, index

            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="semantic-init") as executor:
                self.sentence_embeddings, self.sentence_index = await loop.run_in_executor(
                    executor, _load_all
                )

            # Restore persisted caches from L2
            await self._query_cache_manager.load_query_cache_from_l2()
            await self._query_cache_manager.load_result_cache_from_l2()

        except Exception as e:
            logger.error(f"Failed to load embeddings/index from cache: {e}", exc_info=True)
            # Reset to trigger rebuild
            self.sentence_embeddings = None
            self.sentence_index = None
            raise RuntimeError(
                f"Corrupted semantic index for '{self.index.corpus_name}': {e}"
            ) from e

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

        # Initialize encoder model if not already done
        if not self._encoder.sentence_model:
            self._encoder.device = self._encoder.detect_optimal_device()
            self.index.device = self._encoder.device
            await self._encoder.initialize_model(
                model_name=self.index.model_name,
                device=self._encoder.device,
            )

        # Delegate to builder
        builder = SemanticEmbeddingBuilder(self._encoder)
        (
            self.sentence_embeddings,
            self.sentence_index,
            self._word_embeddings,
        ) = await builder.build_embeddings_from_corpus(self.corpus, self.index)

    async def update_corpus(self, corpus: Corpus) -> None:
        """Update corpus and reinitialize if vocabulary hash has changed.

        Uses incremental embedding updates for corpora <50k words:
        only encodes new words and removes deleted ones, then rebuilds
        the FAISS index (cheap) from the updated embedding matrix.

        Args:
            corpus: New corpus instance

        """
        if not self.index:
            raise ValueError("Index required for corpus update")

        if corpus.vocabulary_hash != self.index.vocabulary_hash:
            old_vocab = set(self.corpus.lemmatized_vocabulary) if self.corpus else set()
            new_vocab = set(corpus.lemmatized_vocabulary)

            can_incremental = (
                self.sentence_embeddings is not None
                and self._word_embeddings is not None
                and len(new_vocab) < 50000
                and old_vocab  # Must have previous vocab to diff against
            )

            if can_incremental:
                added = new_vocab - old_vocab
                removed = old_vocab - new_vocab

                logger.info(
                    f"Incremental update for '{corpus.corpus_name}': "
                    f"+{len(added)} -{len(removed)} words "
                    f"(total: {len(old_vocab)} -> {len(new_vocab)})"
                )

                self.corpus = corpus
                self.index = await SemanticIndex.create(
                    corpus=corpus,
                    model_name=self.index.model_name,
                    batch_size=self.index.batch_size,
                )

                # Remove deleted words from per-word cache
                for w in removed:
                    self._word_embeddings.pop(w, None)

                # Encode only new words
                if added:
                    added_list = sorted(added)
                    # encoder.encode() applies Matryoshka truncation internally
                    new_embs = self._encoder.encode(
                        added_list,
                        model_name=self.index.model_name,
                        batch_size=self.index.batch_size,
                        use_multiprocessing=False,
                    )
                    for word, emb in zip(added_list, new_embs):
                        self._word_embeddings[word] = emb

                # Rebuild embedding matrix from per-word cache in corpus order
                ordered_vocab = corpus.lemmatized_vocabulary
                self.sentence_embeddings = np.vstack(
                    [self._word_embeddings[w] for w in ordered_vocab]
                )

                # Identity variant mapping
                self.index.variant_mapping = {i: i for i in range(len(ordered_vocab))}

                # Rebuild FAISS index (cheap — sub-millisecond for <50k)
                configure_faiss_threading()
                dimension = self.sentence_embeddings.shape[1]
                self.sentence_index = build_optimized_index(
                    dimension, len(ordered_vocab), self.sentence_embeddings
                )

                self.index.vocabulary_hash = corpus.vocabulary_hash
                self.index.num_embeddings = len(ordered_vocab)
                self.index.embedding_dimension = dimension

                self._query_cache_manager.clear_result_cache()

                # Save updated index
                await save_embeddings_and_index(
                    index=self.index,
                    sentence_embeddings=self.sentence_embeddings,
                    sentence_index=self.sentence_index,
                    build_time=0.0,
                    corpus_uuid=corpus.corpus_uuid if corpus else self.index.corpus_uuid,
                )
            else:
                logger.info(
                    f"Vocabulary hash changed for corpus '{corpus.corpus_name}', "
                    f"full rebuild (incremental not available)"
                )
                self.corpus = corpus
                self.index = await SemanticIndex.create(
                    corpus=corpus,
                    model_name=self.index.model_name,
                    batch_size=self.index.batch_size,
                )
                self.sentence_embeddings = None
                self.sentence_index = None
                self._word_embeddings = None
                self._query_cache_manager.clear_result_cache()

                # Delegate full rebuild to builder
                builder = SemanticEmbeddingBuilder(self._encoder)
                (
                    self.sentence_embeddings,
                    self.sentence_index,
                    self._word_embeddings,
                ) = await builder.build_embeddings_from_corpus(self.corpus, self.index)
        else:
            self.corpus = corpus

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

        Three O(1) lookups: vocabulary_to_index -> word_to_lemma_indices -> sentence_embeddings.
        Returns None for out-of-vocabulary queries (which fall through to transformer encoding).
        """
        if self.corpus is None or self.sentence_embeddings is None:
            return None

        # Corpus vocabulary_to_index uses batch_normalize -> normalize_comprehensive
        # (lowercased + diacritics stripped + contractions expanded). Apply the same
        # normalization here so "cafe", "CAFE", "Cafe" all match the "cafe" key.
        from floridify.text.normalize import normalize

        lookup_key = normalize(normalized_query)

        # O(1) dict lookup: normalized word -> vocabulary index
        word_idx = self.corpus.vocabulary_to_index.get(lookup_key)
        if word_idx is None:
            return None

        # O(1) dict lookup: word index -> lemma index
        lemma_idx = self.corpus.word_to_lemma_indices.get(word_idx)
        if lemma_idx is None:
            return None

        # O(1) array access: lemma index -> pre-computed embedding
        # variant_mapping is embedding_idx->lemma_idx, but currently always identity.
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
            cached_results = self._query_cache_manager.get_cached_results(
                normalized_query, max_results, min_score
            )
            if cached_results is not None:
                return cached_results

            # Fast path: look up pre-computed embedding for in-vocabulary words (~0.001ms)
            query_embedding = self._lookup_vocab_embedding(normalized_query)

            if query_embedding is None:
                # Check embedding cache
                query_embedding = self._query_cache_manager.get_cached_query_embedding(
                    normalized_query
                )

            if query_embedding is None:
                # Cache miss - generate embedding asynchronously (releases GIL)
                # encoder.encode() applies Matryoshka truncation internally
                query_embedding = await asyncio.to_thread(
                    self._encoder.encode,
                    [normalized_query],
                    self.index.model_name,
                    self.index.batch_size,
                    False,  # use_multiprocessing
                )
                query_embedding = query_embedding[0]

                if query_embedding is None:
                    return []

                # Cache the embedding for future queries
                self._query_cache_manager.cache_query_embedding(normalized_query, query_embedding)

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

            # Get variant mapping from index if available (already int->int)
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
            self._query_cache_manager.cache_results(
                normalized_query, max_results, min_score, results
            )

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

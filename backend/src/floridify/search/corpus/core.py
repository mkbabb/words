"""
Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic.
"""

from __future__ import annotations

import time
from typing import Any

from ...text.normalize import batch_lemmatize, batch_normalize
from ...utils.logging import get_logger
from ..utils import get_vocabulary_hash

logger = get_logger(__name__)


class Corpus:
    """
    In-memory corpus containing vocabulary data and processing logic.

    This class contains all the actual vocabulary data that was previously
    stored in CorpusData. It's designed to be passed by reference without
    copying large datasets.
    """

    def __init__(self, corpus_name: str) -> None:
        """Initialize empty corpus with given name."""
        self.corpus_name = corpus_name

        # Core vocabulary data - dual storage for original preservation
        self.vocabulary: list[str] = []  # Normalized forms for search indexing
        self.original_vocabulary: list[str] = []  # Original forms for display

        # Mapping between normalized and original forms
        self.normalized_to_original_indices: dict[int, int] = {}  # normalized_idx -> original_idx

        # O(1) lookup dictionary for performance
        self.vocabulary_to_index: dict[str, int] = {}  # word -> vocabulary index

        # Computed data
        self.vocabulary_hash: str = ""
        self.vocabulary_indices: dict[str, Any] = {}
        self.vocabulary_stats: dict[str, int] = {}

        # Lemmatization data
        self.lemmatized_vocabulary: list[str] = []
        self.word_to_lemma_indices: list[int] = []
        self.lemma_to_word_indices: list[int] = []

        # Metadata
        self.metadata: dict[str, Any] = {}

        # Character signature-based candidate selection index
        self.signature_buckets: dict[str, list[int]] = {}  # signature -> [word_indices]
        self.length_buckets: dict[int, list[int]] = {}  # length -> [word_indices]

    @classmethod
    async def create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        semantic: bool = True,
        model_name: str | None = None,
    ) -> Corpus:
        """
        Create new corpus with full vocabulary processing.

        Enhanced for BGE-M3 integration - includes model name in vocabulary hash
        to prevent cache conflicts between embedding models.

        Args:
            corpus_name: Unique name for the corpus
            vocabulary: Combined list of words and phrases
            semantic: Enable semantic search integration
            model_name: Embedding model name for hash calculation (when semantic=True)

        Returns:
            Fully processed Corpus instance
        """
        logger.info(f"Creating corpus '{corpus_name}' with {len(vocabulary)} vocabulary items")
        start_time = time.perf_counter()

        corpus = cls(corpus_name)

        # Store reference to original vocabulary (no copy needed - we don't modify it)
        corpus.original_vocabulary = vocabulary  # Reference, not copy

        # Process vocabulary - normalize all at once, then deduplicate while preserving original mapping
        # CRITICAL: When multiple originals map to same normalized form, prefer the one with diacritics
        normalized_vocabulary = batch_normalize(vocabulary)

        # Group all originals by their normalized form
        normalized_to_originals: dict[str, list[tuple[int, str]]] = {}
        for orig_idx, (original_word, normalized_word) in enumerate(
            zip(vocabulary, normalized_vocabulary)
        ):
            if normalized_word not in normalized_to_originals:
                normalized_to_originals[normalized_word] = []
            normalized_to_originals[normalized_word].append((orig_idx, original_word))

        # For each normalized form, pick the best original (prefer diacritics/special chars)
        normalized_vocab_with_originals = []
        for normalized_word, originals in normalized_to_originals.items():
            # Sort by: 1) has diacritics/special chars, 2) length, 3) lexicographic
            best_orig_idx, best_orig_word = max(
                originals, key=lambda x: (x[1] != normalized_word, len(x[1]), x[1])
            )

            # Could add debug logging here if needed in future

            normalized_vocab_with_originals.append((normalized_word, best_orig_idx))

        # Build final structures
        corpus.vocabulary = [item[0] for item in normalized_vocab_with_originals]
        corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(corpus.vocabulary)}
        corpus.normalized_to_original_indices = {
            idx: orig_idx for idx, (_, orig_idx) in enumerate(normalized_vocab_with_originals)
        }

        # Include model name in hash for semantic search to prevent cache conflicts
        hash_model_name = model_name if semantic and model_name else None
        corpus.vocabulary_hash = get_vocabulary_hash(corpus.vocabulary, hash_model_name)

        # Batch process lemmas with parallelization for large vocabularies
        vocab_count = len(corpus.vocabulary)
        logger.info(f"🔄 Starting lemmatization: {vocab_count:,} vocabulary items")
        lemma_start = time.time()
        (
            corpus.lemmatized_vocabulary,
            corpus.word_to_lemma_indices,
            corpus.lemma_to_word_indices,
        ) = batch_lemmatize(corpus.vocabulary)
        lemma_time = time.time() - lemma_start
        lemma_count = len(corpus.lemmatized_vocabulary)
        logger.info(
            f"✅ Lemmatization complete: {vocab_count:,} → {lemma_count:,} lemmas ({lemma_time:.1f}s, {vocab_count / lemma_time:.0f} items/s)"
        )

        # Pre-compute indices with character signature-based candidate selection
        corpus.vocabulary_indices = corpus._create_unified_indices()
        corpus._build_signature_index()

        # Calculate statistics
        corpus.vocabulary_stats = {
            "vocabulary_count": len(corpus.vocabulary),
            "unique_lemmas": len(corpus.lemmatized_vocabulary),
            "avg_word_length": int(
                sum(len(w) for w in corpus.vocabulary) / max(1, len(corpus.vocabulary))
            ),
        }

        # Set metadata
        corpus.metadata = {
            "semantic_enabled": semantic,
            "creation_time": time.time(),
        }

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Created corpus '{corpus_name}' in {elapsed_ms}ms")

        return corpus

    def _create_unified_indices(self) -> dict[str, Any]:
        """Pre-compute all search indices for maximum performance."""
        # Use integer keys and direct dict access for better performance
        length_groups: dict[int, list[int]] = {}
        prefix_groups: dict[str, list[int]] = {}
        lowercase_map = []
        frequency_map = {}

        # Single pass optimization - process all indexing in one loop
        for i, word in enumerate(self.vocabulary):
            if not word:
                lowercase_map.append("")
                continue

            word_len = len(word)
            word_lower = word.lower()

            # Length indexing with integer keys (more efficient)
            if word_len not in length_groups:
                length_groups[word_len] = []
            length_groups[word_len].append(i)

            # Variable prefix length based on word characteristics
            prefix_len = min(3, max(2, word_len // 3))
            prefix = word_lower[:prefix_len]
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(i)

            # Pre-computed lowercase for fuzzy matching
            lowercase_map.append(word_lower)

            # Calculate word frequencies (heuristic based on length/commonality)
            frequency_map[i] = max(1.0, 10.0 - word_len * 0.5)

        return {
            "length_groups": length_groups,  # Now using integer keys
            "prefix_groups": prefix_groups,
            "lowercase_map": lowercase_map,
            "frequency_map": frequency_map,
        }

    def get_word_by_index(self, index: int) -> str:
        """Get normalized word by index from vocabulary."""
        return self.vocabulary[index]

    def get_original_word_by_index(self, normalized_index: int) -> str:
        """Get original word by normalized index, preserving diacritics."""
        if normalized_index in self.normalized_to_original_indices:
            original_index = self.normalized_to_original_indices[normalized_index]
            original_word = self.original_vocabulary[original_index]
            return original_word
        # Fallback to normalized form if mapping not found
        return (
            self.vocabulary[normalized_index]
            if 0 <= normalized_index < len(self.vocabulary)
            else ""
        )

    def get_words_by_indices(self, indices: list[int]) -> list[str]:
        """Get multiple normalized words by indices in single call - 3-5x faster than individual calls."""
        return [self.vocabulary[i] for i in indices if 0 <= i < len(self.vocabulary)]

    def get_original_words_by_indices(self, indices: list[int]) -> list[str]:
        """Get multiple original words by normalized indices, preserving diacritics."""
        result = []
        for i in indices:
            if 0 <= i < len(self.vocabulary):
                result.append(self.get_original_word_by_index(i))
        return result

    def get_candidates(
        self,
        query: str,
        max_candidates: int = 1000,
        use_lsh: bool = True,
    ) -> list[int]:
        """
        High-performance LSH-based candidate selection.

        Args:
            query: Normalized search query string
            max_candidates: Maximum number of candidates to return
            use_lsh: Unused - always uses LSH

        Returns:
            List of candidate word indices
        """
        if not query or not self.signature_buckets:
            return []

        candidate_set: set[int] = set()
        query_len = len(query)

        # Pre-compute query characteristics once
        query_chars = set(query.replace(" ", ""))
        query_signature = "".join(sorted(query.replace(" ", "")))
        query_char_counts: dict[str, int] = {}
        for char in query.replace(" ", ""):
            query_char_counts[char] = query_char_counts.get(char, 0) + 1

        # Single optimized pass through signature buckets
        max_diff_threshold = max(2, query_len // 5)
        min_candidates_for_fuzzy = max_candidates // 3  # Inverted condition threshold

        for signature, indices in self.signature_buckets.items():
            if len(candidate_set) >= max_candidates:
                break

            # Level 1: Exact signature match (highest priority)
            if signature == query_signature:
                candidate_set.update(indices)
                continue

            # Level 2: High character overlap (85%+)
            sig_chars = set(signature)
            if query_chars and sig_chars:
                overlap = len(query_chars & sig_chars) / len(query_chars | sig_chars)

                if overlap >= 0.85:
                    candidate_set.update(indices[: max_candidates // 10])
                    continue

                # Level 3: Character frequency matching (60%+ overlap)
                if overlap >= 0.6 and len(candidate_set) < min_candidates_for_fuzzy:
                    # Fast character frequency difference calculation
                    sig_char_counts: dict[str, int] = {}
                    for char in signature:
                        sig_char_counts[char] = sig_char_counts.get(char, 0) + 1

                    total_diff = sum(
                        abs(query_char_counts.get(c, 0) - sig_char_counts.get(c, 0))
                        for c in query_chars | sig_chars
                    )

                    if total_diff <= max_diff_threshold:
                        remaining = max_candidates - len(candidate_set)
                        candidate_set.update(indices[: remaining // 5])

        # Level 4: Length-based completion if needed
        if len(candidate_set) < max_candidates:
            length_tolerance = max(2, min(4, query_len // 3))
            target_lengths = range(
                max(1, query_len - length_tolerance), query_len + length_tolerance + 1
            )

            for length in target_lengths:
                if length in self.length_buckets and len(candidate_set) < max_candidates:
                    remaining = max_candidates - len(candidate_set)
                    take_count = remaining if length == query_len else remaining // 3
                    candidate_set.update(self.length_buckets[length][:take_count])

        return list(candidate_set)[:max_candidates]

    def _build_signature_index(self) -> None:
        """Build character signature index for robust misspelling-tolerant candidate selection."""
        logger.debug("Building character signature index for candidate selection")

        self.signature_buckets.clear()
        self.length_buckets.clear()

        for word_idx, word in enumerate(self.vocabulary):
            if not word:
                continue

            # Create character signature (sorted characters)
            signature = "".join(sorted(word.lower().replace(" ", "")))

            # Add to signature buckets
            if signature not in self.signature_buckets:
                self.signature_buckets[signature] = []
            self.signature_buckets[signature].append(word_idx)

            # Add to length buckets for fast filtering
            word_len = len(word)
            if word_len not in self.length_buckets:
                self.length_buckets[word_len] = []
            self.length_buckets[word_len].append(word_idx)

        signature_count = len(self.signature_buckets)
        avg_signature_size = sum(len(bucket) for bucket in self.signature_buckets.values()) / max(
            signature_count, 1
        )
        logger.debug(
            f"Built signature index: {signature_count} signatures, avg size {avg_signature_size:.1f}"
        )

    def model_dump(self) -> dict[str, Any]:
        """Serialize corpus to dictionary for caching."""
        return {
            "corpus_name": self.corpus_name,
            "vocabulary": self.vocabulary,
            "original_vocabulary": self.original_vocabulary,
            "normalized_to_original_indices": self.normalized_to_original_indices,
            "vocabulary_to_index": self.vocabulary_to_index,  # Store the index mapping
            "vocabulary_hash": self.vocabulary_hash,
            "vocabulary_indices": self.vocabulary_indices,
            "vocabulary_stats": self.vocabulary_stats,
            "lemmatized_vocabulary": self.lemmatized_vocabulary,
            "word_to_lemma_indices": self.word_to_lemma_indices,
            "lemma_to_word_indices": self.lemma_to_word_indices,
            "metadata": self.metadata,
            "signature_buckets": self.signature_buckets,
            "length_buckets": self.length_buckets,
        }

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Deserialize corpus from cached dictionary."""
        corpus = cls(data["corpus_name"])
        corpus.vocabulary = data["vocabulary"]
        corpus.original_vocabulary = data["original_vocabulary"]
        corpus.normalized_to_original_indices = data["normalized_to_original_indices"]
        corpus.vocabulary_hash = data["vocabulary_hash"]
        corpus.vocabulary_indices = data["vocabulary_indices"]
        corpus.vocabulary_stats = data["vocabulary_stats"]
        corpus.lemmatized_vocabulary = data["lemmatized_vocabulary"]
        corpus.word_to_lemma_indices = data["word_to_lemma_indices"]
        corpus.lemma_to_word_indices = data["lemma_to_word_indices"]
        corpus.metadata = data["metadata"]
        corpus.vocabulary_to_index = data["vocabulary_to_index"]

        # Load signature buckets
        corpus.signature_buckets = data.get("signature_buckets", {})
        corpus.length_buckets = data.get("length_buckets", {})

        # Rebuild if empty (older cached data)
        if not corpus.signature_buckets or not corpus.length_buckets:
            corpus._build_signature_index()

        return corpus

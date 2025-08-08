"""
Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
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
        self._signature_buckets: dict[str, list[int]] = {}  # signature -> [word_indices]
        self._length_buckets: dict[int, list[int]] = {}  # length -> [word_indices]

    @classmethod
    async def create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        semantic: bool = True,
    ) -> Corpus:
        """
        Create new corpus with full vocabulary processing.

        Args:
            corpus_name: Unique name for the corpus
            vocabulary: Combined list of words and phrases
            semantic: Enable semantic search integration

        Returns:
            Fully processed Corpus instance
        """
        logger.info(f"Creating corpus '{corpus_name}' with {len(vocabulary)} vocabulary items")
        start_time = time.perf_counter()

        corpus = cls(corpus_name)

        # Store reference to original vocabulary (no copy needed - we don't modify it)
        corpus.original_vocabulary = vocabulary  # Reference, not copy

        # Process vocabulary - use comprehensive normalization for compile-time corpus building
        normalized_vocabulary = batch_normalize(vocabulary)
        corpus.vocabulary_hash = get_vocabulary_hash(normalized_vocabulary)

        # Build normalized vocabulary and create mapping
        corpus.vocabulary = normalized_vocabulary

        # Build O(1) lookup dictionary and mappings
        corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(normalized_vocabulary)}

        # Create mapping from normalized index to original index
        # Handle case where normalization might deduplicate entries
        normalized_to_original_map = {}
        for orig_idx, (original_word, normalized_word) in enumerate(
            zip(vocabulary, normalized_vocabulary)
        ):
            # Use O(1) dict lookup instead of O(n) list.index()
            normalized_idx = corpus.vocabulary_to_index.get(normalized_word)
            if normalized_idx is not None:
                # Map normalized index to original index (first occurrence wins for duplicates)
                if normalized_idx not in normalized_to_original_map:
                    normalized_to_original_map[normalized_idx] = orig_idx

        corpus.normalized_to_original_indices = normalized_to_original_map

        # Batch process lemmas with parallelization for large vocabularies
        vocab_count = len(normalized_vocabulary)
        logger.info(f"🔄 Starting lemmatization: {vocab_count:,} vocabulary items")
        lemma_start = time.time()
        (
            corpus.lemmatized_vocabulary,
            corpus.word_to_lemma_indices,
            corpus.lemma_to_word_indices,
        ) = batch_lemmatize(normalized_vocabulary)
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
            return self.original_vocabulary[original_index]
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
        Modern candidate selection with LSH or fallback methods.
        
        Args:
            query: Search query string
            max_candidates: Maximum number of candidates to return
            use_lsh: Whether to use LSH-based selection (recommended)
            
        Returns:
            List of candidate word indices
        """
        if use_lsh and self._signature_buckets:
            return self.get_candidates_signature(query, max_candidates)
        else:
            # Fallback to length-based selection
            return self._get_candidates_fallback(query, max_candidates)
    
    def _get_candidates_fallback(
        self,
        query: str,
        max_candidates: int = 1000,
    ) -> list[int]:
        """Fallback candidate selection using length and prefix filtering."""
        length_groups = self.vocabulary_indices.get("length_groups", {})
        candidate_set: set[int] = set()
        query_len = len(query)
        
        # Length-based candidates with tolerance
        for length in range(max(1, query_len - 2), query_len + 3):
            if length in length_groups and len(candidate_set) < max_candidates:
                remaining_slots = max_candidates - len(candidate_set)
                candidate_set.update(length_groups[length][:remaining_slots])
        
        # Add prefix candidates if available
        if len(candidate_set) < max_candidates and len(query) >= 2:
            prefix_groups = self.vocabulary_indices.get("prefix_groups", {})
            prefix = query[:2].lower()
            remaining_slots = max_candidates - len(candidate_set)
            
            if prefix in prefix_groups:
                candidate_set.update(prefix_groups[prefix][:remaining_slots])
        
        return list(candidate_set)[:max_candidates]

    def _build_signature_index(self) -> None:
        """Build character signature index for robust misspelling-tolerant candidate selection."""
        logger.debug("Building character signature index for candidate selection")
        
        self._signature_buckets.clear()
        self._length_buckets.clear()
        
        for word_idx, word in enumerate(self.vocabulary):
            if not word:
                continue
            
            # Create character signature (sorted characters)
            signature = ''.join(sorted(word.lower()))
            
            # Add to signature buckets
            if signature not in self._signature_buckets:
                self._signature_buckets[signature] = []
            self._signature_buckets[signature].append(word_idx)
            
            # Add to length buckets for fast filtering
            word_len = len(word)
            if word_len not in self._length_buckets:
                self._length_buckets[word_len] = []
            self._length_buckets[word_len].append(word_idx)
        
        signature_count = len(self._signature_buckets)
        avg_signature_size = sum(len(bucket) for bucket in self._signature_buckets.values()) / max(signature_count, 1)
        logger.debug(f"Built signature index: {signature_count} signatures, avg size {avg_signature_size:.1f}")

    def get_candidates_signature(
        self,
        query: str,
        max_candidates: int = 1000,
    ) -> list[int]:
        """High-performance character signature candidate selection for robust misspelling handling."""
        if not query:
            return []
        
        candidate_set: set[int] = set()
        query_lower = query.lower()
        query_len = len(query_lower)
        
        # Primary: Exact signature match (handles perfect transpositions)
        query_signature = ''.join(sorted(query_lower))
        if query_signature in self._signature_buckets:
            candidate_set.update(self._signature_buckets[query_signature])
        
        # Enhanced: Near-signature matches (1-2 character differences in frequency)
        if len(candidate_set) < max_candidates * 0.5:
            self._add_near_signature_candidates(query_lower, query_signature, candidate_set, max_candidates)
        
        # Secondary: Length-based filtering with signature proximity
        length_tolerance = max(1, min(3, query_len // 4))  # Adaptive tolerance
        target_lengths = range(max(1, query_len - length_tolerance), query_len + length_tolerance + 1)
        
        for length in target_lengths:
            if length in self._length_buckets and len(candidate_set) < max_candidates:
                length_candidates = self._length_buckets[length]
                remaining = max_candidates - len(candidate_set)
                
                # For same-length candidates, check signature similarity
                if length == query_len:
                    candidate_set.update(length_candidates[:remaining])
                else:
                    # For different lengths, add subset with character overlap heuristic
                    added = 0
                    for idx in length_candidates:
                        if added >= remaining:
                            break
                        word = self.vocabulary[idx].lower()
                        if self._has_character_overlap(query_lower, word, threshold=0.6):
                            candidate_set.add(idx)
                            added += 1
        
        return list(candidate_set)[:max_candidates]
    
    def _has_character_overlap(self, query: str, word: str, threshold: float) -> bool:
        """Fast character overlap check for signature-based filtering."""
        query_chars = set(query)
        word_chars = set(word)
        
        if not query_chars or not word_chars:
            return False
            
        intersection = len(query_chars & word_chars)
        union = len(query_chars | word_chars)
        
        return (intersection / union) >= threshold if union > 0 else False
    
    def _add_near_signature_candidates(self, query: str, query_signature: str, candidate_set: set[int], max_candidates: int) -> None:
        """Add candidates with signatures that are similar but not identical (handles character frequency differences)."""
        query_chars = set(query)
        query_char_counts = {}
        for char in query:
            query_char_counts[char] = query_char_counts.get(char, 0) + 1
        
        # Check signatures that differ slightly in character frequency
        for signature, indices in self._signature_buckets.items():
            if len(candidate_set) >= max_candidates:
                break
                
            if signature == query_signature:
                continue  # Already handled in exact match
            
            # Quick character set similarity check
            sig_chars = set(signature)
            char_overlap = len(query_chars & sig_chars) / len(query_chars | sig_chars)
            
            if char_overlap >= 0.7:  # High character overlap
                # More precise character frequency comparison
                sig_char_counts = {}
                for char in signature:
                    sig_char_counts[char] = sig_char_counts.get(char, 0) + 1
                
                # Allow small differences in character counts (1-2 characters different)
                total_diff = sum(abs(query_char_counts.get(c, 0) - sig_char_counts.get(c, 0)) 
                               for c in query_chars | sig_chars)
                
                if total_diff <= 2:  # Allow up to 2 character count differences
                    remaining = max_candidates - len(candidate_set)
                    candidate_set.update(indices[:remaining])
    

    def model_dump(self) -> dict[str, Any]:
        """Serialize corpus to dictionary for caching."""
        return {
            "corpus_name": self.corpus_name,
            "vocabulary": self.vocabulary,
            "original_vocabulary": self.original_vocabulary,
            "normalized_to_original_indices": self.normalized_to_original_indices,
            "vocabulary_hash": self.vocabulary_hash,
            "vocabulary_indices": self.vocabulary_indices,
            "vocabulary_stats": self.vocabulary_stats,
            "lemmatized_vocabulary": self.lemmatized_vocabulary,
            "word_to_lemma_indices": self.word_to_lemma_indices,
            "lemma_to_word_indices": self.lemma_to_word_indices,
            "metadata": self.metadata,
            "signature_buckets": self._signature_buckets,
            "length_buckets": self._length_buckets,
        }

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Deserialize corpus from cached dictionary."""
        corpus = cls(data["corpus_name"])
        corpus.vocabulary = data["vocabulary"]
        corpus.original_vocabulary = data.get(
            "original_vocabulary", data["vocabulary"]
        )  # Backwards compatibility
        corpus.normalized_to_original_indices = data.get(
            "normalized_to_original_indices", {}
        )  # Backwards compatibility
        corpus.vocabulary_hash = data["vocabulary_hash"]
        corpus.vocabulary_indices = data["vocabulary_indices"]
        corpus.vocabulary_stats = data["vocabulary_stats"]
        corpus.lemmatized_vocabulary = data["lemmatized_vocabulary"]
        corpus.word_to_lemma_indices = data["word_to_lemma_indices"]
        corpus.lemma_to_word_indices = data["lemma_to_word_indices"]
        corpus.metadata = data["metadata"]
        
        # Load signature buckets if available
        if "signature_buckets" in data and "length_buckets" in data:
            corpus._signature_buckets = data["signature_buckets"]
            corpus._length_buckets = data["length_buckets"]
        else:
            # Rebuild signature index for older cached data
            corpus._build_signature_index()
        
        return corpus

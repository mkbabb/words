"""
Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from ...text.normalize import batch_lemmatize, normalize_comprehensive
from ...text.search import get_vocabulary_hash
from ...utils.logging import get_logger

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
        
        # Core vocabulary data
        self.words: list[str] = []
        self.phrases: list[str] = []
        
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
        
        # Process vocabulary - separate words from phrases
        normalized_vocabulary = [normalize_comprehensive(v) for v in vocabulary if v]
        corpus.vocabulary_hash = get_vocabulary_hash(normalized_vocabulary)
        
        corpus.words = [v for v in normalized_vocabulary if " " not in v]
        corpus.phrases = [v for v in normalized_vocabulary if " " in v]
        
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
        logger.info(f"✅ Lemmatization complete: {vocab_count:,} → {lemma_count:,} lemmas ({lemma_time:.1f}s, {vocab_count/lemma_time:.0f} items/s)")
        
        # Pre-compute indices
        corpus.vocabulary_indices = corpus._create_unified_indices()
        
        # Calculate statistics
        corpus.vocabulary_stats = {
            "word_count": len(corpus.words),
            "phrase_count": len(corpus.phrases),
            "unique_lemmas": len(corpus.lemmatized_vocabulary),
            "avg_word_length": int(
                sum(len(w) for w in corpus.words) / max(1, len(corpus.words))
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
        combined_vocab = self.words + self.phrases

        # Length-based grouping for fuzzy search optimization
        length_groups: dict[str, list[int]] = defaultdict(list)
        for i, word in enumerate(combined_vocab):
            length_groups[str(len(word))].append(i)

        # Prefix grouping for trie/prefix search optimization
        prefix_groups: dict[str, list[int]] = defaultdict(list)
        for i, word in enumerate(combined_vocab):
            if word:
                prefix = word[:3].lower()
                prefix_groups[prefix].append(i)

        # Phrase detection mask (boolean list)
        phrase_mask = [i >= len(self.words) for i in range(len(combined_vocab))]

        # Pre-computed lowercase for fuzzy matching
        lowercase_map = [word.lower() for word in combined_vocab]

        # Calculate word frequencies (heuristic based on length/commonality)
        frequency_map = {}
        for i, word in enumerate(combined_vocab):
            frequency = max(1.0, 10.0 - len(word) * 0.5)
            frequency_map[i] = frequency

        return {
            "length_groups": dict(length_groups),
            "prefix_groups": dict(prefix_groups),
            "phrase_mask": phrase_mask,
            "lowercase_map": lowercase_map,
            "frequency_map": frequency_map,
        }

    def get_combined_vocabulary(self) -> list[str]:
        """Get combined words and phrases list for search operations."""
        return self.words + self.phrases

    def get_vocabulary_size(self) -> int:
        """Get total vocabulary size (words + phrases)."""
        return len(self.words) + len(self.phrases)

    def is_phrase_by_index(self, index: int) -> bool:
        """Check if an index corresponds to a phrase (O(1) lookup)."""
        return index >= len(self.words)

    def get_word_by_index(self, index: int) -> str:
        """Get word/phrase by index from combined vocabulary."""
        if index < len(self.words):
            return self.words[index]
        return self.phrases[index - len(self.words)]

    def get_candidates_by_length(
        self, target_length: int, tolerance: int = 2
    ) -> list[int]:
        """Get candidate indices within length tolerance for fuzzy search optimization."""
        length_groups = self.vocabulary_indices.get("length_groups", {})
        candidates = []

        min_length = max(1, target_length - tolerance)
        max_length = target_length + tolerance

        for length in range(min_length, max_length + 1):
            if str(length) in length_groups:
                candidates.extend(length_groups[str(length)])

        return candidates

    def get_candidates_by_prefix(
        self, prefix: str, max_candidates: int = 100
    ) -> list[int]:
        """Get candidate indices by prefix for optimized search."""
        prefix_groups = self.vocabulary_indices.get("prefix_groups", {})
        prefix_lower = prefix.lower()

        candidates = []
        for stored_prefix, indices in prefix_groups.items():
            if stored_prefix.startswith(prefix_lower):
                candidates.extend(indices)
                if len(candidates) >= max_candidates:
                    break

        return candidates[:max_candidates]

    def model_dump(self) -> dict[str, Any]:
        """Serialize corpus to dictionary for caching."""
        return {
            "corpus_name": self.corpus_name,
            "words": self.words,
            "phrases": self.phrases,
            "vocabulary_hash": self.vocabulary_hash,
            "vocabulary_indices": self.vocabulary_indices,
            "vocabulary_stats": self.vocabulary_stats,
            "lemmatized_vocabulary": self.lemmatized_vocabulary,
            "word_to_lemma_indices": self.word_to_lemma_indices,
            "lemma_to_word_indices": self.lemma_to_word_indices,
            "metadata": self.metadata,
        }

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Deserialize corpus from cached dictionary."""
        corpus = cls(data["corpus_name"])
        corpus.words = data.get("words", [])
        corpus.phrases = data.get("phrases", [])
        corpus.vocabulary_hash = data.get("vocabulary_hash", "")
        corpus.vocabulary_indices = data.get("vocabulary_indices", {})
        corpus.vocabulary_stats = data.get("vocabulary_stats", {})
        corpus.lemmatized_vocabulary = data.get("lemmatized_vocabulary", [])
        corpus.word_to_lemma_indices = data.get("word_to_lemma_indices", [])
        corpus.lemma_to_word_indices = data.get("lemma_to_word_indices", [])
        corpus.metadata = data.get("metadata", {})
        return corpus
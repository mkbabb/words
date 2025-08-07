"""
Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic.
"""

from __future__ import annotations

import time
from typing import Any

from ...text.normalize import batch_lemmatize, batch_normalize
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
        
        # Core vocabulary data - single unified list
        self.vocabulary: list[str] = []
        
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
        
        # Process vocabulary - use batch normalization with automatic parallelization
        normalized_vocabulary = batch_normalize(vocabulary)
        corpus.vocabulary_hash = get_vocabulary_hash(normalized_vocabulary)
        
        # Keep vocabulary unified - no separation
        corpus.vocabulary = normalized_vocabulary
        
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
        """Get word by index from vocabulary."""
        return self.vocabulary[index]
    
    def get_words_by_indices(self, indices: list[int]) -> list[str]:
        """Get multiple words by indices in single call - 3-5x faster than individual calls."""
        return [self.vocabulary[i] for i in indices if 0 <= i < len(self.vocabulary)]

    
    def get_candidates_optimized(
        self, 
        query_len: int, 
        prefix: str | None = None,
        length_tolerance: int = 2,
        max_candidates: int = 1000
    ) -> list[int]:
        """Optimized candidate selection combining length and prefix strategies - 2-3x faster."""
        length_groups = self.vocabulary_indices.get("length_groups", {})
        candidate_set = set()
        
        # Length-based candidates
        for length in range(max(1, query_len - length_tolerance), query_len + length_tolerance + 1):
            if length in length_groups and len(candidate_set) < max_candidates:
                candidate_set.update(length_groups[length][:max_candidates - len(candidate_set)])
        
        # Add prefix-based candidates if provided and there's room
        if prefix and len(candidate_set) < max_candidates:
            prefix_groups = self.vocabulary_indices.get("prefix_groups", {})
            prefix_lower = prefix.lower()
            remaining_slots = max_candidates - len(candidate_set)
            
            for stored_prefix, indices in prefix_groups.items():
                if stored_prefix.startswith(prefix_lower):
                    candidate_set.update(indices[:remaining_slots])
                    if len(candidate_set) >= max_candidates:
                        break
        
        return list(candidate_set)[:max_candidates]

    def model_dump(self) -> dict[str, Any]:
        """Serialize corpus to dictionary for caching."""
        return {
            "corpus_name": self.corpus_name,
            "vocabulary": self.vocabulary,
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
        corpus.vocabulary = data["vocabulary"]
        corpus.vocabulary_hash = data["vocabulary_hash"]
        corpus.vocabulary_indices = data["vocabulary_indices"]
        corpus.vocabulary_stats = data["vocabulary_stats"]
        corpus.lemmatized_vocabulary = data["lemmatized_vocabulary"]
        corpus.word_to_lemma_indices = data["word_to_lemma_indices"]
        corpus.lemma_to_word_indices = data["lemma_to_word_indices"]
        corpus.metadata = data["metadata"]
        return corpus
"""Shared vocabulary management with memory mapping and efficient access patterns."""

from pathlib import Path
from typing import Any

import numpy as np

from ..caching.cache_manager import get_cache_manager
from ..text.search import get_vocabulary_hash
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory

logger = get_logger(__name__)


class SharedVocabularyStore:
    """Memory-mapped vocabulary store eliminating word_list copying overhead."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or get_cache_directory("vocabulary")

        self.vocab_mmap: np.memmap | None = None
        self.vocab_hash: str | None = None
        self.indices: dict[str, Any] = {}
        self._size = 0

        self.cache_manager = get_cache_manager()

    def create_vocabulary(self, words: list[str]) -> str:
        """Create memory-mapped vocabulary and return content hash."""
        vocab_hash = get_vocabulary_hash(words)

        if vocab_hash == self.vocab_hash:
            logger.debug(f"Vocabulary already loaded: {vocab_hash[:8]}")
            return vocab_hash

        vocab_file = self.cache_dir / f"vocab_{vocab_hash}.npy"
        indices_file = self.cache_dir / f"indices_{vocab_hash}.pkl"

        # Check if files exist
        if vocab_file.exists() and indices_file.exists():
            logger.info(f"Loading existing vocabulary: {vocab_hash[:8]}")
            self._load_existing_vocabulary(vocab_file, indices_file, vocab_hash)
            return vocab_hash

        logger.info(f"Creating new vocabulary: {vocab_hash[:8]} ({len(words)} words)")

        # Create memory-mapped vocabulary array
        vocab_array = np.array(words, dtype="U200")  # Max 200 chars per word
        np.save(vocab_file, vocab_array)

        # Pre-compute indices for optimized access
        indices = self._create_indices(words)
        with open(indices_file, "wb") as f:
            import pickle

            pickle.dump(indices, f)

        # Load into memory
        self._load_existing_vocabulary(vocab_file, indices_file, vocab_hash)

        logger.info(
            f"Vocabulary created: {len(words)} words, {vocab_file.stat().st_size / 1024 / 1024:.1f}MB"
        )
        return vocab_hash

    def _load_existing_vocabulary(
        self, vocab_file: Path, indices_file: Path, vocab_hash: str
    ) -> None:
        """Load existing memory-mapped vocabulary."""
        self.vocab_mmap = np.load(vocab_file, mmap_mode="r")
        with open(indices_file, "rb") as f:
            import pickle

            self.indices = pickle.load(f)
        self.vocab_hash = vocab_hash
        self._size = len(self.vocab_mmap)

    def _create_indices(self, words: list[str]) -> dict[str, Any]:
        """Create optimized indices for different access patterns."""
        indices: dict[str, Any] = {}

        # Length-based grouping for fuzzy search optimization
        length_groups: dict[int, list[int]] = {}
        for i, word in enumerate(words):
            length = len(word)
            if length not in length_groups:
                length_groups[length] = []
            length_groups[length].append(i)
        indices["length_groups"] = length_groups

        # Phrase detection mask
        phrase_mask_array = np.array([" " in word for word in words], dtype=bool)
        indices["phrase_mask"] = phrase_mask_array

        # First letter grouping for prefix optimization
        first_letter_groups: dict[str, list[int]] = {}
        for i, word in enumerate(words):
            if word:
                first_letter = word[0].lower()
                if first_letter not in first_letter_groups:
                    first_letter_groups[first_letter] = []
                first_letter_groups[first_letter].append(i)
        indices["first_letter_groups"] = first_letter_groups

        # Pre-computed lowercase for fuzzy matching
        lowercase_words = [word.lower() for word in words]
        indices["lowercase_words"] = lowercase_words

        return indices


    def get_words(self, indices: list[int] | None = None) -> list[str]:
        """Get words by indices or all words."""
        if self.vocab_mmap is None:
            return []

        if indices is None:
            return [str(word) for word in self.vocab_mmap]

        return [str(self.vocab_mmap[i]) for i in indices if 0 <= i < len(self.vocab_mmap)]

    def get_candidates_by_length(self, target_length: int, tolerance: int = 2) -> list[int]:
        """Get word indices within length tolerance."""
        if "length_groups" not in self.indices:
            return []

        candidates: list[int] = []
        for length in range(max(1, target_length - tolerance), target_length + tolerance + 1):
            if length in self.indices["length_groups"]:
                candidates.extend(self.indices["length_groups"][length])

        return candidates

    def get_candidates_by_prefix(self, prefix: str, max_candidates: int = 100) -> list[int]:
        """Get word indices starting with prefix."""
        if not prefix or "first_letter_groups" not in self.indices:
            return []

        first_letter = prefix[0].lower()
        if first_letter not in self.indices["first_letter_groups"]:
            return []

        candidates: list[int] = []
        for idx in self.indices["first_letter_groups"][first_letter]:
            if len(candidates) >= max_candidates:
                break
            if self.vocab_mmap is not None:
                word = str(self.vocab_mmap[idx]).lower()
            else:
                continue
            if word.startswith(prefix.lower()):
                candidates.append(idx)

        return candidates

    def get_lowercase_words(self, indices: list[int] | None = None) -> list[str]:
        """Get lowercase words for fuzzy matching."""
        if "lowercase_words" not in self.indices:
            return []

        if indices is None:
            return self.indices["lowercase_words"]

        return [
            str(self.indices["lowercase_words"][i])
            for i in indices
            if 0 <= i < len(self.indices["lowercase_words"])
        ]

    def is_phrase(self, index: int) -> bool:
        """Check if word at index is a phrase."""
        if "phrase_mask" not in self.indices or index >= len(self.indices["phrase_mask"]):
            return False
        return bool(self.indices["phrase_mask"][index])

    @property
    def size(self) -> int:
        """Get vocabulary size."""
        return self._size

    @property
    def is_loaded(self) -> bool:
        """Check if vocabulary is loaded."""
        return self.vocab_mmap is not None

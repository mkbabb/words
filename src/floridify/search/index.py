"""Core word indexing infrastructure using advanced data structures.

Implements multiple indexing approaches for different search patterns:
1. Trie for prefix matching and autocomplete
2. BK-Tree for edit distance-based fuzzy matching
3. N-gram index for substring and phonetic matching
4. Suffix array for efficient substring queries
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import pygtrie


class TrieIndex:
    """Efficient prefix-based word indexing using compressed trie."""

    def __init__(self) -> None:
        self.trie = pygtrie.CharTrie()
        self._word_count = 0

    def add_word(self, word: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a word to the trie with optional metadata."""
        word_lower = word.lower().strip()
        # Allow letters, spaces, hyphens, and apostrophes for phrases
        if (word_lower and 
            len(word_lower) > 1 and 
            word_lower.replace(' ', '').replace('-', '').replace("'", '').isalpha()):
            self.trie[word_lower] = {
                "word": word,
                "metadata": metadata or {},
                "frequency": self.trie.get(word_lower, {}).get("frequency", 0) + 1,
            }
            self._word_count += 1

    def prefix_search(self, prefix: str, max_results: int = 50) -> list[tuple[str, float]]:
        """Find words with given prefix, scored by frequency and relevance."""
        prefix_lower = prefix.lower().strip()
        if not prefix_lower:
            return []

        results = []
        try:
            # Get all words with this prefix
            prefix_items = self.trie.items(prefix_lower)

            for word, data in prefix_items:
                # Score based on frequency and length similarity to prefix
                frequency_score = data.get("frequency", 1)
                length_ratio = len(prefix_lower) / len(word)

                # Prefer words closer in length to the prefix
                length_bonus = 1.0 - abs(1.0 - length_ratio) * 0.3
                score = frequency_score * length_bonus

                results.append((data["word"], score))

            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:max_results]

        except KeyError:
            return []

    def exact_match(self, word: str) -> bool:
        """Check if word exists in index."""
        return word.lower().strip() in self.trie

    def get_word_count(self) -> int:
        """Get total number of unique words in index."""
        return len(self.trie)


class BKTree:
    """BK-Tree for efficient edit distance-based fuzzy matching.

    Based on Burkhard-Keller tree structure optimized for string similarity.
    """

    def __init__(self) -> None:
        self.root: BKNode | None = None
        self._word_count = 0

    def add_word(self, word: str, metadata: dict[str, Any] | None = None) -> None:
        """Add word to BK-tree."""
        word_clean = word.lower().strip()
        # Allow letters, spaces, hyphens, and apostrophes for phrases
        if not (word_clean and 
                len(word_clean) > 1 and 
                word_clean.replace(' ', '').replace('-', '').replace("'", '').isalpha()):
            return

        word_data = {"word": word, "metadata": metadata or {}, "frequency": 1}

        if self.root is None:
            self.root = BKNode(word_clean, word_data)
        else:
            self.root.add_word(word_clean, word_data)

        self._word_count += 1

    def search(
        self, target: str, max_distance: int = 2, max_results: int = 50
    ) -> list[tuple[str, float]]:
        """Find words within edit distance of target."""
        if self.root is None:
            return []

        target_clean = target.lower().strip()
        results: list[tuple[dict[str, Any], int]] = []

        self._search_recursive(self.root, target_clean, max_distance, results)

        # Convert edit distances to similarity scores (0.0 to 1.0)
        scored_results = []
        for word_data, distance in results:
            # Calculate similarity score
            max_len = max(len(target_clean), len(word_data["word"].lower()))
            similarity = 1.0 - (distance / max_len) if max_len > 0 else 0.0

            # Apply frequency bonus
            frequency_bonus = min(word_data.get("frequency", 1) / 100.0, 0.2)
            final_score = similarity + frequency_bonus

            scored_results.append((word_data["word"], final_score))

        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:max_results]

    def _search_recursive(
        self, node: BKNode, target: str, max_distance: int, results: list[tuple[dict[str, Any], int]]
    ) -> None:
        """Recursively search BK-tree for matches within edit distance."""
        current_distance = self._edit_distance(node.word, target)

        if current_distance <= max_distance:
            results.append((node.data, current_distance))

        # Search child nodes that could contain matches
        for distance, child in node.children.items():
            if abs(distance - current_distance) <= max_distance:
                self._search_recursive(child, target, max_distance, results)

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class BKNode:
    """Node in BK-Tree structure."""

    def __init__(self, word: str, data: dict[str, Any]) -> None:
        self.word = word
        self.data = data
        self.children: dict[int, BKNode] = {}

    def add_word(self, word: str, data: dict[str, Any]) -> None:
        """Add word to this node or appropriate child."""
        distance = self._edit_distance(self.word, word)

        if distance == 0:
            # Same word, update frequency
            self.data["frequency"] = self.data.get("frequency", 0) + 1
            return

        if distance in self.children:
            self.children[distance].add_word(word, data)
        else:
            self.children[distance] = BKNode(word, data)

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance (same as BKTree method)."""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class NGramIndex:
    """N-gram based index for substring and phonetic matching."""

    def __init__(self, n: int = 3) -> None:
        self.n = n
        self.ngram_to_words: dict[str, set[str]] = {}
        self.word_to_ngrams: dict[str, set[str]] = {}
        self.word_data: dict[str, dict[str, Any]] = {}

    def add_word(self, word: str, metadata: dict[str, Any] | None = None) -> None:
        """Add word to n-gram index."""
        word_clean = word.lower().strip()
        # Allow letters, spaces, hyphens, and apostrophes for phrases
        if not (word_clean and 
                len(word_clean) > 1 and 
                word_clean.replace(' ', '').replace('-', '').replace("'", '').isalpha()):
            return

        # Generate n-grams for the word
        ngrams = self._generate_ngrams(word_clean)

        # Store word data
        self.word_data[word_clean] = {
            "word": word,
            "metadata": metadata or {},
            "frequency": self.word_data.get(word_clean, {}).get("frequency", 0) + 1,
        }

        # Update indices
        self.word_to_ngrams[word_clean] = ngrams
        for ngram in ngrams:
            if ngram not in self.ngram_to_words:
                self.ngram_to_words[ngram] = set()
            self.ngram_to_words[ngram].add(word_clean)

    def search(self, query: str, max_results: int = 50) -> list[tuple[str, float]]:
        """Find words with similar n-gram patterns."""
        query_clean = query.lower().strip()
        query_ngrams = self._generate_ngrams(query_clean)

        if not query_ngrams:
            return []

        # Find candidate words that share n-grams
        candidates: dict[str, int] = {}
        for ngram in query_ngrams:
            if ngram in self.ngram_to_words:
                for word in self.ngram_to_words[ngram]:
                    candidates[word] = candidates.get(word, 0) + 1

        # Score candidates based on n-gram overlap
        results = []
        for word, overlap_count in candidates.items():
            word_ngrams = self.word_to_ngrams[word]

            # Jaccard similarity
            intersection = len(query_ngrams & word_ngrams)
            union = len(query_ngrams | word_ngrams)
            jaccard_score = intersection / union if union > 0 else 0.0

            # Overlap ratio
            overlap_score = overlap_count / len(query_ngrams)

            # Combined score with frequency bonus
            frequency_bonus = min(self.word_data[word].get("frequency", 1) / 100.0, 0.1)
            final_score = (jaccard_score * 0.7 + overlap_score * 0.3) + frequency_bonus

            results.append((self.word_data[word]["word"], final_score))

        # Sort and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def _generate_ngrams(self, word: str) -> set[str]:
        """Generate n-grams for a word with boundary markers."""
        if len(word) < self.n:
            return {word}

        # Add boundary markers
        padded_word = "^" + word + "$"
        ngrams = set()

        for i in range(len(padded_word) - self.n + 1):
            ngrams.add(padded_word[i : i + self.n])

        return ngrams


class WordIndex:
    """Comprehensive word index combining multiple search strategies."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path("data/search_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize indices
        self.trie = TrieIndex()
        self.bk_tree = BKTree()
        self.trigram_index = NGramIndex(n=3)
        self.bigram_index = NGramIndex(n=2)

        # Index metadata
        self._languages: set[str] = set()
        self._total_words = 0
        self._is_loaded = False

    def add_word(
        self, word: str, language: str = "en", metadata: dict[str, Any] | None = None
    ) -> None:
        """Add word to all indices."""
        if not word or not word.strip():
            return

        word_metadata = metadata or {}
        word_metadata["language"] = language

        # Add to all indices
        self.trie.add_word(word, word_metadata)
        self.bk_tree.add_word(word, word_metadata)
        self.trigram_index.add_word(word, word_metadata)
        self.bigram_index.add_word(word, word_metadata)

        self._languages.add(language)
        self._total_words += 1

    def prefix_search(self, prefix: str, max_results: int = 20) -> list[tuple[str, float]]:
        """Fast prefix-based search using trie."""
        return self.trie.prefix_search(prefix, max_results)

    def fuzzy_search(
        self, query: str, max_distance: int = 2, max_results: int = 20
    ) -> list[tuple[str, float]]:
        """Edit distance-based fuzzy search using BK-tree."""
        return self.bk_tree.search(query, max_distance, max_results)

    def ngram_search(self, query: str, max_results: int = 20) -> list[tuple[str, float]]:
        """N-gram based substring and phonetic search."""
        # Combine trigram and bigram results
        trigram_results = self.trigram_index.search(query, max_results)
        bigram_results = self.bigram_index.search(query, max_results)

        # Merge and re-score results
        combined_scores: dict[str, float] = {}

        for word, score in trigram_results:
            combined_scores[word] = score * 0.7  # Trigrams weighted higher

        for word, score in bigram_results:
            if word in combined_scores:
                combined_scores[word] += score * 0.3
            else:
                combined_scores[word] = score * 0.3

        # Sort and return
        results = [(word, score) for word, score in combined_scores.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def hybrid_search(self, query: str, max_results: int = 20) -> list[tuple[str, float, str]]:
        """Hybrid search combining all methods with result type annotation."""
        all_results: list[tuple[str, float, str]] = []

        # Prefix search (highest priority for short queries)
        if len(query) <= 4:
            prefix_results = self.prefix_search(query, max_results // 2)
            all_results.extend([(word, score * 1.2, "prefix") for word, score in prefix_results])

        # Fuzzy search (edit distance)
        fuzzy_results = self.fuzzy_search(query, max_distance=2, max_results=max_results)
        all_results.extend([(word, score, "fuzzy") for word, score in fuzzy_results])

        # N-gram search (substring similarity)
        ngram_results = self.ngram_search(query, max_results)
        all_results.extend([(word, score * 0.9, "ngram") for word, score in ngram_results])

        # Remove duplicates, keeping highest score
        seen_words: dict[str, tuple[float, str]] = {}
        for word, score, method in all_results:
            if word not in seen_words or score > seen_words[word][0]:
                seen_words[word] = (score, method)

        # Convert back to list and sort
        final_results = [(word, score, method) for word, (score, method) in seen_words.items()]
        final_results.sort(key=lambda x: x[1], reverse=True)

        return final_results[:max_results]

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "total_words": self._total_words,
            "unique_words": self.trie.get_word_count(),
            "languages": list(self._languages),
            "trie_words": self.trie.get_word_count(),
            "bk_tree_words": self.bk_tree._word_count,
            "is_loaded": self._is_loaded,
        }

    def save_cache(self) -> None:
        """Save indices to cache files."""
        cache_file = self.cache_dir / "word_index.pkl"

        with open(cache_file, "wb") as f:
            pickle.dump(
                {
                    "trie": self.trie,
                    "bk_tree": self.bk_tree,
                    "trigram_index": self.trigram_index,
                    "bigram_index": self.bigram_index,
                    "languages": self._languages,
                    "total_words": self._total_words,
                    "is_loaded": self._is_loaded,
                },
                f,
            )

    def load_cache(self) -> bool:
        """Load indices from cache files."""
        cache_file = self.cache_dir / "word_index.pkl"

        if not cache_file.exists():
            return False

        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)

            self.trie = data["trie"]
            self.bk_tree = data["bk_tree"]
            self.trigram_index = data["trigram_index"]
            self.bigram_index = data["bigram_index"]
            self._languages = data["languages"]
            self._total_words = data["total_words"]
            self._is_loaded = data["is_loaded"]

            return True

        except Exception:
            return False

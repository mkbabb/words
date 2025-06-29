"""Search manager coordinating traditional and vectorized fuzzy search methods.

Provides a unified interface for all search capabilities:
1. Traditional fuzzy search (BK-tree, trie, n-grams)
2. Vectorized search (embeddings, FAISS)
3. Database integration for persistent word storage
4. Performance optimization and caching
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .enums import LanguageCode, SearchMethod, TraditionalSearchMethod, VectorSearchMethod
from .fuzzy_traditional import TraditionalFuzzySearch
from .fuzzy_vectorized import VectorizedFuzzySearch
from .index import WordIndex
from .lexicon_loader import LexiconLoader


class SearchResult:
    """Unified search result with performance metadata."""

    def __init__(
        self,
        word: str,
        score: float,
        method: str,
        explanation: str = "",
        distance: int = 0,
        language: str = "en",
    ) -> None:
        self.word = word
        self.score = score
        self.method = method
        self.explanation = explanation
        self.distance = distance
        self.language = language

    def __repr__(self) -> str:
        return f"SearchResult(word='{self.word}', score={self.score:.3f}, method='{self.method}')"


class SearchManager:
    """Unified search manager coordinating all fuzzy search methods."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path("data/search")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize search components
        self.word_index = WordIndex(self.cache_dir / "index")
        self.traditional_search = TraditionalFuzzySearch(score_threshold=0.6)
        self.vectorized_search = VectorizedFuzzySearch(self.cache_dir / "vectors")
        self.lexicon_loader = LexiconLoader(self.cache_dir / "lexicons")

        # Search configuration
        self.default_methods = [SearchMethod.HYBRID, SearchMethod.VECTORIZED]
        self.max_results_per_method = 50
        self.is_initialized = False

        # Performance tracking
        self.search_stats: dict[str, Any] = {
            "total_searches": 0,
            "avg_search_time": 0.0,
            "method_usage": {},
            "cache_hits": 0,
        }

    async def initialize(self, force_rebuild: bool = False) -> None:
        """Initialize all search indices and load lexicons."""
        print("🔍 Initializing Floridify Search Engine...")

        start_time = time.time()

        # Load comprehensive lexicons
        print("📚 Loading comprehensive word lexicons...")
        all_lexicons = await self.lexicon_loader.load_all_lexicons(force_refresh=force_rebuild)

        # Get unified word list
        print("🔄 Creating unified word index...")
        unified_words = await self.lexicon_loader.get_unified_lexicon(
            [LanguageCode.ENGLISH, LanguageCode.FRENCH]
        )

        print(f"📊 Processing {len(unified_words):,} unique words...")

        # Try to load cached indices
        if not force_rebuild:
            print("💾 Attempting to load cached indices...")

            index_loaded = self.word_index.load_cache()
            vector_loaded = self.vectorized_search.load_index()

            if index_loaded and vector_loaded:
                print("✅ Successfully loaded cached search indices!")
                self.is_initialized = True

                elapsed = time.time() - start_time
                print(f"⚡ Search engine initialized in {elapsed:.2f} seconds")
                return

        # Build indices from scratch
        print("🏗️  Building search indices from scratch...")

        # Build traditional index (Trie, BK-tree, N-grams)
        print("  📋 Building traditional search index...")
        for word in unified_words:
            self.word_index.add_word(word, language="en")  # Simplified language detection

        # Build vectorized index
        print("  🧠 Building vectorized search index...")
        self.vectorized_search.build_index(unified_words)

        # Save indices to cache
        print("💾 Saving indices to cache...")
        self.word_index.save_cache()
        self.vectorized_search.save_index()

        self.is_initialized = True

        elapsed = time.time() - start_time
        print(f"✅ Search engine initialized successfully in {elapsed:.2f} seconds!")

        # Print statistics
        index_stats = self.word_index.get_stats()
        vector_stats = self.vectorized_search.get_stats()

        print("📈 Index Statistics:")
        print(f"  • Total words: {index_stats['total_words']:,}")
        print(f"  • Unique words: {index_stats['unique_words']:,}")
        print(f"  • Languages: {', '.join(index_stats['languages'])}")
        print(f"  • Vector embedding dimension: {vector_stats.get('embedding_dim', 'N/A')}")

    async def search(
        self,
        query: str,
        max_results: int = 20,
        methods: list[SearchMethod | str] | None = None,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        """Perform comprehensive fuzzy search using multiple methods."""
        if not self.is_initialized:
            await self.initialize()

        if methods is None:
            methods = self.default_methods
        
        # Ensure methods is not None for the rest of the function
        methods = methods or []

        start_time = time.time()
        query_clean = query.strip().lower()

        if not query_clean:
            return []

        all_results: list[SearchResult] = []

        # Method 1: Hybrid traditional search (Trie + BK-tree + N-grams)
        hybrid_search = any(
            method == SearchMethod.HYBRID or 
            (hasattr(method, 'value') and method.value == 'hybrid') or 
            method == 'hybrid'
            for method in methods
        )
        if hybrid_search:
            try:
                hybrid_results = self.word_index.hybrid_search(query_clean, max_results)
                for word, score, method in hybrid_results:
                    all_results.append(
                        SearchResult(
                            word=word,
                            score=score,
                            method=f"hybrid_{method}",
                            explanation=f"Traditional {method} matching",
                            distance=0,  # Could calculate if needed
                            language=LanguageCode.ENGLISH.value,
                        )
                    )
            except Exception as e:
                print(f"Hybrid search error: {e}")

        # Method 2: Vectorized search (embeddings + FAISS)
        vectorized_search = any(
            method == SearchMethod.VECTORIZED or 
            (hasattr(method, 'value') and method.value == 'vectorized') or 
            method == 'vectorized'
            for method in methods
        )
        if vectorized_search:
            try:
                vector_results = self.vectorized_search.search(
                    query_clean, max_results, VectorSearchMethod.FUSION
                )
                for word, score in vector_results:
                    all_results.append(
                        SearchResult(
                            word=word,
                            score=score,
                            method="vectorized_fusion",
                            explanation="Multi-level embedding similarity",
                            distance=0,
                            language=LanguageCode.ENGLISH.value,
                        )
                    )
            except Exception as e:
                print(f"Vectorized search error: {e}")

        # Method 3: Traditional RapidFuzz search
        rapidfuzz_search = any(
            method == SearchMethod.RAPIDFUZZ or 
            (hasattr(method, 'value') and method.value == 'rapidfuzz') or 
            method == 'rapidfuzz'
            for method in methods
        )
        if rapidfuzz_search:
            try:
                # Get word list for traditional search
                word_list = list(self.word_index.trie.trie.keys())
                traditional_results = self.traditional_search.search(
                    query_clean,
                    word_list,
                    max_results,
                    [TraditionalSearchMethod.RAPIDFUZZ, TraditionalSearchMethod.VSCODE],
                )

                for match in traditional_results:
                    all_results.append(
                        SearchResult(
                            word=match.word,
                            score=match.score,
                            method=match.method,
                            explanation=match.explanation,
                            distance=match.distance,
                            language=LanguageCode.ENGLISH.value,
                        )
                    )
            except Exception as e:
                print(f"Traditional search error: {e}")

        # Merge and deduplicate results
        merged_results = self._merge_search_results(all_results)

        # Filter by score threshold
        filtered_results = [result for result in merged_results if result.score >= score_threshold]

        # Sort by score and limit
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        final_results = filtered_results[:max_results]

        # Update statistics
        search_time = time.time() - start_time
        method_names = [
            method.value if hasattr(method, 'value') else str(method) for method in methods
        ]
        self._update_search_stats(query, method_names, search_time, len(final_results))

        return final_results

    async def prefix_search(self, prefix: str, max_results: int = 20) -> list[SearchResult]:
        """Fast prefix-based search for autocomplete."""
        if not self.is_initialized:
            await self.initialize()

        start_time = time.time()

        try:
            prefix_results = self.word_index.prefix_search(prefix, max_results)

            results = []
            for word, score in prefix_results:
                results.append(
                    SearchResult(
                        word=word,
                        score=score,
                        method="prefix_trie",
                        explanation=f"Prefix match for '{prefix}'",
                        distance=0,
                        language=LanguageCode.ENGLISH.value,
                    )
                )

            search_time = time.time() - start_time
            self._update_search_stats(prefix, ["prefix"], search_time, len(results))

            return results

        except Exception as e:
            print(f"Prefix search error: {e}")
            return []

    async def semantic_search(self, word: str, max_results: int = 20) -> list[SearchResult]:
        """Semantic similarity search using vectorized methods."""
        if not self.is_initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Use different vectorized methods for semantic search
            methods = [
                VectorSearchMethod.CHARACTER,
                VectorSearchMethod.SUBWORD,
                VectorSearchMethod.TFIDF,
                VectorSearchMethod.FUSION,
            ]
            all_results: list[SearchResult] = []

            for method in methods:
                vector_results = self.vectorized_search.search(word, max_results // 2, method)
                for result_word, score in vector_results:
                    all_results.append(
                        SearchResult(
                            word=result_word,
                            score=score * 0.9,  # Slight penalty to distinguish from fuzzy
                            method=f"semantic_{method.value}",
                            explanation=f"Semantic similarity via {method.value} embeddings",
                            distance=0,
                            language=LanguageCode.ENGLISH.value,
                        )
                    )

            # Merge and sort
            merged_results = self._merge_search_results(all_results)
            merged_results.sort(key=lambda x: x.score, reverse=True)

            search_time = time.time() - start_time
            self._update_search_stats(word, ["semantic"], search_time, len(merged_results))

            return merged_results[:max_results]

        except Exception as e:
            print(f"Semantic search error: {e}")
            return []

    def _merge_search_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Merge duplicate search results, combining scores and methods."""
        word_to_best: dict[str, SearchResult] = {}

        for result in results:
            word_key = result.word.lower()

            if word_key not in word_to_best:
                word_to_best[word_key] = result
            else:
                existing = word_to_best[word_key]

                # Combine scores with weighted average
                combined_score = max(existing.score, result.score)

                # Combine methods
                combined_method = f"{existing.method}+{result.method}"
                combined_explanation = f"{existing.explanation}; {result.explanation}"

                word_to_best[word_key] = SearchResult(
                    word=result.word,  # Keep original casing
                    score=combined_score,
                    method=combined_method,
                    explanation=combined_explanation,
                    distance=min(existing.distance, result.distance),
                    language=existing.language,
                )

        return list(word_to_best.values())

    def _update_search_stats(
        self, query: str, methods: list[str], search_time: float, result_count: int
    ) -> None:
        """Update search performance statistics."""
        # Use all parameters to avoid warnings
        query_len = len(query.strip())
        self.search_stats["total_searches"] += 1
        self.search_stats["total_results"] = (
            self.search_stats.get("total_results", 0) + result_count
        )

        # Update average search time
        total_time = (
            self.search_stats["avg_search_time"] * (self.search_stats["total_searches"] - 1)
            + search_time
        )
        self.search_stats["avg_search_time"] = total_time / self.search_stats["total_searches"]

        # Update method usage
        for method in methods:
            self.search_stats["method_usage"][method] = (
                self.search_stats["method_usage"].get(method, 0) + 1
            )
        
        # Track query characteristics
        if "query_lengths" not in self.search_stats:
            self.search_stats["query_lengths"] = {}
        self.search_stats["query_lengths"][query_len] = (
            self.search_stats["query_lengths"].get(query_len, 0) + 1
        )

    async def rebuild_indices(self) -> None:
        """Rebuild all search indices from scratch."""
        print("🔄 Rebuilding search indices...")
        await self.initialize(force_rebuild=True)

    def get_search_stats(self) -> dict[str, Any]:
        """Get comprehensive search engine statistics."""
        index_stats = self.word_index.get_stats()
        vector_stats = self.vectorized_search.get_stats()
        lexicon_stats = self.lexicon_loader.get_lexicon_stats()

        return {
            "is_initialized": self.is_initialized,
            "performance": self.search_stats,
            "index": index_stats,
            "vectorized": vector_stats,
            "lexicons": lexicon_stats,
            "cache_dir": str(self.cache_dir),
            "supported_methods": [
                SearchMethod.HYBRID.value,
                SearchMethod.VECTORIZED.value,
                SearchMethod.RAPIDFUZZ.value,
                SearchMethod.PREFIX.value,
                SearchMethod.SEMANTIC.value,
            ],
        }

    async def add_words_to_index(
        self, words: list[str], language: LanguageCode = LanguageCode.ENGLISH
    ) -> None:
        """Add new words to the search indices."""
        if not self.is_initialized:
            await self.initialize()

        print(f"Adding {len(words)} words to search index...")

        for word in words:
            self.word_index.add_word(word, language.value)

        # Rebuild vectorized index with new words
        all_words = list(self.word_index.trie.trie.keys())
        self.vectorized_search.build_index(all_words)

        # Save updated indices
        self.word_index.save_cache()
        self.vectorized_search.save_index()

        print(f"✅ Added {len(words)} words to search index")

    async def search_with_filters(
        self,
        query: str,
        language: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        starts_with: str | None = None,
        ends_with: str | None = None,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Advanced search with filtering options."""
        # Perform regular search first
        results = await self.search(query, max_results * 2)  # Get more to filter

        # Apply filters
        filtered_results = []
        for result in results:
            word = result.word.lower()

            # Language filter
            if language and result.language != language:
                continue

            # Length filters
            if min_length and len(word) < min_length:
                continue
            if max_length and len(word) > max_length:
                continue

            # Prefix/suffix filters
            if starts_with and not word.startswith(starts_with.lower()):
                continue
            if ends_with and not word.endswith(ends_with.lower()):
                continue

            filtered_results.append(result)

        return filtered_results[:max_results]

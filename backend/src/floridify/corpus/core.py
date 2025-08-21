"""Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic and base corpus source configuration.
"""

from __future__ import annotations

import time
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.models import VersionConfig
from ..models.base import Language
from ..text.normalize import batch_lemmatize, batch_normalize
from ..utils.logging import get_logger
from .manager import get_tree_corpus_manager
from .models import CorpusType
from .utils import get_vocabulary_hash

logger = get_logger(__name__)


class Corpus(BaseModel):
    """In-memory corpus containing vocabulary data and processing logic.

    This class contains all vocabulary data and provides processing functionality.
    Integrates with VersionedDataManager for persistence.
    """

    # Core identification
    corpus_name: str
    corpus_type: CorpusType = CorpusType.LEXICON
    language: Language = Language.ENGLISH

    # Core vocabulary data - dual storage for original preservation
    vocabulary: list[str] = Field(default_factory=list)  # Normalized forms for search
    original_vocabulary: list[str] = Field(
        default_factory=list
    )  # Original forms for display

    # Mappings and indices
    normalized_to_original_indices: dict[int, int] = Field(default_factory=dict)
    vocabulary_to_index: dict[str, int] = Field(default_factory=dict)

    # Lemmatization data
    lemmatized_vocabulary: list[str] = Field(default_factory=list)
    word_to_lemma_indices: list[int] = Field(default_factory=list)
    lemma_to_word_indices: list[int] = Field(default_factory=list)

    # Search optimization structures
    signature_buckets: dict[str, list[int]] = Field(default_factory=dict)
    length_buckets: dict[int, list[int]] = Field(default_factory=dict)

    # Metadata and statistics
    metadata: dict[str, Any] = Field(default_factory=dict)
    vocabulary_stats: dict[str, int] = Field(default_factory=dict)
    vocabulary_hash: str = ""
    vocabulary_indices: dict[str, Any] = Field(default_factory=dict)

    # Source information
    sources: list[str] = Field(default_factory=list)
    unique_word_count: int = 0
    total_word_count: int = 0
    last_updated: str | None = None

    # Hierarchical relationships (for tree structure)
    corpus_id: PydanticObjectId | None = None
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Word frequencies (loaded from external storage if needed)
    word_frequencies: dict[str, int] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    async def create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        semantic: bool = True,
        model_name: str | None = None,
        language: Language = Language.ENGLISH,
    ) -> Corpus:
        """Create new corpus with full vocabulary processing.

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
        logger.info(
            f"Creating corpus '{corpus_name}' with {len(vocabulary)} vocabulary items"
        )
        start_time = time.perf_counter()

        corpus = cls(corpus_name=corpus_name, language=language)

        # Store reference to original vocabulary (no copy needed - we don't modify it)
        corpus.original_vocabulary = vocabulary  # Reference, not copy

        # Process vocabulary - normalize all at once, then deduplicate while preserving
        # original mapping. CRITICAL: When multiple originals map to same normalized form,
        # prefer the one with diacritics
        normalized_vocabulary = batch_normalize(vocabulary)

        # Group all originals by their normalized form
        normalized_to_originals: dict[str, list[tuple[int, str]]] = {}
        for orig_idx, (original_word, normalized_word) in enumerate(
            zip(vocabulary, normalized_vocabulary, strict=False),
        ):
            if normalized_word not in normalized_to_originals:
                normalized_to_originals[normalized_word] = []

            normalized_to_originals[normalized_word].append((orig_idx, original_word))

        # For each normalized form, pick the best original (prefer diacritics/special chars)
        normalized_vocab_with_originals = []
        for normalized_word, originals in normalized_to_originals.items():
            # Sort by: 1) has diacritics/special chars, 2) length, 3) lexicographic
            best_orig_idx, best_orig_word = max(
                originals,
                key=lambda x: (x[1] != normalized_word, len(x[1]), x[1]),
            )

            # Could add debug logging here if needed in future
            normalized_vocab_with_originals.append((normalized_word, best_orig_idx))

        # Build final structures
        corpus.vocabulary = [item[0] for item in normalized_vocab_with_originals]
        corpus.vocabulary_to_index = {
            word: idx for idx, word in enumerate(corpus.vocabulary)
        }
        corpus.normalized_to_original_indices = {
            idx: orig_idx
            for idx, (_, orig_idx) in enumerate(normalized_vocab_with_originals)
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
            f"✅ Lemmatization complete: {vocab_count:,} → {lemma_count:,} lemmas "
            f"({lemma_time:.1f}s, {vocab_count / lemma_time:.0f} items/s)",
        )

        # Pre-compute indices with character signature-based candidate selection
        corpus.vocabulary_indices = corpus._create_unified_indices()
        corpus._build_signature_index()

        # Calculate statistics
        corpus.vocabulary_stats = {
            "vocabulary_count": len(corpus.vocabulary),
            "unique_lemmas": len(corpus.lemmatized_vocabulary),
            "avg_word_length": int(
                sum(len(w) for w in corpus.vocabulary) / max(1, len(corpus.vocabulary)),
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
        """Get multiple normalized words by indices in single call.

        3-5x faster than individual calls.
        """
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
        """High-performance LSH-based candidate selection.

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
                max(1, query_len - length_tolerance),
                query_len + length_tolerance + 1,
            )

            for length in target_lengths:
                if (
                    length in self.length_buckets
                    and len(candidate_set) < max_candidates
                ):
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
        avg_signature_size = sum(
            len(bucket) for bucket in self.signature_buckets.values()
        ) / max(
            signature_count,
            1,
        )
        logger.debug(
            f"Built signature index: {signature_count} signatures, "
            f"avg size {avg_signature_size:.1f}",
        )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize corpus to dictionary for caching."""
        return super().model_dump(exclude_none=True, **kwargs)

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Deserialize corpus from cached dictionary."""
        corpus = cls.model_validate(data)

        # Rebuild indices if needed
        if not corpus.signature_buckets or not corpus.length_buckets:
            corpus._build_signature_index()

        return corpus

    @classmethod
    async def get(
        cls,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Get corpus from versioned storage.

        Args:
            corpus_name: Name of the corpus
            config: Version configuration

        Returns:
            Corpus instance or None if not found
        """
        manager = get_tree_corpus_manager()

        # Get the latest corpus metadata
        corpus_metadata = await manager.get_corpus(
            corpus_name=corpus_name,
            config=config,
        )

        if not corpus_metadata:
            return None

        # Load content from metadata
        content = await corpus_metadata.get_content()
        if not content:
            return None

        return cls.model_load(content)

    @classmethod
    async def get_or_create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        language: Language = Language.ENGLISH,
        corpus_type: CorpusType = CorpusType.LEXICON,
        semantic: bool = True,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus:
        """Get existing corpus or create new one.

        Args:
            corpus_name: Name of the corpus
            vocabulary: List of words if creating new
            language: Language of the corpus
            corpus_type: Type of corpus
            semantic: Enable semantic search
            model_name: Embedding model name
            config: Version configuration

        Returns:
            Corpus instance
        """
        # Try to get existing
        existing = await cls.get(corpus_name, config)
        if existing:
            return existing

        # Create new corpus
        corpus = await cls.create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            semantic=semantic,
            model_name=model_name,
            language=language,
        )

        # Set the corpus type
        corpus.corpus_type = corpus_type

        # Save the new corpus
        await corpus.save(config)

        return corpus

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save corpus to versioned storage.

        Args:
            config: Version configuration
        """
        manager = get_tree_corpus_manager()

        # Prepare content to save
        content = self.model_dump()

        # Save using tree corpus manager
        saved = await manager.save_corpus(
            corpus_name=self.corpus_name,
            content=content,
            corpus_type=self.corpus_type,
            language=self.language,
            parent_id=self.parent_corpus_id,
            config=config,
            metadata=self.metadata,
        )

        # Update corpus_id if new
        if saved.id and not self.corpus_id:
            self.corpus_id = saved.id

    async def delete(self) -> None:
        """Delete corpus from storage."""
        if self.corpus_id:

            # TODO: Implement proper deletion through version manager
            corpus_meta = None  # await CorpusMetadata.get(self.corpus_id)
            if corpus_meta:
                await corpus_meta.delete()


class MultisourceCorpus(Corpus):
    """Multi-source corpus with tree structure and vocabulary aggregation.
    
    Provides hierarchical management of multiple corpus sources with automatic
    vocabulary aggregation from child corpora.
    """
    
    # Source management
    source_corpora: dict[str, Corpus] = Field(default_factory=dict)
    source_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
    
    async def add_source(
        self,
        source_name: str,
        vocabulary: list[str] | None = None,
        corpus: Corpus | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a new source to the multi-source corpus.
        
        Args:
            source_name: Unique identifier for the source
            vocabulary: Raw vocabulary list to create corpus from
            corpus: Existing corpus to add as source
            metadata: Additional metadata for the source
        """
        if source_name in self.source_corpora:
            logger.warning(f"Source '{source_name}' already exists, updating...")
            
        if corpus:
            source_corpus = corpus
        elif vocabulary:
            source_corpus = await Corpus.create(
                corpus_name=f"{self.corpus_name}_{source_name}",
                vocabulary=vocabulary,
                language=self.language,
                semantic=self.metadata.get("semantic_enabled", False),
                model_name=self.metadata.get("model_name"),
            )
        else:
            raise ValueError("Either vocabulary or corpus must be provided")
            
        # Set parent relationship
        source_corpus.parent_corpus_id = self.corpus_id
        
        # Store source
        self.source_corpora[source_name] = source_corpus
        self.source_metadata[source_name] = metadata or {}
        
        # Update child IDs
        if source_corpus.corpus_id and source_corpus.corpus_id not in self.child_corpus_ids:
            self.child_corpus_ids.append(source_corpus.corpus_id)
            
        # Update sources list
        if source_name not in self.sources:
            self.sources.append(source_name)
            
        # Aggregate vocabulary
        await self.aggregate_vocabulary()
        
    async def remove_source(self, source_name: str) -> None:
        """Remove a source from the multi-source corpus.
        
        Args:
            source_name: Name of the source to remove
        """
        if source_name not in self.source_corpora:
            logger.warning(f"Source '{source_name}' not found")
            return
            
        source_corpus = self.source_corpora[source_name]
        
        # Remove from collections
        del self.source_corpora[source_name]
        del self.source_metadata[source_name]
        
        # Update child IDs
        if source_corpus.corpus_id in self.child_corpus_ids:
            self.child_corpus_ids.remove(source_corpus.corpus_id)
            
        # Update sources list
        if source_name in self.sources:
            self.sources.remove(source_name)
            
        # Re-aggregate vocabulary
        await self.aggregate_vocabulary()
        
    async def update_source(
        self,
        source_name: str,
        vocabulary: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update an existing source.
        
        Args:
            source_name: Name of the source to update
            vocabulary: New vocabulary for the source
            metadata: Updated metadata
        """
        if source_name not in self.source_corpora:
            logger.warning(f"Source '{source_name}' not found, adding as new")
            await self.add_source(source_name, vocabulary, metadata=metadata)
            return
            
        if vocabulary:
            # Re-create corpus with new vocabulary
            updated_corpus = await Corpus.create(
                corpus_name=f"{self.corpus_name}_{source_name}",
                vocabulary=vocabulary,
                language=self.language,
                semantic=self.metadata.get("semantic_enabled", False),
                model_name=self.metadata.get("model_name"),
            )
            updated_corpus.parent_corpus_id = self.corpus_id
            updated_corpus.corpus_id = self.source_corpora[source_name].corpus_id
            
            self.source_corpora[source_name] = updated_corpus
            
        if metadata:
            self.source_metadata[source_name].update(metadata)
            
        # Re-aggregate vocabulary
        await self.aggregate_vocabulary()
        
    async def update_sources_bulk(
        self,
        updates: dict[str, dict[str, Any]],
    ) -> None:
        """Update multiple sources in a single operation.
        
        Args:
            updates: Dict mapping source names to update data
                    Each update can contain 'vocabulary' and/or 'metadata'
        """
        for source_name, update_data in updates.items():
            await self.update_source(
                source_name,
                vocabulary=update_data.get("vocabulary"),
                metadata=update_data.get("metadata"),
            )
            
    async def re_download_source(
        self,
        source_name: str,
        download_func: Any = None,
    ) -> None:
        """Re-download and update a source.
        
        Args:
            source_name: Name of the source to re-download
            download_func: Async function to download source data
        """
        if source_name not in self.source_corpora:
            raise ValueError(f"Source '{source_name}' not found")
            
        if not download_func:
            raise ValueError("download_func must be provided")
            
        # Download new data
        logger.info(f"Re-downloading source '{source_name}'...")
        new_vocabulary = await download_func(self.source_metadata[source_name])
        
        # Update source with new data
        await self.update_source(source_name, vocabulary=new_vocabulary)
        
        # Update metadata
        self.source_metadata[source_name]["last_downloaded"] = time.time()
        
    async def aggregate_vocabulary(self) -> None:
        """Aggregate vocabulary from all child sources."""
        if not self.source_corpora:
            return
            
        logger.info(f"Aggregating vocabulary from {len(self.source_corpora)} sources")
        
        # Collect all vocabularies
        all_vocabularies = []
        all_original_vocabularies = []
        
        for source_name, source_corpus in self.source_corpora.items():
            all_vocabularies.extend(source_corpus.vocabulary)
            all_original_vocabularies.extend(source_corpus.original_vocabulary)
            
        # Deduplicate while preserving originals
        unique_normalized = list(dict.fromkeys(all_vocabularies))
        
        # Build mapping from normalized to best original
        normalized_to_original: dict[str, str] = {}
        for norm, orig in zip(all_vocabularies, all_original_vocabularies):
            if norm not in normalized_to_original or len(orig) > len(normalized_to_original[norm]):
                normalized_to_original[norm] = orig
                
        # Update corpus vocabulary
        self.vocabulary = unique_normalized
        self.original_vocabulary = [normalized_to_original[norm] for norm in unique_normalized]
        
        # Rebuild indices
        self.vocabulary_to_index = {word: idx for idx, word in enumerate(self.vocabulary)}
        self._build_signature_index()
        
        # Update statistics
        self.unique_word_count = len(self.vocabulary)
        self.total_word_count = len(all_vocabularies)
        self.vocabulary_stats.update({
            "source_count": len(self.source_corpora),
            "total_words": self.total_word_count,
            "unique_words": self.unique_word_count,
            "deduplication_ratio": float(self.unique_word_count) / max(1, self.total_word_count),
        })
        
        # Update hash
        self.vocabulary_hash = get_vocabulary_hash(
            self.vocabulary,
            self.metadata.get("model_name"),
        )
        
        logger.info(
            f"Aggregated {self.total_word_count:,} words → {self.unique_word_count:,} unique"
        )
        
    async def get_source_vocabulary(self, source_name: str) -> list[str]:
        """Get vocabulary from a specific source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            List of words from the source
        """
        if source_name not in self.source_corpora:
            raise ValueError(f"Source '{source_name}' not found")
            
        return self.source_corpora[source_name].vocabulary
        
    async def save(self, config: VersionConfig | None = None) -> None:
        """Save multi-source corpus and all child sources."""
        # Mark as master corpus
        self.is_master = True
        
        # Save child sources first
        for source_name, source_corpus in self.source_corpora.items():
            await source_corpus.save(config)
            
        # Save master corpus
        await super().save(config)
        
        # Update tree relationships
        manager = get_tree_corpus_manager()
        if self.corpus_id:
            for child_id in self.child_corpus_ids:
                await manager.update_parent(child_id, self.corpus_id)
                
    @classmethod
    async def create_from_sources(
        cls,
        corpus_name: str,
        sources: dict[str, list[str] | Corpus],
        language: Language = Language.ENGLISH,
        corpus_type: CorpusType = CorpusType.LEXICON,
        semantic: bool = False,
        model_name: str | None = None,
    ) -> MultisourceCorpus:
        """Create multi-source corpus from multiple sources.
        
        Args:
            corpus_name: Name for the master corpus
            sources: Dict mapping source names to vocabularies or corpora
            language: Language of the corpus
            corpus_type: Type of corpus
            semantic: Enable semantic search
            model_name: Embedding model name
            
        Returns:
            Configured MultisourceCorpus instance
        """
        # Create empty master corpus
        corpus = cls(
            corpus_name=corpus_name,
            corpus_type=corpus_type,
            language=language,
            is_master=True,
        )
        
        corpus.metadata = {
            "semantic_enabled": semantic,
            "model_name": model_name,
            "creation_time": time.time(),
        }
        
        # Add all sources
        for source_name, source_data in sources.items():
            if isinstance(source_data, Corpus):
                await corpus.add_source(source_name, corpus=source_data)
            else:
                await corpus.add_source(source_name, vocabulary=source_data)
                
        return corpus

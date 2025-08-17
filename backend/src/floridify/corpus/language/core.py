"""Language corpus core models and functionality.

Contains the LanguageCorpus model inheriting from base Corpus.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from ...caching.manager import get_tree_corpus_manager
from ...models.dictionary import CorpusType, Language
from ...models.versioned import VersionConfig
from ..core import Corpus
from ..utils import get_vocabulary_hash


class LanguageCorpus(Corpus):
    """Language corpus with aggregated vocabulary from multiple sources.
    
    Inherits all base corpus functionality and adds language-specific
    source management and aggregation capabilities.
    """
    
    # Source tracking
    source_vocabularies: dict[str, list[str]] = Field(default_factory=dict)
    source_count: int = 0
    
    def __init__(self, **data: Any) -> None:
        """Initialize language corpus with correct type."""
        data["corpus_type"] = CorpusType.LANGUAGE
        super().__init__(**data)
    
    async def add_source(
        self, 
        source_name: str, 
        vocabulary: list[str],
        config: VersionConfig | None = None,
    ) -> None:
        """Add or update a source corpus vocabulary.
        
        Args:
            source_name: Name of the source (e.g., "wikipedia_idioms")
            vocabulary: Vocabulary from this source
            config: Version configuration for saving
        """
        self.source_vocabularies[source_name] = vocabulary
        
        if source_name not in self.sources:
            self.sources.append(source_name)
        
        # Aggregate vocabularies
        all_words = []
        for source_vocab in self.source_vocabularies.values():
            all_words.extend(source_vocab)
        
        # Deduplicate while preserving order
        seen = set()
        unique_vocab = []
        for word in all_words:
            if word not in seen:
                seen.add(word)
                unique_vocab.append(word)
        
        # Update vocabulary
        self.vocabulary = unique_vocab
        self.original_vocabulary = unique_vocab
        self.unique_word_count = len(unique_vocab)
        self.total_word_count = len(all_words)
        self.source_count = len(self.sources)
        
        # Update hash using utility
        self.vocabulary_hash = get_vocabulary_hash(unique_vocab)
        
        # Rebuild indices for search
        self._build_signature_index()
        self.vocabulary_indices = self._create_unified_indices()
        
        # Save if config provided
        if config:
            await self.save(config)
    
    async def remove_source(
        self, 
        source_name: str,
        config: VersionConfig | None = None,
    ) -> bool:
        """Remove a source corpus and its vocabulary.
        
        Args:
            source_name: Name of the source to remove
            config: Version configuration for saving
            
        Returns:
            True if source was removed, False if not found
        """
        if source_name not in self.sources:
            return False
        
        self.sources.remove(source_name)
        del self.source_vocabularies[source_name]
        
        # Re-aggregate without the removed source
        all_words = []
        for source_vocab in self.source_vocabularies.values():
            all_words.extend(source_vocab)
        
        # Deduplicate
        seen = set()
        unique_vocab = []
        for word in all_words:
            if word not in seen:
                seen.add(word)
                unique_vocab.append(word)
        
        # Update vocabulary
        self.vocabulary = unique_vocab
        self.original_vocabulary = unique_vocab
        self.unique_word_count = len(unique_vocab)
        self.total_word_count = len(all_words)
        self.source_count = len(self.sources)
        
        # Update hash
        self.vocabulary_hash = get_vocabulary_hash(unique_vocab)
        
        # Rebuild indices
        self._build_signature_index()
        self.vocabulary_indices = self._create_unified_indices()
        
        # Save if config provided
        if config:
            await self.save(config)
        
        return True
    
    async def rebuild_source(
        self,
        source_name: str,
        new_vocabulary: list[str],
        config: VersionConfig | None = None,
    ) -> None:
        """Rebuild a specific source with new vocabulary.
        
        Args:
            source_name: Name of the source to rebuild
            new_vocabulary: New vocabulary for the source
            config: Version configuration for saving
        """
        await self.add_source(source_name, new_vocabulary, config)
    
    def get_source_vocabulary(self, source_name: str) -> list[str] | None:
        """Get vocabulary for a specific source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            Vocabulary list or None if source not found
        """
        return self.source_vocabularies.get(source_name)
    
    @classmethod
    async def create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        semantic: bool = True,
        model_name: str | None = None,
        language: Language = Language.ENGLISH,
    ) -> LanguageCorpus:
        """Create new language corpus with vocabulary processing.
        
        Args:
            corpus_name: Name for the corpus
            vocabulary: List of words
            semantic: Enable semantic search
            model_name: Embedding model name
            language: Language of the corpus
            
        Returns:
            New LanguageCorpus instance
        """
        # Use parent create method
        corpus = await super().create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            semantic=semantic,
            model_name=model_name,
            language=language,
        )
        
        # Convert to LanguageCorpus
        return cls(**corpus.model_dump())
    
    @classmethod
    async def create_from_sources(
        cls,
        corpus_name: str,
        source_vocabularies: dict[str, list[str]],
        language: Language = Language.ENGLISH,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Create a language corpus from multiple source vocabularies.
        
        Args:
            corpus_name: Name for the corpus
            source_vocabularies: Dictionary mapping source names to vocabularies
            language: Language of the corpus
            config: Version configuration
            
        Returns:
            New LanguageCorpus instance
        """
        # Aggregate all vocabularies
        all_words = []
        for vocab in source_vocabularies.values():
            all_words.extend(vocab)
        
        # Create corpus
        corpus = await cls.create(
            corpus_name=corpus_name,
            vocabulary=all_words,
            language=language,
        )
        
        # Set source-specific data
        corpus.source_vocabularies = source_vocabularies
        corpus.sources = list(source_vocabularies.keys())
        corpus.source_count = len(corpus.sources)
        
        # Save if config provided
        if config:
            await corpus.save(config)
        
        return corpus
    
    @classmethod
    async def create_with_tree(
        cls,
        corpus_name: str,
        source_vocabularies: dict[str, list[str]],
        language: Language = Language.ENGLISH,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Create language corpus with TreeCorpusManager hierarchy.
        
        Creates individual source corpora as children and aggregates
        them into a master corpus using TreeCorpusManager.
        
        Args:
            corpus_name: Name for the master corpus
            source_vocabularies: Dictionary mapping source names to vocabularies
            language: Language of the corpus
            config: Version configuration
            
        Returns:
            Master LanguageCorpus with child relationships
        """
        manager = get_tree_corpus_manager()
        
        # Create child corpora for each source
        child_ids = []
        for source_name, vocab in source_vocabularies.items():
            child_corpus = await cls.create(
                corpus_name=f"{corpus_name}_{source_name}",
                vocabulary=vocab,
                language=language,
            )
            child_corpus.sources = [source_name]
            
            # Save child
            await child_corpus.save(config)
            if child_corpus.corpus_id:
                child_ids.append(child_corpus.corpus_id)
        
        # Create master corpus
        master_corpus = await cls.create_from_sources(
            corpus_name=corpus_name,
            source_vocabularies=source_vocabularies,
            language=language,
            config=config,
        )
        
        # Establish tree relationships
        if master_corpus.corpus_id:
            master_corpus.is_master = True
            master_corpus.child_corpus_ids = child_ids
            
            # Update relationships
            for child_id in child_ids:
                await manager.update_parent(master_corpus.corpus_id, child_id)
            
            # Aggregate vocabularies
            await manager.aggregate_vocabularies(master_corpus.corpus_id, child_ids)
            
            # Save master with relationships
            await master_corpus.save(config)
        
        return master_corpus
    
    @classmethod
    async def get(
        cls,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus | None:
        """Get language corpus from storage.
        
        Args:
            corpus_name: Name of the corpus
            config: Version configuration
            
        Returns:
            LanguageCorpus instance or None
        """
        corpus = await super().get(corpus_name, config)
        if not corpus:
            return None
        
        if not isinstance(corpus, cls):
            return cls(**corpus.model_dump())
        
        return corpus
    
    @classmethod
    async def get_or_create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        language: Language = Language.ENGLISH,
        corpus_type: CorpusType = CorpusType.LANGUAGE,
        semantic: bool = True,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Get existing language corpus or create new one.
        
        Args:
            corpus_name: Name of the corpus
            vocabulary: Vocabulary list for creation
            language: Language of the corpus
            corpus_type: Type of corpus (ignored, always LANGUAGE)
            semantic: Enable semantic search
            model_name: Embedding model name
            config: Version configuration
            
        Returns:
            LanguageCorpus instance
        """
        # Try to get existing
        existing = await cls.get(corpus_name, config)
        if existing:
            return existing
        
        # Create new
        corpus = await cls.create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            semantic=semantic,
            model_name=model_name,
            language=language,
        )
        
        if config:
            await corpus.save(config)
        
        return corpus
    
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize corpus to dictionary."""
        data = super().model_dump(**kwargs)
        
        # Ensure language-specific fields are included
        data["source_vocabularies"] = self.source_vocabularies
        data["source_count"] = self.source_count
        
        return data
    
    @classmethod
    def model_load(cls, data: dict[str, Any]) -> LanguageCorpus:
        """Deserialize corpus from dictionary."""
        corpus = cls.model_validate(data)
        
        # Rebuild indices if needed
        if not corpus.signature_buckets or not corpus.length_buckets:
            corpus._build_signature_index()
        
        return corpus


__all__ = [
    "LanguageCorpus",
]
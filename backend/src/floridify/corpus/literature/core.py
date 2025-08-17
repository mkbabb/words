"""Literature corpus core models and functionality.

Contains the LiteratureCorpus model inheriting from base Corpus.
"""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import Field

from ...caching.manager import get_tree_corpus_manager
from ...models.dictionary import CorpusType, Language
from ...models.literature import AuthorInfo, Genre, LiteraryWork, Period
from ...models.versioned import VersionConfig
from ..core import Corpus
from ..utils import get_vocabulary_hash


class LiteratureCorpus(Corpus):
    """Literature corpus with vocabulary from literary works.
    
    Inherits all base corpus functionality and adds literature-specific
    work and author management capabilities.
    """
    
    # Literature metadata
    literature_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    authors: list[AuthorInfo] = Field(default_factory=list)
    works: list[LiteraryWork] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)
    
    # Work-level tracking
    work_vocabularies: dict[str, list[str]] = Field(default_factory=dict)
    author_vocabularies: dict[str, list[str]] = Field(default_factory=dict)
    
    # Literature-specific statistics
    total_works: int = 0
    total_authors: int = 0
    work_titles: list[str] = Field(default_factory=list)
    publication_years: list[int] = Field(default_factory=list)
    
    def __init__(self, **data: Any) -> None:
        """Initialize literature corpus with correct type."""
        data["corpus_type"] = CorpusType.LITERATURE
        super().__init__(**data)
    
    async def add_work(
        self,
        work: LiteraryWork,
        author: AuthorInfo,
        vocabulary: list[str],
        config: VersionConfig | None = None,
    ) -> None:
        """Add a literary work with its vocabulary.
        
        Args:
            work: Literary work metadata
            author: Author information
            vocabulary: Vocabulary extracted from the work
            config: Version configuration for saving
        """
        work_id = f"{author.name}:{work.title}"
        
        # Update work vocabulary
        self.work_vocabularies[work_id] = vocabulary
        
        # Update author vocabulary
        if author.name not in self.author_vocabularies:
            self.author_vocabularies[author.name] = []
        self.author_vocabularies[author.name].extend(vocabulary)
        
        # Add to metadata lists if new
        if work not in self.works:
            self.works.append(work)
            self.work_titles.append(work.title)
            if work.year:
                self.publication_years.append(work.year)
        
        if author not in self.authors:
            self.authors.append(author)
        
        if author.period and author.period not in self.periods:
            self.periods.append(author.period)
        
        if work.genre and work.genre not in self.genres:
            self.genres.append(work.genre)
        
        # Aggregate vocabularies
        all_words = []
        for work_vocab in self.work_vocabularies.values():
            all_words.extend(work_vocab)
        
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
        self.total_works = len(self.works)
        self.total_authors = len(self.authors)
        
        # Update hash using utility
        self.vocabulary_hash = get_vocabulary_hash(unique_vocab)
        
        # Rebuild indices
        self._build_signature_index()
        self.vocabulary_indices = self._create_unified_indices()
        
        # Save if config provided
        if config:
            await self.save(config)
    
    async def remove_work(
        self, 
        work_title: str, 
        author_name: str,
        config: VersionConfig | None = None,
    ) -> bool:
        """Remove a work and its vocabulary.
        
        Args:
            work_title: Title of the work
            author_name: Name of the author
            config: Version configuration for saving
            
        Returns:
            True if work was removed, False if not found
        """
        work_id = f"{author_name}:{work_title}"
        
        if work_id not in self.work_vocabularies:
            return False
        
        # Remove vocabulary
        del self.work_vocabularies[work_id]
        
        # Remove from works list
        self.works = [w for w in self.works if w.title != work_title]
        self.work_titles = [t for t in self.work_titles if t != work_title]
        
        # Rebuild author vocabulary without this work
        author_vocab = []
        for wid, vocab in self.work_vocabularies.items():
            if wid.startswith(f"{author_name}:"):
                author_vocab.extend(vocab)
        
        if author_vocab:
            self.author_vocabularies[author_name] = author_vocab
        elif author_name in self.author_vocabularies:
            del self.author_vocabularies[author_name]
            self.authors = [a for a in self.authors if a.name != author_name]
        
        # Re-aggregate all vocabularies
        all_words = []
        for work_vocab in self.work_vocabularies.values():
            all_words.extend(work_vocab)
        
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
        self.total_works = len(self.works)
        self.total_authors = len(self.authors)
        
        # Update hash
        self.vocabulary_hash = get_vocabulary_hash(unique_vocab)
        
        # Rebuild indices
        self._build_signature_index()
        self.vocabulary_indices = self._create_unified_indices()
        
        # Save if config provided
        if config:
            await self.save(config)
        
        return True
    
    async def rebuild_work(
        self,
        work: LiteraryWork,
        author: AuthorInfo,
        new_vocabulary: list[str],
        config: VersionConfig | None = None,
    ) -> None:
        """Rebuild a work with new vocabulary.
        
        Args:
            work: Literary work metadata
            author: Author information
            new_vocabulary: New vocabulary for the work
            config: Version configuration for saving
        """
        await self.add_work(work, author, new_vocabulary, config)
    
    def get_author_vocabulary(self, author_name: str) -> list[str] | None:
        """Get aggregated vocabulary for an author.
        
        Args:
            author_name: Name of the author
            
        Returns:
            Vocabulary list or None if author not found
        """
        return self.author_vocabularies.get(author_name)
    
    def get_work_vocabulary(self, work_title: str, author_name: str) -> list[str] | None:
        """Get vocabulary for a specific work.
        
        Args:
            work_title: Title of the work
            author_name: Name of the author
            
        Returns:
            Vocabulary list or None if work not found
        """
        work_id = f"{author_name}:{work_title}"
        return self.work_vocabularies.get(work_id)
    
    def get_period_vocabulary(self, period: Period) -> list[str]:
        """Get aggregated vocabulary for a literary period.
        
        Args:
            period: Literary period
            
        Returns:
            Aggregated vocabulary for all works in that period
        """
        period_vocab = []
        for author in self.authors:
            if author.period == period:
                author_vocab = self.author_vocabularies.get(author.name, [])
                period_vocab.extend(author_vocab)
        
        # Deduplicate
        return list(set(period_vocab))
    
    @classmethod
    async def create(
        cls,
        corpus_name: str,
        vocabulary: list[str],
        semantic: bool = True,
        model_name: str | None = None,
        language: Language = Language.ENGLISH,
    ) -> LiteratureCorpus:
        """Create new literature corpus with vocabulary processing.
        
        Args:
            corpus_name: Name for the corpus
            vocabulary: List of words
            semantic: Enable semantic search
            model_name: Embedding model name
            language: Language of the corpus
            
        Returns:
            New LiteratureCorpus instance
        """
        # Use parent create method
        corpus = await super().create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            semantic=semantic,
            model_name=model_name,
            language=language,
        )
        
        # Convert to LiteratureCorpus
        return cls(**corpus.model_dump())
    
    @classmethod
    async def create_from_works(
        cls,
        corpus_name: str,
        works: list[tuple[LiteraryWork, AuthorInfo, list[str]]],
        language: Language = Language.ENGLISH,
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Create a literature corpus from multiple works.
        
        Args:
            corpus_name: Name for the corpus
            works: List of (work, author, vocabulary) tuples
            language: Language of the corpus
            config: Version configuration
            
        Returns:
            New LiteratureCorpus instance
        """
        # Aggregate all vocabularies
        all_words = []
        for _, _, vocab in works:
            all_words.extend(vocab)
        
        # Create corpus
        corpus = await cls.create(
            corpus_name=corpus_name,
            vocabulary=all_words,
            language=language,
        )
        
        # Add all works
        for work, author, vocab in works:
            # Add work without saving each time
            await corpus.add_work(work, author, vocab, config=None)
        
        # Save once at the end if config provided
        if config:
            await corpus.save(config)
        
        return corpus
    
    @classmethod
    async def create_with_tree(
        cls,
        corpus_name: str,
        works: list[tuple[LiteraryWork, AuthorInfo, list[str]]],
        language: Language = Language.ENGLISH,
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Create literature corpus with TreeCorpusManager hierarchy.
        
        Creates individual work corpora as children and aggregates
        them into a master corpus using TreeCorpusManager.
        
        Args:
            corpus_name: Name for the master corpus
            works: List of (work, author, vocabulary) tuples
            language: Language of the corpus
            config: Version configuration
            
        Returns:
            Master LiteratureCorpus with child relationships
        """
        manager = get_tree_corpus_manager()
        
        # Create child corpora for each work
        child_ids = []
        for work, author, vocab in works:
            work_id = f"{author.name}_{work.title}".replace(" ", "_")
            child_corpus = await cls.create(
                corpus_name=f"{corpus_name}_{work_id}",
                vocabulary=vocab,
                language=language,
            )
            child_corpus.works = [work]
            child_corpus.authors = [author]
            
            # Save child
            await child_corpus.save(config)
            if child_corpus.corpus_id:
                child_ids.append(child_corpus.corpus_id)
        
        # Create master corpus
        master_corpus = await cls.create_from_works(
            corpus_name=corpus_name,
            works=works,
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
    ) -> LiteratureCorpus | None:
        """Get literature corpus from storage.
        
        Args:
            corpus_name: Name of the corpus
            config: Version configuration
            
        Returns:
            LiteratureCorpus instance or None
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
        corpus_type: CorpusType = CorpusType.LITERATURE,
        semantic: bool = True,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Get existing literature corpus or create new one.
        
        Args:
            corpus_name: Name of the corpus
            vocabulary: Vocabulary list for creation
            language: Language of the corpus
            corpus_type: Type of corpus (ignored, always LITERATURE)
            semantic: Enable semantic search
            model_name: Embedding model name
            config: Version configuration
            
        Returns:
            LiteratureCorpus instance
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
        
        # Ensure literature-specific fields are included
        data["literature_data_ids"] = [str(id) for id in self.literature_data_ids]
        data["authors"] = [a.model_dump() for a in self.authors]
        data["works"] = [w.model_dump() for w in self.works]
        data["periods"] = [p.value if hasattr(p, "value") else p for p in self.periods]
        data["genres"] = [g.value if hasattr(g, "value") else g for g in self.genres]
        data["work_vocabularies"] = self.work_vocabularies
        data["author_vocabularies"] = self.author_vocabularies
        data["total_works"] = self.total_works
        data["total_authors"] = self.total_authors
        data["work_titles"] = self.work_titles
        data["publication_years"] = self.publication_years
        
        return data
    
    @classmethod
    def model_load(cls, data: dict[str, Any]) -> LiteratureCorpus:
        """Deserialize corpus from dictionary."""
        # Convert string IDs back to ObjectIds
        if "literature_data_ids" in data:
            data["literature_data_ids"] = [
                PydanticObjectId(id) if isinstance(id, str) else id
                for id in data["literature_data_ids"]
            ]
        
        # Convert author/work dicts back to models
        if "authors" in data:
            data["authors"] = [
                AuthorInfo(**a) if isinstance(a, dict) else a for a in data["authors"]
            ]
        
        if "works" in data:
            data["works"] = [LiteraryWork(**w) if isinstance(w, dict) else w for w in data["works"]]
        
        # Convert periods/genres back to enums if needed
        if "periods" in data:
            data["periods"] = [Period(p) if isinstance(p, str) else p for p in data["periods"]]
        
        if "genres" in data:
            data["genres"] = [Genre(g) if isinstance(g, str) else g for g in data["genres"]]
        
        corpus = cls.model_validate(data)
        
        # Rebuild indices if needed
        if not corpus.signature_buckets or not corpus.length_buckets:
            corpus._build_signature_index()
        
        return corpus


__all__ = [
    "LiteratureCorpus",
]
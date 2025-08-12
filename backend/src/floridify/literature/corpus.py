"""Literature corpus building and integration with Floridify search infrastructure.

This module bridges literature data with Floridify's existing corpus management,
search engine, and caching systems for seamless integration.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from ..caching import get_unified
from ..models.definition import LiteratureSource as ExistingLiteratureSource
from ..search.corpus.core import Corpus
from ..search.corpus.manager import CorpusManager  
from ..search.models import CorpusMetadata
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory
from .models import (
    Author,
    AuthorMetadata,
    LiteratureCorpusMetadata,
    LiteraryWord,
    LiteraryWork,
    Period,
)

logger = get_logger(__name__)


class LiteratureCorpus:
    """Literature-based corpus that integrates with Floridify search infrastructure.
    
    This class bridges literature data with the existing Corpus and CorpusManager
    systems, providing seamless integration with search, caching, and API layers.
    """
    
    def __init__(
        self,
        corpus_id: str,
        name: str,
        words: list[LiteraryWord],
        metadata: Optional[LiteratureCorpusMetadata] = None
    ):
        self.corpus_id = corpus_id
        self.name = name
        self.words = words
        self.metadata = metadata or LiteratureCorpusMetadata(
            corpus_id=corpus_id,
            name=name
        )
        
        # Create search-compatible word list
        self._vocabulary = [word.to_search_word() for word in words]
        
        # Initialize search corpus integration
        self._search_corpus: Optional[Corpus] = None
        self._corpus_manager: Optional[CorpusManager] = None
    
    @property
    def vocabulary(self) -> list[str]:
        """Get vocabulary as list of strings for search integration."""
        return self._vocabulary
    
    @property
    def vocabulary_set(self) -> set[str]:
        """Get vocabulary as set for fast membership testing."""
        return set(self._vocabulary)
    
    async def to_search_corpus(self) -> Corpus:
        """Convert to search-compatible Corpus object."""
        if self._search_corpus is None:
            logger.info(f"🔍 Creating search corpus for {self.name}")
            
            # Create fully processed Corpus using the proper factory method
            self._search_corpus = await Corpus.create(
                corpus_name=self.corpus_id,
                vocabulary=self._vocabulary,
                semantic=False,  # Literature corpus doesn't need semantic embeddings initially
                model_name="literature_processor"
            )
            
            logger.info(f"✅ Created search corpus: {len(self._vocabulary)} words")
        
        return self._search_corpus
    
    async def register_with_corpus_manager(self) -> None:
        """Register this literature corpus with the search system."""
        if not self._corpus_manager:
            self._corpus_manager = CorpusManager()
        
        # Create search-compatible metadata
        search_metadata = CorpusMetadata(
            corpus_name=self.corpus_id,
            vocabulary_hash=self._compute_vocabulary_hash(),
            vocabulary_stats={
                "word_count": len(self._vocabulary),
                "unique_count": len(set(self._vocabulary)),
                "avg_length": sum(len(w) for w in self._vocabulary) / len(self._vocabulary) if self._vocabulary else 0
            },
            metadata={
                "source": "literature",
                "authors": [author.name for author in self.metadata.authors],
                "periods": [period.value for period in self.metadata.periods],
                "total_works": self.metadata.total_works,
                "literature_version": "1.0.0"
            }
        )
        
        # Get search corpus
        search_corpus = await self.to_search_corpus()
        
        # Use the corpus manager's create method which handles both corpus creation and metadata storage
        created_corpus = await self._corpus_manager.create_corpus(
            corpus_name=self.corpus_id,
            vocabulary=self._vocabulary
        )
        
        # Update our reference to use the properly created corpus
        self._search_corpus = created_corpus
        
        logger.info(f"📊 Registered literature corpus {self.corpus_id} with search system")
    
    def _compute_vocabulary_hash(self) -> str:
        """Compute hash of vocabulary for cache invalidation."""
        vocab_str = json.dumps(sorted(self._vocabulary), sort_keys=True)
        return hashlib.sha256(vocab_str.encode()).hexdigest()
    
    async def save_metadata(self) -> None:
        """Save literature corpus metadata to database."""
        await self.metadata.save()
        logger.debug(f"💾 Saved metadata for corpus {self.corpus_id}")
    
    @classmethod
    async def load_from_metadata(cls, corpus_id: str) -> Optional[LiteratureCorpus]:
        """Load literature corpus from stored metadata."""
        metadata = await LiteratureCorpusMetadata.find_one(
            LiteratureCorpusMetadata.corpus_id == corpus_id
        )
        
        if not metadata:
            return None
        
        # This would require loading the actual words from cache or database
        # For now, return empty corpus with metadata
        return cls(
            corpus_id=corpus_id,
            name=metadata.name,
            words=[],  # Would load from cache
            metadata=metadata
        )
    
    def get_author_statistics(self) -> dict[str, AuthorMetadata]:
        """Get statistics grouped by author."""
        author_stats = {}
        
        for word in self.words:
            author_name = word.author_name
            if author_name not in author_stats:
                # Find author in metadata
                author_obj = None
                for author in self.metadata.authors:
                    if author.name == author_name:
                        author_obj = author
                        break
                
                if not author_obj:
                    continue
                    
                author_stats[author_name] = AuthorMetadata(author=author_obj)
            
            # Update statistics
            stats = author_stats[author_name]
            stats.total_words += word.frequency
            
            if word.word not in stats.most_frequent_words:
                stats.most_frequent_words.append(word.word)
        
        # Finalize statistics
        for stats in author_stats.values():
            stats.unique_vocabulary_size = len(stats.most_frequent_words)
            # Limit to top 50 words
            stats.most_frequent_words = stats.most_frequent_words[:50]
        
        return author_stats
    
    def to_wotd_format(self) -> dict[str, Any]:
        """Convert to WOTD training format."""
        # Extract semantic attributes from first author/work
        if not self.metadata.authors:
            style_idx = 0
            complexity_idx = 0
            era_idx = 0
        else:
            author = self.metadata.authors[0]
            style_idx = author.get_semantic_style_index()
            era_idx = author.get_semantic_era_index()
            
            # Infer complexity from vocabulary characteristics
            avg_length = sum(len(word.word) for word in self.words) / len(self.words) if self.words else 5
            complexity_idx = min(7, max(0, int((avg_length - 3) * 1.5)))
        
        return {
            "id": self.corpus_id,
            "style": ["classical", "modern", "romantic", "neutral"][style_idx % 4],
            "complexity": ["simple", "beautiful", "complex", "plain"][complexity_idx % 4],
            "era": ["shakespearean", "victorian", "modernist", "contemporary"][era_idx % 4],
            "words": [
                {"word": word.word, "frequency": word.frequency}
                for word in self.words
            ],
            "metadata": {
                "source": "literature",
                "authors": [author.name for author in self.metadata.authors],
                "total_works": self.metadata.total_works,
                "corpus_type": "literature"
            }
        }


class LiteratureCorpusBuilder:
    """Builder for creating literature corpora from various sources."""
    
    def __init__(self):
        self.cache_dir = get_cache_directory("literature_corpora")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def build_author_corpus(
        self,
        author: Author,
        works: list[LiteraryWork],
        max_words: int = 1000,
        min_frequency: int = 2
    ) -> LiteratureCorpus:
        """Build corpus for a single author from their works."""
        
        logger.info(f"📚 Building corpus for {author.name} from {len(works)} works")
        
        # Extract words from all works
        word_counter = Counter()
        work_occurrences = {}
        
        # This would integrate with actual text processing
        # For now, create sample data
        sample_words = self._generate_sample_vocabulary(author, works)
        
        for word_text, frequency in sample_words.most_common(max_words):
            if frequency >= min_frequency:
                word_counter[word_text] = frequency
                work_occurrences[word_text] = [work.title for work in works[:3]]  # Sample
        
        # Convert to LiteraryWord objects
        literary_words = []
        for word_text, frequency in word_counter.items():
            literary_word = LiteraryWord(
                word=word_text,
                frequency=frequency,
                works=work_occurrences.get(word_text, []),
                author_name=author.name,
                period=author.period,
            )
            literary_words.append(literary_word)
        
        # Create corpus metadata
        corpus_id = f"{author.name.lower().replace(' ', '_')}_corpus"
        metadata = LiteratureCorpusMetadata(
            corpus_id=corpus_id,
            name=f"{author.name} Literary Corpus",
            authors=[author],
            periods=[author.period],
            genres=[author.primary_genre],
            works=[str(work.id) for work in works if work.id],
            total_works=len(works),
            total_unique_words=len(literary_words),
            total_word_occurrences=sum(word.frequency for word in literary_words)
        )
        
        # Create corpus
        corpus = LiteratureCorpus(
            corpus_id=corpus_id,
            name=metadata.name,
            words=literary_words,
            metadata=metadata
        )
        
        logger.info(f"✅ Built corpus: {len(literary_words)} unique words, "
                   f"{metadata.total_word_occurrences} total occurrences")
        
        return corpus
    
    async def build_multi_author_corpus(
        self,
        authors: list[Author],
        works_per_author: dict[Author, list[LiteraryWork]],
        corpus_name: str,
        max_words_per_author: int = 500
    ) -> LiteratureCorpus:
        """Build corpus combining multiple authors."""
        
        logger.info(f"📚 Building multi-author corpus: {corpus_name}")
        
        all_words = []
        all_authors = []
        all_periods = set()
        all_genres = set()
        all_works = []
        total_works = 0
        
        # Build individual corpora and combine
        for author in authors:
            works = works_per_author.get(author, [])
            if not works:
                continue
                
            author_corpus = await self.build_author_corpus(
                author, works, max_words_per_author
            )
            
            all_words.extend(author_corpus.words)
            all_authors.append(author)
            all_periods.add(author.period)
            all_genres.add(author.primary_genre)
            all_works.extend(author_corpus.metadata.works)
            total_works += len(works)
        
        # Create combined metadata
        corpus_id = corpus_name.lower().replace(' ', '_')
        metadata = LiteratureCorpusMetadata(
            corpus_id=corpus_id,
            name=corpus_name,
            authors=all_authors,
            periods=list(all_periods),
            genres=list(all_genres),
            works=all_works,
            total_works=total_works,
            total_unique_words=len(all_words),
            total_word_occurrences=sum(word.frequency for word in all_words)
        )
        
        corpus = LiteratureCorpus(
            corpus_id=corpus_id,
            name=corpus_name,
            words=all_words,
            metadata=metadata
        )
        
        logger.info(f"✅ Built multi-author corpus: {len(all_words)} words from {len(all_authors)} authors")
        return corpus
    
    def _generate_sample_vocabulary(self, author: Author, works: list[LiteraryWork]) -> Counter:
        """Generate sample vocabulary for testing (would be replaced with actual text processing)."""
        
        # Author-specific sample vocabularies for testing
        vocabularies = {
            "william shakespeare": [
                "thou", "thee", "thy", "thine", "hath", "doth", "wherefore", 
                "prithee", "beauteous", "sovereign", "tempest", "melancholy",
                "fortune", "noble", "gentle", "fair", "sweet", "dear", "love",
                "heart", "soul", "heaven", "earth", "nature", "time", "death"
            ],
            "virginia woolf": [
                "consciousness", "stream", "moment", "memory", "perception",
                "luminous", "wavering", "fragmentary", "interior", "mind",
                "thought", "feeling", "experience", "reality", "time", "space",
                "being", "existence", "identity", "self", "other", "life", "death"
            ],
            "dante alighieri": [
                "divine", "comedy", "paradise", "purgatory", "inferno", "sin",
                "virtue", "heaven", "hell", "pilgrim", "journey", "guide",
                "beatrice", "virgil", "love", "light", "darkness", "truth",
                "justice", "mercy", "faith", "hope", "charity", "soul"
            ],
            "james joyce": [
                "stream", "consciousness", "epiphany", "Dublin", "Irish",
                "language", "wordplay", "narrative", "interior", "monologue",
                "memory", "time", "space", "identity", "exile", "paralysis",
                "art", "artist", "creation", "words", "meaning", "sound"
            ]
        }
        
        # Get sample words or generate generic ones
        sample_words = vocabularies.get(
            author.name.lower(),
            ["word", "language", "literature", "text", "meaning", "expression"]
        )
        
        # Create frequency distribution
        word_freq = Counter()
        for i, word in enumerate(sample_words):
            # Higher frequency for earlier words
            frequency = max(1, 50 - i * 2)
            word_freq[word] = frequency
        
        return word_freq
    
    async def cache_corpus(self, corpus: LiteratureCorpus) -> None:
        """Cache corpus to disk for later retrieval."""
        cache_file = self.cache_dir / f"{corpus.corpus_id}.json"
        
        cache_data = {
            "corpus_id": corpus.corpus_id,
            "name": corpus.name,
            "words": [
                {
                    "word": word.word,
                    "frequency": word.frequency,
                    "works": word.works,
                    "author_name": word.author_name,
                    "period": word.period.value,
                }
                for word in corpus.words
            ],
            "metadata": corpus.metadata.model_dump() if corpus.metadata else None
        }
        
        async with get_unified() as cache:
            await cache.set(
                "literature_corpora",
                corpus.corpus_id,
                cache_data,
                ttl_hours=168  # 7 days
            )
        
        logger.debug(f"💾 Cached corpus {corpus.corpus_id}")
    
    async def load_cached_corpus(self, corpus_id: str) -> Optional[LiteratureCorpus]:
        """Load corpus from cache."""
        async with get_unified() as cache:
            cache_data = await cache.get("literature_corpora", corpus_id)
        
        if not cache_data:
            return None
        
        # Reconstruct corpus from cached data
        words = []
        for word_data in cache_data["words"]:
            word = LiteraryWord(
                word=word_data["word"],
                frequency=word_data["frequency"],
                works=word_data["works"],
                author_name=word_data["author_name"],
                period=Period(word_data["period"])
            )
            words.append(word)
        
        # Reconstruct metadata if available
        metadata = None
        if cache_data["metadata"]:
            metadata = LiteratureCorpusMetadata(**cache_data["metadata"])
        
        corpus = LiteratureCorpus(
            corpus_id=cache_data["corpus_id"],
            name=cache_data["name"],
            words=words,
            metadata=metadata
        )
        
        logger.info(f"📋 Loaded cached corpus {corpus_id}")
        return corpus
"""Literature corpus system integrated with search/corpus.

Provides corpus-based literature analysis using the same infrastructure
as CorpusLanguageLoader but specialized for literary texts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import track

from ...caching.core import CacheNamespace, CacheTTL
from ...caching.unified import get_unified
from ...search.corpus.core import Corpus
from ...text.normalize import batch_lemmatize, batch_normalize
from ...utils.logging import get_logger
from .api.gutenberg import GutenbergConnector
from .mappings import dickens, homer, shakespeare, sophocles
from .models import AuthorInfo, LiteraryWork, Period

logger = get_logger(__name__)
console = Console()


class LiteratureCorpusData(BaseModel):
    """Container for literature corpus data with metadata."""
    
    vocabulary: list[str] = Field(..., description="All vocabulary items from works")
    metadata: dict[str, any] = Field(..., description="Corpus metadata")
    authors: list[AuthorInfo] = Field(default_factory=list, description="Authors included")
    works: list[LiteraryWork] = Field(default_factory=list, description="Works included")
    total_words: int = Field(default=0, ge=0, description="Total word count")
    unique_words: int = Field(default=0, ge=0, description="Unique word count")
    last_updated: str = Field(default="", description="Last update timestamp")
    
    model_config = {"frozen": True}


class LiteratureCorpusLoader:
    """Literature corpus loader integrated with Corpus system.
    
    Similar to CorpusLanguageLoader but specialized for literary texts
    with author and period tracking.
    """
    
    def __init__(self, cache_dir: Path | None = None, force_rebuild: bool = False) -> None:
        """Initialize the literature corpus loader.
        
        Args:
            cache_dir: Optional cache directory for downloaded texts
            force_rebuild: If True, rebuild corpora even if cache exists
        """
        self.force_rebuild = force_rebuild
        self.cache_dir = cache_dir
        
        # Loaded corpora by author
        self.author_corpora: dict[str, LiteratureCorpusData] = {}
        self.period_corpora: dict[Period, LiteratureCorpusData] = {}
        
        # Connectors
        self.gutenberg = GutenbergConnector(cache_dir=cache_dir)
        
        # Author mappings
        self.author_mappings = {
            "homer": homer,
            "shakespeare": shakespeare,
            "dickens": dickens,
            "sophocles": sophocles,
        }
    
    async def load_author_corpus(
        self,
        author_name: str,
        max_works: int | None = None,
        normalize: bool = True,
        lemmatize: bool = False,
    ) -> Corpus:
        """Load corpus for a specific author.
        
        Args:
            author_name: Name of the author (must be in mappings)
            max_works: Maximum number of works to load
            normalize: Whether to normalize text
            lemmatize: Whether to lemmatize words
            
        Returns:
            Corpus object with author's vocabulary
        """
        author_key = author_name.lower().replace(" ", "_")
        
        # Check cache first
        cache_key = f"literature_corpus_{author_key}_{max_works}"
        if not self.force_rebuild:
            cached = await self._load_from_cache(cache_key)
            if cached:
                return await self._create_corpus_from_data(cached, normalize, lemmatize)
        
        # Load author mapping
        if author_key not in self.author_mappings:
            raise ValueError(f"No mapping found for author: {author_name}")
        
        author_module = self.author_mappings[author_key]
        author_info = author_module.get_author()
        works = author_module.get_works()
        
        if max_works:
            works = works[:max_works]
        
        # Download and process works
        vocabulary = []
        console.print(f"[blue]Loading {len(works)} works by {author_info.name}...[/blue]")
        
        for work in track(works, description=f"Processing {author_info.name}"):
            try:
                text = await self.gutenberg.download_work(work)
                words = await self._extract_vocabulary(text, normalize)
                vocabulary.extend(words)
            except Exception as e:
                logger.warning(f"Failed to process {work.title}: {e}")
                continue
        
        # Create corpus data
        unique_words = list(set(vocabulary))
        corpus_data = LiteratureCorpusData(
            vocabulary=unique_words,
            metadata={
                "author": author_info.name,
                "period": author_info.period.value,
                "genre": author_info.primary_genre.value,
                "works_count": len(works),
            },
            authors=[author_info],
            works=works,
            total_words=len(vocabulary),
            unique_words=len(unique_words),
            last_updated=datetime.now(UTC).isoformat(),
        )
        
        # Cache the data
        await self._save_to_cache(cache_key, corpus_data)
        
        # Create and return corpus
        return await self._create_corpus_from_data(corpus_data, normalize, lemmatize)
    
    async def load_period_corpus(
        self,
        period: Period,
        max_authors: int | None = None,
        max_works_per_author: int | None = None,
        normalize: bool = True,
    ) -> Corpus:
        """Load corpus for all authors in a specific period.
        
        Args:
            period: Literary period to load
            max_authors: Maximum number of authors to include
            max_works_per_author: Maximum works per author
            normalize: Whether to normalize text
            
        Returns:
            Corpus object with period's vocabulary
        """
        # Find all authors in this period
        period_authors = []
        for module_name, module in self.author_mappings.items():
            author_info = module.get_author()
            if author_info.period == period:
                period_authors.append((module_name, module))
        
        if max_authors:
            period_authors = period_authors[:max_authors]
        
        # Collect vocabulary from all authors
        all_vocabulary = []
        all_works = []
        all_authors = []
        
        for module_name, module in period_authors:
            author_info = module.get_author()
            works = module.get_works()
            
            if max_works_per_author:
                works = works[:max_works_per_author]
            
            all_authors.append(author_info)
            all_works.extend(works)
            
            # Process works
            for work in works:
                try:
                    text = await self.gutenberg.download_work(work)
                    words = await self._extract_vocabulary(text, normalize)
                    all_vocabulary.extend(words)
                except Exception as e:
                    logger.warning(f"Failed to process {work.title}: {e}")
                    continue
        
        # Create corpus
        unique_words = list(set(all_vocabulary))
        corpus_data = LiteratureCorpusData(
            vocabulary=unique_words,
            metadata={
                "period": period.value,
                "authors_count": len(all_authors),
                "works_count": len(all_works),
            },
            authors=all_authors,
            works=all_works,
            total_words=len(all_vocabulary),
            unique_words=len(unique_words),
            last_updated=datetime.now(UTC).isoformat(),
        )
        
        corpus_name = f"literature_{period.value}"
        return await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=unique_words,
            semantic=False,
        )
    
    async def load_multi_author_corpus(
        self,
        author_names: list[str],
        max_works_per_author: int | None = None,
        normalize: bool = True,
    ) -> Corpus:
        """Load corpus combining multiple authors.
        
        Args:
            author_names: List of author names to include
            max_works_per_author: Maximum works per author
            normalize: Whether to normalize text
            
        Returns:
            Combined corpus for all authors
        """
        all_vocabulary = []
        all_works = []
        all_authors = []
        
        for author_name in author_names:
            author_key = author_name.lower().replace(" ", "_")
            
            if author_key not in self.author_mappings:
                logger.warning(f"No mapping for author: {author_name}")
                continue
            
            module = self.author_mappings[author_key]
            author_info = module.get_author()
            works = module.get_works()
            
            if max_works_per_author:
                works = works[:max_works_per_author]
            
            all_authors.append(author_info)
            all_works.extend(works)
            
            # Process works
            for work in works:
                try:
                    text = await self.gutenberg.download_work(work)
                    words = await self._extract_vocabulary(text, normalize)
                    all_vocabulary.extend(words)
                except Exception as e:
                    logger.warning(f"Failed to process {work.title}: {e}")
                    continue
        
        # Create combined corpus
        unique_words = list(set(all_vocabulary))
        corpus_name = f"literature_combined_{len(author_names)}_authors"
        
        return await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=unique_words,
            semantic=False,
        )
    
    async def _extract_vocabulary(self, text: str, normalize: bool = True) -> list[str]:
        """Extract vocabulary from text.
        
        Args:
            text: Raw text to process
            normalize: Whether to normalize text
            
        Returns:
            List of words extracted
        """
        if normalize:
            # Use text normalization from text/normalize.py
            from ...text.normalize import normalize_comprehensive
            text = normalize_comprehensive(
                text,
                fix_encoding=True,
                expand_contractions=True,
                remove_articles=False,
                lowercase=True,
            )
        
        # Simple word extraction (can be enhanced with spaCy)
        import re
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter short words and numbers
        return [w for w in words if len(w) > 2 and not w.isdigit()]
    
    async def _create_corpus_from_data(
        self,
        data: LiteratureCorpusData,
        normalize: bool,
        lemmatize: bool,
    ) -> Corpus:
        """Create Corpus object from literature data.
        
        Args:
            data: Literature corpus data
            normalize: Whether to normalize vocabulary
            lemmatize: Whether to lemmatize vocabulary
            
        Returns:
            Corpus object
        """
        vocabulary = data.vocabulary
        
        if normalize:
            vocabulary = await batch_normalize(vocabulary)
        
        if lemmatize:
            vocabulary = await batch_lemmatize(vocabulary)
        
        # Create corpus name from metadata
        if "author" in data.metadata:
            corpus_name = f"literature_{data.metadata['author'].lower().replace(' ', '_')}"
        elif "period" in data.metadata:
            corpus_name = f"literature_{data.metadata['period']}"
        else:
            corpus_name = "literature_corpus"
        
        return await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            semantic=False,  # Can be enabled for semantic search
        )
    
    async def _load_from_cache(self, cache_key: str) -> LiteratureCorpusData | None:
        """Load corpus data from cache.
        
        Args:
            cache_key: Cache key to load
            
        Returns:
            Cached corpus data or None
        """
        try:
            cache = get_unified()
            cached_data = await cache.get(
                key=cache_key,
                namespace=CacheNamespace.CORPUS,
            )
            
            if cached_data:
                return LiteratureCorpusData.model_validate(cached_data)
        except Exception as e:
            logger.debug(f"Cache load failed for {cache_key}: {e}")
        
        return None
    
    async def _save_to_cache(self, cache_key: str, data: LiteratureCorpusData) -> None:
        """Save corpus data to cache.
        
        Args:
            cache_key: Cache key to save under
            data: Corpus data to save
        """
        try:
            cache = get_unified()
            await cache.set(
                key=cache_key,
                value=data.model_dump(),
                namespace=CacheNamespace.CORPUS,
                ttl=CacheTTL.LONG,
            )
        except Exception as e:
            logger.warning(f"Failed to cache {cache_key}: {e}")
    
    def get_available_authors(self) -> list[str]:
        """Get list of available authors."""
        return list(self.author_mappings.keys())
    
    def get_author_info(self, author_name: str) -> AuthorInfo | None:
        """Get author information.
        
        Args:
            author_name: Name of the author
            
        Returns:
            AuthorInfo or None if not found
        """
        author_key = author_name.lower().replace(" ", "_")
        if author_key in self.author_mappings:
            return self.author_mappings[author_key].get_author()
        return None
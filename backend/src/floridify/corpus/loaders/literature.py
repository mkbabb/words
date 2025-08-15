"""Literature corpus system integrated with search/corpus.

Provides corpus-based literature analysis using the same infrastructure
as CorpusLanguageLoader but specialized for literary texts.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console
from rich.progress import track

from ...caching.core import CacheNamespace, CacheTTL
from ...caching.unified import get_unified
from ...models.dictionary import Language
from ...providers.literature.api.gutenberg import GutenbergConnector
from ...providers.literature.models import AuthorInfo, LiteraryWork, Period
from ...text.normalize import batch_lemmatize, batch_normalize
from ...utils.logging import get_logger
from ..core import Corpus
from ..models import LexiconData
from .base import BaseCorpusLoader

logger = get_logger(__name__)
console = Console()


class LiteratureLexiconData(LexiconData):
    """Literature-specific lexicon data with author and work metadata."""

    # Literature-specific fields
    authors: list[AuthorInfo] = []
    works: list[LiteraryWork] = []
    periods: list[Period] = []

    # Additional metrics
    total_works: int = 0
    sentences_count: int = 0
    paragraphs_count: int = 0


class LiteratureCorpusLoader(BaseCorpusLoader):
    """Literature corpus loader integrated with Corpus system.

    Similar to CorpusLanguageLoader but specialized for literary texts
    with author and period tracking.
    """

    def __init__(self, force_rebuild: bool = False) -> None:
        """Initialize the literature corpus loader.

        Args:
            force_rebuild: If True, rebuild corpora even if cache exists

        """
        super().__init__(force_rebuild=force_rebuild)

        # Loaded corpora by author
        self.author_corpora: dict[str, LexiconData] = {}
        self.period_corpora: dict[Period, LexiconData] = {}

        # Connectors
        self.gutenberg = GutenbergConnector()

        # Author mappings - removed since mappings.py was deleted
        self.author_mappings = {}

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

        # Create corpus data with unique vocabulary
        unique_vocabulary = list(set(vocabulary))
        corpus_data = LiteratureLexiconData(
            vocabulary=unique_vocabulary,  # Always store unique vocabulary
            language=author_info.language if hasattr(author_info, "language") else Language.ENGLISH,
            sources=[work.title for work in works],
            metadata={
                "author": author_info.name,
                "period": author_info.period.value,
                "genre": author_info.primary_genre.value,
                "works_count": len(works),
                "total_word_occurrences": len(vocabulary),  # Store original count in metadata
                "unique_word_count": len(unique_vocabulary),
            },
            authors=[author_info],
            works=works,
            total_works=len(works),
            unique_word_count=len(unique_vocabulary),
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

        words = re.findall(r"\b[a-z]+\b", text.lower())

        # Filter short words and numbers
        return [w for w in words if len(w) > 2 and not w.isdigit()]

    async def _create_corpus_from_data(
        self,
        data: LiteratureLexiconData,
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

    async def _load_from_cache(self, cache_key: str) -> LiteratureLexiconData | None:
        """Load corpus data from cache.

        Args:
            cache_key: Cache key to load

        Returns:
            Cached corpus data or None

        """
        try:
            cache = await get_unified()
            cached_data = await cache.get(
                key=cache_key,
                namespace=CacheNamespace.CORPUS,
            )

            if cached_data:
                return LiteratureLexiconData.model_validate(cached_data)
        except Exception as e:
            logger.debug(f"Cache load failed for {cache_key}: {e}")

        return None

    async def _save_to_cache(self, cache_key: str, data: LexiconData) -> None:
        """Save corpus data to cache.

        Args:
            cache_key: Cache key to save under
            data: Corpus data to save

        """
        try:
            cache = await get_unified()
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

    async def load_corpus(
        self,
        source_id: str,
        **kwargs,
    ) -> LexiconData | None:
        """Load corpus from source.

        Args:
            source_id: Author name or period name
            **kwargs: Additional parameters

        Returns:
            Loaded corpus data or None

        """
        # Try as author first
        if source_id.lower() in [a.lower() for a in self.get_available_authors()]:
            await self.load_author_corpus(
                source_id,
                max_works=kwargs.get("max_works"),
                normalize=kwargs.get("normalize", True),
                lemmatize=kwargs.get("lemmatize", False),
            )
            # Extract data from corpus
            return self.author_corpora.get(source_id.lower())
        return None

    async def get_or_create_corpus(
        self,
        corpus_name: str,
        **kwargs,
    ) -> LexiconData | None:
        """Get existing corpus from cache or create new one.

        Args:
            corpus_name: Name of the corpus
            **kwargs: Additional parameters

        Returns:
            Corpus data from cache or newly created

        """
        # Check cache first
        cache_key = f"literature_corpus_{corpus_name}"
        cached = await self._load_from_cache(cache_key)
        if cached:
            return cached

        # Otherwise try to load
        return await self.load_corpus(corpus_name, **kwargs)

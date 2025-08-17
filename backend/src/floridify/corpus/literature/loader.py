"""Literature corpus loader with hierarchical work management.

Implements the BaseCorpusLoader for literature corpora with support for
authors, works, periods, and versioned storage.
"""

from __future__ import annotations

import re
from typing import Any

from ...models.dictionary import CorpusType, Language
from ...models.literature import AuthorInfo, Genre, LiteraryWork, Period
from ...models.versioned import VersionConfig
from ...providers.literature.api.gutenberg import GutenbergConnector
from ...text.normalize import batch_normalize, normalize_comprehensive
from ...utils.logging import get_logger
from ..loaders.core import BaseCorpusLoader
from .core import LiteratureCorpus

logger = get_logger(__name__)


class LiteratureCorpusLoader(BaseCorpusLoader[LiteratureCorpus]):
    """Literature corpus loader with work-level granularity.

    Features:
    - Author and work-based organization
    - Period and genre classification
    - Work-level granular rebuilding
    - Integration with Gutenberg and other providers
    - Deep integration with VersionManager and TreeCorpusManager
    """

    def __init__(self) -> None:
        """Initialize the literature corpus loader."""
        super().__init__(
            corpus_type=CorpusType.LITERATURE,
            default_language=Language.ENGLISH,
        )

        # Literature providers
        self.gutenberg = GutenbergConnector()

        # Text processing options
        self.min_word_length = 3
        self.exclude_numbers = True

    def _create_corpus_model(
        self,
        corpus_name: str,
        vocabulary: list[str],
        sources: list[str],
        metadata: dict[str, Any],
    ) -> LiteratureCorpus:
        """Create a LiteratureCorpus model.

        Args:
            corpus_name: Name of the corpus
            vocabulary: Aggregated vocabulary
            sources: List of source names (work titles)
            metadata: Additional metadata

        Returns:
            LiteratureCorpus instance
        """
        language = Language(metadata.get("language", self.default_language.value))

        corpus = LiteratureCorpus(
            corpus_name=corpus_name,
            language=language,
            vocabulary=vocabulary,
            metadata=metadata,
        )

        # Set literature-specific fields from metadata
        if "authors" in metadata:
            corpus.authors = metadata["authors"]
        if "works" in metadata:
            corpus.works = metadata["works"]
        if "periods" in metadata:
            corpus.periods = metadata["periods"]
        if "work_vocabularies" in metadata:
            corpus.work_vocabularies = metadata["work_vocabularies"]
        if "author_vocabularies" in metadata:
            corpus.author_vocabularies = metadata["author_vocabularies"]

        return corpus

    async def build_corpus(
        self,
        corpus_name: str,
        sources: list[dict[str, Any]],
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Build a literature corpus from works.

        Args:
            corpus_name: Name for the corpus
            sources: List of work configurations
            config: Version configuration

        Returns:
            Built LiteratureCorpus
        """
        config = config or VersionConfig()

        # Collect vocabulary from all works
        all_vocabulary: list[str] = []
        work_vocabularies: dict[str, list[str]] = {}
        author_vocabularies: dict[str, list[str]] = {}

        authors: list[AuthorInfo] = []
        works: list[LiteraryWork] = []
        periods: set[Period] = set()

        # Process each work
        for source_config in sources:
            work_data = await self._load_work(source_config)

            if not work_data:
                continue

            work = work_data["work"]
            author = work_data["author"]
            vocabulary = work_data["vocabulary"]

            # Store work vocabulary
            work_id = f"{author.name}:{work.title}"
            work_vocabularies[work_id] = vocabulary

            # Update author vocabulary
            if author.name not in author_vocabularies:
                author_vocabularies[author.name] = []
            author_vocabularies[author.name].extend(vocabulary)

            # Add to collections
            all_vocabulary.extend(vocabulary)
            if work not in works:
                works.append(work)
            if author not in authors:
                authors.append(author)
            if author.period:
                periods.add(author.period)

            logger.info(f"Loaded {len(vocabulary)} words from '{work.title}' by {author.name}")

        # Process vocabulary
        all_vocabulary = batch_normalize(all_vocabulary)

        # Prepare works tuples for create_from_works
        works_with_vocab = []
        for work in works:
            # Find matching author
            matching_author = next(
                (
                    a
                    for a in authors
                    if any(
                        work_id.startswith(f"{a.name}:") and work.title in work_id
                        for work_id in work_vocabularies.keys()
                    )
                ),
                None,
            )

            if matching_author:
                work_id = f"{matching_author.name}:{work.title}"
                vocab = work_vocabularies.get(work_id, [])
                works_with_vocab.append((work, matching_author, vocab))

        # Use LiteratureCorpus class method to create
        corpus = await LiteratureCorpus.create_from_works(
            corpus_name=corpus_name,
            works=works_with_vocab,
            language=Language.ENGLISH,
            config=config,
        )

        # Add metadata
        corpus.metadata.update(
            {
                "total_works": len(works),
                "total_authors": len(authors),
                "periods": [p.value for p in periods],
            }
        )

        logger.info(
            f"Built literature corpus '{corpus_name}' with {len(corpus.vocabulary)} unique words "
            f"from {len(works)} works by {len(authors)} authors"
        )

        return corpus

    async def rebuild_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Rebuild a specific work within a literature corpus.

        Args:
            corpus_name: Name of the parent corpus
            source_name: Work title to rebuild (format: "Author:Title")
            config: Version configuration

        Returns:
            Updated LiteratureCorpus with rebuilt work
        """
        config = config or VersionConfig(increment_version=True)

        # Use LiteratureCorpus class method to get
        corpus = await LiteratureCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")

        # Parse work identifier
        if ":" in source_name:
            author_name, work_title = source_name.split(":", 1)
        else:
            # Try to find work by title alone
            work_title = source_name
            author_name = None
            for work_id in corpus.work_vocabularies:
                if work_id.endswith(f":{work_title}"):
                    author_name = work_id.split(":", 1)[0]
                    break

            if not author_name:
                raise ValueError(f"Work '{work_title}' not found in corpus")

        logger.info(f"Rebuilding work '{work_title}' by {author_name} in corpus '{corpus_name}'")

        # Find the work
        target_work = None
        for work in corpus.works:
            if work.title == work_title:
                target_work = work
                break

        if not target_work:
            raise ValueError(f"Work '{work_title}' not found in corpus")

        # Reload the work
        work_data = await self._load_work(
            {
                "title": work_title,
                "author": author_name,
                "gutenberg_id": target_work.gutenberg_id,
            }
        )

        if work_data:
            # Use corpus method to rebuild
            await corpus.rebuild_work(
                work=work_data["work"],
                author=work_data["author"],
                new_vocabulary=work_data["vocabulary"],
                config=config,
            )

        logger.info(f"Rebuilt work '{work_title}' in corpus '{corpus_name}'")

        return corpus

    async def add_source(
        self,
        corpus_name: str,
        source_name: str,
        source_data: dict[str, Any],
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Add a new work to a literature corpus.

        Args:
            corpus_name: Name of the parent corpus
            source_name: Work identifier (format: "Author:Title")
            source_data: Work configuration
            config: Version configuration

        Returns:
            Updated LiteratureCorpus with new work
        """
        config = config or VersionConfig(increment_version=True)

        # Use LiteratureCorpus class method to get
        corpus = await LiteratureCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")

        logger.info(f"Adding work '{source_name}' to corpus '{corpus_name}'")

        # Load the new work
        work_data = await self._load_work(source_data)

        if work_data:
            # Use corpus method to add
            await corpus.add_work(
                work=work_data["work"],
                author=work_data["author"],
                vocabulary=work_data["vocabulary"],
                config=config,
            )

        logger.info(f"Added work '{source_name}' to corpus '{corpus_name}'")

        return corpus

    async def remove_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> LiteratureCorpus:
        """Remove a work from a literature corpus.

        Args:
            corpus_name: Name of the parent corpus
            source_name: Work identifier (format: "Author:Title")
            config: Version configuration

        Returns:
            Updated LiteratureCorpus without the work
        """
        config = config or VersionConfig(increment_version=True)

        # Use LiteratureCorpus class method to get
        corpus = await LiteratureCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")

        # Parse work identifier
        if ":" in source_name:
            author_name, work_title = source_name.split(":", 1)
        else:
            raise ValueError("Work identifier must be in format 'Author:Title'")

        # Use corpus method to remove
        if not await corpus.remove_work(work_title, author_name, config):
            raise ValueError(f"Work '{source_name}' not found in corpus")

        logger.info(f"Removed work '{source_name}' from corpus '{corpus_name}'")

        return corpus

    async def list_sources(
        self,
        corpus_name: str,
    ) -> list[str]:
        """List all works in a literature corpus.

        Args:
            corpus_name: Name of the corpus

        Returns:
            List of work identifiers (format: "Author:Title")
        """
        corpus = await LiteratureCorpus.get(corpus_name)
        if not corpus:
            return []

        return list(corpus.work_vocabularies.keys())

    async def build_author_corpus(
        self,
        author_name: str,
        config: VersionConfig | None = None,
        max_works: int | None = None,
    ) -> LiteratureCorpus:
        """Build a corpus for a specific author.

        Args:
            author_name: Name of the author
            config: Version configuration
            max_works: Maximum number of works to include

        Returns:
            Author-specific LiteratureCorpus
        """
        # Search for author's works
        results = await self.gutenberg.search_works(author_name=author_name)

        if max_works:
            results = results[:max_works]

        # Convert to source configs
        source_configs = []
        for work in results:
            source_configs.append(
                {
                    "title": work.get("title", "Unknown"),
                    "author": author_name,
                    "gutenberg_id": work.get("source_id"),
                }
            )

        # Build corpus
        corpus_name = f"author_{author_name.lower().replace(' ', '_')}"
        return await self.build_corpus(
            corpus_name=corpus_name,
            sources=source_configs,
            config=config,
        )

    async def build_period_corpus(
        self,
        period: Period,
        config: VersionConfig | None = None,
        max_authors: int | None = None,
        max_works_per_author: int | None = None,
    ) -> LiteratureCorpus:
        """Build a corpus for a literary period.

        Args:
            period: Literary period
            config: Version configuration
            max_authors: Maximum number of authors
            max_works_per_author: Maximum works per author

        Returns:
            Period-specific LiteratureCorpus
        """
        # Get canonical authors for period
        period_authors = self._get_period_authors(period)

        if max_authors:
            period_authors = period_authors[:max_authors]

        # Collect works from all authors
        source_configs = []
        for author_name in period_authors:
            results = await self.gutenberg.search_works(author_name=author_name)

            if max_works_per_author:
                results = results[:max_works_per_author]

            for work in results:
                source_configs.append(
                    {
                        "title": work.get("title", "Unknown"),
                        "author": author_name,
                        "gutenberg_id": work.get("source_id"),
                        "period": period,
                    }
                )

        # Build corpus
        corpus_name = f"period_{period.value}"
        return await self.build_corpus(
            corpus_name=corpus_name,
            sources=source_configs,
            config=config,
        )

    async def build_genre_corpus(
        self,
        genre: Genre,
        config: VersionConfig | None = None,
        max_works: int | None = None,
    ) -> LiteratureCorpus:
        """Build a corpus for a literary genre.

        Args:
            genre: Literary genre
            config: Version configuration
            max_works: Maximum number of works

        Returns:
            Genre-specific LiteratureCorpus
        """
        # Search for works by genre
        results = await self.gutenberg.search_works(subject=genre.value)

        if max_works:
            results = results[:max_works]

        # Convert to source configs
        source_configs = []
        for work in results:
            source_configs.append(
                {
                    "title": work.get("title", "Unknown"),
                    "author": work.get("author", "Unknown"),
                    "gutenberg_id": work.get("source_id"),
                    "genre": genre,
                }
            )

        # Build corpus
        corpus_name = f"genre_{genre.value}"
        return await self.build_corpus(
            corpus_name=corpus_name,
            sources=source_configs,
            config=config,
        )

    # Helper methods

    async def _load_work(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Load a literary work and extract vocabulary.

        Args:
            config: Work configuration with title, author, etc.

        Returns:
            Dictionary with work, author, and vocabulary data
        """
        try:
            # Get work metadata
            if "gutenberg_id" in config:
                work_id = config["gutenberg_id"]
            else:
                # Search for the work
                results = await self.gutenberg.search_works(
                    title=config.get("title"),
                    author_name=config.get("author"),
                )
                if not results:
                    logger.warning(f"Work not found: {config}")
                    return None
                work_id = results[0].get("source_id")

            # Download work text
            work_obj = LiteraryWork(
                title=config.get("title", "Unknown"),
                author=self._create_author_info(config.get("author", "Unknown")),
                gutenberg_id=work_id,
                genre=Genre(config.get("genre", Genre.NOVEL.value))
                if "genre" in config
                else Genre.NOVEL,
                period=Period(config.get("period", Period.CONTEMPORARY.value))
                if "period" in config
                else Period.CONTEMPORARY,
            )
            text = await self.gutenberg.download_work(work_obj)
            if not text:
                logger.warning(f"No text available for work ID {work_id}")
                return None

            # Extract vocabulary
            vocabulary = await self._extract_vocabulary(text)

            # Create work metadata
            work = LiteraryWork(
                title=config.get("title", "Unknown"),
                author=self._create_author_info(config.get("author", "Unknown")),
                gutenberg_id=work_id,
                genre=Genre(config.get("genre", Genre.NOVEL.value))
                if "genre" in config
                else Genre.NOVEL,
                period=Period(config.get("period", Period.CONTEMPORARY.value))
                if "period" in config
                else Period.CONTEMPORARY,
            )

            return {
                "work": work,
                "author": work.author,
                "vocabulary": vocabulary,
            }

        except Exception as e:
            logger.error(f"Failed to load work {config}: {e}")
            return None

    async def _extract_vocabulary(
        self,
        text: str,
        normalize: bool = True,
    ) -> list[str]:
        """Extract vocabulary from text.

        Args:
            text: Raw text to process
            normalize: Whether to normalize text

        Returns:
            List of words extracted
        """
        if normalize:
            text = normalize_comprehensive(
                text,
                fix_encoding=True,
                expand_contractions=True,
                remove_articles=False,
                lowercase=True,
            )

        # Extract words
        words = re.findall(r"\b[a-z]+\b", text.lower())

        # Filter based on settings
        filtered = []
        for word in words:
            if len(word) >= self.min_word_length:
                if not self.exclude_numbers or not word.isdigit():
                    filtered.append(word)

        return filtered

    def _create_author_info(
        self,
        author_name: str,
        period: Period | None = None,
        genre: Genre | None = None,
    ) -> AuthorInfo:
        """Create author info from name and optional metadata.

        Args:
            author_name: Author's name
            period: Literary period
            genre: Primary genre

        Returns:
            AuthorInfo instance
        """
        # Try to infer period from known authors
        if not period:
            period = self._infer_period(author_name)

        if not genre:
            genre = Genre.NOVEL  # Default

        return AuthorInfo(
            name=author_name,
            period=period or Period.CONTEMPORARY,
            primary_genre=genre,
            language=self.default_language,
        )

    def _infer_period(self, author_name: str) -> Period | None:
        """Infer literary period from author name.

        Args:
            author_name: Author's name

        Returns:
            Inferred Period or None
        """
        # Simplified period inference based on canonical authors
        period_mapping = {
            Period.ANCIENT: ["Homer", "Virgil", "Ovid", "Sophocles"],
            Period.MEDIEVAL: ["Dante", "Chaucer", "Boccaccio"],
            Period.RENAISSANCE: ["Shakespeare", "Milton", "Cervantes"],
            Period.ENLIGHTENMENT: ["Voltaire", "Rousseau", "Swift"],
            Period.ROMANTIC: ["Byron", "Shelley", "Keats", "Wordsworth"],
            Period.VICTORIAN: ["Dickens", "Eliot", "Hardy", "Wilde"],
            Period.MODERNIST: ["Joyce", "Woolf", "Eliot", "Pound"],
        }

        for period, authors in period_mapping.items():
            for author in authors:
                if author.lower() in author_name.lower():
                    return period

        return None

    def _get_period_authors(self, period: Period) -> list[str]:
        """Get canonical authors for a literary period.

        Args:
            period: Literary period

        Returns:
            List of author names
        """
        period_authors = {
            Period.ANCIENT: ["Homer", "Virgil", "Ovid", "Sophocles", "Aeschylus"],
            Period.MEDIEVAL: ["Dante Alighieri", "Geoffrey Chaucer", "Giovanni Boccaccio"],
            Period.RENAISSANCE: ["William Shakespeare", "John Milton", "Miguel de Cervantes"],
            Period.ENLIGHTENMENT: ["Voltaire", "Jean-Jacques Rousseau", "Jonathan Swift"],
            Period.ROMANTIC: [
                "Lord Byron",
                "Percy Bysshe Shelley",
                "John Keats",
                "William Wordsworth",
            ],
            Period.VICTORIAN: ["Charles Dickens", "George Eliot", "Thomas Hardy", "Oscar Wilde"],
            Period.MODERNIST: ["James Joyce", "Virginia Woolf", "T.S. Eliot", "Ezra Pound"],
            Period.CONTEMPORARY: ["George Orwell", "J.D. Salinger", "Kurt Vonnegut"],
        }

        return period_authors.get(period, [])

"""Language corpus loader with hierarchical source management.

Simplified loader that delegates source management to LanguageCorpus.
"""

from __future__ import annotations

from typing import Any

from ...models.dictionary import CorpusType, Language
from ...models.versioned import VersionConfig
from ...utils.logging import get_logger
from .. import parser
from ..core import CorpusSource
from ..loaders.core import BaseCorpusLoader
from .core import LanguageCorpus
from .sources import LANGUAGE_CORPUS_SOURCES

logger = get_logger(__name__)


class LanguageCorpusLoader(BaseCorpusLoader[LanguageCorpus]):
    """Language corpus loader with multi-source support.
    
    Simplified loader that focuses on data loading and delegates
    source management to LanguageCorpus model.
    """
    
    def __init__(self) -> None:
        """Initialize the language corpus loader."""
        super().__init__(
            corpus_type=CorpusType.LANGUAGE,
            default_language=Language.ENGLISH,
        )
        self.corpus_sources = LANGUAGE_CORPUS_SOURCES
    
    def _create_corpus_model(
        self,
        corpus_name: str,
        vocabulary: list[str],
        sources: list[str],
        metadata: dict[str, Any],
    ) -> LanguageCorpus:
        """Create a LanguageCorpus model.
        
        Args:
            corpus_name: Name of the corpus
            vocabulary: Aggregated vocabulary
            sources: List of source names
            metadata: Additional metadata
            
        Returns:
            LanguageCorpus instance
        """
        language = Language(metadata.get("language", self.default_language.value))
        
        corpus = LanguageCorpus(
            corpus_name=corpus_name,
            language=language,
            vocabulary=vocabulary,
            sources=sources,
            metadata=metadata,
        )
        
        # Set source vocabularies if provided
        if "source_vocabularies" in metadata:
            corpus.source_vocabularies = metadata["source_vocabularies"]
        
        return corpus
    
    async def build_corpus(
        self,
        corpus_name: str,
        sources: list[dict[str, Any]],
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Build a language corpus from sources.
        
        Args:
            corpus_name: Name for the corpus
            sources: List of source configurations
            config: Version configuration
            
        Returns:
            Built LanguageCorpus
        """
        config = config or VersionConfig()
        
        # Collect vocabulary from all sources
        source_vocabularies: dict[str, list[str]] = {}
        
        # Process each source
        for source_config in sources:
            if "name" in source_config:
                source_name = source_config["name"]
                source_vocab = await self._load_source_by_config(source_config)
            else:
                source_name = source_config.get("source_name", "unknown")
                language = Language(source_config.get("language", Language.ENGLISH.value))
                source_vocab = await self._load_source_by_name(source_name, language)
            
            if source_vocab:
                source_vocabularies[source_name] = source_vocab
                logger.info(f"Loaded {len(source_vocab)} words from source '{source_name}'")
        
        # Use LanguageCorpus class method to create
        corpus = await LanguageCorpus.create_from_sources(
            corpus_name=corpus_name,
            source_vocabularies=source_vocabularies,
            language=Language.ENGLISH,
            config=config,
        )
        
        logger.info(
            f"Built language corpus '{corpus_name}' with {len(corpus.vocabulary)} unique words "
            f"from {len(source_vocabularies)} sources"
        )
        
        return corpus
    
    async def build_language_corpus(
        self,
        language: Language,
        config: VersionConfig | None = None,
        max_sources: int | None = None,
    ) -> LanguageCorpus:
        """Build a complete corpus for a language from all available sources.
        
        Args:
            language: Language to build corpus for
            config: Version configuration
            max_sources: Maximum number of sources to include
            
        Returns:
            Complete LanguageCorpus for the language
        """
        # Get all sources for this language
        language_sources = [s for s in self.corpus_sources if s.language == language]
        
        if max_sources:
            language_sources = language_sources[:max_sources]
        
        # Convert to source configs
        source_configs = [
            {"source_name": source.name, "language": language}
            for source in language_sources
        ]
        
        # Build corpus
        corpus_name = f"language_{language.value}_complete"
        return await self.build_corpus(
            corpus_name=corpus_name,
            sources=source_configs,
            config=config,
        )
    
    # These methods now delegate to corpus model
    
    async def rebuild_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Rebuild a specific source within a language corpus.
        
        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the source to rebuild
            config: Version configuration
            
        Returns:
            Updated LanguageCorpus with rebuilt source
        """
        config = config or VersionConfig(increment_version=True)
        
        # Get corpus
        corpus = await LanguageCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")
        
        # Get source configuration
        source_config = self._find_source_config(source_name, corpus.language)
        if not source_config:
            raise ValueError(f"Source '{source_name}' not found in configuration")
        
        # Reload the source
        new_vocab = await self._load_source(source_config)
        
        # Use corpus method to rebuild
        await corpus.rebuild_source(source_name, new_vocab, config)
        
        logger.info(f"Rebuilt source '{source_name}' in corpus '{corpus_name}'")
        
        return corpus
    
    async def add_source(
        self,
        corpus_name: str,
        source_name: str,
        source_data: dict[str, Any],
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Add a new source to a language corpus.
        
        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the new source
            source_data: Configuration for the new source
            config: Version configuration
            
        Returns:
            Updated LanguageCorpus with new source
        """
        config = config or VersionConfig(increment_version=True)
        
        # Get corpus
        corpus = await LanguageCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")
        
        # Load the new source
        if "url" in source_data:
            new_vocab = await self._load_source_by_config(source_data)
        else:
            new_vocab = await self._load_source_by_name(source_name, corpus.language)
        
        # Use corpus method to add
        await corpus.add_source(source_name, new_vocab, config)
        
        logger.info(f"Added source '{source_name}' to corpus '{corpus_name}'")
        
        return corpus
    
    async def remove_source(
        self,
        corpus_name: str,
        source_name: str,
        config: VersionConfig | None = None,
    ) -> LanguageCorpus:
        """Remove a source from a language corpus.
        
        Args:
            corpus_name: Name of the parent corpus
            source_name: Name of the source to remove
            config: Version configuration
            
        Returns:
            Updated LanguageCorpus without the source
        """
        config = config or VersionConfig(increment_version=True)
        
        # Get corpus
        corpus = await LanguageCorpus.get(corpus_name)
        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")
        
        # Use corpus method to remove
        if not await corpus.remove_source(source_name, config):
            raise ValueError(f"Source '{source_name}' not found in corpus")
        
        logger.info(f"Removed source '{source_name}' from corpus '{corpus_name}'")
        
        return corpus
    
    async def list_sources(self, corpus_name: str) -> list[str]:
        """List all sources in a language corpus.
        
        Args:
            corpus_name: Name of the corpus
            
        Returns:
            List of source names
        """
        corpus = await LanguageCorpus.get(corpus_name)
        if not corpus:
            return []
        
        return corpus.sources
    
    # Helper methods for source loading
    
    def _find_source_config(
        self,
        source_name: str,
        language: Language,
    ) -> CorpusSource | None:
        """Find source configuration by name and language."""
        for source in self.corpus_sources:
            if source.name == source_name and source.language == language:
                return source
        return None
    
    async def _load_source_by_name(
        self,
        source_name: str,
        language: Language,
    ) -> list[str]:
        """Load a source by name from LANGUAGE_CORPUS_SOURCES."""
        source_config = self._find_source_config(source_name, language)
        if not source_config:
            logger.warning(f"Source '{source_name}' not found for language {language.value}")
            return []
        
        return await self._load_source(source_config)
    
    async def _load_source_by_config(
        self,
        config: dict[str, Any],
    ) -> list[str]:
        """Load a source from custom configuration."""
        from .scrapers import default_scraper
        
        source = CorpusSource(
            name=config.get("name", "custom"),
            url=config["url"],
            parser=config.get("parser", "parse_text_lines"),
            language=Language(config.get("language", "en")),
            scraper=config.get("scraper", default_scraper),
        )
        
        return await self._load_source(source)
    
    async def _load_source(
        self,
        source: CorpusSource,
    ) -> list[str]:
        """Load data from a specific source.
        
        Args:
            source: Source configuration
            
        Returns:
            List of vocabulary items from the source
        """
        try:
            # Use the scraper function
            if source.scraper:
                result = await source.scraper(source.url)
            else:
                from .scrapers import default_scraper
                result = await default_scraper(source.url)
            
            # Parse the result using the specified parser
            parser_func = getattr(parser, source.parser, None)
            if not parser_func:
                logger.error(f"Parser function '{source.parser}' not found in parser module")
                return []
            
            # Parse the content
            if isinstance(result, str):
                words, phrases = parser_func(result, source.language)
                return list(words + phrases)
            elif isinstance(result, dict):
                words, phrases = parser.parse_scraped_data(result, source.language)
                return list(words + phrases)
            
            logger.warning(f"Invalid response type from source {source.name}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to load source {source.name}: {e}")
            return []


__all__ = [
    "LanguageCorpusLoader",
]
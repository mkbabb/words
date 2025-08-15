"""Lexicon loading and management system.

Supports multiple languages and sources with comprehensive phrase/idiom support.
Implements caching and modular architecture for easy language extension.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from ...caching.core import CacheNamespace, CacheTTL, CompressionType
from ...caching.unified import get_unified
from ...models.dictionary import Language
from ...utils.logging import get_logger
from ..constants import LexiconFormat
from ..models import LexiconData
from ..sources import LEXICON_SOURCES, LexiconSourceConfig
from .base import BaseCorpusLoader

logger = get_logger(__name__)


class CorpusLanguageLoader(BaseCorpusLoader):
    """MongoDB-based corpus loader with multi-language support.

    Features:
    - MongoDB caching instead of filesystem
    - Automatic download from lexicon sources
    - Support for words, phrases, and idioms
    - Language-specific processing
    - Integration with unified CorpusManager
    """

    def __init__(self, force_rebuild: bool = False) -> None:
        """Initialize the corpus loader.

        Args:
            force_rebuild: If True, rebuild corpora even if cache exists

        """
        self.force_rebuild = force_rebuild

        # Loaded data
        self.lexicons: dict[Language, LexiconData] = {}
        self.vocabulary: list[str] = []

        # Use lexicon sources from sources.py
        self.lexicon_sources = LEXICON_SOURCES

    async def load_languages(self, languages: list[Language]) -> None:
        """Load lexicons for specified languages.

        Args:
            languages: List of languages to load

        """
        # Initialize HTTP client
        # HTTP client now handled by scrapers
        logger.info(
            f"Starting to load {len(languages)} language(s): {[lang.value for lang in languages]}",
        )

        # Load each language
        for language in languages:
            await self._load_language(language)

        # Rebuild unified indices
        self._rebuild_unified_indices()
        logger.info(f"Loaded total vocabulary size: {len(self.vocabulary)} items")

    async def _load_language(self, language: Language) -> None:
        """Load corpus data for a specific language from unified cache or sources."""
        source_hash = self._get_source_hash(language)
        cache_key = f"{language.value}_{source_hash}"

        logger.debug(
            f"Loading {language.value} lexicon - cache_key={cache_key[:16]}..., force_rebuild={self.force_rebuild}",
        )

        # Try to load from unified cache first (unless force rebuild)
        if not self.force_rebuild:
            cache = await get_unified()
            cached_data = await cache.get_compressed(CacheNamespace.CORPUS, cache_key)

            if cached_data:
                # Deserialize cached lexicon data
                vocabulary = cached_data.get("vocabulary", [])
                metadata = cached_data.get("metadata", {})

                # Ensure vocabulary is unique
                unique_vocabulary = list(set(vocabulary))
                lexicon = LexiconData(
                    vocabulary=unique_vocabulary,
                    metadata=metadata,
                    language=language,
                    sources=metadata.get("sources", []),
                    unique_word_count=len(unique_vocabulary),
                    last_updated=metadata.get("last_updated", ""),
                )
                self.lexicons[language] = lexicon
                logger.debug(
                    f"Loaded {language.value} lexicon from cache ({len(vocabulary)} items)",
                )
                return
            logger.debug(f"No cached data found for {language.value}, loading from sources")

        # Load from sources
        logger.info(f"Loading {language.value} lexicon from external sources")
        lexicon_data = await self._load_from_sources(language)
        self.lexicons[language] = lexicon_data
        logger.info(
            f"Loaded {language.value} lexicon: {len(lexicon_data.vocabulary)} items from {len(lexicon_data.sources)} sources",
        )

        # Save to unified cache
        await self._save_to_cache(language, lexicon_data, source_hash)

    async def _load_from_sources(self, language: Language) -> LexiconData:
        """Load lexicon data from online sources."""
        vocabulary: list[str] = []

        # Get sources for this language
        sources = self._get_sources_for_language(language)
        logger.debug(
            f"Found {len(sources)} sources for {language.value}: {[s.name for s in sources]}",
        )

        # Load all sources in parallel for performance
        source_tasks = [self._load_source(source) for source in sources]
        source_results = await asyncio.gather(*source_tasks, return_exceptions=True)

        for source, result in zip(sources, source_results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"Failed to load lexicon source {source.name}: {result}")
                continue
            if not isinstance(result, list):
                logger.warning(
                    f"Invalid result type from source {source.name}: expected list[str], got {type(result)}",
                )
                continue

            logger.debug(f"Source {source.name} provided {len(result)} items")
            vocabulary.extend(result)

        # Just deduplicate raw vocabulary - normalization happens in language.py
        logger.debug(f"Deduplicating {len(vocabulary)} raw items")
        unique_vocabulary = sorted(set(vocabulary))
        logger.debug(f"After deduplication: {len(unique_vocabulary)} unique raw items")

        vocabulary = unique_vocabulary

        # Vocabulary is already unique from the processing above
        lexicon = LexiconData(
            vocabulary=vocabulary,  # Already unique
            metadata={"loaded_sources": [s.name for s in sources]},
            language=language,
            sources=[s.name for s in sources],
            unique_word_count=len(vocabulary),
            last_updated=datetime.now(UTC).isoformat(),
        )
        return lexicon

    def _get_sources_for_language(self, language: Language) -> list[LexiconSourceConfig]:
        """Get appropriate sources for a language."""
        return [source for source in self.lexicon_sources if source.language == language]

    def get_lexicon_ext(self, source: LexiconSourceConfig) -> str:
        """Get the file extension for a lexicon source."""
        return ".json" if source.format.value.startswith("json") else ".txt"

    async def _load_source(self, source: LexiconSourceConfig) -> list[str]:
        """Load data from a specific source."""
        # Use the downloader function (handles both regular URLs and custom scraping)
        result = await source.scraper(source.url)

        # Handle custom scraper results (returns dict) vs regular HTTP responses
        if isinstance(result, dict):
            # Custom scraper returned structured data directly
            return self._parse_scraped_data(result, source.language)

        # Regular HTTP response - handle string response from default_scraper
        response_text = result
        if not isinstance(response_text, str):
            logger.warning(
                f"Invalid response type from downloader for {source.name}: expected string, got {type(response_text)}",
            )
            return []

        # Parse based on format
        if source.format == LexiconFormat.TEXT_LINES:
            return self._parse_text_lines(response_text, source.language)
        if source.format == LexiconFormat.JSON_IDIOMS:
            return self._parse_json_idioms(response_text, source.language)
        if source.format == LexiconFormat.FREQUENCY_LIST:
            return self._parse_frequency_list(response_text, source.language)
        if source.format == LexiconFormat.JSON_DICT:
            return self._parse_json_dict(response_text, source.language)
        if source.format == LexiconFormat.JSON_ARRAY:
            return self._parse_json_array(response_text, source.language)
        if source.format == LexiconFormat.JSON_GITHUB_API:
            return self._parse_github_api_response(response_text, source.language)
        if source.format == LexiconFormat.CSV_IDIOMS:
            return self._parse_csv_idioms(response_text, source.language)
        if source.format == LexiconFormat.JSON_PHRASAL_VERBS:
            return self._parse_json_phrasal_verbs(response_text, source.language)
        return []

    def _parse_text_lines(self, text: str, language: Language) -> list[str]:
        """Parse simple text file with one word per line."""
        vocabulary = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            vocabulary.append(line)

        return vocabulary

    def _parse_json_idioms(self, text: str, language: Language) -> list[str]:
        """Parse JSON file containing idioms and phrases."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        vocabulary = []

        # Handle different JSON structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "idioms" in data:
            items = data["idioms"]
        elif isinstance(data, dict):
            items = list(data.values())
        else:
            return []

        for item in items:
            if isinstance(item, str):
                phrase_text = item
            elif isinstance(item, dict):
                # Try common keys for phrase text
                phrase_text = item.get("idiom") or item.get("phrase") or item.get("text") or ""
            else:
                continue

            if phrase_text:
                vocabulary.append(phrase_text)

        return vocabulary

    def _parse_frequency_list(self, text: str, language: Language) -> list[str]:
        """Parse frequency list with word and frequency columns."""
        vocabulary = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split by whitespace - first column is word
            parts = line.split()
            if parts:
                word = parts[0]
                vocabulary.append(word)

        return vocabulary

    def _parse_json_dict(self, text: str, language: Language) -> list[str]:
        """Parse JSON dictionary format."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        vocabulary = []

        if isinstance(data, dict):
            for key in data.keys():
                vocabulary.append(key)

        return vocabulary

    def _parse_json_array(self, text: str, language: Language) -> list[str]:
        """Parse JSON array format."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        vocabulary = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    vocabulary.append(item)

        return vocabulary

    def _parse_github_api_response(self, text: str, language: Language) -> list[str]:
        """Parse GitHub API response for file content."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "content" in data:
                # Decode base64 content
                content = base64.b64decode(data["content"]).decode("utf-8")
                return self._parse_json_array(content, language)
        except Exception as e:
            logger.warning(f"Failed to parse GitHub API response: {e}")
            return []

        logger.warning("GitHub API response missing 'content' field")
        return []

    def _parse_csv_idioms(self, text: str, language: Language) -> list[str]:
        """Parse CSV format with idiom,definition columns."""
        vocabulary = []

        try:
            # Parse CSV data
            csv_reader = csv.DictReader(StringIO(text))

            for row in csv_reader:
                # Try common column names for idiom text
                idiom_text = (
                    row.get("idiom")
                    or row.get("phrase")
                    or row.get("expression")
                    or row.get("text")
                    or ""
                ).strip()

                if not idiom_text:
                    continue

                # Get definition if available (unused but kept for future use)
                _definition = (
                    row.get("def") or row.get("definition") or row.get("meaning") or ""
                ).strip()

                vocabulary.append(idiom_text)

        except Exception as e:
            logger.warning(f"Failed to parse CSV idioms: {e}")
            return []

        return vocabulary

    def _parse_json_phrasal_verbs(self, text: str, language: Language) -> list[str]:
        """Parse JSON format with phrasal verbs, definitions, and examples."""
        vocabulary = []

        try:
            data = json.loads(text)

            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        # Get the phrasal verb text
                        verb_text = (
                            entry.get("verb")
                            or entry.get("phrasal_verb")
                            or entry.get("phrase")
                            or ""
                        ).strip()

                        if not verb_text:
                            continue

                        # Clean up verb text (remove asterisks and plus signs)
                        verb_text = verb_text.replace("*", "").replace("+", "").strip()

                        vocabulary.append(verb_text)

        except Exception as e:
            logger.warning(f"Failed to parse JSON phrasal verbs: {e}")
            return []

        return vocabulary

    def _parse_scraped_data(self, scraped_data: dict[str, Any], language: Language) -> list[str]:
        """Parse data returned by custom scrapers."""
        vocabulary = []

        data = scraped_data.get("data", [])
        if not isinstance(data, list):
            logger.warning("Scraped data should contain a 'data' list")
            return []

        for item in data:
            if isinstance(item, dict):
                expression = item.get("expression", "").strip()
                if not expression:
                    continue

                vocabulary.append(expression)

        return vocabulary

    async def generate_master_index(self, output_path: Path | None = None) -> dict[str, Any]:
        """Generate a master index containing ALL lexical sources, deduplicated.

        Args:
            output_path: Optional path to save the master index

        Returns:
            Master index with statistics and metadata

        """
        # Load all supported languages
        all_languages = [
            Language.ENGLISH,
            Language.FRENCH,
            Language.SPANISH,
            Language.GERMAN,
            Language.ITALIAN,
        ]
        await self.load_languages(all_languages)

        # Collect all unique vocabulary
        master_vocabulary = set()
        source_stats = {}

        for language, lexicon_data in self.lexicons.items():
            # Add vocabulary
            master_vocabulary.update(lexicon_data.vocabulary)

            # Track source statistics
            source_stats[language.value] = {
                "vocabulary": len(lexicon_data.vocabulary),
                "sources": lexicon_data.metadata.get("loaded_sources", []),
                "total_entries": lexicon_data.total_entries,
            }

        # Convert to sorted list
        sorted_vocabulary = sorted(master_vocabulary)

        master_index = {
            "vocabulary": sorted_vocabulary,
            "statistics": {
                "total_vocabulary": len(sorted_vocabulary),
                "languages_processed": list(source_stats.keys()),
                "by_language": source_stats,
            },
            "metadata": {
                "generated_at": datetime.now(UTC).isoformat(),
                "generator": "Floridify LexiconLoader",
                "version": "1.0.0",
            },
        }

        # Save to file if requested
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(master_index, f, indent=2, ensure_ascii=False)

        return master_index

    def _rebuild_unified_indices(self) -> None:
        """Rebuild unified vocabulary index from all loaded languages."""
        self.vocabulary = []

        for lang, lexicon_data in self.lexicons.items():
            logger.debug(f"Adding {len(lexicon_data.vocabulary)} items from {lang.value}")
            self.vocabulary.extend(lexicon_data.vocabulary)

        # Remove duplicates while preserving order
        initial_count = len(self.vocabulary)
        seen = set()
        unique_vocabulary = []
        for item in self.vocabulary:
            if item not in seen:
                seen.add(item)
                unique_vocabulary.append(item)
        self.vocabulary = unique_vocabulary
        logger.debug(
            f"Unified vocabulary: {initial_count} total → {len(self.vocabulary)} unique items",
        )

    def get_vocabulary(self) -> list[str]:
        """Get all vocabulary from all loaded languages."""
        return self.vocabulary

    def get_vocabulary_normalized(self) -> list[str]:
        """Get normalized vocabulary from all loaded languages."""
        if not self.vocabulary:
            return []

        # Import normalization functions at method level
        from ...text.normalize import batch_normalize, normalize_vocabulary_fast

        logger.debug(f"Normalizing {len(self.vocabulary)} vocabulary items...")
        normalized = batch_normalize(self.vocabulary, normalize_vocabulary_fast)

        # Deduplicate after normalization
        normalized = sorted(set(normalized))
        logger.debug(f"Normalized and deduplicated: {len(normalized)} items")

        return normalized

    def get_vocabulary_for_language(self, language: Language) -> list[str]:
        """Get vocabulary for a specific language."""
        if language in self.lexicons:
            return self.lexicons[language].vocabulary.copy()
        return []

    def get_statistics(self) -> dict[str, Any]:
        """Get loading statistics and metadata."""
        stats: dict[str, Any] = {
            "total_vocabulary": len(self.vocabulary),
            "languages": {},
        }

        for language, lexicon_data in self.lexicons.items():
            stats["languages"][language.value] = {
                "vocabulary": len(lexicon_data.vocabulary),
                "sources": lexicon_data.metadata.get("loaded_sources", []),
                "total_entries": lexicon_data.total_entries,
            }

        return stats

    async def get_or_create_corpus_for_languages(
        self,
        languages: list[Language],
        force_rebuild: bool = False,
    ) -> Any:
        """Get or create a corpus for the specified languages.

        Args:
            languages: List of languages to include in corpus
            force_rebuild: Force rebuild of corpus even if cached

        Returns:
            Corpus object (cached or newly created)

        """
        # Import at method level to avoid circular imports
        from ...models.dictionary import CorpusType
        from ..corpus.manager import get_corpus_manager

        # Load languages if not already loaded
        if not self.lexicons or force_rebuild:
            await self.load_languages(languages)

        # Get normalized vocabulary
        vocabulary = self.get_vocabulary_normalized()

        if not vocabulary:
            raise ValueError(f"No vocabulary loaded for languages {languages}")

        # Generate corpus name
        lang_codes = "-".join(sorted(lang.value for lang in languages))
        corpus_name = f"{CorpusType.LANGUAGE_SEARCH.value}_{lang_codes}"

        # Get or create corpus through manager
        corpus_manager = get_corpus_manager()
        corpus = await corpus_manager.get_or_create_corpus(
            corpus_name=corpus_name,
            vocabulary=vocabulary,
            force_rebuild=force_rebuild,
        )

        return corpus

    async def close(self) -> None:
        """Clean up resources."""
        # HTTP client resources are now managed by the caching layer

    def _get_source_hash(self, language: Language) -> str:
        """Generate a hash of source configuration for caching."""
        sources = self._get_sources_for_language(language)
        source_info = []
        for source in sources:
            source_info.append(f"{source.name}:{source.url}:{source.format.value}")

        source_str = "|".join(sorted(source_info))
        return hashlib.sha256(source_str.encode()).hexdigest()

    async def _save_to_cache(
        self,
        language: Language,
        lexicon_data: LexiconData,
        source_hash: str,
    ) -> None:
        """Save lexicon data to unified cache with compression."""
        cache_key = f"{language.value}_{source_hash}"

        # Prepare data for caching
        cache_data = {
            "vocabulary": lexicon_data.vocabulary,
            "metadata": {
                **lexicon_data.metadata,
                "sources": lexicon_data.sources,
                "last_updated": datetime.now(UTC).isoformat(),
            },
        }

        # Save to unified cache with compression
        cache = await get_unified()
        await cache.set_compressed(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
            value=cache_data,
            compression_type=CompressionType.ZLIB,
            ttl=CacheTTL.CORPUS,
            tags=[f"{CacheNamespace.CORPUS}:{language.value}"],
        )

        logger.info(
            f"Cached {language.value} lexicon ({len(lexicon_data.vocabulary)} vocabulary items)",
        )

    async def load_corpus(
        self,
        source_id: str,
        **kwargs,
    ) -> LexiconData | None:
        """Load corpus from source.

        Args:
            source_id: Language code (e.g., "en", "fr")
            **kwargs: Additional parameters

        Returns:
            Loaded corpus data or None

        """
        try:
            language = Language(source_id)
            return await self.get_or_create_lexicon(language)
        except ValueError:
            logger.warning(f"Invalid language code: {source_id}")
            return None

    async def get_or_create_corpus(
        self,
        corpus_name: str,
        **kwargs,
    ) -> LexiconData | None:
        """Get existing corpus from cache or create new one.

        Args:
            corpus_name: Language name or code
            **kwargs: Additional parameters

        Returns:
            Corpus data from cache or newly created

        """
        return await self.load_corpus(corpus_name, **kwargs)

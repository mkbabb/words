"""
Lexicon loading and management system.

Supports multiple languages and sources with comprehensive phrase/idiom support.
Implements caching and modular architecture for easy language extension.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import datetime
import hashlib
import json
from datetime import UTC, timedelta
from datetime import datetime as dt
from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ...models.definition import Language
from ...text import normalize_comprehensive
from ...utils.logging import get_logger
from ..constants import LexiconFormat
from ..models import CorpusCacheEntry, CorpusCompressionUtils
from ..utils import normalize_lexicon_entry
from .sources import LEXICON_SOURCES, LexiconSourceConfig

logger = get_logger(__name__)


class MultiWordExpression(BaseModel):
    """Simple multi-word expression data structure."""

    expression: str = Field(..., description="The multi-word expression")
    normalized: str = Field(..., description="Normalized form")
    frequency: int = Field(default=1, description="Frequency count")
    variants: list[str] = Field(default_factory=list, description="Alternative forms")

    model_config = {"frozen": True}


class LexiconData(BaseModel):
    """Container for lexicon data with metadata."""

    words: list[str] = Field(..., description="Single words")
    phrases: list[MultiWordExpression] = Field(..., description="Multi-word expressions")
    metadata: dict[str, Any] = Field(..., description="Source metadata")
    language: Language = Field(..., description="Language of the lexicon")
    sources: list[str] = Field(default_factory=list, description="Names of loaded sources")
    total_entries: int = Field(default=0, ge=0, description="Total number of entries")
    last_updated: str = Field(default="", description="Last update timestamp")

    model_config = {"frozen": True}


class CorpusLanguageLoader:
    """
    MongoDB-based corpus loader with multi-language support.

    Features:
    - MongoDB caching instead of filesystem
    - Automatic download from lexicon sources
    - Support for words, phrases, and idioms
    - Language-specific processing
    - Integration with unified CorpusManager
    """

    def __init__(self, force_rebuild: bool = False) -> None:
        """
        Initialize the corpus loader.

        Args:
            force_rebuild: If True, rebuild corpora even if cache exists
        """
        self.force_rebuild = force_rebuild

        # Loaded data
        self.lexicons: dict[Language, LexiconData] = {}
        self._all_words: list[str] = []
        self._all_phrases: list[MultiWordExpression] = []

        # Use lexicon sources from sources.py
        self.lexicon_sources = LEXICON_SOURCES

    async def load_languages(self, languages: list[Language]) -> None:
        """
        Load lexicons for specified languages.

        Args:
            languages: List of languages to load
        """
        # Initialize HTTP client
        # HTTP client now handled by scrapers

        # Load each language
        for language in languages:
            await self._load_language(language)

        # Rebuild unified indices
        self._rebuild_unified_indices()

    async def _load_language(self, language: Language) -> None:
        """Load corpus data for a specific language from MongoDB or sources."""
        source_hash = self._get_source_hash(language)

        # Try to load from MongoDB cache first (unless force rebuild)
        if not self.force_rebuild:
            cached = await CorpusCacheEntry.get_cached_corpus(language, source_hash)
            if cached:
                # Decompress and load data
                words_json = CorpusCompressionUtils.decompress_data(cached.words_data).decode(
                    "utf-8"
                )
                phrases_json = CorpusCompressionUtils.decompress_data(cached.phrases_data).decode(
                    "utf-8"
                )
                metadata_json = CorpusCompressionUtils.decompress_data(cached.metadata_data).decode(
                    "utf-8"
                )

                words = json.loads(words_json)
                phrases = [MultiWordExpression(**p) for p in json.loads(phrases_json)]
                metadata = json.loads(metadata_json)

                self.lexicons[language] = LexiconData(
                    words=words,
                    phrases=phrases,
                    metadata=metadata,
                    language=language,
                    sources=metadata.get("sources", []),
                    total_entries=len(words) + len(phrases),
                    last_updated=metadata.get("last_updated", ""),
                )
                return

        # Load from sources
        lexicon_data = await self._load_from_sources(language)
        self.lexicons[language] = lexicon_data

        # Save to MongoDB cache
        await self._save_to_cache(language, lexicon_data)

    async def _load_from_sources(self, language: Language) -> LexiconData:
        """Load lexicon data from online sources."""
        words: list[str] = []
        phrases: list[MultiWordExpression] = []

        # Get sources for this language
        sources = self._get_sources_for_language(language)

        # Load all sources in parallel for performance
        source_tasks = [self._load_source(source) for source in sources]
        source_results = await asyncio.gather(*source_tasks, return_exceptions=True)

        for source, result in zip(sources, source_results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"Failed to load lexicon source {source.name}: {result}")
                continue
            if not isinstance(result, tuple):
                logger.warning(f"Invalid result type from source {source.name}")
                continue

            source_words, source_phrases = result
            words.extend(source_words)
            phrases.extend(source_phrases)

        # Enhanced deduplication with diacritic handling
        normalized_words_map = {}
        for word in words:
            # Generate all diacritic variants
            variants = normalize_lexicon_entry(word)

            for variant in variants:
                if variant not in normalized_words_map:
                    normalized_words_map[variant] = word  # Keep original as reference

        # Create deduplicated word list, sorted
        words = sorted(normalized_words_map.keys())

        # Deduplicate phrases by normalized text with priority
        phrase_dict = {}

        for phrase in phrases:
            # Use existing normalized form, but ensure it's in our map
            key = phrase.normalized
            if key not in phrase_dict:
                phrase_dict[key] = phrase
            else:
                # Keep phrase with higher frequency or from better source
                existing = phrase_dict[key]
                if phrase.frequency > existing.frequency:
                    phrase_dict[key] = phrase

        phrases = list(phrase_dict.values())

        return LexiconData(
            words=words,
            phrases=phrases,
            metadata={"loaded_sources": [s.name for s in sources]},
            language=language,
            sources=[s.name for s in sources],
            total_entries=len(words) + len(phrases),
        )

    def _get_sources_for_language(self, language: Language) -> list[LexiconSourceConfig]:
        """Get appropriate sources for a language."""
        return [source for source in self.lexicon_sources if source.language == language]

    def get_lexicon_ext(self, source: LexiconSourceConfig) -> str:
        """Get the file extension for a lexicon source."""
        return ".json" if source.format.value.startswith("json") else ".txt"

    async def _load_source(
        self, source: LexiconSourceConfig
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Load data from a specific source."""
        # Use the downloader function (handles both regular URLs and custom scraping)
        logger.info(f"Downloading data for source: {source.name}")
        result = await source.scraper(source.url)
        logger.debug(f"Downloaded data for {source.name}, type: {type(result).__name__}")

        # Handle custom scraper results (returns dict) vs regular HTTP responses
        if isinstance(result, dict):
            # Custom scraper returned structured data directly
            return self._parse_scraped_data(result, source.language)

        # Regular HTTP response - process as before
        response = result
        if not hasattr(response, "text"):
            logger.warning(f"Invalid response type from downloader for {source.name}")
            return [], []

        # Parse based on format
        if source.format == LexiconFormat.TEXT_LINES:
            return self._parse_text_lines(response.text, source.language)
        elif source.format == LexiconFormat.JSON_IDIOMS:
            return self._parse_json_idioms(response.text, source.language)
        elif source.format == LexiconFormat.FREQUENCY_LIST:
            return self._parse_frequency_list(response.text, source.language)
        elif source.format == LexiconFormat.JSON_DICT:
            return self._parse_json_dict(response.text, source.language)
        elif source.format == LexiconFormat.JSON_ARRAY:
            return self._parse_json_array(response.text, source.language)
        elif source.format == LexiconFormat.JSON_GITHUB_API:
            return self._parse_github_api_response(response.text, source.language)
        elif source.format == LexiconFormat.CSV_IDIOMS:
            return self._parse_csv_idioms(response.text, source.language)
        elif source.format == LexiconFormat.JSON_PHRASAL_VERBS:
            return self._parse_json_phrasal_verbs(response.text, source.language)
        else:
            return [], []

    def _parse_text_lines(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse simple text file with one word per line."""
        words = []
        phrases = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Normalize the entry
            normalized = normalize_comprehensive(line)
            if not normalized:
                continue

            # Check if it's a phrase (multiple words)
            if len(normalized.split()) > 1:
                phrase = MultiWordExpression(
                    expression=line,
                    normalized=normalized,
                )
                phrases.append(phrase)
            else:
                words.append(normalized)

        return words, phrases

    def _parse_json_idioms(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse JSON file containing idioms and phrases."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return [], []

        phrases = []

        # Handle different JSON structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "idioms" in data:
            items = data["idioms"]
        elif isinstance(data, dict):
            items = list(data.values())
        else:
            return [], []

        for item in items:
            if isinstance(item, str):
                phrase_text = item
            elif isinstance(item, dict):
                # Try common keys for phrase text
                phrase_text = item.get("idiom") or item.get("phrase") or item.get("text") or ""
            else:
                continue

            if not phrase_text:
                continue

            normalized = normalize_comprehensive(phrase_text)
            if normalized and len(normalized.split()) > 1:
                phrase = MultiWordExpression(
                    expression=phrase_text,
                    normalized=normalized,
                )
                phrases.append(phrase)

        return [], phrases  # No single words from idiom sources

    def _parse_frequency_list(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse frequency list with word and frequency columns."""
        words = []
        phrases = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split by whitespace - first column is word, second is frequency
            parts = line.split()
            if len(parts) >= 2:
                word = parts[0]
                try:
                    frequency = float(parts[1])
                except ValueError:
                    frequency = 0.0
            else:
                word = parts[0] if parts else ""
                frequency = 0.0

            if not word:
                continue

            # Normalize the entry
            normalized = normalize_comprehensive(word)
            if not normalized:
                continue

            # Check if it's a phrase
            if len(normalized.split()) > 1:
                phrase = MultiWordExpression(
                    expression=word,
                    normalized=normalized,
                    frequency=int(frequency),
                )
                phrases.append(phrase)
            else:
                words.append(normalized)

        return words, phrases

    def _parse_json_dict(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse JSON dictionary format."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return [], []

        words = []
        phrases = []

        if isinstance(data, dict):
            for key, value in data.items():
                # Key is the word/phrase, value might be expansion or metadata
                normalized = normalize_comprehensive(key)
                if normalized and len(normalized.split()) > 1:
                    phrase = MultiWordExpression(
                        expression=key,
                        normalized=normalized,
                    )
                    phrases.append(phrase)
                elif normalized:
                    words.append(normalized)

        return words, phrases

    def _parse_json_array(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse JSON array format."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return [], []

        words = []
        phrases = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    normalized = normalize_comprehensive(item)
                    if normalized and len(normalized.split()) > 1:
                        phrase = MultiWordExpression(
                            expression=item,
                            normalized=normalized,
                        )
                        phrases.append(phrase)
                    elif normalized:
                        words.append(normalized)

        return words, phrases

    def _parse_github_api_response(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse GitHub API response for file content."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "content" in data:
                # Decode base64 content
                content = base64.b64decode(data["content"]).decode("utf-8")
                return self._parse_json_array(content, language)
        except Exception:
            pass
        return [], []

    def _parse_csv_idioms(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse CSV format with idiom,definition columns."""
        phrases = []

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

                # Normalize the idiom
                normalized = normalize_comprehensive(idiom_text)
                if normalized and len(normalized.split()) > 1:
                    phrase = MultiWordExpression(
                        expression=idiom_text,
                        normalized=normalized,
                    )
                    phrases.append(phrase)

        except Exception as e:
            logger.warning(f"Failed to parse CSV idioms: {e}")
            return [], []

        return [], phrases  # CSV idioms only contain phrases, no single words

    def _parse_json_phrasal_verbs(
        self, text: str, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse JSON format with phrasal verbs, definitions, and examples."""
        phrases = []

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

                        # Normalize the phrasal verb
                        normalized = normalize_comprehensive(verb_text)
                        if normalized and len(normalized.split()) > 1:
                            phrase = MultiWordExpression(
                                expression=verb_text,
                                normalized=normalized,
                            )
                            phrases.append(phrase)

        except Exception as e:
            logger.warning(f"Failed to parse JSON phrasal verbs: {e}")
            return [], []

        return [], phrases  # JSON phrasal verbs only contain phrases, no single words

    def _parse_scraped_data(
        self, scraped_data: dict[str, Any], language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Parse data returned by custom scrapers."""
        words = []
        phrases = []

        data = scraped_data.get("data", [])
        if not isinstance(data, list):
            logger.warning("Scraped data should contain a 'data' list")
            return [], []

        for item in data:
            if isinstance(item, dict):
                expression = item.get("expression", "").strip()
                if not expression:
                    continue

                # Normalize the expression
                normalized = normalize_comprehensive(expression)
                if not normalized:
                    continue

                # Determine if it's a phrase or single word
                if len(normalized.split()) > 1:
                    phrase = MultiWordExpression(
                        expression=expression,
                        normalized=normalized,
                    )
                    phrases.append(phrase)
                else:
                    words.append(normalized)

        logger.info(f"Parsed scraped data: {len(words)} words, {len(phrases)} phrases")
        return words, phrases

    async def generate_master_index(self, output_path: Path | None = None) -> dict[str, Any]:
        """
        Generate a master index containing ALL lexical sources, deduplicated.

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

        # Collect all unique words and phrases
        master_words = set()
        master_phrases = {}  # normalized -> MultiWordExpression
        source_stats = {}

        for language, lexicon_data in self.lexicons.items():
            # Add words
            master_words.update(lexicon_data.words)

            # Add phrases (deduplicate by normalized form)
            for phrase in lexicon_data.phrases:
                if phrase.normalized not in master_phrases:
                    master_phrases[phrase.normalized] = phrase
                else:
                    # Keep the phrase with higher frequency
                    existing = master_phrases[phrase.normalized]
                    if phrase.frequency > existing.frequency:
                        master_phrases[phrase.normalized] = phrase

            # Track source statistics
            source_stats[language.value] = {
                "words": len(lexicon_data.words),
                "phrases": len(lexicon_data.phrases),
                "sources": lexicon_data.metadata.get("loaded_sources", []),
                "total_entries": lexicon_data.total_entries,
            }

        # Convert to sorted lists
        sorted_words = sorted(master_words)
        sorted_phrases = sorted(master_phrases.values(), key=lambda p: p.normalized)

        master_index = {
            "words": sorted_words,
            "phrases": [phrase.model_dump() for phrase in sorted_phrases],
            "statistics": {
                "total_words": len(sorted_words),
                "total_phrases": len(sorted_phrases),
                "total_entries": len(sorted_words) + len(sorted_phrases),
                "languages_processed": list(source_stats.keys()),
                "by_language": source_stats,
            },
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
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
        """Rebuild unified word and phrase indices from all loaded languages."""
        self._all_words = []
        self._all_phrases = []

        for lexicon_data in self.lexicons.values():
            self._all_words.extend(lexicon_data.words)
            self._all_phrases.extend(lexicon_data.phrases)

        # Remove duplicates while preserving order
        seen_words = set()
        unique_words = []
        for word in self._all_words:
            if word not in seen_words:
                seen_words.add(word)
                unique_words.append(word)
        self._all_words = unique_words

        # Deduplicate phrases by normalized text
        phrase_dict = {p.normalized: p for p in self._all_phrases}
        self._all_phrases = list(phrase_dict.values())

    def get_all_words(self) -> list[str]:
        """Get all words from all loaded languages."""
        return self._all_words  # No copy needed since SearchEngine caches

    def get_all_phrases(self) -> list[str]:
        """Get all phrases as strings from all loaded languages."""
        # Cache phrase strings to avoid rebuilding list every time
        if not hasattr(self, "_phrase_strings") or len(self._phrase_strings) != len(
            self._all_phrases
        ):
            self._phrase_strings: list[str] = [phrase.normalized for phrase in self._all_phrases]
        return self._phrase_strings

    def get_phrases(self) -> list[MultiWordExpression]:
        """Get all phrase objects with metadata."""
        return self._all_phrases.copy()

    def get_words_for_language(self, language: Language) -> list[str]:
        """Get words for a specific language."""
        if language in self.lexicons:
            return self.lexicons[language].words.copy()
        return []

    def get_phrases_for_language(self, language: Language) -> list[MultiWordExpression]:
        """Get phrases for a specific language."""
        if language in self.lexicons:
            return self.lexicons[language].phrases.copy()
        return []

    def get_statistics(self) -> dict[str, Any]:
        """Get loading statistics and metadata."""
        stats: dict[str, Any] = {
            "total_words": len(self._all_words),
            "total_phrases": len(self._all_phrases),
            "languages": {},
        }

        for language, lexicon_data in self.lexicons.items():
            stats["languages"][language.value] = {
                "words": len(lexicon_data.words),
                "phrases": len(lexicon_data.phrases),
                "sources": lexicon_data.metadata.get("loaded_sources", []),
                "total_entries": lexicon_data.total_entries,
            }

        return stats

    async def close(self) -> None:
        """Clean up resources."""
        # HTTP client resources are now managed by the caching layer
        pass

    def _get_source_hash(self, language: Language) -> str:
        """Generate a hash of source configuration for caching."""
        sources = self._get_sources_for_language(language)
        source_info = []
        for source in sources:
            source_info.append(f"{source.name}:{source.url}:{source.format.value}")

        source_str = "|".join(sorted(source_info))
        return hashlib.sha256(source_str.encode()).hexdigest()

    async def _save_to_cache(self, language: Language, lexicon_data: LexiconData) -> None:
        """Save lexicon data to MongoDB cache."""
        # Prepare data for compression
        words_json = json.dumps(lexicon_data.words).encode("utf-8")
        phrases_json = json.dumps([p.model_dump() for p in lexicon_data.phrases]).encode("utf-8")
        metadata_json = json.dumps(lexicon_data.metadata).encode("utf-8")

        # Compress data
        words_compressed, words_ratio = CorpusCompressionUtils.compress_data(words_json)
        phrases_compressed, phrases_ratio = CorpusCompressionUtils.compress_data(phrases_json)
        metadata_compressed, metadata_ratio = CorpusCompressionUtils.compress_data(metadata_json)

        # Calculate sizes
        original_size = len(words_json) + len(phrases_json) + len(metadata_json)
        compressed_size = len(words_compressed) + len(phrases_compressed) + len(metadata_compressed)

        # Create cache entry
        cache_entry = CorpusCacheEntry(
            language=language,
            source_hash=self._get_source_hash(language),
            words_data=words_compressed,
            phrases_data=phrases_compressed,
            metadata_data=metadata_compressed,
            compression_ratio=original_size / compressed_size if compressed_size > 0 else 1.0,
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            word_count=len(lexicon_data.words),
            phrase_count=len(lexicon_data.phrases),
            total_entries=lexicon_data.total_entries,
            load_time_ms=0.0,  # Could track actual load time
            compression_time_ms=0.0,  # Could track actual compression time
            expires_at=dt.now(UTC) + timedelta(hours=168),  # 1 week
        )

        # Save to MongoDB
        await cache_entry.save()

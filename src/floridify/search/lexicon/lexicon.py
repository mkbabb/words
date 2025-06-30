"""
Lexicon loading and management system.

Supports multiple languages and sources with comprehensive phrase/idiom support.
Implements caching and modular architecture for easy language extension.
"""

from __future__ import annotations

import datetime
import json
import pickle
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ..phrase import MultiWordExpression, PhraseNormalizer
from .sources import LEXICON_SOURCES, Language, LexiconSourceConfig


class LexiconData(BaseModel):
    """Container for lexicon data with metadata."""

    words: list[str] = Field(..., description="Single words")
    phrases: list[MultiWordExpression] = Field(
        ..., description="Multi-word expressions"
    )
    metadata: dict[str, Any] = Field(..., description="Source metadata")
    language: Language = Field(..., description="Language of the lexicon")
    sources: list[str] = Field(default_factory=list, description="Names of loaded sources")
    total_entries: int = Field(default=0, ge=0, description="Total number of entries")
    last_updated: str = Field(default="", description="Last update timestamp")

    model_config = {"frozen": True}


class LexiconLoader:
    """
    Modular lexicon loader with caching and multi-language support.

    Features:
    - Automatic download and caching of lexicon sources
    - Support for words, phrases, and idioms
    - Language-specific processing
    - Efficient pickle-based caching
    - Extensible architecture for new languages/sources
    """

    def __init__(self, cache_dir: Path, force_rebuild: bool = False) -> None:
        """
        Initialize the lexicon loader.

        Args:
            cache_dir: Directory for caching lexicon data
            force_rebuild: If True, rebuild lexicons even if cache exists
        """
        self.cache_dir = cache_dir
        self.lexicon_dir = cache_dir / "lexicons"
        self.index_dir = cache_dir / "index"
        self.force_rebuild = force_rebuild

        # Ensure directories exist
        self.lexicon_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Core components
        self.phrase_normalizer = PhraseNormalizer()

        # Loaded data
        self.lexicons: dict[Language, LexiconData] = {}
        self._all_words: list[str] = []
        self._all_phrases: list[MultiWordExpression] = []

        # HTTP client for downloads
        self._http_client: httpx.AsyncClient | None = None

        # Use lexicon sources from sources.py
        self.lexicon_sources = LEXICON_SOURCES

    async def load_languages(self, languages: list[Language]) -> None:
        """
        Load lexicons for specified languages.

        Args:
            languages: List of languages to load
        """
        # Initialize HTTP client
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        # Load each language
        for language in languages:
            await self._load_language(language)

        # Rebuild unified indices
        self._rebuild_unified_indices()

    async def _load_language(self, language: Language) -> None:
        """Load lexicon data for a specific language."""
        cache_file = self.index_dir / f"{language.value}_lexicon.pkl"

        # Try to load from cache first (unless force rebuild)
        if not self.force_rebuild and cache_file.exists():
            try:
                with cache_file.open("rb") as f:
                    self.lexicons[language] = pickle.load(f)
                return
            except Exception:
                # Cache corrupted, reload from sources
                pass

        # Load from sources
        lexicon_data = await self._load_from_sources(language)
        self.lexicons[language] = lexicon_data

        # Save to cache
        with cache_file.open("wb") as f:
            pickle.dump(lexicon_data, f)

    async def _load_from_sources(self, language: Language) -> LexiconData:
        """Load lexicon data from online sources."""
        words: list[str] = []
        phrases: list[MultiWordExpression] = []

        # Get sources for this language
        sources = self._get_sources_for_language(language)

        # Load each source
        for source in sources:
            try:
                source_words, source_phrases = await self._load_source(source)
                words.extend(source_words)
                phrases.extend(source_phrases)
            except Exception as e:
                print(f"Warning: Failed to load {source.name}: {e}")
                continue

        # Remove duplicates and normalize
        words = list(set(words))
        words.sort()

        # Deduplicate phrases by normalized text
        phrase_dict = {p.normalized: p for p in phrases}
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
        return ".json" if source.format.startswith("json") else ".txt"

    async def _load_source(
        self, source: LexiconSourceConfig
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Load data from a specific source."""
        # Download data
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        response = await self._http_client.get(source.url)
        response.raise_for_status()

        ext = self.get_lexicon_ext(source)

        # Save to cache
        cache_filepath = self.lexicon_dir / f"{source.name}"
        cache_filepath = cache_filepath.with_suffix(ext)

        with cache_filepath.open("w", encoding="utf-8") as f:
            f.write(response.text)

        # Parse based on format
        if source.format == "text_lines":
            return self._parse_text_lines(response.text, source.language)
        elif source.format == "json_idioms":
            return self._parse_json_idioms(response.text, source.language)
        elif source.format == "frequency_list":
            return self._parse_frequency_list(response.text, source.language)
        elif source.format == "json_dict":
            return self._parse_json_dict(response.text, source.language)
        elif source.format == "json_array":
            return self._parse_json_array(response.text, source.language)
        elif source.format == "json_github_api":
            return self._parse_github_api_response(response.text, source.language)
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
            normalized = self.phrase_normalizer.normalize(line)
            if not normalized:
                continue

            # Check if it's a phrase
            if self.phrase_normalizer.is_phrase(normalized):
                phrase = MultiWordExpression(
                    text=line,
                    normalized=normalized,
                    word_count=len(normalized.split()),
                    language=language.value,
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
                phrase_text = (
                    item.get("idiom") or item.get("phrase") or item.get("text") or ""
                )
            else:
                continue

            if not phrase_text:
                continue

            normalized = self.phrase_normalizer.normalize(phrase_text)
            if normalized and self.phrase_normalizer.is_phrase(normalized):
                phrase = MultiWordExpression(
                    text=phrase_text,
                    normalized=normalized,
                    word_count=len(normalized.split()),
                    is_idiom=True,
                    language=language.value,
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
            normalized = self.phrase_normalizer.normalize(word)
            if not normalized:
                continue

            # Check if it's a phrase
            if self.phrase_normalizer.is_phrase(normalized):
                phrase = MultiWordExpression(
                    text=word,
                    normalized=normalized,
                    word_count=len(normalized.split()),
                    language=language.value,
                    frequency=frequency,
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
                normalized = self.phrase_normalizer.normalize(key)
                if normalized and self.phrase_normalizer.is_phrase(normalized):
                    phrase = MultiWordExpression(
                        text=key,
                        normalized=normalized,
                        word_count=len(normalized.split()),
                        language=language.value,
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
                    normalized = self.phrase_normalizer.normalize(item)
                    if normalized and self.phrase_normalizer.is_phrase(normalized):
                        phrase = MultiWordExpression(
                            text=item,
                            normalized=normalized,
                            word_count=len(normalized.split()),
                            language=language.value,
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
                import base64
                content = base64.b64decode(data["content"]).decode("utf-8")
                return self._parse_json_array(content, language)
        except Exception:
            pass
        return [], []

    async def generate_master_index(
        self, output_path: Path | None = None
    ) -> dict[str, Any]:
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
        return self._all_words.copy()

    def get_all_phrases(self) -> list[str]:
        """Get all phrases as strings from all loaded languages."""
        return [phrase.normalized for phrase in self._all_phrases]

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
        """Close HTTP client and clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
"""
Lexicon loading and management system.

Supports multiple languages and sources with comprehensive phrase/idiom support.
Implements caching and modular architecture for easy language extension.
"""

from __future__ import annotations

import json
import pickle
from enum import Enum
from pathlib import Path
from typing import Any
import datetime

import httpx
from pydantic import BaseModel, Field

from .phrase import MultiWordExpression, PhraseNormalizer


class Language(Enum):
    """Supported languages with ISO codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    # Easily extensible for future languages
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


class LexiconSource(Enum):
    """Available lexicon sources with quality ratings."""

    # English - Primary Dictionaries
    DWYL_ENGLISH_WORDS = "dwyl_english_words"  # 479k words
    ENGLISH_WORDS_HUGE = "english_words_huge"  # 466k+ words
    MOBY_WORDS = "moby_words"  # 354k+ Moby project words
    SCOWL_WORDS = "scowl_words"  # SCOWL word lists
    WORDNET_WORDS = "wordnet_words"  # WordNet lemmas

    # English - Frequency Lists
    GOOGLE_10K_ENGLISH = "google_10k_english"  # 10k most common
    GOOGLE_20K_ENGLISH = "google_20k_english"  # 20k most common
    COCA_FREQUENCY = "coca_frequency"  # Corpus of Contemporary American English
    BNC_FREQUENCY = "bnc_frequency"  # British National Corpus
    SUBTLEX_FREQUENCY = "subtlex_frequency"  # Subtitle-based frequency

    # English - Specialized
    ENGLISH_IDIOMS = "english_idioms"  # 22k+ idioms
    ENGLISH_PHRASES = "english_phrases"  # Common phrases
    ENGLISH_COLLOCATIONS = "english_collocations"  # Word combinations
    ENGLISH_CONTRACTIONS = "english_contractions"  # Contractions list
    ENGLISH_ABBREVIATIONS = "english_abbreviations"  # Abbreviations
    ENGLISH_SLANG = "english_slang"  # Slang dictionary

    # English - Technical/Academic
    ACADEMIC_VOCABULARY = "academic_vocabulary"  # Academic word list
    TECHNICAL_TERMS = "technical_terms"  # Technical vocabulary
    MEDICAL_TERMS = "medical_terms"  # Medical terminology
    LEGAL_TERMS = "legal_terms"  # Legal terminology

    # French - Primary
    FRENCH_LEXIQUE = "french_lexique"  # Lexique.org database
    FRENCH_LEFFF = "french_lefff"  # LEFFF morphological lexicon
    FRENCH_DELA = "french_dela"  # DELA dictionary
    COFINLEY_FRENCH_FREQ = "cofinley_french_freq"  # 5k most common

    # French - Specialized
    FRENCH_IDIOMS = "french_idioms"  # French idioms
    FRENCH_PHRASES = "french_phrases"  # Common French phrases
    FRENCH_VERBS = "french_verbs"  # French verb forms

    # Spanish
    SPANISH_FREQUENCY = "spanish_frequency"  # Spanish frequency list
    SPANISH_WORDS = "spanish_words"  # Spanish dictionary
    SPANISH_IDIOMS = "spanish_idioms"  # Spanish idioms

    # German
    GERMAN_FREQUENCY = "german_frequency"  # German frequency list
    GERMAN_WORDS = "german_words"  # German dictionary
    GERMAN_COMPOUND = "german_compound"  # German compound words

    # Italian
    ITALIAN_FREQUENCY = "italian_frequency"  # Italian frequency list
    ITALIAN_WORDS = "italian_words"  # Italian dictionary

    # Multi-language
    WIKTIONARY_MULTILANG = "wiktionary_multilang"  # Wiktionary dumps
    UNICODE_CLDR = "unicode_cldr"  # Unicode CLDR data
    PHRASE_MACHINE = "phrase_machine"  # Multi-word expressions
    POLYGLOT_IDIOMS = "polyglot_idioms"  # Multilingual idioms


class LexiconData(BaseModel):
    """Container for lexicon data with metadata."""

    words: list[str] = Field(..., description="Single words")
    phrases: list[MultiWordExpression] = Field(
        ..., description="Multi-word expressions"
    )
    metadata: dict[str, Any] = Field(..., description="Source metadata")
    language: Language = Field(..., description="Language of the lexicon")
    source: LexiconSource = Field(..., description="Source of the data")
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

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize the lexicon loader.

        Args:
            cache_dir: Directory for caching lexicon data
        """
        self.cache_dir = cache_dir
        self.lexicon_dir = cache_dir / "lexicons"
        self.index_dir = cache_dir / "index"

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

        # Comprehensive source URLs mapping
        self._source_urls = {
            # English - Primary Dictionaries
            LexiconSource.DWYL_ENGLISH_WORDS: {
                "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
                "format": "text_lines",
            },
            LexiconSource.ENGLISH_WORDS_HUGE: {
                "url": "https://raw.githubusercontent.com/powerlanguage/word-lists/master/english-words-huge.txt",
                "format": "text_lines",
            },
            LexiconSource.MOBY_WORDS: {
                "url": "https://raw.githubusercontent.com/titusowuor30/moby-english-words/master/moby-english-words.txt",
                "format": "text_lines",
            },
            LexiconSource.SCOWL_WORDS: {
                "url": "https://raw.githubusercontent.com/en-wl/wordlist/master/alt12dicts/2of12inf.txt",
                "format": "text_lines",
            },
            # English - Frequency Lists
            LexiconSource.GOOGLE_10K_ENGLISH: {
                "url": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
                "format": "text_lines",
            },
            LexiconSource.GOOGLE_20K_ENGLISH: {
                "url": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/20k.txt",
                "format": "text_lines",
            },
            LexiconSource.COCA_FREQUENCY: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
                "format": "frequency_list",
            },
            LexiconSource.SUBTLEX_FREQUENCY: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/en/en_full.txt",
                "format": "frequency_list",
            },
            # English - Specialized
            LexiconSource.ENGLISH_IDIOMS: {
                "url": "https://raw.githubusercontent.com/english-words/english-idioms/master/idioms.json",
                "format": "json_idioms",
            },
            LexiconSource.ENGLISH_PHRASES: {
                "url": "https://raw.githubusercontent.com/english-words/english-phrases/master/phrases.txt",
                "format": "text_lines",
            },
            LexiconSource.ENGLISH_CONTRACTIONS: {
                "url": "https://raw.githubusercontent.com/kootenpv/contractions/master/contractions/data/contractions_dict.json",
                "format": "json_dict",
            },
            LexiconSource.ENGLISH_SLANG: {
                "url": "https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en",
                "format": "text_lines",
            },
            # French
            LexiconSource.FRENCH_LEXIQUE: {
                "url": "https://raw.githubusercontent.com/hbenbel/French-Dictionary/master/dictionary/francais.txt",
                "format": "text_lines",
            },
            LexiconSource.COFINLEY_FRENCH_FREQ: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/fr/fr_50k.txt",
                "format": "frequency_list",
            },
            LexiconSource.FRENCH_LEXIQUE: {
                "url": "https://raw.githubusercontent.com/chrplr/openlexicon/master/datasets-info/French-Lexique382/README.md",
                "format": "text_lines",
            },
            # Spanish
            LexiconSource.SPANISH_FREQUENCY: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/es/es_50k.txt",
                "format": "frequency_list",
            },
            LexiconSource.SPANISH_WORDS: {
                "url": "https://raw.githubusercontent.com/JorgeDuenasLerin/diccionario-espanol-txt/master/0_palabras_todas.txt",
                "format": "text_lines",
            },
            # German
            LexiconSource.GERMAN_FREQUENCY: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/de/de_50k.txt",
                "format": "frequency_list",
            },
            LexiconSource.GERMAN_WORDS: {
                "url": "https://raw.githubusercontent.com/davidak/wortliste/master/wortliste",
                "format": "text_lines",
            },
            # Italian
            LexiconSource.ITALIAN_FREQUENCY: {
                "url": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/it/it_50k.txt",
                "format": "frequency_list",
            },
            LexiconSource.ITALIAN_WORDS: {
                "url": "https://raw.githubusercontent.com/napolux/paroleitaliane/master/paroleitaliane/280000_parole_italiane.txt",
                "format": "text_lines",
            },
        }

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

        # Try to load from cache first
        if cache_file.exists():
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
                source_words, source_phrases = await self._load_source(source, language)
                words.extend(source_words)
                phrases.extend(source_phrases)
            except Exception as e:
                print(f"Warning: Failed to load {source.value}: {e}")
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
            metadata={"loaded_sources": [s.value for s in sources]},
            language=language,
            source=sources[0] if sources else LexiconSource.DWYL_ENGLISH_WORDS,
            total_entries=len(words) + len(phrases),
        )

    def _get_sources_for_language(self, language: Language) -> list[LexiconSource]:
        """Get appropriate sources for a language."""
        if language == Language.ENGLISH:
            return [
                # Primary dictionaries
                LexiconSource.DWYL_ENGLISH_WORDS,
                LexiconSource.ENGLISH_WORDS_HUGE,
                LexiconSource.MOBY_WORDS,
                # Frequency lists
                LexiconSource.GOOGLE_10K_ENGLISH,
                LexiconSource.GOOGLE_20K_ENGLISH,
                LexiconSource.COCA_FREQUENCY,
                # Specialized
                LexiconSource.ENGLISH_IDIOMS,
                LexiconSource.ENGLISH_PHRASES,
                LexiconSource.ENGLISH_CONTRACTIONS,
            ]
        elif language == Language.FRENCH:
            return [
                LexiconSource.FRENCH_LEXIQUE,
                LexiconSource.COFINLEY_FRENCH_FREQ,
                LexiconSource.FRENCH_LEFFF,
            ]
        elif language == Language.SPANISH:
            return [
                LexiconSource.SPANISH_FREQUENCY,
                LexiconSource.SPANISH_WORDS,
            ]
        elif language == Language.GERMAN:
            return [
                LexiconSource.GERMAN_FREQUENCY,
                LexiconSource.GERMAN_WORDS,
            ]
        elif language == Language.ITALIAN:
            return [
                LexiconSource.ITALIAN_FREQUENCY,
                LexiconSource.ITALIAN_WORDS,
            ]
        else:
            # Default fallback (empty for unsupported languages)
            return []

    def get_lexicon_ext(self, source: LexiconSource) -> str:
        """Get the file extension for a lexicon source."""
        if source in self._source_urls:
            format_type = self._source_urls[source]["format"]
            return ".json" if format_type.startswith("json") else ".txt"

        return ".txt"

    async def _load_source(
        self, source: LexiconSource, language: Language
    ) -> tuple[list[str], list[MultiWordExpression]]:
        """Load data from a specific source."""
        if source not in self._source_urls:
            return [], []

        source_config = self._source_urls[source]
        url = source_config["url"]
        format_type = source_config["format"]

        # Download data
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        response = await self._http_client.get(url)
        response.raise_for_status()

        ext = self.get_lexicon_ext(source)

        # Save to cache
        cache_filepath = self.lexicon_dir / f"{source.value}"
        cache_filepath = cache_filepath.with_suffix(ext)

        with cache_filepath.open("w", encoding="utf-8") as f:
            f.write(response.text)

        # Parse based on format
        if format_type == "text_lines":
            return self._parse_text_lines(response.text, language)
        elif format_type == "json_idioms":
            return self._parse_json_idioms(response.text, language)
        elif format_type == "frequency_list":
            return self._parse_frequency_list(response.text, language)
        elif format_type == "json_dict":
            return self._parse_json_dict(response.text, language)
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

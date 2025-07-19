"""Wiktionary connector using MediaWiki API with comprehensive wikitext parsing."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any

import wikitextparser as wtp

from ..caching import get_cached_http_client
from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
)
from ..utils.logging import get_logger
from ..utils.state_tracker import ProviderMetrics, StateTracker
from .base import DictionaryConnector

logger = get_logger(__name__)


@dataclass
class WiktionaryExtractedData:
    """Container for all extracted Wiktionary data."""

    definitions: list[Definition]
    etymology: str | None = None
    pronunciation: Pronunciation | None = None
    alternative_forms: list[str] | None = None
    related_terms: list[str] | None = None


class WikitextCleaner:
    """Unified wikitext cleaning using wikitextparser."""

    @staticmethod
    def clean_text(text: str, preserve_structure: bool = False) -> str:
        """Clean wikitext using wikitextparser and targeted regex."""
        if not text:
            return ""

        try:
            # Parse with wikitextparser for proper handling
            parsed = wtp.parse(text)

            # Remove templates but preserve their content where appropriate
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                # Preserve content from certain templates
                if template_name in ['term', 'mention', 'lang']:
                    # Keep the main content, remove the template wrapper
                    if template.arguments:
                        # Usually the last argument is the display text
                        content = str(template.arguments[-1].value).strip()
                        template.string = content
                else:
                    # Remove template entirely
                    template.string = ""

            # Convert wikilinks to plain text
            for wikilink in parsed.wikilinks:
                # Use display text if available, otherwise use target
                display_text = wikilink.text or wikilink.target
                wikilink.string = display_text or ""

            # Get the cleaned text
            cleaned = str(parsed)

        except Exception:
            # Fallback to regex cleaning if wtp fails
            cleaned = text

        # Final cleanup with regex
        cleaned = re.sub(r'<[^>]+>', '', cleaned)  # Remove HTML tags
        cleaned = re.sub(r'\{\{[^}]*\}\}', '', cleaned)  # Remove remaining templates
        cleaned = re.sub(
            r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', cleaned
        )  # Clean links
        cleaned = re.sub(
            r'<ref[^>]*>.*?</ref>', '', cleaned, flags=re.DOTALL
        )  # Remove refs

        if not preserve_structure:
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
            cleaned = re.sub(r'^[^\w]*', '', cleaned)  # Remove leading punctuation

        return cleaned.strip()


class WiktionaryConnector(DictionaryConnector):
    """Enhanced Wiktionary connector with comprehensive wikitext parsing."""

    # Word type mappings
    POS_MAPPINGS = {
        "noun": "noun",
        "verb": "verb",
        "adjective": "adjective",
        "adverb": "adverb",
        "pronoun": "pronoun",
        "preposition": "preposition",
        "conjunction": "conjunction",
        "interjection": "interjection",
        "determiner": "adjective",  # Map to adjective
        "article": "adjective",  # Map to adjective
    }

    def __init__(self, rate_limit: float = 8.0, force_refresh: bool = False) -> None:
        """Initialize enhanced Wiktionary connector."""
        super().__init__(rate_limit=rate_limit / 3600.0)
        self.base_url = "https://en.wiktionary.org/w/api.php"
        self.http_client = get_cached_http_client(
            force_refresh=force_refresh,
            default_ttl_hours=24.0,
        )
        self.cleaner = WikitextCleaner()

    @property
    def provider_name(self) -> str:
        return "wiktionary"

    async def fetch_definition(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
        progress_callback: Any | None = None,
    ) -> ProviderData | None:
        """Fetch comprehensive definition data from Wiktionary."""
        await self._enforce_rate_limit()

        # Initialize timing and metrics
        start_time = time.time()
        metrics = ProviderMetrics(
            provider_name=self.provider_name,
            response_time_ms=0,
            response_size_bytes=0,
        )

        try:
            # Report start
            if state_tracker:
                await self._report_progress(
                    'start',
                    0,
                    {'provider': self.provider_name, 'word': word},
                    state_tracker,
                )

            params = {
                "action": "query",
                "prop": "revisions",
                "titles": word,
                "rvslots": "*",
                "rvprop": "content",
                "formatversion": "2",
                "format": "json",
            }

            # Progress callback for HTTP request
            http_progress_data = {}

            def http_progress_callback(stage: str, metadata: dict[str, Any]) -> None:
                http_progress_data.update(metadata)
                if stage == 'connecting' and state_tracker:
                    # Schedule async progress report
                    asyncio.create_task(self._report_progress(
                        'connecting',
                        25,
                        {'provider': self.provider_name, **metadata},
                        state_tracker,
                    ))
                elif stage == 'downloaded':
                    metrics.connection_time_ms = metadata.get('connection_time_ms', 0)
                    metrics.download_time_ms = metadata.get('download_time_ms', 0)
                    metrics.response_size_bytes = metadata.get('response_size_bytes', 0)
                    if state_tracker:
                        # Schedule async progress report
                        asyncio.create_task(self._report_progress(
                            'downloading',
                            50,
                            {'provider': self.provider_name, **metadata},
                            state_tracker,
                        ))

            response = await self.http_client.get(
                self.base_url,
                params=params,
                ttl_hours=24.0,
                headers={
                    "User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"
                },
                timeout=30.0,
                progress_callback=http_progress_callback if state_tracker else None,
            )

            if response.status_code == 429:
                logger.warning("Rate limited by Wiktionary, waiting 60s...")
                if state_tracker:
                    await self._report_progress(
                        'downloading',
                        50,
                        {
                            'provider': self.provider_name,
                            'status': 'rate_limited',
                            'wait_time': 60,
                        },
                        state_tracker,
                    )
                await asyncio.sleep(60)
                response = await self.http_client.get(
                    self.base_url,
                    params=params,
                    force_refresh=True,
                    headers={
                        "User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"
                    },
                    timeout=30.0,
                    progress_callback=http_progress_callback if state_tracker else None,
                )

            response.raise_for_status()
            data = response.json()

            # Report parsing start
            if state_tracker:
                await self._report_progress(
                    'parsing',
                    75,
                    {
                        'provider': self.provider_name,
                        'word': word,
                        'response_size': len(str(data)),
                    },
                    state_tracker,
                )

            parse_start = time.time()
            result = self._parse_wiktionary_response(word, data)
            metrics.parse_time_ms = (time.time() - parse_start) * 1000

            # Calculate quality metrics if we have a result
            if result:
                metrics.success = True
                metrics.definitions_count = (
                    len(result.definitions) if result.definitions else 0
                )
                metrics.has_pronunciation = bool(
                    result.raw_metadata.get('pronunciation')
                )
                metrics.has_etymology = bool(result.raw_metadata.get('etymology'))
                metrics.has_examples = any(
                    d.examples and (d.examples.generated or d.examples.literature)
                    for d in (result.definitions or [])
                )
                metrics.calculate_completeness_score()
            else:
                metrics.success = False

            metrics.response_time_ms = (time.time() - start_time) * 1000

            # Report completion
            if state_tracker:
                await self._report_progress(
                    'complete',
                    100,
                    {
                        'provider': self.provider_name,
                        'word': word,
                        'success': metrics.success,
                        'metrics': metrics.__dict__,
                    },
                    state_tracker,
                )

            return result

        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            metrics.response_time_ms = (time.time() - start_time) * 1000

            if state_tracker:
                await self._report_progress(
                    'complete',
                    100,
                    {
                        'provider': self.provider_name,
                        'word': word,
                        'success': False,
                        'error': str(e),
                        'metrics': metrics.__dict__,
                    },
                    state_tracker,
                )

            logger.error(f"Error fetching {word} from Wiktionary: {e}")
            return None

    def _parse_wiktionary_response(
        self, word: str, data: dict[str, Any]
    ) -> ProviderData | None:
        """Parse Wiktionary response comprehensively."""
        try:
            pages = data.get("query", {}).get("pages", [])
            if not pages or "revisions" not in pages[0]:
                return None

            content = pages[0]["revisions"][0]["slots"]["main"]["content"]

            # Extract all components comprehensively
            extracted_data = self._extract_comprehensive_data(content)

            return ProviderData(
                provider_name=self.provider_name,
                definitions=extracted_data.definitions,
                raw_metadata={
                    "wikitext_sample": content[:1000],
                    "etymology": extracted_data.etymology,
                    "pronunciation": (
                        extracted_data.pronunciation.model_dump()
                        if extracted_data.pronunciation
                        else None
                    ),
                    "alternative_forms": extracted_data.alternative_forms,
                    "related_terms": extracted_data.related_terms,
                },
            )

        except Exception as e:
            logger.error(f"Error parsing Wiktionary response for {word}: {e}")
            return None

    def _extract_comprehensive_data(self, wikitext: str) -> WiktionaryExtractedData:
        """Extract all available data from wikitext using systematic parsing."""
        try:
            parsed = wtp.parse(wikitext)

            # Find English section
            english_section = self._find_language_section(parsed, "English")
            if not english_section:
                english_section = parsed

            # Extract all components
            definitions = self._extract_definitions(english_section)
            etymology = self._extract_etymology(english_section)
            pronunciation = self._extract_pronunciation(english_section)
            alternative_forms = self._extract_alternative_forms(english_section)
            related_terms = self._extract_related_terms(english_section)

            return WiktionaryExtractedData(
                definitions=definitions,
                etymology=etymology,
                pronunciation=pronunciation,
                alternative_forms=alternative_forms,
                related_terms=related_terms,
            )

        except Exception as e:
            logger.error(f"Error in comprehensive extraction: {e}")
            return WiktionaryExtractedData(definitions=[])

    def _find_language_section(
        self, parsed: wtp.WikiList, language: str
    ) -> wtp.Section | None:
        """Find the specific language section using wtp.Section hierarchy."""
        for section in parsed.sections:
            if (
                section.title
                and section.title.strip().lower() == language.lower()
                and section.level == 2
            ):  # Language sections are level 2 (==)
                return section
        return None

    def _extract_definitions(self, section: wtp.Section) -> list[Definition]:
        """Extract definitions systematically using wtp structure."""
        definitions = []

        for subsection in section.sections:
            if not subsection.title:
                continue

            section_title = subsection.title.strip().lower()

            # Find matching word type
            word_type = None
            for pos_name, pos_enum in self.POS_MAPPINGS.items():
                if pos_name in section_title:
                    word_type = pos_enum
                    break

            if not word_type:
                continue

            # Use wtp.WikiList to extract numbered definitions
            definition_texts = self._extract_wikilist_items(str(subsection))

            for def_text in definition_texts:
                if not def_text or len(def_text.strip()) < 5:
                    continue

                # Extract components from definition
                examples = self._extract_examples(def_text)
                synonyms = self._extract_synonyms(def_text)
                clean_def = self.cleaner.clean_text(def_text)

                if clean_def:
                    definitions.append(
                        Definition(
                            word_type=word_type,
                            definition=clean_def,
                            examples=examples,
                            synonyms=synonyms,
                        )
                    )

        return definitions

    def _extract_wikilist_items(self, section_text: str) -> list[str]:
        """Extract numbered definition items from section text."""
        items = []

        # Use regex to find numbered definitions (more reliable than wtp for this)
        pattern = r"^#\s*([^#\n]+)"
        matches = re.findall(pattern, section_text, re.MULTILINE)

        for match in matches:
            # Clean up the definition text
            content = match.strip()
            if content and len(content) > 5:  # Basic quality filter
                items.append(content)

        return items

    def _extract_examples(self, definition_text: str) -> Examples:
        """Extract examples systematically from templates and patterns."""
        examples = Examples()

        try:
            parsed = wtp.parse(definition_text)

            # Extract from templates
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ['ux', 'uxi', 'usex']:
                    # Usage example templates
                    if len(template.arguments) >= 2:
                        example_text = str(template.arguments[1].value).strip()
                        clean_example = self.cleaner.clean_text(
                            example_text, preserve_structure=True
                        )
                        if clean_example and len(clean_example) > 10:
                            examples.generated.append(
                                GeneratedExample(
                                    sentence=clean_example, regenerable=False
                                )
                            )

                elif template_name.startswith('quote'):
                    # Quote templates
                    for arg in template.arguments:
                        if 'text' in str(arg.name).lower() or not arg.name:
                            quote_text = str(arg.value).strip()
                            clean_quote = self.cleaner.clean_text(
                                quote_text, preserve_structure=True
                            )
                            if clean_quote and len(clean_quote) > 15:
                                examples.generated.append(
                                    GeneratedExample(
                                        sentence=clean_quote, regenerable=False
                                    )
                                )
                                break

        except Exception as e:
            logger.debug(f"Error extracting examples: {e}")

        # Fallback regex patterns for quotes
        quote_patterns = [r'"([^"]{15,})"', r"'([^']{15,})'", r"''([^']{15,})''"]

        for pattern in quote_patterns:
            matches = re.findall(pattern, definition_text)
            for match in matches:
                clean_example = self.cleaner.clean_text(match, preserve_structure=True)
                if clean_example and len(clean_example) > 10:
                    examples.generated.append(
                        GeneratedExample(sentence=clean_example, regenerable=False)
                    )

        return examples

    def _extract_synonyms(self, definition_text: str) -> list[str]:
        """Extract synonyms systematically from templates."""
        synonyms = []

        try:
            parsed = wtp.parse(definition_text)

            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ['syn', 'synonym', 'synonyms']:
                    for arg in template.arguments:
                        if not arg.name:  # Positional arguments
                            arg_value = str(arg.value).strip()
                            if (
                                arg_value
                                and len(arg_value) > 1
                                and arg_value not in ['en', 'lang']
                            ):
                                clean_syn = self._clean_synonym(arg_value)
                                if clean_syn:
                                    synonyms.append(clean_syn)

        except Exception as e:
            logger.debug(f"Error extracting synonyms: {e}")

        return synonyms[:10]  # Limit to 10 synonyms

    def _extract_etymology(self, section: wtp.Section) -> str | None:
        """Extract etymology from dedicated section."""
        for subsection in section.sections:
            if subsection.title and 'etymology' in subsection.title.lower():
                etymology_text = str(subsection.contents)
                return self.cleaner.clean_text(etymology_text, preserve_structure=True)
        return None

    def _extract_pronunciation(self, section: wtp.Section) -> Pronunciation | None:
        """Extract pronunciation comprehensively."""
        ipa = None
        phonetic = None

        try:
            # Look for pronunciation section
            for subsection in section.sections:
                if subsection.title and 'pronunciation' in subsection.title.lower():
                    section_text = str(subsection)
                    break
            else:
                section_text = str(section)

            parsed = wtp.parse(section_text)

            # Extract from IPA templates
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if 'ipa' in template_name:
                    for arg in template.arguments:
                        if not arg.name:  # Positional argument
                            arg_value = str(arg.value).strip()
                            if '/' in arg_value or '[' in arg_value:
                                ipa = arg_value
                                phonetic = self._ipa_to_phonetic(ipa)
                                break

                elif template_name in ['pron', 'pronunciation', 'audio']:
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()
                        if arg_value and len(arg_value) > 2:
                            if not phonetic:  # Don't override IPA-derived phonetic
                                phonetic = arg_value
                            break

            if ipa or phonetic:
                return Pronunciation(phonetic=phonetic or "unknown", ipa=ipa)

        except Exception as e:
            logger.debug(f"Error extracting pronunciation: {e}")

        return None

    def _extract_alternative_forms(self, section: wtp.Section) -> list[str] | None:
        """Extract alternative forms/spellings."""
        alternatives = []

        for subsection in section.sections:
            title = subsection.title
            if title and any(
                term in title.lower() for term in ['alternative', 'variant', 'spelling']
            ):
                items = self._extract_wikilist_items(str(subsection))
                for item in items:
                    clean_alt = self.cleaner.clean_text(item)
                    if clean_alt and len(clean_alt) > 1:
                        alternatives.append(clean_alt)

        return alternatives if alternatives else None

    def _extract_related_terms(self, section: wtp.Section) -> list[str] | None:
        """Extract related terms, derived terms, etc."""
        related = []

        for subsection in section.sections:
            title = subsection.title
            if title and any(
                term in title.lower() for term in ['related', 'derived', 'see also']
            ):
                items = self._extract_wikilist_items(str(subsection))
                for item in items:
                    clean_term = self.cleaner.clean_text(item)
                    if clean_term and len(clean_term) > 1:
                        related.append(clean_term)

        return related[:20] if related else None  # Limit to 20 terms

    def _ipa_to_phonetic(self, ipa: str) -> str:
        """Convert IPA to simplified phonetic representation."""
        if not ipa:
            return "unknown"

        phonetic = ipa.replace('/', '').replace('[', '').replace(']', '')
        phonetic = phonetic.replace('ˈ', '').replace('ˌ', '')  # Remove stress

        # Enhanced IPA to phonetic mapping
        substitutions = {
            'ɪ': 'i',
            'ɛ': 'e',
            'æ': 'a',
            'ɑ': 'ah',
            'ɔ': 'aw',
            'ʊ': 'u',
            'ə': 'uh',
            'θ': 'th',
            'ð': 'th',
            'ʃ': 'sh',
            'ʒ': 'zh',
            'ŋ': 'ng',
            'ʧ': 'ch',
            'ʤ': 'j',
            'ɹ': 'r',
            'ɾ': 't',
            'ʔ': '',
            'ː': '',
            'ˑ': '',
            'eɪ': 'ay',
            'aɪ': 'eye',
            'ɔɪ': 'oy',
            'aʊ': 'ow',
            'oʊ': 'oh',
        }

        for ipa_char, simple_char in substitutions.items():
            phonetic = phonetic.replace(ipa_char, simple_char)

        return phonetic.strip() or "unknown"

    def _clean_synonym(self, synonym_text: str) -> str | None:
        """Clean and validate synonym text."""
        if not synonym_text:
            return None

        cleaned = self.cleaner.clean_text(synonym_text)

        # Validation
        if (
            len(cleaned) < 2
            or len(cleaned) > 50
            or cleaned.lower()
            in {'thesaurus', 'see', 'also', 'compare', 'etc', 'and', 'or'}
        ):
            return None

        return cleaned

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.close()

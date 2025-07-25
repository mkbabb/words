"""Wiktionary connector using MediaWiki API with comprehensive wikitext parsing."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

import wikitextparser as wtp  # type: ignore[import-untyped]

from ..caching import get_cached_http_client
from ..constants import Language
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Definition,
    Etymology,
    Example,
    Pronunciation,
    ProviderData,
    Word,
)
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
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
                if template_name in ["term", "mention", "lang"]:
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
        cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Remove HTML tags
        cleaned = re.sub(r"\{\{[^}]*\}\}", "", cleaned)  # Remove remaining templates
        cleaned = re.sub(
            r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cleaned
        )  # Clean links
        cleaned = re.sub(
            r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.DOTALL
        )  # Remove refs

        if not preserve_structure:
            cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
            cleaned = re.sub(r"^[^\w]*", "", cleaned)  # Remove leading punctuation

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
    ) -> ProviderData | None:
        """Fetch comprehensive definition data from Wiktionary."""
        await self._enforce_rate_limit()

        try:
            # Report start
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

            # First, get or create the Word document
            storage = await get_storage()
            word_obj = await storage.get_word(word)
            if not word_obj:
                # Create new Word if doesn't exist
                word_obj = Word(
                    text=word,
                    normalized=word.lower(),
                    language=Language.ENGLISH,
                )
                await word_obj.save()

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
                if stage == "connecting" and state_tracker:
                    # Schedule async progress report
                    asyncio.create_task(
                        state_tracker.update(
                            stage="PROVIDER_FETCH_HTTP_CONNECTING",
                            message=f"Connecting to {self.provider_name}",
                            details={"word": word, **metadata},
                        )
                    )
                elif stage == "downloaded":

                    if state_tracker:
                        # Schedule async progress report
                        asyncio.create_task(
                            state_tracker.update(
                                stage="PROVIDER_FETCH_HTTP_DOWNLOADING",
                                message=f"Downloading from {self.provider_name}",
                                details={"word": word, **metadata},
                            )
                        )

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
                    await state_tracker.update(
                        stage=Stages.PROVIDER_FETCH_HTTP_RATE_LIMITED,
                        message="Rate limited - waiting 60s"
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
                await state_tracker.update(
                    stage=Stages.PROVIDER_FETCH_HTTP_PARSING,
                    progress=55
                )

            result = await self._parse_wiktionary_response(word, data, word_obj)

            # Report completion
            if state_tracker:
                await state_tracker.update(
                    stage=Stages.PROVIDER_FETCH_HTTP_COMPLETE,
                    progress=58
                )

            return result

        except Exception as e:

            if state_tracker:
                await state_tracker.update_error(f"Provider error: {str(e)}")

            logger.error(f"Error fetching {word} from Wiktionary: {e}")
            return None

    async def _parse_wiktionary_response(
        self, word: str, data: dict[str, Any], word_obj: Word
    ) -> ProviderData | None:
        """Parse Wiktionary response comprehensively."""
        try:
            pages = data.get("query", {}).get("pages", [])
            if not pages or "revisions" not in pages[0]:
                return None

            content = pages[0]["revisions"][0]["slots"]["main"]["content"]

            # Extract all components comprehensively
            extracted_data = await self._extract_comprehensive_data(content, word_obj)

            # Create raw metadata for base class to use
            raw_metadata = {
                "wikitext_sample": content[:1000],
                "definitions": extracted_data.definitions,
                "etymology": extracted_data.etymology,
                "pronunciation": (
                    extracted_data.pronunciation.model_dump()
                    if extracted_data.pronunciation
                    else None
                ),
                "alternative_forms": extracted_data.alternative_forms,
                "related_terms": extracted_data.related_terms,
                # Store definition count for debugging, not the actual objects
                "definition_count": len(extracted_data.definitions),
            }

            # Use base class method to normalize and save
            return await self._normalize_response(raw_metadata, word_obj)

        except Exception as e:
            logger.error(f"Error parsing Wiktionary response for {word}: {e}")
            return None

    async def _extract_comprehensive_data(self, wikitext: str, word_obj: Word) -> WiktionaryExtractedData:
        """Extract all available data from wikitext using systematic parsing."""
        try:
            parsed = wtp.parse(wikitext)

            # Find English section
            english_section = self._find_language_section(parsed, "English")
            if not english_section:
                english_section = parsed

            # Extract all components
            definitions = await self._extract_definitions(english_section, str(word_obj.id))
            etymology = self._extract_etymology(english_section)
            pronunciation = self._extract_pronunciation(english_section, str(word_obj.id))
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

    async def _extract_definitions(self, section: wtp.Section, word_id: str) -> list[Definition]:
        """Extract definitions using new model structure."""
        definitions = []

        for subsection in section.sections:
            if not subsection.title:
                continue

            section_title = subsection.title.strip().lower()

            # Find matching part of speech
            part_of_speech = None
            for pos_name, pos_enum in self.POS_MAPPINGS.items():
                if pos_name in section_title:
                    part_of_speech = pos_enum
                    break

            if not part_of_speech:
                continue

            # Use wtp.WikiList to extract numbered definitions
            definition_texts = self._extract_wikilist_items(str(subsection))

            for idx, def_text in enumerate(definition_texts):
                if not def_text or len(def_text.strip()) < 5:
                    continue

                # Extract components from definition
                clean_def = self.cleaner.clean_text(def_text)
                if not clean_def:
                    continue

                # Extract synonyms and antonyms
                synonyms = self._extract_synonyms(def_text)
                
                # Create definition (meaning_cluster will be added by AI synthesis)
                definition = Definition(
                    word_id=word_id,
                    part_of_speech=part_of_speech,
                    text=clean_def,
                    sense_number=f"{idx + 1}",
                    synonyms=synonyms,
                    antonyms=[],
                    example_ids=[],
                    frequency_band=None,
                )
                
                # Save definition to get ID
                await definition.save()
                
                # Extract and save examples
                example_objs = await self._extract_examples(def_text, str(definition.id))
                definition.example_ids = [str(ex.id) for ex in example_objs]
                await definition.save()  # Update with example IDs
                
                definitions.append(definition)

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

    async def _extract_examples(self, definition_text: str, definition_id: str) -> list[Example]:
        """Extract and save examples using new model structure."""
        examples = []

        try:
            parsed = wtp.parse(definition_text)

            # Extract from templates
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ["ux", "uxi", "usex"]:
                    # Usage example templates
                    if len(template.arguments) >= 2:
                        example_text = str(template.arguments[1].value).strip()
                        clean_example = self.cleaner.clean_text(
                            example_text, preserve_structure=True
                        )
                        if clean_example and len(clean_example) > 10:
                            example = Example(
                                definition_id=definition_id,
                                text=clean_example,
                                type="literature",  # Wiktionary examples are from real usage
                            )
                            await example.save()
                            examples.append(example)
        except Exception as e:
            logger.error(f"Error extracting examples: {e}")

        return examples


    def _extract_synonyms(self, definition_text: str) -> list[str]:
        """Extract synonyms systematically from templates."""
        synonyms = []

        try:
            parsed = wtp.parse(definition_text)

            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ["syn", "synonym", "synonyms"]:
                    for arg in template.arguments:
                        if not arg.name:  # Positional arguments
                            arg_value = str(arg.value).strip()
                            if (
                                arg_value
                                and len(arg_value) > 1
                                and arg_value not in ["en", "lang"]
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
            if subsection.title and "etymology" in subsection.title.lower():
                etymology_text = str(subsection.contents)
                return self.cleaner.clean_text(etymology_text, preserve_structure=True)
        return None

    def _extract_pronunciation(self, section: wtp.Section, word_id: str) -> Pronunciation | None:
        """Extract pronunciation comprehensively."""
        ipa = None
        phonetic = None

        try:
            # Look for pronunciation section
            for subsection in section.sections:
                if subsection.title and "pronunciation" in subsection.title.lower():
                    section_text = str(subsection)
                    break
            else:
                section_text = str(section)

            parsed = wtp.parse(section_text)

            # Extract from IPA templates
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if "ipa" in template_name:
                    for arg in template.arguments:
                        if not arg.name:  # Positional argument
                            arg_value = str(arg.value).strip()
                            if "/" in arg_value or "[" in arg_value:
                                ipa = arg_value
                                phonetic = self._ipa_to_phonetic(ipa)
                                break

                elif template_name in ["pron", "pronunciation", "audio"]:
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()
                        if arg_value and len(arg_value) > 2:
                            if not phonetic:  # Don't override IPA-derived phonetic
                                phonetic = arg_value
                            break

            if ipa or phonetic:
                return Pronunciation(
                    word_id=word_id,
                    phonetic=phonetic or "unknown",
                    ipa_american=ipa
                )

        except Exception as e:
            logger.debug(f"Error extracting pronunciation: {e}")

        return None

    def _extract_alternative_forms(self, section: wtp.Section) -> list[str] | None:
        """Extract alternative forms/spellings."""
        alternatives = []

        for subsection in section.sections:
            title = subsection.title
            if title and any(
                term in title.lower() for term in ["alternative", "variant", "spelling"]
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
                term in title.lower() for term in ["related", "derived", "see also"]
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

        phonetic = ipa.replace("/", "").replace("[", "").replace("]", "")
        phonetic = phonetic.replace("ˈ", "").replace("ˌ", "")  # Remove stress

        # Enhanced IPA to phonetic mapping
        substitutions = {
            "ɪ": "i",
            "ɛ": "e",
            "æ": "a",
            "ɑ": "ah",
            "ɔ": "aw",
            "ʊ": "u",
            "ə": "uh",
            "θ": "th",
            "ð": "th",
            "ʃ": "sh",
            "ʒ": "zh",
            "ŋ": "ng",
            "ʧ": "ch",
            "ʤ": "j",
            "ɹ": "r",
            "ɾ": "t",
            "ʔ": "",
            "ː": "",
            "ˑ": "",
            "eɪ": "ay",
            "aɪ": "eye",
            "ɔɪ": "oy",
            "aʊ": "ow",
            "oʊ": "oh",
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
            in {"thesaurus", "see", "also", "compare", "etc", "and", "or"}
        ):
            return None

        return cleaned

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.close()

    async def extract_pronunciation(self, raw_data: dict[str, Any]) -> Pronunciation | None:
        """Extract pronunciation from Wiktionary data.

        Args:
            raw_data: Raw response metadata containing pronunciation info

        Returns:
            Pronunciation if found, None otherwise
        """
        if not raw_data or "pronunciation" not in raw_data:
            return None
        
        pron_data = raw_data["pronunciation"]
        if not pron_data:
            return None
        
        # Create Pronunciation without word_id (will be set by base connector)
        return Pronunciation(
            word_id="",  # Will be set by base connector
            phonetic=pron_data.get("phonetic", ""),
            ipa_american=pron_data.get("ipa"),
            syllables=[],
            stress_pattern=None,
        )

    async def extract_definitions(self, raw_data: dict[str, Any], word_id: str) -> list[Definition]:
        """Extract definitions from Wiktionary data.

        Args:
            raw_data: Raw response from Wiktionary containing extracted definitions
            word_id: ID of the word these definitions belong to

        Returns:
            List of Definition objects
        """
        # Return the definitions that were already extracted and passed in raw_data
        return raw_data.get("definitions", [])

    async def extract_etymology(self, raw_data: dict[str, Any]) -> Etymology | None:
        """Extract etymology from Wiktionary data.

        Args:
            raw_data: Raw response metadata containing etymology

        Returns:
            Etymology if found, None otherwise
        """
        if not raw_data or "etymology" not in raw_data:
            return None
        
        etym_text = raw_data["etymology"]
        if not etym_text:
            return None
        
        # Clean and structure etymology text
        cleaned_text = self.cleaner.clean_text(etym_text)
        
        # Try to extract language of origin
        origin_language = None
        if "from" in cleaned_text.lower():
            # Simple pattern matching for common cases
            patterns = [
                r"from (\w+) (?:language|word)",
                r"borrowed from (\w+)",
                r"derived from (\w+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE)
                if match:
                    origin_language = match.group(1)
                    break
        
        return Etymology(
            text=cleaned_text,
            origin_language=origin_language,
            root_words=[],  # Could extract these with more sophisticated parsing
        )

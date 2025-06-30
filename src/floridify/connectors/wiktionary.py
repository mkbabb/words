"""Wiktionary connector using MediaWiki API with improved parsing."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx
import wikitextparser as wtp  # type: ignore[import-untyped]

from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
    SynonymReference,
    Word,
    WordType,
)
from .base import DictionaryConnector


class WiktionaryConnector(DictionaryConnector):
    """Connector for Wiktionary using MediaWiki API with proper wikitext parsing."""

    def __init__(self, rate_limit: float = 8.0) -> None:
        """Initialize Wiktionary connector.

        Args:
            rate_limit: Requests per hour (max 500 for anonymous)
        """
        # Convert hourly to per-second rate limit
        super().__init__(rate_limit=rate_limit / 3600.0)
        self.base_url = "https://en.wiktionary.org/w/api.php"
        self.session = httpx.AsyncClient(
            headers={"User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"},
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        return "wiktionary"

    async def fetch_definition(self, word: str) -> ProviderData | None:
        """Fetch definition data for a word from Wiktionary.

        Args:
            word: The word to look up

        Returns:
            ProviderData if successful, None if not found or error
        """
        await self._enforce_rate_limit()

        try:
            params = {
                "action": "query",
                "prop": "revisions",
                "titles": word,
                "rvslots": "*",
                "rvprop": "content",
                "formatversion": "2",
                "format": "json",
            }

            response = await self.session.get(self.base_url, params=params)

            if response.status_code == 429:
                # Rate limited - wait and retry once
                await asyncio.sleep(60)
                response = await self.session.get(self.base_url, params=params)

            response.raise_for_status()
            data = response.json()

            return self._parse_wiktionary_response(word, data)

        except Exception as e:
            print(f"Error fetching {word} from Wiktionary: {e}")
            return None

    def _parse_wiktionary_response(self, word: str, data: dict[str, Any]) -> ProviderData | None:
        """Parse Wiktionary API response using wikitextparser.

        Args:
            word: The word being looked up
            data: Raw API response

        Returns:
            Parsed ProviderData or None if no content
        """
        try:
            pages = data.get("query", {}).get("pages", [])
            if not pages or "revisions" not in pages[0]:
                return None

            content = pages[0]["revisions"][0]["slots"]["main"]["content"]

            # Parse the wikitext content
            definitions = self._extract_definitions_from_wikitext(content)

            return ProviderData(
                provider_name=self.provider_name,
                definitions=definitions,
                raw_metadata={"wikitext": content[:1000]},  # Store sample for debugging
            )

        except Exception as e:
            print(f"Error parsing Wiktionary response for {word}: {e}")
            return None

    def _extract_definitions_from_wikitext(self, wikitext: str) -> list[Definition]:
        """Extract definitions from Wiktionary wikitext using proper parsing.

        Args:
            wikitext: Raw wikitext content

        Returns:
            List of parsed definitions
        """
        definitions: list[Definition] = []

        try:
            parsed = wtp.parse(wikitext)

            # Find the English language section
            english_section = None
            for section in parsed.sections:
                if section.title and "english" in section.title.lower().strip():
                    english_section = section
                    break

            if not english_section:
                # Fallback: try to find any section with definitions
                english_section = parsed

            # Extract definitions from different parts of speech
            pos_mappings = {
                "noun": WordType.NOUN,
                "verb": WordType.VERB,
                "adjective": WordType.ADJECTIVE,
                "adverb": WordType.ADVERB,
                "pronoun": WordType.PRONOUN,
                "preposition": WordType.PREPOSITION,
                "conjunction": WordType.CONJUNCTION,
                "interjection": WordType.INTERJECTION,
            }

            for subsection in english_section.sections:
                if not subsection.title:
                    continue

                section_title = subsection.title.strip().lower()

                # Check if this is a part of speech section
                word_type = None
                for pos_name, pos_enum in pos_mappings.items():
                    if pos_name in section_title:
                        word_type = pos_enum
                        break

                if not word_type:
                    continue

                # Extract numbered definitions
                section_defs = self._extract_numbered_definitions(str(subsection))

                for def_text in section_defs:
                    if def_text and len(def_text.strip()) > 5:  # Basic quality filter
                        # Extract examples if present
                        examples = self._extract_examples_from_definition(def_text)

                        # Extract synonyms if present
                        synonyms = self._extract_synonyms_from_definition(def_text, word_type)

                        # Clean the definition text
                        clean_def = self._clean_definition_text(def_text)

                        if clean_def:
                            definitions.append(
                                Definition(
                                    word_type=word_type,
                                    definition=clean_def,
                                    examples=examples,
                                    synonyms=synonyms,
                                )
                            )

        except Exception as e:
            print(f"Error extracting definitions: {e}")

        return definitions

    def _extract_numbered_definitions(self, section_text: str) -> list[str]:
        """Extract numbered definitions from a section.

        Args:
            section_text: Text of the section

        Returns:
            List of definition texts
        """
        definitions = []

        # Pattern for numbered definitions (# at start of line)
        pattern = r"^#\s*([^#\n]+)"
        matches = re.findall(pattern, section_text, re.MULTILINE)

        for match in matches:
            # Skip if it's a sub-definition (contains colons or other formatting)
            if not re.match(r"^[\s*:]+", match):
                definitions.append(match.strip())

        return definitions

    def _extract_examples_from_definition(self, definition_text: str) -> Examples:
        """Extract usage examples from definition text.

        Args:
            definition_text: The definition text

        Returns:
            Examples object with extracted examples
        """
        examples = Examples()

        # Look for quoted examples or examples in parentheses
        quote_patterns = [
            r'"([^"]+)"',  # Double quotes
            r"'([^']+)'",  # Single quotes
            r"\{\{ux\|[^|]*\|([^}]+)\}\}",  # Wiktionary usage example template
            r"\{\{quote[^}]*\|([^}]+)\}\}",  # Quote templates
        ]

        for pattern in quote_patterns:
            matches = re.findall(pattern, definition_text, re.IGNORECASE)
            for match in matches:
                clean_example = self._clean_example_text(match)
                if clean_example and len(clean_example) > 10:
                    examples.generated.append(
                        GeneratedExample(sentence=clean_example, regenerable=False)
                    )

        return examples

    def _clean_definition_text(self, text: str) -> str:
        """Clean up definition text by removing wikitext markup.

        Args:
            text: Raw definition text

        Returns:
            Cleaned definition text
        """
        # Remove wikitext links [[word]] or [[word|display]]
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)

        # Remove templates {{template|content}}
        text = re.sub(r"\{\{[^}]+\}\}", "", text)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove reference markers
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove leading punctuation or numbers from definitions
        text = re.sub(r"^[^\w]*", "", text)

        return text

    def _clean_example_text(self, text: str) -> str:
        """Clean up example text.

        Args:
            text: Raw example text

        Returns:
            Cleaned example text
        """
        # Basic cleanup similar to definitions but preserve structure
        text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _extract_pronunciation_from_wikitext(self, wikitext: str) -> Pronunciation:
        """Extract pronunciation from Wiktionary wikitext.

        Args:
            wikitext: Raw wikitext content

        Returns:
            Pronunciation data
        """
        try:
            parsed = wtp.parse(wikitext)

            # Look for IPA templates
            ipa = None
            phonetic = "unknown"

            # Search for IPA templates in the wikitext
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if "ipa" in template_name:
                    # Extract IPA from template arguments
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()
                        if "/" in arg_value:  # IPA notation typically has slashes
                            ipa = arg_value
                            break

                elif template_name in ["pron", "pronunciation"]:
                    # Alternative pronunciation templates
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()
                        if arg_value and len(arg_value) > 2:
                            phonetic = arg_value
                            break

            # If we found IPA, try to create a simple phonetic version
            if ipa:
                phonetic = self._ipa_to_simple_phonetic(ipa)

            # Fallback: look for pronunciation sections with regex
            if ipa is None:
                ipa_match = re.search(r"\{\{IPA\|[^|]*\|([^}]+)\}\}", wikitext)
                if ipa_match:
                    ipa = ipa_match.group(1)
                    phonetic = self._ipa_to_simple_phonetic(ipa)

            return Pronunciation(phonetic=phonetic, ipa=ipa)

        except Exception as e:
            print(f"Error extracting pronunciation: {e}")
            return Pronunciation(phonetic="unknown")

    def _ipa_to_simple_phonetic(self, ipa: str) -> str:
        """Convert IPA notation to simple phonetic representation.

        Args:
            ipa: IPA notation

        Returns:
            Simplified phonetic representation
        """
        # Basic IPA to phonetic conversion
        phonetic = ipa.replace("/", "").replace("[", "").replace("]", "")

        # Remove stress markers
        phonetic = phonetic.replace("ˈ", "").replace("ˌ", "")

        # Basic character substitutions (very simplified)
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
        }

        for ipa_char, simple_char in substitutions.items():
            phonetic = phonetic.replace(ipa_char, simple_char)

        return phonetic.strip() or "unknown"

    def _extract_synonyms_from_definition(
        self, def_text: str, word_type: WordType
    ) -> list[SynonymReference]:
        """Extract synonyms from Wiktionary definition text.

        Args:
            def_text: Definition text that may contain synonym templates
            word_type: Word type for the definition

        Returns:
            List of synonym references
        """
        synonyms = []

        try:
            # Parse the definition text for synonym templates
            parsed = wtp.parse(def_text)

            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ["syn", "synonym", "synonyms"]:
                    # Extract synonym words from template arguments
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()

                        # Skip language codes and empty arguments
                        if arg_value and len(arg_value) > 1 and arg_value not in ["en", "lang"]:
                            # Clean up the synonym text
                            clean_synonym = self._clean_synonym_text(arg_value)
                            if clean_synonym:
                                synonyms.append(
                                    SynonymReference(
                                        word=Word(text=clean_synonym), word_type=word_type
                                    )
                                )

            # Also look for inline synonym patterns like "syn: word1, word2"
            syn_patterns = [
                r"syn:\s*([^;|}\n]+)",
                r"synonym[s]?:\s*([^;|}\n]+)",
                r"see also:\s*([^;|}\n]+)",
            ]

            for pattern in syn_patterns:
                matches = re.findall(pattern, def_text, re.IGNORECASE)
                for match in matches:
                    # Split on commas and extract individual synonyms
                    syn_words = [word.strip() for word in match.split(",")]
                    for syn_word in syn_words:
                        clean_synonym = self._clean_synonym_text(syn_word)
                        if clean_synonym:
                            synonyms.append(
                                SynonymReference(word=Word(text=clean_synonym), word_type=word_type)
                            )

        except Exception as e:
            print(f"Error extracting synonyms: {e}")

        return synonyms[:10]  # Limit to 10 synonyms per definition

    def _clean_synonym_text(self, synonym_text: str) -> str:
        """Clean and normalize synonym text.

        Args:
            synonym_text: Raw synonym text

        Returns:
            Cleaned synonym text or empty string if invalid
        """
        if not synonym_text:
            return ""

        # Remove wikitext markup
        cleaned = re.sub(r"\[\[([^|\]]+)(\|[^\]]+)?\]\]", r"\1", synonym_text)
        cleaned = re.sub(r"\{\{[^}]+\}\}", "", cleaned)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # Remove extra whitespace and punctuation
        cleaned = re.sub(r"[^\w\s-]", "", cleaned).strip()

        # Basic validation
        if len(cleaned) < 2 or len(cleaned) > 50:
            return ""

        # Skip common non-synonym words
        skip_words = {"thesaurus", "more", "see", "also", "compare", "cf", "etc", "and", "or"}
        if cleaned.lower() in skip_words:
            return ""

        return cleaned

    async def close(self) -> None:
        """Close the HTTP session."""
        await self.session.aclose()

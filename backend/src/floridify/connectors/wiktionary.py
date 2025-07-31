"""Wiktionary connector using MediaWiki API with comprehensive wikitext parsing."""

from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass
from typing import Any

import wikitextparser as wtp  # type: ignore[import-untyped]
from beanie import PydanticObjectId

from ..caching import get_cached_http_client
from ..constants import DictionaryProvider, Language
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Collocation,
    Definition,
    Etymology,
    Example,
    Pronunciation,
    ProviderData,
    UsageNote,
    Word,
)
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
from .base import DictionaryConnector

logger = get_logger(__name__)


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

        # Decode HTML entities
        cleaned = html.unescape(cleaned)

        # Remove any remaining wikitext artifacts
        cleaned = re.sub(r"'''(.+?)'''", r"\1", cleaned)  # Bold text
        cleaned = re.sub(r"''(.+?)''", r"\1", cleaned)  # Italic text
        cleaned = re.sub(r"\[\.\.\.\.?\]", "...", cleaned)  # [...] to ...
        cleaned = re.sub(r"&[a-zA-Z]+;", "", cleaned)  # Remove any remaining entities

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
    def provider_name(self) -> DictionaryProvider:
        return DictionaryProvider.WIKTIONARY

    async def fetch_definition(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch comprehensive definition data from Wiktionary."""
        await self._enforce_rate_limit()

        try:
            # Report start
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

            params = {
                "action": "query",
                "prop": "revisions",
                "titles": word_obj.text,
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
                            details={"word": word_obj.text, **metadata},
                        )
                    )
                elif stage == "downloaded":
                    if state_tracker:
                        # Schedule async progress report
                        asyncio.create_task(
                            state_tracker.update(
                                stage="PROVIDER_FETCH_HTTP_DOWNLOADING",
                                message=f"Downloading from {self.provider_name}",
                                details={"word": word_obj.text, **metadata},
                            )
                        )

            response = await self.http_client.get(
                self.base_url,
                params=params,
                ttl_hours=24.0,
                headers={
                    "User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"
                },
                timeout=120.0,
                progress_callback=http_progress_callback if state_tracker else None,
            )

            if response.status_code == 429:
                logger.warning("Rate limited by Wiktionary, waiting 60s...")
                if state_tracker:
                    await state_tracker.update(
                        stage=Stages.PROVIDER_FETCH_HTTP_RATE_LIMITED,
                        message="Rate limited - waiting 60s",
                    )

                await asyncio.sleep(60)

                response = await self.http_client.get(
                    self.base_url,
                    params=params,
                    force_refresh=True,
                    headers={
                        "User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"
                    },
                    timeout=120.0,
                    progress_callback=http_progress_callback if state_tracker else None,
                )

            response.raise_for_status()
            data = response.json()

            # Report parsing start
            if state_tracker:
                await state_tracker.update(
                    stage=Stages.PROVIDER_FETCH_HTTP_PARSING, progress=55
                )

            result = await self._parse_wiktionary_response(word_obj, data)

            # Report completion
            if state_tracker:
                await state_tracker.update(
                    stage=Stages.PROVIDER_FETCH_HTTP_COMPLETE, progress=58
                )

            return result

        except Exception as e:
            if state_tracker:
                await state_tracker.update_error(f"Provider error: {str(e)}")

            logger.error(f"Error fetching {word_obj.text} from Wiktionary: {e}")
            return None

    async def _parse_wiktionary_response(
        self,
        word_obj: Word,
        data: dict[str, Any],
    ) -> ProviderData | None:
        """Parse Wiktionary response comprehensively."""
        try:
            pages = data.get("query", {}).get("pages", [])
            if not pages or "revisions" not in pages[0]:
                return None

            content = pages[0]["revisions"][0]["slots"]["main"]["content"]

            # Extract all components comprehensively
            return await self._extract_comprehensive_data(content, word_obj)

        except Exception as e:
            logger.error(f"Error parsing Wiktionary response for {word_obj.text}: {e}")
            return None

    async def _extract_comprehensive_data(
        self, wikitext: str, word_obj: Word
    ) -> ProviderData | None:
        """Extract all available data from wikitext using systematic parsing."""
        try:
            parsed = wtp.parse(wikitext)

            # Find English section
            english_section = self._find_language_section(parsed, "English")
            if not english_section:
                english_section = parsed

            # Extract all components
            # After save(), word_obj.id is guaranteed to be not None
            assert word_obj.id is not None

            definitions = await self._extract_definitions(english_section, word_obj.id)
            etymology = self._extract_etymology(english_section)
            pronunciation = self._extract_pronunciation(english_section, word_obj.id)

            # alternative_forms = self._extract_alternative_forms(english_section)

            # related_terms = self._extract_related_terms(english_section)

            # usage_notes = self._extract_usage_notes(english_section)

            # quotations = self._extract_quotations(english_section)

            # Extract synonyms from the dedicated section and add to definitions
            section_synonyms = self._extract_section_synonyms(english_section)

            # Merge section synonyms with each definition
            for definition in definitions:
                assert (
                    definition.id is not None
                )  # After save(), id is guaranteed to be not None

                synonyms = set(definition.synonyms)
                synonyms.update(section_synonyms)

                definition.synonyms = list(synonyms)

                await definition.save()  # Update the definition

            return ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=[d.id for d in definitions],  # type:ignore
                etymology=(Etymology(text=etymology) if etymology else None),
                pronunciation_id=pronunciation.id if pronunciation else None,
            )

        except Exception as e:
            logger.error(f"Error in comprehensive extraction: {e}")
            return None

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

    async def _extract_definitions(
        self, section: wtp.Section, word_id: PydanticObjectId
    ) -> list[Definition]:
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

            # Store the full subsection text for example extraction
            subsection_text = str(subsection)

            for idx, def_text in enumerate(definition_texts):
                if not def_text or len(def_text.strip()) < 5:
                    continue

                # Extract components from definition
                clean_def = self.cleaner.clean_text(def_text)
                if not clean_def:
                    continue

                # Extract inline synonyms from definition
                synonyms = self._extract_inline_synonyms(def_text)

                # Extract collocations from the definition context
                collocations = self._extract_collocations_from_definition(def_text)

                # Extract any inline usage notes
                usage_notes = self._extract_usage_notes_from_definition(def_text)

                # Create definition (meaning_cluster will be added by AI synthesis)
                definition = Definition(
                    word_id=word_id,
                    part_of_speech=part_of_speech,
                    text=clean_def,
                    sense_number=f"{idx + 1}",
                    synonyms=synonyms,
                    frequency_band=None,
                    collocations=collocations,
                    usage_notes=usage_notes,
                )

                # Save definition to get ID
                await definition.save()
                assert (
                    definition.id is not None
                )  # After save(), id is guaranteed to be not None

                # Extract and save examples from both the definition and the full subsection
                # This ensures we capture quotations that appear after the definition
                example_objs = await self._extract_examples(
                    subsection_text, definition.id
                )
                definition.example_ids = [
                    ex.id for ex in example_objs if ex.id is not None
                ]
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

    async def _extract_examples(
        self, definition_text: str, definition_id: PydanticObjectId
    ) -> list[Example]:
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

                elif template_name.startswith("quote-") or template_name in [
                    "quote",
                    "quotation",
                ]:
                    # Quote templates (e.g., quote-book, quote-journal, etc.)
                    # Extract the passage/text parameter
                    passage = None
                    year = None
                    author = None

                    for arg in template.arguments:
                        arg_name = str(arg.name).strip().lower() if arg.name else ""
                        arg_value = str(arg.value).strip()

                        if arg_name in ["passage", "text", "quote"]:
                            passage = arg_value
                        elif arg_name == "year":
                            year = arg_value
                        elif arg_name in ["author", "last"]:
                            author = arg_value

                    if passage:
                        clean_passage = self.cleaner.clean_text(
                            passage, preserve_structure=True
                        )
                        if clean_passage and len(clean_passage) > 10:
                            # Format with metadata if available
                            if year or author:
                                metadata_parts = []
                                if year:
                                    metadata_parts.append(year)
                                if author:
                                    metadata_parts.append(author)
                                full_text = (
                                    f"({', '.join(metadata_parts)}) {clean_passage}"
                                )
                            else:
                                full_text = clean_passage

                            example = Example(
                                definition_id=definition_id,
                                text=full_text,
                                type="literature",
                            )
                            await example.save()
                            examples.append(example)
        except Exception as e:
            logger.error(f"Error extracting examples: {e}")

        return examples

    def _extract_inline_synonyms(self, definition_text: str) -> list[str]:
        """Extract synonyms from inline templates in definitions."""
        synonyms = []

        try:
            parsed = wtp.parse(definition_text)

            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in ["syn", "synonym", "synonyms", "l", "link"]:
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
            logger.debug(f"Error extracting inline synonyms: {e}")

        return synonyms[:10]  # Limit to 10 synonyms

    def _extract_section_synonyms(self, section: wtp.Section) -> list[str]:
        """Extract synonyms from dedicated Synonyms and See also sections."""
        all_synonyms = []

        # Look for Synonyms and See also subsections
        for subsection in section.sections:
            if subsection.title and any(
                keyword in subsection.title.lower()
                for keyword in ["synonym", "see also"]
            ):
                # Extract all wikilist items and plain text
                items = self._extract_wikilist_items(str(subsection))

                # Also parse templates in the section
                parsed = wtp.parse(str(subsection))

                # Extract from templates
                for template in parsed.templates:
                    template_name = template.name.strip().lower()
                    if template_name in ["l", "link", "syn", "synonym"]:
                        for arg in template.arguments:
                            if (
                                not arg.name or arg.name == "2"
                            ):  # Second arg is usually the word
                                value = str(arg.value).strip()
                                if value and value not in ["en", "English"]:
                                    clean_syn = self._clean_synonym(value)
                                    if clean_syn and self._is_valid_synonym(clean_syn):
                                        all_synonyms.append(clean_syn)

                # Extract from list items
                for item in items:
                    # Clean the item
                    clean_item = self.cleaner.clean_text(item)
                    if clean_item and len(clean_item) > 1:
                        # Filter out Thesaurus references
                        if "thesaurus:" in clean_item.lower():
                            continue

                        # Split by commas if multiple synonyms in one line
                        parts = clean_item.split(",")
                        for part in parts:
                            syn = part.strip()
                            if syn and len(syn) > 1 and self._is_valid_synonym(syn):
                                all_synonyms.append(syn)

        # Remove duplicates while preserving order
        seen = set()
        unique_synonyms = []
        for syn in all_synonyms:
            if syn.lower() not in seen:
                seen.add(syn.lower())
                unique_synonyms.append(syn)

        return unique_synonyms[:20]  # Limit to 20 synonyms

    def _is_valid_synonym(self, synonym: str) -> bool:
        """Check if a synonym is valid (not a meta-reference)."""
        lower_syn = synonym.lower()
        # Filter out meta-references
        invalid_patterns = [
            "thesaurus:",
            "see also",
            "appendix:",
            "category:",
            "wikipedia:",
            "wikisaurus:",
        ]
        return not any(pattern in lower_syn for pattern in invalid_patterns)

    def _extract_etymology(self, section: wtp.Section) -> str | None:
        """Extract etymology from dedicated section."""
        for subsection in section.sections:
            if subsection.title and "etymology" in subsection.title.lower():
                # Get only the direct text content, not subsections
                # This avoids including pronunciation, noun definitions, etc.
                text_parts = []
                for content in subsection.contents.split("\n"):
                    # Stop at the first subsection marker
                    if content.strip().startswith("===") or content.strip().startswith(
                        "===="
                    ):
                        break
                    text_parts.append(content)

                etymology_text = "\n".join(text_parts).strip()
                if etymology_text:
                    # Special cleaning for etymology to preserve language links
                    return self._clean_etymology_text(etymology_text)

        return None

    def _clean_etymology_text(self, text: str) -> str:
        """Clean etymology text with a simple, focused approach."""
        if not text:
            return ""

        # Language code mapping
        lang_map = {
            "enm": "Middle English",
            "ang": "Old English",
            "fro": "Old French",
            "fr": "French",
            "la": "Latin",
            "grc": "Ancient Greek",
            "de": "German",
            "es": "Spanish",
            "it": "Italian",
            "ar": "Arabic",
            "sa": "Sanskrit",
            "zh": "Chinese",
            "ja": "Japanese",
            "pt": "Portuguese",
            "nl": "Dutch",
        }

        try:
            parsed = wtp.parse(text)

            # Process templates more carefully
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                # Handle specific etymology templates
                if template_name in [
                    "der",
                    "inh",
                    "bor",
                    "cog",
                    "m",
                    "mention",
                    "l",
                    "lang",
                ]:
                    args = [str(arg.value).strip() for arg in template.arguments]

                    # Common pattern: {{template|en|lang_code|word|...}}
                    if len(args) >= 3:
                        # args[1] is usually the language code
                        # args[2] is usually the word
                        lang_code = args[1] if len(args[1]) <= 3 else None
                        word = args[2] if len(args[2]) > 1 else None

                        if word:
                            if lang_code in lang_map:
                                template.string = f"{lang_map[lang_code]} {word}"
                            else:
                                template.string = word
                        else:
                            template.string = ""
                    else:
                        template.string = ""

                # Handle quotation templates (preserve the quoted text)
                elif template_name in ["quote", "gloss"]:
                    # Look for the gloss/translation argument
                    gloss_text = ""
                    for arg in template.arguments:
                        if arg.name and str(arg.name).strip() in [
                            "t",
                            "gloss",
                            "translation",
                            "3",
                        ]:
                            gloss_text = str(arg.value).strip()
                            break
                        elif not arg.name and len(str(arg.value).strip()) > 3:
                            # Sometimes the gloss is a positional argument
                            gloss_text = str(arg.value).strip()

                    if gloss_text:
                        template.string = f'("{gloss_text}")'
                    else:
                        template.string = ""

                # Remove other templates but preserve doublet/see also references
                elif template_name in ["doublet", "see"]:
                    # Extract the word reference
                    if template.arguments:
                        word_ref = str(template.arguments[-1].value).strip()
                        if word_ref and len(word_ref) > 1:
                            template.string = word_ref
                        else:
                            template.string = ""
                    else:
                        template.string = ""
                else:
                    # Remove unhandled templates
                    template.string = ""

            # Convert wikilinks to their display text
            for wikilink in parsed.wikilinks:
                display_text = wikilink.text or wikilink.target
                wikilink.string = display_text or ""

            # Get the cleaned text
            cleaned = str(parsed)

        except Exception as e:
            logger.debug(f"Etymology parsing error: {e}")
            # Fallback to regex cleaning
            cleaned = text

            # Simple template removal
            cleaned = re.sub(r"\{\{[^}]+\}\}", "", cleaned)

            # Convert wikilinks
            cleaned = re.sub(
                r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                lambda m: m.group(2) or m.group(1),
                cleaned,
            )

        # Final cleanup
        cleaned = html.unescape(cleaned)

        # Clean up punctuation and whitespace
        cleaned = re.sub(r"\s*([,;])\s*([,;])", r"\1", cleaned)  # Multiple punctuation
        cleaned = re.sub(r"\s+([,;.!?])", r"\1", cleaned)  # Space before punctuation
        cleaned = re.sub(
            r"([,;])\s*$", ".", cleaned
        )  # Change trailing comma/semicolon to period
        cleaned = re.sub(r"^\s*[,;.]\s*", "", cleaned)  # Remove leading punctuation
        cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
        cleaned = re.sub(r"\.\s*\.", ".", cleaned)  # Multiple periods

        # Ensure it ends with a period if it doesn't have ending punctuation
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."

        cleaned = cleaned.strip()

        return cleaned

    def _extract_pronunciation(
        self, section: wtp.Section, word_id: PydanticObjectId
    ) -> Pronunciation | None:
        """Extract pronunciation comprehensively."""
        ipa_american = None
        ipa_british = None
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
                    # Extract IPA values and dialect information
                    ipa_value = None
                    dialect = None

                    for i, arg in enumerate(template.arguments):
                        arg_value = str(arg.value).strip()

                        # First argument is usually the language code
                        if i == 0 and arg_value in ["en", "eng", "english"]:
                            continue

                        # Check if this is a dialect indicator
                        if arg_value.lower() in [
                            "us",
                            "usa",
                            "american",
                            "ame",
                            "gen-am",
                            "genam",
                        ]:
                            dialect = "american"
                        elif arg_value.lower() in ["uk", "british", "rp", "gb", "bre"]:
                            dialect = "british"
                        elif "/" in arg_value or "[" in arg_value:
                            # This is likely an IPA transcription
                            ipa_value = arg_value

                    # Assign based on dialect or use as American by default
                    if ipa_value:
                        if dialect == "british":
                            ipa_british = ipa_value
                        else:
                            ipa_american = ipa_value

                elif template_name == "audio":
                    # Skip audio templates entirely
                    continue

                elif template_name in ["pron", "pronunciation", "enpr"]:
                    # Extract traditional pronunciation guides
                    for arg in template.arguments:
                        arg_value = str(arg.value).strip()
                        # Filter out file extensions and language codes
                        if (
                            arg_value
                            and len(arg_value) > 2
                            and not any(
                                marker in arg_value.lower()
                                for marker in [
                                    ".ogg",
                                    ".mp3",
                                    ".wav",
                                    "audio",
                                    "file:",
                                    "en",
                                    "us",
                                    "uk",
                                ]
                            )
                            and "/" not in arg_value
                            and "|" not in arg_value
                        ):  # Avoid template syntax
                            # This might be a phonetic pronunciation
                            if not phonetic and not arg_value.startswith("{{"):
                                phonetic = arg_value
                                break

            # Generate phonetic from IPA if we don't have one
            if not phonetic and ipa_american:
                phonetic = self._ipa_to_phonetic(ipa_american)
            elif not phonetic and ipa_british:
                phonetic = self._ipa_to_phonetic(ipa_british)

            # Return pronunciation if we have any data
            if ipa_american or ipa_british or phonetic:
                # Use American IPA as primary, fallback to British, then phonetic
                primary_ipa = ipa_american or ipa_british or phonetic or "unknown"
                return Pronunciation(
                    word_id=word_id,
                    phonetic=phonetic if phonetic else "unknown",
                    ipa=primary_ipa,
                    syllables=[],
                    stress_pattern=None,
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

    def _extract_collocations_from_definition(
        self, definition_text: str
    ) -> list[Collocation]:
        """Extract collocations from definition text."""
        collocations = []

        try:
            # Look for common collocation patterns in parentheses or after "with", "of", etc.
            patterns = [
                r"\((?:with|of|to|for|in|on|at|by)\s+([^)]+)\)",  # (with something)
                r"(?:used|often|typically|usually)\s+(?:with|of|to|for)\s+([^,.;]+)",
                r"(?:followed\s+by|preceded\s+by)\s+([^,.;]+)",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, definition_text, re.IGNORECASE)
                for match in matches:
                    clean_match = self.cleaner.clean_text(match)
                    if clean_match and len(clean_match) > 2:
                        collocation = Collocation(
                            text=clean_match,
                            type="contextual",
                            frequency=0.5,  # Default medium frequency
                        )
                        collocations.append(collocation)

        except Exception as e:
            logger.debug(f"Error extracting collocations: {e}")

        return collocations[:5]  # Limit to 5 collocations

    def _extract_usage_notes_from_definition(
        self, definition_text: str
    ) -> list[UsageNote]:
        """Extract usage notes from definition text."""
        notes = []

        try:
            # Look for usage indicators in the definition
            indicators = {
                "informal": ["informal", "colloquial", "slang"],
                "formal": ["formal", "literary", "written"],
                "regional": ["british", "american", "australian", "chiefly"],
                "archaic": ["archaic", "obsolete", "dated", "historical"],
                "technical": ["technical", "specialized", "scientific"],
            }

            lower_text = definition_text.lower()

            for note_type, keywords in indicators.items():
                for keyword in keywords:
                    if keyword in lower_text:
                        # Extract context around the keyword
                        pattern = rf"[^.]*{keyword}[^.]*"
                        matches = re.findall(pattern, lower_text)
                        if matches:
                            note_text = self.cleaner.clean_text(matches[0])
                            if note_text:
                                # Map to valid UsageNote types
                                # Valid types: "grammar", "confusion", "regional", "register", "error"
                                from typing import Literal

                                usage_type: Literal[
                                    "grammar",
                                    "confusion",
                                    "regional",
                                    "register",
                                    "error",
                                ]

                                if note_type in [
                                    "informal",
                                    "formal",
                                    "archaic",
                                    "technical",
                                ]:
                                    usage_type = "register"
                                elif note_type == "regional":
                                    usage_type = "regional"
                                else:
                                    usage_type = "register"  # Safe default

                                usage_note = UsageNote(type=usage_type, text=note_text)
                                notes.append(usage_note)
                                break  # Only one note per type

        except Exception as e:
            logger.debug(f"Error extracting usage notes: {e}")

        return notes[:3]  # Limit to 3 notes

    def _extract_usage_notes(self, section: wtp.Section) -> list[str] | None:
        """Extract usage notes from Wiktionary."""
        notes = []

        for subsection in section.sections:
            title = subsection.title
            if title and "usage" in title.lower() and "note" in title.lower():
                # Extract paragraphs and items from usage notes section
                section_text = str(subsection.contents)

                # Clean up the text
                cleaned_text = self.cleaner.clean_text(
                    section_text, preserve_structure=True
                )

                # Split by paragraph or list items
                parts = re.split(r"\n\s*\n|\n\s*[*#]", cleaned_text)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 20:  # Minimum length for meaningful note
                        notes.append(part)

        return notes[:5] if notes else None  # Limit to 5 notes

    def _extract_quotations(self, section: wtp.Section) -> list[dict[str, str]] | None:
        """Extract quotations from Wiktionary."""
        quotations = []

        try:
            # Search through all subsections for quotations
            section_text = str(section)
            parsed = wtp.parse(section_text)

            # Look for quotation templates
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                if template_name in [
                    "quote",
                    "quotation",
                    "quote-book",
                    "quote-journal",
                    "quote-text",
                ]:
                    quotation_data = {}

                    # Extract quotation details
                    for arg in template.arguments:
                        arg_name = str(arg.name).strip() if arg.name else None
                        arg_value = str(arg.value).strip()

                        if arg_name == "text" or arg_name == "passage":
                            quotation_data["text"] = self.cleaner.clean_text(arg_value)
                        elif arg_name == "author":
                            quotation_data["author"] = arg_value
                        elif arg_name == "year":
                            quotation_data["year"] = arg_value
                        elif arg_name == "title":
                            quotation_data["title"] = arg_value
                        elif arg_name == "source":
                            quotation_data["source"] = arg_value

                    # Only add if we have at least the text
                    if "text" in quotation_data and quotation_data["text"]:
                        quotations.append(quotation_data)

        except Exception as e:
            logger.debug(f"Error extracting quotations: {e}")

        return quotations[:10] if quotations else None  # Limit to 10 quotations

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

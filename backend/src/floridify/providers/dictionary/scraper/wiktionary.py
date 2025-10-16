"""Wiktionary connector using MediaWiki API with comprehensive wikitext parsing."""

from __future__ import annotations

import asyncio
import html
import json
import re
from typing import Any

import httpx
import wikitextparser as wtp  # type: ignore[import-untyped]
from beanie import PydanticObjectId

from ....caching.decorators import cached_computation_async
from ....core.state_tracker import Stages, StateTracker
from ....models.base import Language
from ....models.dictionary import (
    Definition,
    DictionaryProvider,
    Example,
    Pronunciation,
    Word,
)
from ....models.relationships import (
    Collocation,
    UsageNote,
)
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector
from ..models import DictionaryProviderEntry

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

            # Handle templates with specialized logic
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                # Handle templates with general approach
                if template_name.startswith("quote-") or template_name in ["quote", "quotation"]:
                    # Quote templates should be completely removed from definitions
                    # They will be handled separately as examples
                    template.string = ""

                elif template_name in ["term", "mention", "lang", "l", "link"]:
                    # Keep the main content, remove the template wrapper
                    if template.arguments:
                        # Usually the last argument is the display text, or second for {{l|lang|word}}
                        if len(template.arguments) >= 2:
                            content = str(template.arguments[1].value).strip()
                        else:
                            content = str(template.arguments[-1].value).strip()
                        template.string = content
                    else:
                        template.string = ""

                elif template_name in ["gloss", "gl"]:
                    # Gloss templates: {{gloss|meaning}} -> "(meaning)"
                    if template.arguments:
                        gloss_text = str(template.arguments[0].value).strip()
                        template.string = f"({gloss_text})"
                    else:
                        template.string = ""

                elif template_name in ["lb", "label", "qualifier", "q"]:
                    # Label/qualifier templates: {{lb|en|informal}} -> "(informal)"
                    labels = []
                    for arg in template.arguments:
                        arg_val = str(arg.value).strip()
                        if arg_val and arg_val not in ["en", "eng"]:  # Skip language codes
                            labels.append(arg_val)
                    if labels:
                        template.string = f"({', '.join(labels)})"
                    else:
                        template.string = ""

                # For other templates, try to extract meaningful content from arguments
                # This handles templates like {{synonym of|en|word}}, {{form of|...}}, etc.
                elif template.arguments:
                    # Skip language codes and template metadata, look for actual content
                    content_args = []
                    for arg in template.arguments:
                        arg_val = str(arg.value).strip()
                        # Skip language codes and common metadata
                        if (
                            arg_val
                            and len(arg_val) > 1
                            and arg_val not in ["en", "eng", "1", "2", "3"]
                            and not arg_val.startswith("http")
                        ):
                            content_args.append(arg_val)

                    if content_args:
                        # Use the first meaningful content argument
                        template.string = content_args[0]
                    else:
                        template.string = ""
                else:
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

        # Final cleanup with regex for any remaining templates
        cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Remove HTML tags
        cleaned = re.sub(r"\{\{[^}]*\}\}", "", cleaned)  # Remove remaining templates
        cleaned = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cleaned)  # Clean links
        cleaned = re.sub(r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.DOTALL)  # Remove refs

        # Decode HTML entities
        cleaned = html.unescape(cleaned)

        # Remove any remaining wikitext artifacts
        cleaned = re.sub(r"'''(.+?)'''", r"\1", cleaned)  # Bold text
        cleaned = re.sub(r"''(.+?)''", r"\1", cleaned)  # Italic text
        cleaned = re.sub(r"\[\.\.\.\.?\]", "...", cleaned)  # [...] to ...
        cleaned = re.sub(r"&[a-zA-Z]+;", "", cleaned)  # Remove any remaining entities

        # Clean up extra whitespace and punctuation
        cleaned = re.sub(r"\s*\.\s*$", "", cleaned)  # Remove trailing period
        cleaned = re.sub(r"^\s*[.,;:]\s*", "", cleaned)  # Remove leading punctuation

        if not preserve_structure:
            cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace

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

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        """Initialize enhanced Wiktionary connector."""
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.API_STANDARD.value)
        super().__init__(provider=DictionaryProvider.WIKTIONARY, config=config)
        self.base_url = "https://en.wiktionary.org/w/api.php"
        self.cleaner = WikitextCleaner()

    @cached_computation_async(ttl_hours=24.0, key_prefix="wiktionary_api")
    async def _cached_get(self, url: str, params: dict[str, Any]) -> str:
        """Cached HTTP GET for API calls."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers={"User-Agent": "Floridify/1.0 (https://github.com/user/floridify)"},
                timeout=120.0,
            )
            if response.status_code == 429:
                raise Exception("Rate limited by Wiktionary")
            response.raise_for_status()
            return response.text

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        """Fetch comprehensive definition data from Wiktionary."""
        # Rate limiting is handled by the base class fetch method

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

            # Progress callback for HTTP request
            http_progress_data = {}

            def http_progress_callback(stage: str, metadata: dict[str, Any]) -> None:
                http_progress_data.update(metadata)
                if stage == "connecting" and state_tracker:
                    # Schedule async progress report
                    asyncio.create_task(
                        state_tracker.update(
                            stage="PROVIDER_FETCH_HTTP_CONNECTING",
                            message=f"Connecting to {self.provider.display_name}",
                            details={"word": word, **metadata},
                        ),
                    )
                elif stage == "downloaded":
                    if state_tracker:
                        # Schedule async progress report
                        asyncio.create_task(
                            state_tracker.update(
                                stage="PROVIDER_FETCH_HTTP_DOWNLOADING",
                                message=f"Downloading from {self.provider.display_name}",
                                details={"word": word, **metadata},
                            ),
                        )

            response_text = await self._cached_get(self.base_url, params)

            # Parse JSON response

            data = json.loads(response_text)

            # Report parsing start
            if state_tracker:
                await state_tracker.update(stage=Stages.PROVIDER_FETCH_HTTP_PARSING, progress=55)

            # Create Word object for processing
            word_obj = Word(text=word)
            await word_obj.save()

            result = await self._parse_wiktionary_response(word_obj, data)

            # Report completion
            if state_tracker:
                await state_tracker.update(stage=Stages.PROVIDER_FETCH_HTTP_COMPLETE, progress=58)

            return result

        except Exception as e:
            if state_tracker:
                await state_tracker.update_error(f"Provider error: {e!s}")

            logger.error(f"Error fetching {word} from Wiktionary: {e}")
            return None

    async def _parse_wiktionary_response(
        self,
        word_obj: Word,
        data: dict[str, Any],
    ) -> DictionaryProviderEntry | None:
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
        self,
        wikitext: str,
        word_obj: Word,
    ) -> DictionaryProviderEntry | None:
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

            # Extract synonyms from the dedicated section and add to definitions
            section_synonyms = self._extract_section_synonyms(english_section)

            # Merge section synonyms with each definition
            for definition in definitions:
                assert definition.id is not None  # After save(), id is guaranteed to be not None

                synonyms = set(definition.synonyms)
                synonyms.update(section_synonyms)

                definition.synonyms = list(synonyms)

                await definition.save()  # Update the definition

            return DictionaryProviderEntry(
                word=word_obj.text,
                provider=self.provider.value,
                language=Language.ENGLISH,
                definitions=[
                    {
                        "id": str(definition.id),
                        "part_of_speech": definition.part_of_speech,
                        "text": definition.text,
                        "sense_number": definition.sense_number,
                        "synonyms": definition.synonyms,
                        "frequency_band": definition.frequency_band,
                        "collocations": [
                            {
                                "text": c.text,
                                "type": c.type,
                                "frequency": c.frequency,
                            }
                            for c in definition.collocations
                        ],
                        "usage_notes": [
                            {
                                "type": n.type,
                                "text": n.text,
                            }
                            for n in definition.usage_notes
                        ],
                        "example_ids": [str(eid) for eid in definition.example_ids],
                    }
                    for definition in definitions
                ],
                pronunciation=pronunciation.phonetic if pronunciation else None,
                etymology=etymology,
                examples=[],
                raw_data={"wikitext": wikitext},
                provider_metadata={
                    "pronunciation": pronunciation.model_dump(mode="json")
                    if pronunciation
                    else None,
                },
            )

        except Exception as e:
            logger.error(f"Error in comprehensive extraction: {e}")
            return None

    def _find_language_section(self, parsed: wtp.WikiList, language: str) -> wtp.Section | None:
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
        self,
        section: wtp.Section,
        word_id: PydanticObjectId,
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
                assert definition.id is not None  # After save(), id is guaranteed to be not None

                # Extract and save examples from both the definition and the full subsection
                # This ensures we capture quotations that appear after the definition
                example_objs = await self._extract_examples(subsection_text, definition.id)
                definition.example_ids = [ex.id for ex in example_objs if ex.id is not None]
                await definition.save()  # Update with example IDs

                definitions.append(definition)

        return definitions

    def _extract_wikilist_items(self, section_text: str) -> list[str]:
        """Extract numbered definition items from section text, separating definitions from examples."""
        items = []

        # Split section into lines for more precise processing
        lines = section_text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for numbered definition lines starting with #
            if re.match(r"^#\s+", line):
                # Extract the definition part (everything after # until we hit a quote template or new definition)
                definition_text = line[1:].strip()  # Remove the # and leading whitespace

                # Check if this line contains quote templates - if so, extract only the part before quotes
                quote_match = re.search(r"\{\{quote-", definition_text)
                if quote_match:
                    # Take only the part before the quote template
                    definition_text = definition_text[: quote_match.start()].strip()

                # Continue collecting the definition if it spans multiple lines (before hitting quotes)
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()

                    # Stop if we hit another definition, quote template, or section header
                    if (
                        re.match(r"^#", next_line)
                        or next_line.startswith("{{quote-")
                        or next_line.startswith("==")
                        or next_line.startswith("===")
                    ):
                        break

                    # Add non-quote content to definition
                    if next_line and not next_line.startswith("{{quote-"):
                        # Check if this line contains quote templates
                        quote_match = re.search(r"\{\{quote-", next_line)
                        if quote_match:
                            # Take only the part before the quote template
                            definition_text += " " + next_line[: quote_match.start()].strip()
                            break
                        definition_text += " " + next_line
                    i += 1

                # Clean and validate the definition text
                if definition_text and len(definition_text.strip()) > 5:
                    items.append(definition_text.strip())

                # Don't increment i again since we already processed multiple lines
                continue

            i += 1

        return items

    async def _extract_examples(
        self,
        definition_text: str,
        definition_id: PydanticObjectId,
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
                            example_text,
                            preserve_structure=True,
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
                        elif arg_name in [
                            "author",
                            "last",
                            "1",
                        ]:  # Add "1" as potential author field
                            if not author:  # Only set if we don't already have an author
                                author = arg_value

                    if passage:
                        # Clean up {{...}} placeholders commonly found in quotes
                        passage = re.sub(r"\{\{\.\.\.+\}\}", "...", passage)

                        clean_passage = self.cleaner.clean_text(passage, preserve_structure=True)
                        if clean_passage and len(clean_passage) > 10:
                            # Format with metadata if available
                            if year or author:
                                metadata_parts = []
                                if year:
                                    metadata_parts.append(year)
                                if author:
                                    metadata_parts.append(author)
                                full_text = f"({', '.join(metadata_parts)}) {clean_passage}"
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
                            if arg_value and len(arg_value) > 1 and arg_value not in ["en", "lang"]:
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
                keyword in subsection.title.lower() for keyword in ["synonym", "see also"]
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
                            if not arg.name or arg.name == "2":  # Second arg is usually the word
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
                    if content.strip().startswith("===") or content.strip().startswith("===="):
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
                        if not arg.name and len(str(arg.value).strip()) > 3:
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
        cleaned = re.sub(r"([,;])\s*$", ".", cleaned)  # Change trailing comma/semicolon to period
        cleaned = re.sub(r"^\s*[,;.]\s*", "", cleaned)  # Remove leading punctuation
        cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
        cleaned = re.sub(r"\.\s*\.", ".", cleaned)  # Multiple periods

        # Ensure it ends with a period if it doesn't have ending punctuation
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."

        cleaned = cleaned.strip()

        return cleaned

    def _extract_pronunciation(
        self,
        section: wtp.Section,
        word_id: PydanticObjectId,
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

    def _extract_collocations_from_definition(self, definition_text: str) -> list[Collocation]:
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

    def _extract_usage_notes_from_definition(self, definition_text: str) -> list[UsageNote]:
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
            or cleaned.lower() in {"thesaurus", "see", "also", "compare", "etc", "and", "or"}
        ):
            return None

        return cleaned

    async def close(self) -> None:
        """Close HTTP client."""
        # No HTTP client to close - using cached decorator

"""Wiktionary connector using MediaWiki API with comprehensive wikitext parsing."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import wikitextparser as wtp  # type: ignore[import-untyped]

from ....caching.decorators import cached_computation_async
from ....core.state_tracker import Stages, StateTracker
from ....models.base import Language
from ....models.dictionary import (
    DictionaryProvider,
    Word,
)
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector
from ..models import DictionaryProviderEntry
from .wikitext_cleaner import WikitextCleaner
from .wiktionary_parser import (
    extract_definitions,
    extract_derived_terms,
    extract_etymology,
    extract_hypernyms,
    extract_hyponyms,
    extract_pronunciation,
    extract_related_terms,
    extract_section_antonyms,
    extract_section_synonyms,
    extract_section_usage_notes,
    find_all_language_sections,
    find_language_section,
)

logger = get_logger(__name__)

WIKTIONARY_SECTION_TITLES: dict[str, str] = {
    Language.ENGLISH.value: "English",
    Language.FRENCH.value: "French",
    Language.SPANISH.value: "Spanish",
    Language.GERMAN.value: "German",
    Language.ITALIAN.value: "Italian",
}

# Reverse: Wiktionary section name → Language code
_SECTION_TO_LANGUAGE: dict[str, Language] = {
    name.lower(): Language(code) for code, name in WIKTIONARY_SECTION_TITLES.items()
}


class WiktionaryConnector(DictionaryConnector):
    """Enhanced Wiktionary connector with comprehensive wikitext parsing."""

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
        languages: list[str] | None = None,
    ) -> DictionaryProviderEntry | None:
        """Fetch comprehensive definition data from Wiktionary."""
        # Rate limiting is handled by the base class fetch method

        try:
            requested_languages = list(languages) if languages else [Language.ENGLISH.value]
            primary_language_code = requested_languages[0]
            primary_language = Language(primary_language_code)

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

            # Create or update Word object for processing
            word_obj = await Word.find_one(Word.text == word)
            if not word_obj:
                word_obj = Word(text=word, languages=requested_languages)
                await word_obj.save()

            result = await self._parse_wiktionary_response(
                word_obj=word_obj,
                data=data,
                primary_language=primary_language,
            )

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
        primary_language: Language,
    ) -> DictionaryProviderEntry | None:
        """Parse Wiktionary response comprehensively."""
        try:
            pages = data.get("query", {}).get("pages", [])
            if not pages or "revisions" not in pages[0]:
                return None

            content = pages[0]["revisions"][0]["slots"]["main"]["content"]

            # Extract all components comprehensively
            return await self._extract_comprehensive_data(
                wikitext=content,
                word_obj=word_obj,
                primary_language=primary_language,
            )

        except Exception as e:
            logger.error(f"Error parsing Wiktionary response for {word_obj.text}: {e}")
            return None

    async def _extract_comprehensive_data(
        self,
        wikitext: str,
        word_obj: Word,
        primary_language: Language,
    ) -> DictionaryProviderEntry | None:
        """Extract all available data from wikitext across all language sections.

        English Wiktionary is a multilingual dictionary — a single page may
        have ==English==, ==French==, ==Latin== sections. We parse ALL
        recognized language sections (primary first), merge the definitions,
        and tag the word with every language found.

        E.g., "en coulisse" has a ==French== section on en.wiktionary.org.
        A word like "resume" might have both ==English== and ==French==.
        """
        try:
            parsed = wtp.parse(wikitext)

            # Discover all language sections on this page
            available = find_all_language_sections(parsed)
            if not available:
                return None

            # Resolve to known Language enums, primary language first
            sections_to_parse: list[tuple[Language, wtp.Section]] = []
            seen_languages: set[str] = set()

            # Primary language gets priority
            for section_name, section in available:
                resolved = _SECTION_TO_LANGUAGE.get(section_name.lower())
                if resolved is not None and resolved == primary_language:
                    sections_to_parse.insert(0, (resolved, section))
                    seen_languages.add(resolved.value)

            # Then all other recognized languages
            for section_name, section in available:
                resolved = _SECTION_TO_LANGUAGE.get(section_name.lower())
                if resolved is not None and resolved.value not in seen_languages:
                    sections_to_parse.append((resolved, section))
                    seen_languages.add(resolved.value)

            if not sections_to_parse:
                logger.info(
                    "Wiktionary: no recognized language section for '%s' (found: %s)",
                    word_obj.text,
                    [name for name, _ in available],
                )
                return None

            # Update word's language tags to reflect all languages found
            for lang, _ in sections_to_parse:
                if lang.value not in word_obj.languages:
                    word_obj.languages.append(lang.value)
            await word_obj.save()

            assert word_obj.id is not None

            # Parse all language sections, merging definitions
            all_definitions_dicts: list[dict[str, Any]] = []
            first_etymology: str | None = None
            first_pronunciation = None
            all_derived: list[str] = []
            all_related: list[str] = []
            all_hypernyms: list[str] = []
            all_hyponyms: list[str] = []
            all_usage_notes: list[dict[str, str]] = []
            entry_language = sections_to_parse[0][0]  # Primary or first found

            for lang, language_section in sections_to_parse:
                section_syns = extract_section_synonyms(language_section)
                section_ants = extract_section_antonyms(language_section)

                definitions = await extract_definitions(
                    language_section,
                    word_obj.id,
                    section_synonyms=section_syns,
                    section_antonyms=section_ants,
                )

                for definition in definitions:
                    all_definitions_dicts.append({
                        "id": str(definition.id),
                        "part_of_speech": definition.part_of_speech,
                        "text": definition.text,
                        "sense_number": definition.sense_number,
                        "synonyms": definition.synonyms,
                        "antonyms": definition.antonyms,
                        "frequency_band": definition.frequency_band,
                        "collocations": [
                            {"text": c.text, "type": c.type, "frequency": c.frequency}
                            for c in definition.collocations
                        ],
                        "usage_notes": [
                            {"type": n.type, "text": n.text}
                            for n in definition.usage_notes
                        ],
                        "example_ids": [str(eid) for eid in definition.example_ids],
                        "language": lang.value,  # Tag which language this def came from
                    })

                # First section with etymology/pronunciation wins
                if first_etymology is None:
                    first_etymology = extract_etymology(language_section)
                if first_pronunciation is None:
                    first_pronunciation = extract_pronunciation(language_section, word_obj.id)

                all_derived.extend(extract_derived_terms(language_section))
                all_related.extend(extract_related_terms(language_section))
                all_hypernyms.extend(extract_hypernyms(language_section))
                all_hyponyms.extend(extract_hyponyms(language_section))
                all_usage_notes.extend(
                    {"type": n.type, "text": n.text}
                    for n in extract_section_usage_notes(language_section)
                )

            if not all_definitions_dicts:
                return None

            languages_found = [lang.value for lang, _ in sections_to_parse]
            if len(languages_found) > 1:
                logger.info(
                    "Wiktionary: '%s' parsed from %d language sections: %s",
                    word_obj.text, len(languages_found), languages_found,
                )

            return DictionaryProviderEntry(
                word=word_obj.text,
                provider=self.provider.value,
                language=entry_language,
                definitions=all_definitions_dicts,
                pronunciation=first_pronunciation.phonetic if first_pronunciation else None,
                etymology=first_etymology,
                examples=[],
                raw_data={"wikitext": wikitext},
                provider_metadata={
                    "pronunciation": first_pronunciation.model_dump(mode="json")
                    if first_pronunciation
                    else None,
                    "languages_found": languages_found,
                    "derived_terms": all_derived,
                    "related_terms": all_related,
                    "hypernyms": all_hypernyms,
                    "hyponyms": all_hyponyms,
                    "section_usage_notes": all_usage_notes,
                },
            )

        except Exception as e:
            logger.error(f"Error in comprehensive extraction: {e}")
            return None

    async def close(self) -> None:
        """Close HTTP client."""
        # No HTTP client to close - using cached decorator

    async def _fetch_provider_entry(
        self,
        word: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        return await self._fetch_from_provider(
            word=word.text,
            state_tracker=state_tracker,
            languages=list(word.languages),
        )

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
    extract_etymology,
    extract_pronunciation,
    extract_section_synonyms,
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
        """Extract all available data from wikitext using systematic parsing."""
        try:
            parsed = wtp.parse(wikitext)

            section_title = WIKTIONARY_SECTION_TITLES[primary_language.value]
            language_section = find_language_section(parsed, section_title)
            if language_section is None:
                logger.info(
                    "Wiktionary section '%s' not found for '%s'",
                    section_title,
                    word_obj.text,
                )
                return None

            # Extract all components
            # After save(), word_obj.id is guaranteed to be not None
            assert word_obj.id is not None

            # Extract section synonyms FIRST so they can be merged into definitions
            # before the initial save (avoids a consistency window with missing synonyms).
            section_syns = extract_section_synonyms(language_section)

            definitions = await extract_definitions(
                language_section,
                word_obj.id,
                section_synonyms=section_syns,
            )
            etymology = extract_etymology(language_section)
            pronunciation = extract_pronunciation(language_section, word_obj.id)

            return DictionaryProviderEntry(
                word=word_obj.text,
                provider=self.provider.value,
                language=primary_language,
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

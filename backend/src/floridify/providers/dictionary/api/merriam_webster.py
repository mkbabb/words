"""Merriam-Webster Dictionary API connector.

Requires API keys from https://dictionaryapi.com/
"""

from __future__ import annotations

from typing import Any

import httpx
from beanie import PydanticObjectId

from ....caching.decorators import cached_api_call
from ....core.state_tracker import Stages, StateTracker
from ....models import Etymology
from ....models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Example,
    Pronunciation,
    Word,
)
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector

logger = get_logger(__name__)


class MerriamWebsterConnector(DictionaryConnector):
    """Connector for Merriam-Webster Dictionary API.

    The Merriam-Webster API provides:
    - Comprehensive definitions with sense hierarchies
    - Audio pronunciations
    - Etymologies
    - Usage examples
    - Date of first known use
    - Synonyms and antonyms
    """

    def __init__(self, api_key: str | None = None, config: ConnectorConfig | None = None) -> None:
        """Initialize Merriam-Webster connector.

        Args:
            api_key: API key for Merriam-Webster (optional, will read from config)
            config: Connector configuration

        """
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.API_STANDARD.value)
        super().__init__(provider=DictionaryProvider.MERRIAM_WEBSTER, config=config)

        # Use provided API key or raise error if not provided
        if not api_key:
            raise ValueError("Merriam-Webster API key required")

        self.api_key = api_key
        self.base_url = "https://dictionaryapi.com/api/v3/references/collegiate/json"

    @cached_api_call(ttl_hours=24.0, key_prefix="merriam_webster")
    async def _fetch_from_api(self, word: str) -> dict[str, Any] | None:
        """Fetch word data from Merriam-Webster API.

        Args:
            word: The word to look up

        Returns:
            API response data or None if not found

        """
        # Rate limiting is handled by the base class fetch method

        url = f"{self.base_url}/{word}"
        params = {"key": self.api_key}

        try:
            session = await self.get_api_session()
            response = await session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # API returns list of suggestions if word not found
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return data[0]  # Return first matching entry
            logger.warning(f"No definition found for '{word}' in Merriam-Webster")
            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Merriam-Webster API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Merriam-Webster: {e}")
            return None

    def _parse_pronunciation(
        self,
        data: dict[str, Any],
        word_id: PydanticObjectId,
    ) -> Pronunciation | None:
        """Parse pronunciation data from API response.

        Args:
            data: API response data

        Returns:
            Pronunciation object or None

        """
        try:
            # Merriam-Webster provides multiple pronunciation formats
            pronunciations = data.get("hwi", {})  # Headword info

            # Get phonetic spelling
            phonetic = pronunciations.get("hw", "")
            if phonetic:
                # MW uses * for syllable breaks
                phonetic = phonetic.replace("*", "·")

            # Note: Merriam-Webster provides audio files, but we're not storing audio URLs directly
            # Audio file handling would need to be implemented through the AudioMedia model

            if phonetic:
                return Pronunciation(
                    word_id=word_id,
                    phonetic=phonetic,
                    ipa=phonetic,
                    syllables=phonetic.split("·") if "·" in phonetic else [],
                )

            return None

        except Exception as e:
            logger.debug(f"Error parsing pronunciation: {e}")
            return None

    def _parse_etymology(self, data: dict[str, Any]) -> Etymology | None:
        """Parse etymology data from API response.

        Args:
            data: API response data

        Returns:
            Etymology object or None

        """
        try:
            # Merriam-Webster includes etymology in "et" field
            et_data = data.get("et", [])
            if not et_data:
                return None

            # Parse etymology text (complex nested structure)
            etymology_parts = []
            for item in et_data:
                if isinstance(item, list) and len(item) > 1:
                    # Format: ["text", "content"] or ["et_link", ...]
                    if item[0] == "text":
                        etymology_parts.append(item[1])

            if etymology_parts:
                etymology_text = " ".join(etymology_parts)

                # Also get first known use date
                date = data.get("date", "")
                if date:
                    etymology_text = f"{etymology_text} (First known use: {date})"

                return Etymology(
                    text=etymology_text,
                    origin_language="en",  # MW is English-focused
                    root_words=[],
                )

            return None

        except Exception as e:
            logger.debug(f"Error parsing etymology: {e}")
            return None

    async def _parse_definitions(
        self,
        data: dict[str, Any],
        word_id: PydanticObjectId,
    ) -> list[Definition]:
        """Parse definitions from API response.

        Args:
            data: API response data
            word_id: ID of the word being defined

        Returns:
            List of Definition objects

        """
        definitions: list[Definition] = []

        try:
            # Get part of speech directly
            pos_raw = data.get("fl", "")  # "fl" = functional label
            part_of_speech = pos_raw.lower() if pos_raw else "unknown"

            # Parse definition sections
            def_sections = data.get("def", [])

            for section in def_sections:
                # Each section contains sense sequences
                sseq = section.get("sseq", [])

                for sense_group in sseq:
                    for sense_item in sense_group:
                        if not isinstance(sense_item, list) or len(sense_item) < 2:
                            continue

                        sense_type = sense_item[0]
                        sense_data = sense_item[1]

                        if sense_type == "sense" and isinstance(sense_data, dict):
                            # Parse the definition text
                            dt = sense_data.get("dt", [])  # Definition text
                            definition_text = self._extract_definition_text(dt)

                            if not definition_text:
                                continue

                            # Create definition
                            definition = Definition(
                                word_id=word_id,
                                part_of_speech=part_of_speech,
                                text=definition_text,
                                sense_number=str(len(definitions) + 1),
                                synonyms=[],
                            )

                            # Save definition to get ID
                            await definition.save()

                            # Parse and save examples
                            example_texts = self._extract_examples(dt)
                            example_ids = []
                            if definition.id is not None:
                                for ex_text in example_texts[:3]:  # Limit to 3 examples
                                    example = Example(
                                        definition_id=definition.id,
                                        text=ex_text,
                                        type="literature",
                                    )
                                    await example.save()
                                    if example.id is not None:
                                        example_ids.append(example.id)

                            # Update definition with example IDs
                            definition.example_ids = example_ids
                            await definition.save()

                            definitions.append(definition)

        except Exception as e:
            logger.error(f"Error parsing definitions: {e}")

        return definitions

    def _extract_definition_text(self, dt: list[Any]) -> str:
        """Extract definition text from dt (definition text) structure.

        Args:
            dt: Definition text structure from API

        Returns:
            Cleaned definition text

        """
        text_parts: list[str] = []

        for item in dt:
            if isinstance(item, list) and len(item) > 1:
                if item[0] == "text":
                    # Clean up MW's markup
                    text = item[1]
                    # Remove {bc} (bold colon) and other markup
                    text = text.replace("{bc}", ": ")
                    text = text.replace("{ldquo}", '"')
                    text = text.replace("{rdquo}", '"')
                    text_parts.append(text)

        return " ".join(text_parts).strip()

    def _extract_examples(self, dt: list[Any]) -> list[str]:
        """Extract examples from definition text structure.

        Args:
            dt: Definition text structure from API

        Returns:
            List of Example objects

        """
        examples: list[str] = []

        for item in dt:
            if isinstance(item, list) and len(item) > 1:
                if item[0] == "vis":
                    # Visual examples (quoted examples)
                    for vis_item in item[1]:
                        if isinstance(vis_item, dict):
                            t = vis_item.get("t", "")
                            if t:
                                # Clean up the example text
                                t = t.replace("{ldquo}", '"')
                                t = t.replace("{rdquo}", '"')
                                t = t.replace("{it}", "")
                                t = t.replace("{/it}", "")

                                examples.append(t)

        return examples

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Fetch definition from Merriam-Webster.

        Args:
            word: Word to look up

        Returns:
            ProviderData with definitions, pronunciation, and etymology

        """
        try:
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

            # Fetch from API
            data = await self._fetch_from_api(word)
            if not data:
                return None

            # Create Word object for processing
            word_obj = Word(text=word)
            await word_obj.save()

            if not word_obj.id:
                raise ValueError(f"Word {word} must be saved before processing")

            # Parse components
            definitions = await self._parse_definitions(data, word_obj.id)
            if not definitions:
                logger.warning(f"No definitions parsed for '{word}'")
                return None

            pronunciation = self._parse_pronunciation(data, word_obj.id)
            etymology = self._parse_etymology(data)

            # Get definition IDs (already saved in parsing)
            definition_ids = [
                definition.id for definition in definitions if definition.id is not None
            ]

            # Save pronunciation if exists
            pronunciation_id = None
            if pronunciation:
                await pronunciation.save()
                pronunciation_id = pronunciation.id

            # Create provider data
            provider_data = DictionaryEntry(
                word_id=word_obj.id,
                provider=self.provider,
                definition_ids=definition_ids,
                pronunciation_id=pronunciation_id,
                etymology=etymology,
                raw_data=data,
            )

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

            return provider_data

        except Exception as e:
            logger.error(f"Error fetching from Merriam-Webster: {e}")
            if state_tracker:
                await state_tracker.update_error(str(e), Stages.PROVIDER_FETCH_ERROR)
            return None

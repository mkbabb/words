"""Oxford Dictionary API connector."""

from __future__ import annotations

import asyncio
from typing import Any

from beanie import PydanticObjectId

from ....core.state_tracker import StateTracker
from ....models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Example,
    Pronunciation,
    Word,
)
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector

logger = get_logger(__name__)


class OxfordConnector(DictionaryConnector):
    """Connector for Oxford Dictionary API."""

    def __init__(self, app_id: str, api_key: str, config: ConnectorConfig | None = None) -> None:
        """Initialize Oxford connector.

        Args:
            app_id: Oxford API application ID
            api_key: Oxford API key
            config: Connector configuration

        """
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.API_CONSERVATIVE.value)
        super().__init__(provider=DictionaryProvider.OXFORD, config=config)
        self.app_id = app_id
        self.api_key = api_key
        self.base_url = "https://od-api.oxforddictionaries.com/api/v2"
        self.headers = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "Accept": "application/json",
        }

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Fetch definition data for a word from Oxford API.

        Args:
            word: The word to look up

        Returns:
            ProviderData if successful, None if not found or error

        """

        try:
            if state_tracker:
                from ....core.state_tracker import Stages

                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

            # Fetch both entries and pronunciation if available
            url = f"{self.base_url}/entries/en-us/{word.lower()}"

            session = await self.get_api_session()
            response = await session.get(url, headers=self.headers)

            if response.status_code == 404:
                return None  # Word not found
            if response.status_code == 429:
                # Rate limited - wait and retry once
                await asyncio.sleep(1)
                response = await session.get(url, headers=self.headers)

            response.raise_for_status()
            data = response.json()

            # Create Word object for processing
            word_obj = Word(text=word)
            await word_obj.save()

            result = await self._parse_oxford_response(word, data, word_obj)

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

            return result

        except Exception as e:
            logger.error(f"Error fetching {word} from Oxford: {e}")
            if state_tracker:
                from ....core.state_tracker import Stages

                await state_tracker.update_error(str(e), Stages.PROVIDER_FETCH_ERROR)
            return None

    async def _parse_oxford_response(
        self,
        word: str,
        data: dict[str, Any],
        word_obj: Word,
    ) -> DictionaryEntry:
        """Parse Oxford API response using new models.

        Args:
            word: The word being looked up
            data: Raw API response
            word_obj: The Word document

        Returns:
            Parsed ProviderData

        """
        # Extract all components using the new API pattern
        assert word_obj.id is not None  # After save(), id is guaranteed to be not None

        # Extract definitions and save them
        definitions = await self.extract_definitions(data, word_obj.id)

        # Extract pronunciation and save it
        pronunciation = await self.extract_pronunciation(data, word_obj.id)
        if pronunciation:
            await pronunciation.save()

        # Extract etymology
        etymology = await self.extract_etymology(data)

        # Create and return ProviderData
        return DictionaryEntry(
            word_id=word_obj.id,
            provider=self.provider,
            definition_ids=[d.id for d in definitions if d.id is not None],
            pronunciation_id=pronunciation.id if pronunciation else None,
            etymology=etymology,
            raw_data=data,
        )

    async def extract_pronunciation(
        self,
        raw_data: dict[str, Any],
        word_id: PydanticObjectId,
    ) -> Pronunciation | None:
        """Extract pronunciation from Oxford data.

        Args:
            raw_data: Raw response from Oxford API

        Returns:
            Pronunciation if found, None otherwise

        """
        try:
            results = raw_data.get("results", [])
            if not results:
                return None

            # Oxford includes pronunciations in lexical entries
            for result in results:
                lexical_entries = result.get("lexicalEntries", [])
                for lexical_entry in lexical_entries:
                    pronunciations = lexical_entry.get("pronunciations", [])
                    if pronunciations:
                        # Get first pronunciation
                        pron = pronunciations[0]
                        phonetic = pron.get("phoneticSpelling", "")

                        # Oxford provides both British and American pronunciations
                        ipa_british = None
                        ipa_american = None

                        for p in pronunciations:
                            dialect = p.get("dialects", [])
                            if "American English" in dialect:
                                ipa_american = p.get("phoneticSpelling")
                            elif "British English" in dialect:
                                ipa_british = p.get("phoneticSpelling")

                        # Use American IPA as primary, fallback to British
                        primary_ipa = ipa_american or ipa_british or phonetic or "unknown"
                        return Pronunciation(
                            word_id=word_id,  # This should be passed as parameter
                            phonetic=phonetic if phonetic else "unknown",
                            ipa=primary_ipa,
                            syllables=[],
                            stress_pattern=None,
                        )
        except Exception as e:
            logger.error(f"Error extracting pronunciation: {e}")

        return None

    async def extract_definitions(
        self,
        raw_data: dict[str, Any],
        word_id: PydanticObjectId,
    ) -> list[Definition]:
        """Extract definitions from Oxford data.

        Args:
            raw_data: Raw response from Oxford API
            word_id: ID of the word these definitions belong to

        Returns:
            List of Definition objects

        """
        definitions: list[Definition] = []

        try:
            results = raw_data.get("results", [])
            if not results:
                return definitions

            for result in results:
                lexical_entries = result.get("lexicalEntries", [])

                for lexical_entry in lexical_entries:
                    # Get part of speech directly
                    oxford_pos = lexical_entry.get("lexicalCategory", {}).get("id", "").lower()
                    part_of_speech = oxford_pos if oxford_pos else "unknown"

                    entries = lexical_entry.get("entries", [])

                    for entry in entries:
                        senses = entry.get("senses", [])

                        for sense_idx, sense in enumerate(senses):
                            definition_texts = sense.get("definitions", [])

                            for def_idx, def_text in enumerate(definition_texts):
                                # Extract domain and register
                                domains = sense.get("domainClasses", [])
                                domain = domains[0].get("text") if domains else None

                                registers = sense.get("registers", [])
                                from typing import Literal

                                register: (
                                    Literal["formal", "informal", "neutral", "slang", "technical"]
                                    | None
                                ) = None
                                if registers:
                                    reg_text = registers[0].get("text", "").lower()
                                    if "formal" in reg_text:
                                        register = "formal"
                                    elif "informal" in reg_text:
                                        register = "informal"
                                    elif "slang" in reg_text:
                                        register = "slang"
                                    elif "technical" in reg_text:
                                        register = "technical"
                                    else:
                                        register = "neutral"  # Default to neutral for other cases

                                # Create definition (meaning_cluster will be added by AI synthesis)
                                definition = Definition(
                                    word_id=word_id,
                                    part_of_speech=part_of_speech,
                                    text=def_text,
                                    sense_number=f"{sense_idx + 1}.{def_idx + 1}",
                                    synonyms=[],
                                    antonyms=[],
                                    example_ids=[],
                                    language_register=register,
                                    domain=domain,
                                    frequency_band=None,
                                )

                                # Save definition to get ID
                                await definition.save()

                                # Extract and save examples
                                oxford_examples = sense.get("examples", [])
                                for example in oxford_examples:
                                    example_text = example.get("text", "")
                                    if example_text:
                                        assert (
                                            definition.id is not None
                                        )  # After save(), id is guaranteed to be not None
                                        example_obj = Example(
                                            definition_id=definition.id,
                                            text=example_text,
                                            type="literature",  # Oxford examples are from real usage
                                        )
                                        await example_obj.save()
                                        assert (
                                            example_obj.id is not None
                                        )  # After save(), id is guaranteed to be not None
                                        definition.example_ids.append(example_obj.id)

                                # Update definition with example IDs
                                await definition.save()
                                definitions.append(definition)

        except Exception as e:
            logger.error(f"Error extracting definitions: {e}")

        return definitions

    async def extract_etymology(self, raw_data: dict[str, Any]) -> Etymology | None:
        """Extract etymology from Oxford data.

        Args:
            raw_data: Raw response from Oxford API

        Returns:
            Etymology if found, None otherwise

        """
        try:
            results = raw_data.get("results", [])
            if not results:
                return None

            for result in results:
                lexical_entries = result.get("lexicalEntries", [])
                for lexical_entry in lexical_entries:
                    entries = lexical_entry.get("entries", [])
                    for entry in entries:
                        etymologies = entry.get("etymologies", [])
                        if etymologies:
                            # Oxford provides detailed etymology
                            etym_text = etymologies[0]
                            return Etymology(
                                text=etym_text,
                                origin_language=None,  # Could parse from text
                                root_words=[],
                            )
        except Exception as e:
            logger.error(f"Error extracting etymology: {e}")

        return None

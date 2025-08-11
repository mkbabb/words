"""Free Dictionary API connector.

Free, open API with no authentication required.
API documentation: https://dictionaryapi.dev/
"""

from __future__ import annotations

from typing import Any

import httpx
from beanie import PydanticObjectId

from ...caching.decorators import cached_api_call
from ...core.state_tracker import Stages, StateTracker
from ...models import (
    Definition,
    Etymology,
    Example,
    Pronunciation,
    ProviderData,
    Word,
)
from ...models.definition import DictionaryProvider
from ...utils.logging import get_logger
from ..base import DictionaryConnector

logger = get_logger(__name__)


class FreeDictionaryConnector(DictionaryConnector):
    """Connector for Free Dictionary API.
    
    The Free Dictionary API provides:
    - Multiple definitions with meanings
    - Phonetic pronunciations with audio
    - Parts of speech
    - Examples
    - Synonyms and antonyms
    - Source attributions
    """

    def __init__(self, rate_limit: float = 60.0) -> None:
        """Initialize Free Dictionary connector.
        
        Args:
            rate_limit: Maximum requests per second (default: 60, very generous)
        """
        super().__init__(rate_limit=rate_limit)
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
        self.session = httpx.AsyncClient(timeout=30.0)

    @property
    def provider_name(self) -> DictionaryProvider:
        """Return the provider name."""
        return DictionaryProvider.FREE_DICTIONARY

    @property
    def provider_version(self) -> str:
        """Version of the Free Dictionary API implementation."""
        return "1.0.0"

    async def __aenter__(self) -> FreeDictionaryConnector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.session.aclose()

    @cached_api_call(ttl_hours=24.0, key_prefix="free_dictionary")
    async def _fetch_from_api(self, word: str) -> list[dict[str, Any]] | None:
        """Fetch word data from Free Dictionary API.
        
        Args:
            word: The word to look up
            
        Returns:
            API response data or None if not found
        """
        await self._enforce_rate_limit()
        
        url = f"{self.base_url}/{word}"
        
        try:
            response = await self.session.get(url)
            
            if response.status_code == 404:
                logger.debug(f"Word '{word}' not found in Free Dictionary")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # API returns a list of entries
            if isinstance(data, list) and data:
                return data
            
            return None
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Free Dictionary API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Free Dictionary: {e}")
            return None

    def _parse_pronunciations(self, entries: list[dict[str, Any]], word_id: PydanticObjectId) -> Pronunciation | None:
        """Parse pronunciation data from API response.
        
        Args:
            entries: List of API response entries
            
        Returns:
            Pronunciation object or None
        """
        try:
            # Look through all entries for pronunciation data
            for entry in entries:
                phonetics = entry.get("phonetics", [])
                
                for phonetic in phonetics:
                    text = phonetic.get("text", "")
                    audio = phonetic.get("audio", "")
                    
                    if text or audio:
                        return Pronunciation(
                            word_id=word_id,
                            ipa=text if text and (text.startswith("/") or text.startswith("[")) else text or "unknown",
                            phonetic=text if text and not (text.startswith("/") or text.startswith("[")) else "unknown",
                            syllables=[],
                        )
            
            # Fallback to phonetic field at entry level
            for entry in entries:
                phonetic = entry.get("phonetic", "")
                if phonetic:
                    return Pronunciation(
                        word_id=word_id,
                        ipa=phonetic if phonetic.startswith("/") or phonetic.startswith("[") else "unknown",
                        phonetic=phonetic if not (phonetic.startswith("/") or phonetic.startswith("[")) else "unknown",
                        syllables=[],
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing pronunciations: {e}")
            return None

    async def _parse_definitions(self, entries: list[dict[str, Any]], word_id: PydanticObjectId) -> list[Definition]:
        """Parse definitions from API response.
        
        Args:
            entries: List of API response entries
            word_id: ID of the word being defined
            
        Returns:
            List of Definition objects
        """
        definitions: list[Definition] = []
        
        try:
            for entry in entries:
                meanings = entry.get("meanings", [])
                
                for meaning in meanings:
                    # Get part of speech directly
                    pos_raw = meaning.get("partOfSpeech", "")
                    part_of_speech = pos_raw.lower() if pos_raw else "unknown"
                    
                    # Get definitions for this part of speech
                    defs = meaning.get("definitions", [])
                    
                    for def_data in defs:
                        definition_text = def_data.get("definition", "")
                        if not definition_text:
                            continue
                        
                        # Get synonyms and antonyms
                        synonyms = def_data.get("synonyms", [])
                        antonyms = def_data.get("antonyms", [])
                        
                        # Create definition
                        definition = Definition(
                            word_id=word_id,
                            part_of_speech=part_of_speech,
                            text=definition_text,
                            sense_number=str(len(definitions) + 1),
                            synonyms=synonyms[:10] if synonyms else [],  # Limit to 10
                            antonyms=antonyms[:10] if antonyms else [],  # Limit to 10
                        )
                        
                        # Save definition to get ID
                        await definition.save()
                        
                        # Parse and save example if available
                        example_text = def_data.get("example", "")
                        if example_text and definition.id is not None:
                            example = Example(
                                definition_id=definition.id,
                                text=example_text,
                                type="generated",
                            )
                            await example.save()
                            if example.id is not None:
                                definition.example_ids = [example.id]
                                await definition.save()
                        
                        definitions.append(definition)
            
        except Exception as e:
            logger.error(f"Error parsing definitions: {e}")
        
        return definitions

    def _parse_etymology(self, entries: list[dict[str, Any]]) -> Etymology | None:
        """Parse etymology from API response.
        
        Args:
            entries: List of API response entries
            
        Returns:
            Etymology object or None
        """
        try:
            # Look for origin field in entries
            for entry in entries:
                origin = entry.get("origin", "")
                if origin:
                    return Etymology(
                        text=origin,
                        origin_language="en",
                        root_words=[],
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing etymology: {e}")
            return None

    async def _fetch_from_provider(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definition from Free Dictionary.
        
        Args:
            word_obj: Word object to look up
            state_tracker: Optional state tracker for progress
            
        Returns:
            ProviderData with definitions, pronunciation, and etymology
        """
        try:
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)
            
            # Fetch from API
            entries = await self._fetch_from_api(word_obj.text)
            if not entries:
                return None
            
            # Check that word_obj has been saved and has an ID
            if not word_obj.id:
                raise ValueError(f"Word {word_obj.text} must be saved before processing")
            
            # Parse components
            definitions = await self._parse_definitions(entries, word_obj.id)
            if not definitions:
                logger.warning(f"No definitions parsed for '{word_obj.text}'")
                return None
            
            pronunciation = self._parse_pronunciations(entries, word_obj.id)
            etymology = self._parse_etymology(entries)
            
            # Get definition IDs (already saved in parsing)
            definition_ids = [definition.id for definition in definitions if definition.id is not None]
            
            # Save pronunciation if exists
            pronunciation_id = None
            if pronunciation:
                await pronunciation.save()
                pronunciation_id = pronunciation.id
            
            # Create provider data
            provider_data = ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=definition_ids,
                pronunciation_id=pronunciation_id,
                etymology=etymology,
                raw_data={"entries": entries},  # Store all entries
            )
            
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error fetching from Free Dictionary: {e}")
            if state_tracker:
                await state_tracker.update_error(str(e), Stages.PROVIDER_FETCH_ERROR)
            return None



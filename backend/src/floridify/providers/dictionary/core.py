"""Dictionary-specific connector base class."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Example,
    Pronunciation,
    Word,
)
from ...models.relationships import Collocation, UsageNote
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig
from .models import DictionaryProviderEntry

logger = get_logger(__name__)


class DictionaryConnector(BaseConnector):
    """Base dictionary connector with versioned storage."""

    def __init__(
        self,
        provider: DictionaryProvider,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize dictionary connector."""
        super().__init__(config or ConnectorConfig())
        self.provider = provider

    def get_resource_type(self) -> ResourceType:
        """Get the resource type for dictionary entries."""
        return ResourceType.DICTIONARY

    def get_cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace for dictionary entries."""
        return CacheNamespace.DICTIONARY

    def get_cache_key_suffix(self) -> str:
        return self.provider.value

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Get dictionary-specific metadata for a resource."""
        return {
            "word": resource_id,
            "provider": self.provider.value,
            "provider_display_name": self.provider.display_name,
        }

    def _coerce_entry(
        self,
        payload: DictionaryProviderEntry | dict[str, Any],
    ) -> DictionaryProviderEntry:
        if isinstance(payload, DictionaryProviderEntry):
            return payload
        return DictionaryProviderEntry.model_validate(payload)

    def model_dump(self, content: Any) -> Any:
        entry = self._coerce_entry(content)
        return entry.model_dump(mode="json")

    def model_load(self, content: Any) -> Any:
        return DictionaryProviderEntry.model_validate(content)

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> DictionaryProviderEntry | None:
        result = await super().get(resource_id, config)
        if result is None:
            return None
        return self._coerce_entry(result)

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        """Fetch dictionary entry from provider and convert to provider model."""
        config = config or VersionConfig()

        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached is not None:
                logger.info(
                    "%s using cached %s entry for '%s'",
                    self.provider.value,
                    self.get_resource_type().value,
                    resource_id,
                )
                return cached

        await self.rate_limiter.acquire()

        if state_tracker:
            await state_tracker.update(
                stage="fetching",
                message=f"{resource_id} from {self.provider.value}",
            )

        entry = await self._fetch_from_provider(resource_id, state_tracker)
        if entry is None:
            return None

        typed_entry = self._coerce_entry(entry)

        if self.config.save_versioned:
            await self.save(resource_id, typed_entry, config)

        return typed_entry

    async def fetch_definition(
        self,
        word: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Fetch complete dictionary entry with MongoDB documents.

        This is the adapter method expected by lookup_pipeline. It:
        1. Fetches DictionaryProviderEntry from provider
        2. Converts raw data to MongoDB documents (Definition, Example, etc.)
        3. Returns DictionaryEntry with all ObjectId references

        Args:
            word: Word object with text, normalized, language fields
            state_tracker: Optional progress tracking

        Returns:
            Complete DictionaryEntry with saved MongoDB documents, or None
        """
        # Fetch raw provider data
        provider_entry = await self._fetch_from_provider(word.text, state_tracker)
        if not provider_entry:
            return None

        # Convert to MongoDB documents
        definition_ids: list[PydanticObjectId] = []
        pronunciation_id: PydanticObjectId | None = None

        # Save definitions with examples
        for def_data in provider_entry.definitions:
            # Create Definition document
            definition = Definition(
                word_id=word.id,
                part_of_speech=def_data.get("part_of_speech", "unknown"),
                text=def_data.get("text", ""),
                sense_number=def_data.get("sense_number"),
                synonyms=def_data.get("synonyms", []),
                antonyms=def_data.get("antonyms", []),
                providers=[self.provider],
                collocations=[
                    Collocation(**c) if isinstance(c, dict) else c
                    for c in def_data.get("collocations", [])
                ],
                usage_notes=[
                    UsageNote(**n) if isinstance(n, dict) else n
                    for n in def_data.get("usage_notes", [])
                ],
            )
            await definition.save()

            # Save examples if present
            example_ids: list[PydanticObjectId] = []
            for example_text in def_data.get("examples", []):
                example = Example(
                    word_id=word.id,
                    definition_id=definition.id,
                    text=example_text,
                )
                await example.save()
                if example.id:
                    example_ids.append(example.id)

            # Update definition with example IDs
            if example_ids:
                definition.example_ids = example_ids
                await definition.save()

            if definition.id:
                definition_ids.append(definition.id)

        # Save pronunciation if present
        if provider_entry.pronunciation:
            pronunciation = Pronunciation(
                word_id=word.id,
                phonetic=provider_entry.pronunciation,
            )
            await pronunciation.save()
            pronunciation_id = pronunciation.id

        # Convert etymology string to Etymology model if present
        etymology: Etymology | None = None
        if provider_entry.etymology:
            etymology = Etymology(text=provider_entry.etymology)

        # Create DictionaryEntry document
        dict_entry = DictionaryEntry(
            word_id=word.id,
            definition_ids=definition_ids,
            pronunciation_id=pronunciation_id,
            provider=self.provider,
            language=word.language,
            etymology=etymology,
            raw_data=provider_entry.raw_data,
        )
        await dict_entry.save()

        return dict_entry

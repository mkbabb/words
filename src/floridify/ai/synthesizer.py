"""Definition synthesizer for creating unified dictionary entries."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
    WordType,
)
from ..storage.mongodb import get_synthesized_entry, save_synthesized_entry
from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .models import AIGeneratedProviderData

logger = get_logger(__name__)


class DefinitionSynthesizer:
    """Synthesizes dictionary entries from multiple providers using AI."""

    def __init__(self, openai_connector: OpenAIConnector) -> None:
        self.ai = openai_connector

    async def synthesize_entry(
        self, word: Word, providers: Mapping[str, ProviderData]
    ) -> SynthesizedDictionaryEntry:
        """Synthesize a complete dictionary entry from provider data."""
        # Check if we already have a synthesized entry
        existing = await get_synthesized_entry(word.text)
        if existing and self._is_fresh(existing, providers):
            return existing

        # Generate pronunciation if not available
        pronunciation = await self._synthesize_pronunciation(word, providers)

        # Group definitions by word type
        definitions_by_type = self._group_definitions_by_type(providers)

        # Synthesize definitions for each word type
        synthesized_definitions: list[Definition] = []
        for word_type, definitions in definitions_by_type.items():
            synthesized_def = await self._synthesize_definition_for_type(
                word, word_type, definitions
            )
            if synthesized_def:
                synthesized_definitions.append(synthesized_def)

        # Create synthesized entry
        entry = SynthesizedDictionaryEntry(
            word=word,
            pronunciation=pronunciation,
            definitions=synthesized_definitions,
            last_updated=datetime.now(),
        )

        # Save to database
        await save_synthesized_entry(entry)
        return entry

    async def generate_fallback_entry(self, word: Word) -> SynthesizedDictionaryEntry:
        """Generate a complete fallback entry using AI."""
        # Generate fallback provider data
        fallback_response = await self.ai.generate_fallback_entry(word.text)

        if fallback_response.is_nonsense or not fallback_response.provider_data:
            # Return minimal entry for nonsense words
            return SynthesizedDictionaryEntry(
                word=word,
                pronunciation=Pronunciation(phonetic="", ipa=None),
                definitions=[],
                last_updated=datetime.now(),
            )

        # Convert to AI-generated provider data
        ai_provider = AIGeneratedProviderData(
            **fallback_response.provider_data.model_dump(),
            confidence_score=fallback_response.confidence,
            model_used=self.ai.model_name,
        )

        # Use the AI provider data to create synthesized entry
        providers = {"ai_fallback": ai_provider}
        return await self.synthesize_entry(word, providers)

    def _is_fresh(
        self, entry: SynthesizedDictionaryEntry, providers: Mapping[str, ProviderData]
    ) -> bool:
        """Check if synthesized entry is still fresh compared to provider data."""
        # If any provider data is newer than the synthesized entry, it's stale
        for provider_data in providers.values():
            if provider_data.last_updated > entry.last_updated:
                return False
        return True

    def _group_definitions_by_type(
        self, providers: Mapping[str, ProviderData]
    ) -> dict[WordType, list[tuple[str, Definition]]]:
        """Group definitions by word type across all providers."""
        definitions_by_type: dict[WordType, list[tuple[str, Definition]]] = {}

        for provider_name, provider_data in providers.items():
            for definition in provider_data.definitions:
                if definition.word_type not in definitions_by_type:
                    definitions_by_type[definition.word_type] = []
                definitions_by_type[definition.word_type].append(
                    (provider_name, definition)
                )

        return definitions_by_type

    async def _synthesize_definition_for_type(
        self, word: Word, word_type: WordType, definitions: list[tuple[str, Definition]]
    ) -> Definition | None:
        """Synthesize definitions for a specific word type."""
        if not definitions:
            return None

        # Extract provider definitions for synthesis
        provider_definitions = [
            (provider, definition.definition) for provider, definition in definitions
        ]

        try:
            # Synthesize the definition
            synthesis_response = await self.ai.synthesize_definition(
                word.text, word_type.value, provider_definitions
            )

            # Generate a modern example
            example_response = await self.ai.generate_example(
                word.text, synthesis_response.synthesized_definition, word_type.value
            )

            # Create the synthesized definition
            return Definition(
                word_type=word_type,
                definition=synthesis_response.synthesized_definition,
                synonyms=[],  # Could be enhanced to synthesize synonyms
                examples=Examples(
                    generated=[
                        GeneratedExample(
                            sentence=example_response.example_sentence,
                            regenerable=True,
                        )
                    ]
                ),
                raw_metadata={
                    "synthesis_confidence": synthesis_response.confidence,
                    "example_confidence": example_response.confidence,
                    "sources_used": synthesis_response.sources_used,
                },
            )

        except Exception as e:
            logger.error(f"Failed to synthesize definition for {word.text}: {e}")
            # Fallback to best available definition
            best_def = max(definitions, key=lambda x: len(x[1].definition))[1]
            return best_def

    async def _synthesize_pronunciation(
        self, word: Word, providers: Mapping[str, ProviderData]
    ) -> Pronunciation:
        """Synthesize pronunciation from providers or generate with AI."""
        # First, try to find existing pronunciation from providers
        # for provider_data in providers.values():
        #     # We'd need to add pronunciation to ProviderData in the future
        #     # For now, generate with AI
        #     pass
        
        _ = providers  # Suppress unused warning until we implement provider lookup

        try:
            pronunciation_response = await self.ai.generate_pronunciation(word.text)
            return Pronunciation(
                phonetic=pronunciation_response.phonetic,
                ipa=pronunciation_response.ipa,
            )
        except Exception as e:
            logger.error(f"Failed to generate pronunciation for {word.text}: {e}")
            return Pronunciation(phonetic="", ipa=None)

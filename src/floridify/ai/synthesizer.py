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
from .models import AIGeneratedProviderData, MeaningCluster

logger = get_logger(__name__)


class DefinitionSynthesizer:
    """Synthesizes dictionary entries from multiple providers using AI."""

    def __init__(self, openai_connector: OpenAIConnector) -> None:
        self.ai = openai_connector

    async def synthesize_entry(
        self, word: Word, providers: Mapping[str, ProviderData]
    ) -> SynthesizedDictionaryEntry:
        """Synthesize a complete dictionary entry from provider data using meaning clusters."""
        # Check if we already have a synthesized entry
        existing = await get_synthesized_entry(word.text)
        if existing and self._is_fresh(existing, providers):
            logger.info(f"📋 Using cached synthesized entry for '{word.text}'")
            return existing

        # Generate pronunciation if not available
        pronunciation = await self._synthesize_pronunciation(word, providers)

        # Extract all provider definitions for meaning clustering
        all_definitions = []
        for provider_name, provider_data in providers.items():
            for definition in provider_data.definitions:
                all_definitions.append(
                    (provider_name, definition.word_type.value, definition.definition)
                )

        if not all_definitions:
            logger.warning(f"No definitions found for '{word.text}'")
            return SynthesizedDictionaryEntry(
                word=word,
                pronunciation=pronunciation,
                definitions=[],
                last_updated=datetime.now(),
            )

        # Extract meaning clusters using AI
        logger.info(
            f"🔍 Analyzing {len(all_definitions)} definitions for meaning clusters"
        )
        meaning_response = await self.ai.extract_meanings(word.text, all_definitions)

        # Synthesize definitions for each meaning cluster
        synthesized_definitions: list[Definition] = []
        meaning_groups: dict[str, list[Definition]] = {}

        for cluster in meaning_response.meaning_clusters:
            cluster_definitions = await self._synthesize_cluster_definitions(
                word, cluster, providers
            )
            synthesized_definitions.extend(cluster_definitions)

            # Group definitions by meaning for display
            if cluster_definitions:
                meaning_groups[cluster.meaning_id] = cluster_definitions

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
        logger.info(f"🔮 Starting AI fallback generation for '{word.text}'")

        # Generate fallback provider data
        fallback_response = await self.ai.generate_fallback_entry(word.text)

        if fallback_response.is_nonsense or not fallback_response.provider_data:
            logger.info(f"🚫 No valid definitions generated for '{word.text}'")
            # Return minimal entry for nonsense words
            return SynthesizedDictionaryEntry(
                word=word,
                pronunciation=Pronunciation(phonetic="", ipa=None),
                definitions=[],
                last_updated=datetime.now(),
            )

        # Convert AI response to full provider data
        ai_definitions = []
        for ai_def in fallback_response.provider_data.definitions:
            full_def = Definition(
                word_type=ai_def.word_type,
                definition=ai_def.definition,
                examples=Examples(
                    generated=[GeneratedExample(sentence=ex) for ex in ai_def.examples]
                ),
                synonyms=[],
            )
            ai_definitions.append(full_def)

        ai_provider = AIGeneratedProviderData(
            provider_name=fallback_response.provider_data.provider_name,
            definitions=ai_definitions,
            confidence_score=fallback_response.confidence,
            model_used=self.ai.model_name,
        )

        # Use the AI provider data to create synthesized entry
        providers = {"ai_fallback": ai_provider}
        logger.success(
            f"🎉 Successfully created AI fallback entry for '{word.text}' "
            f"with {len(ai_definitions)} definitions"
        )
        return await self.synthesize_entry(word, providers)

    async def _synthesize_cluster_definitions(
        self, word: Word, cluster: MeaningCluster, providers: Mapping[str, ProviderData]
    ) -> list[Definition]:
        """Synthesize definitions for a specific meaning cluster."""
        cluster_name = cluster.meaning_id.replace(f"{word.text}_", "")

        synthesized_definitions = []

        # For each word type in this meaning cluster
        for cluster_def in cluster.definitions_by_type:
            word_type = cluster_def.word_type
            provider_definitions = cluster_def.definitions

            if not provider_definitions:
                continue

            # Convert to the format expected by synthesis
            formatted_definitions = []
            for def_text in provider_definitions:
                # Create a temporary Definition object for synthesis
                temp_def = Definition(
                    word_type=word_type,
                    definition=def_text,
                    examples=Examples(),
                    synonyms=[],
                )
                formatted_definitions.append(
                    (f"cluster_{cluster.meaning_id}", temp_def)
                )

            # Synthesize this word type within the meaning cluster
            synthesized_def = await self._synthesize_definition_for_type_with_context(
                word, word_type, formatted_definitions, cluster_name
            )

            if synthesized_def:
                # Set the meaning cluster ID for display grouping
                synthesized_def.meaning_cluster = cluster.meaning_id
                synthesized_definitions.append(synthesized_def)

        def_count = len(synthesized_definitions)
        logger.debug(
            f"✨ Created {def_count} definitions for '{cluster.meaning_id}' cluster"
        )
        return synthesized_definitions

    async def _synthesize_definition_for_type_with_context(
        self,
        word: Word,
        word_type: WordType,
        definitions: list[tuple[str, Definition]],
        context: str,
    ) -> Definition | None:
        """Synthesize definitions for a specific word type with meaning context."""

        # Use the existing method but with context logging
        result = await self._synthesize_definition_for_type(
            word, word_type, definitions
        )

        if result:
            logger.success(
                f"🎯 Synthesized '{word.text}' ({word_type.value}) - {context}"
            )

        return result

    def _is_fresh(
        self, entry: SynthesizedDictionaryEntry, providers: Mapping[str, ProviderData]
    ) -> bool:
        """Check if synthesized entry is still fresh (within reasonable time window)."""
        from datetime import timedelta

        # Consider entry fresh if it's less than 24 hours old
        # Provider timestamps are meaningless since they're set on each fetch
        max_age = timedelta(hours=24)
        age = datetime.now() - entry.last_updated

        return age <= max_age

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
                meaning_cluster=None,  # Will be set by caller if needed
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

"""Definition synthesizer for creating unified dictionary entries."""

from __future__ import annotations

from datetime import datetime

from ..constants import DictionaryProvider
from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
)
from ..storage.mongodb import get_synthesized_entry, save_synthesized_entry
from ..utils.logging import get_logger
from .connector import OpenAIConnector

logger = get_logger(__name__)


class DefinitionSynthesizer:
    """Synthesizes dictionary entries from multiple providers_data using AI."""

    def __init__(self, openai_connector: OpenAIConnector) -> None:
        self.ai = openai_connector

    async def synthesize_entry(
        self, word: str, providers_data: list[ProviderData]
    ) -> SynthesizedDictionaryEntry:
        """Synthesize a complete dictionary entry from provider data using meaning clusters."""

        # Check if we already have a synthesized entry
        existing = await get_synthesized_entry(word)

        if existing is not None:
            logger.info(f"📋 Using cached synthesized entry for '{word}'")
            return existing

        # Generate pronunciation if not available
        pronunciation = await self._synthesize_pronunciation(word)

        # Extract all (provider, word_type, definition) for meaning clustering
        all_definitions: list[tuple[str, str, str]] = []

        for provider_data in providers_data:
            for definition in provider_data.definitions:
                all_definitions.append(
                    (
                        provider_data.provider_name,
                        definition.word_type,
                        definition.definition,
                    )
                )

        if not all_definitions:
            logger.warning(f"No definitions found for '{word}'")

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
        meaning_cluster_response = await self.ai.extract_meaning_clusters(
            word, all_definitions
        )

        # Synthesize definitions for each meaning cluster
        synthesized_definitions: list[Definition] = []

        for cluster in meaning_cluster_response.meaning_clusters:
            logger.info(
                f"🧠 Synthesizing definitions for meaning cluster '{cluster.meaning_cluster}'"
            )

            # Convert MeaningClusterDefinition to tuples for synthesis
            definition_tuples = [
                (defn.provider, defn.word_type, defn.definition)
                for defn in cluster.definitions
            ]

            # Synthesize definition for this word type
            synthesized_def = await self._synthesize_definitions(
                word=word,
                definitions=definition_tuples,
                meaning_cluster=cluster.meaning_cluster,
            )

            if synthesized_def is not None:
                synthesized_definitions.extend(synthesized_def)

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

    async def generate_fallback_entry(self, word: str) -> SynthesizedDictionaryEntry:
        """Generate a complete fallback entry using AI."""
        logger.info(f"🔮 Starting AI fallback generation for '{word}'")

        # Generate fallback provider data
        dictionary_entry = await self.ai.generate_fallback_entry(word)

        if dictionary_entry is None or dictionary_entry.provider_data is None:
            logger.info(f"🚫 No valid definitions generated for '{word}'")
            # Return minimal entry for nonsense words
            return SynthesizedDictionaryEntry(
                word=word,
                pronunciation=Pronunciation(),
                last_updated=datetime.now(),
            )

        # Convert AI response to full provider data
        definitions: list[Definition] = []
        for definition in dictionary_entry.provider_data.definitions:
            examples_response = await self.ai.generate_example(
                word=word,
                word_type=definition.word_type,
                definition=definition.definition,
            )

            examples = Examples(
                generated=[
                    GeneratedExample(
                        sentence=sentence,
                    )
                    for sentence in examples_response.example_sentences
                ]
            )

            full_def = Definition(
                word_type=definition.word_type,
                definition=definition.definition,
                examples=examples,
            )

            definitions.append(full_def)

        provider_data = ProviderData(
            provider_name=DictionaryProvider.AI_FALLBACK.value,
            definitions=definitions,
            last_updated=datetime.now(),
            raw_metadata={
                "synthesis_confidence": dictionary_entry.confidence,
                "model_name": self.ai.model_name,
            },
        )

        providers_data = [provider_data]

        logger.success(
            f"🎉 Successfully created AI fallback entry for '{word}' "
            f"with {len(definitions)} definitions"
        )

        return await self.synthesize_entry(
            word=word,
            providers_data=providers_data,
        )

    async def _synthesize_definitions(
        self,
        word: str,
        definitions: list[tuple[str, str, str]],
        meaning_cluster: str | None,
    ) -> list[Definition] | None:
        """Synthesize definitions for a specific word type across multiple word types and providers.

        Args:
            word: The word to synthesize definitions for.
            definitions: List of tuples containing (provider_name, word_type, definition).
            meaning_cluster: The meaning cluster this definition belongs to.
        """

        if not definitions:
            return None

        try:
            # Synthesize the definition
            synthesis_response = await self.ai.synthesize_definitions(
                word=word,
                provider_definitions=definitions,
                meaning_cluster=meaning_cluster,
            )

            if not synthesis_response.definitions:
                logger.warning(
                    f"⚠️  No definitions synthesized for '{word}' in cluster '{meaning_cluster}'"
                )
                return None

            synthesized_definitions: list[Definition] = []

            for definition in synthesis_response.definitions:
                word_type = definition.word_type

                example_response = await self.ai.generate_example(
                    word=word,
                    word_type=word_type,
                    definition=definition.definition,
                )

                examples = Examples(
                    generated=[
                        GeneratedExample(
                            sentence=sentence,
                        )
                        for sentence in example_response.example_sentences
                    ]
                )

                # Create the synthesized definition
                synthesized_def = Definition(
                    word_type=word_type,
                    definition=definition.definition,
                    synonyms=definition.synonyms,
                    examples=examples,
                    meaning_cluster=meaning_cluster,
                    raw_metadata={
                        "synthesis_confidence": synthesis_response.confidence,
                        "example_confidence": example_response.confidence,
                        "sources_used": synthesis_response.sources_used,
                    },
                )

                synthesized_definitions.append(synthesized_def)

            if not synthesized_definitions:
                logger.warning(
                    f"⚠️  No valid synthesized definitions found for '{word}'"
                )
                return None

            logger.success(
                f"✅ Successfully synthesized {len(synthesized_definitions)} definitions for '{word}'"
            )
            return synthesized_definitions

        except Exception as e:
            logger.error(f"Failed to synthesize definition for {word}: {e}")

            return None

    async def _synthesize_pronunciation(self, word: str) -> Pronunciation:
        """Synthesize pronunciation from providers_data or generate with AI."""
        try:
            pronunciation_response = await self.ai.generate_pronunciation(word)
            return Pronunciation(
                phonetic=pronunciation_response.phonetic,
                ipa=pronunciation_response.ipa,
            )
        except Exception as e:
            logger.error(f"Failed to generate pronunciation for {word}: {e}")
            return Pronunciation(phonetic="", ipa=None)

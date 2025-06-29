"""Definition synthesis engine for combining multiple dictionary sources."""

from __future__ import annotations

from typing import Any

from ..models import DictionaryEntry, ProviderData, Word
from ..storage.mongodb import MongoDBStorage
from .openai_connector import OpenAIConnector


class DefinitionSynthesizer:
    """Synthesizes definitions from multiple providers using AI."""

    def __init__(
        self,
        openai_connector: OpenAIConnector,
        storage: MongoDBStorage,
    ) -> None:
        """Initialize the definition synthesizer.

        Args:
            openai_connector: OpenAI connector for AI generation
            storage: MongoDB storage for caching and persistence
        """
        self.openai_connector = openai_connector
        self.storage = storage

    async def synthesize_word_entry(
        self, word_text: str, provider_data: dict[str, ProviderData]
    ) -> DictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data.

        Args:
            word_text: The word to synthesize
            provider_data: Dictionary of provider definitions

        Returns:
            Complete DictionaryEntry with AI synthesis, or None if failed
        """
        if not provider_data:
            return None

        try:
            # Create word object with embedding
            word = Word(text=word_text)
            print(f"Created word object for '{word_text}'")
            
            word = await self.openai_connector.generate_word_embedding(word)
            print(f"Generated embedding for '{word_text}'")

            # Generate AI synthesis
            ai_synthesis = await self.openai_connector.generate_comprehensive_definition(
                word_text, provider_data
            )
            print(f"Generated AI synthesis for '{word_text}': {len(ai_synthesis.definitions) if ai_synthesis else 0} definitions")

            # Get pronunciation from first available provider
            pronunciation = self._extract_best_pronunciation(provider_data)
            print(f"Extracted pronunciation for '{word_text}': {pronunciation.phonetic}")

            # Create dictionary entry
            entry = DictionaryEntry(
                word=word,
                pronunciation=pronunciation,
                providers=provider_data,
            )
            print(f"Created dictionary entry for '{word_text}' with {len(provider_data)} providers")

            # Add AI synthesis as a provider
            if ai_synthesis:
                entry.add_provider_data(ai_synthesis)
                print(f"Added AI synthesis to entry for '{word_text}'")
            else:
                print(f"No AI synthesis generated for '{word_text}'")

            # Save to database
            save_result = await self.storage.save_entry(entry)
            print(f"Saved entry for '{word_text}': {save_result}")

            return entry

        except Exception as e:
            import traceback
            print(f"Error synthesizing entry for '{word_text}': {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return None

    async def regenerate_ai_synthesis(self, entry: DictionaryEntry) -> bool:
        """Regenerate AI synthesis for an existing entry.

        Args:
            entry: Existing dictionary entry to regenerate synthesis for

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get non-AI provider data
            provider_data = {
                name: data
                for name, data in entry.providers.items()
                if not data.is_synthetic
            }

            if not provider_data:
                return False

            # Generate new AI synthesis
            new_synthesis = await self.openai_connector.generate_comprehensive_definition(
                entry.word.text, provider_data
            )

            # Update entry
            entry.add_provider_data(new_synthesis)

            # Save updated entry
            await self.storage.save_entry(entry)

            return True

        except Exception as e:
            print(f"Error regenerating synthesis for '{entry.word.text}': {e}")
            return False

    async def batch_synthesize_words(
        self, words_with_providers: dict[str, dict[str, ProviderData]]
    ) -> list[DictionaryEntry]:
        """Synthesize multiple words in batch for efficiency.

        Args:
            words_with_providers: Dictionary mapping word -> provider data

        Returns:
            List of synthesized dictionary entries
        """
        entries = []

        for word_text, provider_data in words_with_providers.items():
            entry = await self.synthesize_word_entry(word_text, provider_data)
            if entry:
                entries.append(entry)

        return entries

    def _extract_best_pronunciation(self, provider_data: dict[str, ProviderData]) -> Any:
        """Extract the best pronunciation from available provider data.

        Args:
            provider_data: Dictionary of provider definitions

        Returns:
            Best available pronunciation, or default if none found
        """
        # For now, create a basic pronunciation since ProviderData doesn't contain pronunciation
        # In future, this could be enhanced to extract pronunciation from raw_metadata
        from ..models import Pronunciation

        # TODO: Extract pronunciation from provider raw_metadata if available
        # For example, from Wiktionary IPA data or Oxford pronunciation data
        
        return Pronunciation(phonetic="", ipa=None)

    async def get_cached_synthesis(self, word: str) -> DictionaryEntry | None:
        """Get cached AI synthesis for a word.

        Args:
            word: Word to look up

        Returns:
            Cached dictionary entry if available, None otherwise
        """
        return await self.storage.get_entry(word)

    async def invalidate_cache(self, word: str) -> bool:
        """Invalidate cached synthesis for a word.

        Args:
            word: Word to invalidate cache for

        Returns:
            True if successful, False otherwise
        """
        try:
            entry = await self.storage.get_entry(word)
            if entry and "ai_synthesis" in entry.providers:
                # Remove AI synthesis and save
                del entry.providers["ai_synthesis"]
                await self.storage.save_entry(entry)
                return True
            return False
        except Exception as e:
            print(f"Error invalidating cache for '{word}': {e}")
            return False
"""Word processing pipeline that orchestrates dictionary lookup and AI synthesis."""

from __future__ import annotations

import asyncio
from typing import Any

from ..config import Config
from ..connectors import DictionaryComConnector, OxfordConnector, WiktionaryConnector
from ..connectors.base import DictionaryConnector
from ..connectors.cached_connector import CachedDictionaryConnector
from ..models import DictionaryEntry, ProviderData
from ..storage.mongodb import MongoDBStorage
from .openai_connector import OpenAIConnector
from .synthesis import DefinitionSynthesizer


class WordProcessingPipeline:
    """Complete pipeline for processing words through multiple providers and AI synthesis."""

    def __init__(self, config: Config, storage: MongoDBStorage) -> None:
        """Initialize the word processing pipeline.

        Args:
            config: Configuration with API keys and settings
            storage: MongoDB storage for persistence and caching
        """
        self.config = config
        self.storage = storage

        # Initialize AI components
        self.openai_connector = OpenAIConnector(config.openai)
        self.synthesizer = DefinitionSynthesizer(self.openai_connector, storage)

        # Initialize dictionary connectors
        self.connectors: dict[str, DictionaryConnector] = {
            "wiktionary": WiktionaryConnector(rate_limit=config.rate_limits.wiktionary_rps),
            "oxford": OxfordConnector(
                app_id=config.oxford.app_id,
                api_key=config.oxford.api_key,
                rate_limit=config.rate_limits.oxford_rps,
            ),
            "dictionary_com": DictionaryComConnector(
                api_key=config.dictionary_com.authorization,
                rate_limit=config.rate_limits.dictionary_com_rps,
            ),
        }

    async def process_word(
        self, word: str, force_refresh: bool = False, use_cache: bool = True
    ) -> DictionaryEntry | None:
        """Process a single word through the complete pipeline.

        Args:
            word: Word to process
            force_refresh: Skip cache and force fresh API calls
            use_cache: Whether to use cached results (if not force_refresh)

        Returns:
            Complete DictionaryEntry with all provider data and AI synthesis
        """
        # Check if we already have a complete entry
        if not force_refresh and use_cache:
            existing_entry = await self.storage.get_entry(word)
            if existing_entry and "ai_synthesis" in existing_entry.providers:
                return existing_entry

        # Fetch definitions from all providers
        provider_data = await self._fetch_from_all_providers(word, use_cache)

        if not provider_data:
            print(f"No definitions found for '{word}' from any provider")
            return None

        # Synthesize complete entry
        entry = await self.synthesizer.synthesize_word_entry(word, provider_data)

        return entry

    async def process_word_list(
        self,
        words: list[str],
        max_concurrent: int | None = None,
        use_cache: bool = True,
        progress_callback: Any = None,
    ) -> list[DictionaryEntry]:
        """Process multiple words concurrently.

        Args:
            words: List of words to process
            max_concurrent: Maximum concurrent processing (defaults to config)
            use_cache: Whether to use cached results
            progress_callback: Optional callback for progress updates

        Returns:
            List of processed DictionaryEntry objects
        """
        if max_concurrent is None:
            max_concurrent = self.config.processing.max_concurrent_words

        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_with_semaphore(word: str, index: int) -> DictionaryEntry | None:
            async with semaphore:
                result = await self.process_word(word, use_cache=use_cache)
                if progress_callback:
                    progress_callback(index + 1, len(words), word, result is not None)
                return result

        # Process words concurrently
        tasks = [
            process_with_semaphore(word, i) for i, word in enumerate(words)
        ]

        completed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        for result in completed_results:
            if isinstance(result, DictionaryEntry):
                results.append(result)
            elif isinstance(result, Exception):
                print(f"Error processing word: {result}")

        return results

    async def _fetch_from_all_providers(
        self, word: str, use_cache: bool = True
    ) -> dict[str, ProviderData]:
        """Fetch definitions from all available providers.

        Args:
            word: Word to fetch definitions for
            use_cache: Whether to use cached responses

        Returns:
            Dictionary mapping provider name to ProviderData
        """
        provider_data = {}

        # Create tasks for all providers
        tasks = []
        for provider_name, connector in self.connectors.items():
            if use_cache and hasattr(connector, "fetch_definition_with_cache"):
                task = connector.fetch_definition_with_cache(word)
            else:
                task = connector.fetch_definition(word)
            tasks.append((provider_name, task))

        # Execute all provider calls concurrently
        results = await asyncio.gather(
            *[task for _, task in tasks], return_exceptions=True
        )

        # Collect successful results
        for (provider_name, _), result in zip(tasks, results):
            if isinstance(result, ProviderData) and result.definitions:
                provider_data[provider_name] = result
            elif isinstance(result, Exception):
                print(f"Error fetching from {provider_name}: {result}")

        return provider_data

    async def regenerate_ai_synthesis(self, word: str) -> bool:
        """Regenerate AI synthesis for a word.

        Args:
            word: Word to regenerate synthesis for

        Returns:
            True if successful, False otherwise
        """
        entry = await self.storage.get_entry(word)
        if not entry:
            return False

        return await self.synthesizer.regenerate_ai_synthesis(entry)

    def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        # This could be expanded to include cache hit rates, processing times, etc.
        return {
            "providers_configured": len(self.connectors),
            "storage_connected": self.storage._initialized,
            "ai_model": self.config.openai.model,
            "embedding_model": self.config.openai.embedding_model,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.openai_connector.close()
        
        for connector in self.connectors.values():
            if hasattr(connector, "close"):
                await connector.close()
        
        await self.storage.disconnect()


def simple_progress_callback(current: int, total: int, word: str, success: bool) -> None:
    """Simple progress callback for word processing.

    Args:
        current: Current word number
        total: Total number of words
        word: Current word being processed
        success: Whether processing was successful
    """
    status = "✓" if success else "✗"
    percentage = (current / total) * 100
    print(f"[{current:3d}/{total:3d}] ({percentage:5.1f}%) {status} {word}")
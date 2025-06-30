"""Enhanced word lookup with normalization and search fallback."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console

from ...ai.openai_connector import OpenAIConnector
from ...ai.schemas import DefinitionSynthesisResponse
from ...config import Config
from ...models import Definition, Examples, ProviderData
from ...search.core import SearchEngine
from ...storage.mongodb import MongoDBStorage
from ...utils.logging import vprint
from ...utils.normalization import generate_word_variants, normalize_word
from ...utils.pronunciation import generate_phonetic_pronunciation

console = Console()


class EnhancedWordLookup:
    """Enhanced word lookup with intelligent search fallback and AI generation."""

    def __init__(self, config: Config, storage: MongoDBStorage):
        """Initialize enhanced lookup.

        Args:
            config: Application configuration
            storage: MongoDB storage instance
        """
        self.config = config
        self.storage = storage
        self.search_engine: SearchEngine | None = None
        self.openai_connector: OpenAIConnector | None = None

    async def initialize(self) -> None:
        """Initialize search engine and AI connector."""
        from pathlib import Path

        # Initialize search engine without semantic search to avoid timeouts
        cache_dir = Path("./data/search")
        self.search_engine = SearchEngine(
            cache_dir=cache_dir,
            enable_semantic=False,  # Disable semantic search to prevent timeouts
        )
        try:
            vprint("Initializing search engine (fuzzy + exact search)...")
            await self.search_engine.initialize()
            vprint("Search engine initialized successfully")
        except Exception as e:
            vprint(f"Search engine initialization failed: {e}")
            self.search_engine = None

        # Initialize OpenAI connector
        self.openai_connector = OpenAIConnector(self.config.openai, self.storage)

    async def lookup_with_fallback(
        self, query: str, providers: list[Any] | None = None
    ) -> tuple[str | None, list[ProviderData]]:
        """Perform enhanced lookup with normalization and search fallback.

        Args:
            query: Original query word/phrase
            providers: List of provider connectors to try

        Returns:
            Tuple of (normalized_word, provider_data_list)
        """
        vprint(f"Starting enhanced lookup for: '{query}'")

        # Step 1: Try direct normalization
        normalized_query = normalize_word(query)
        vprint(f"Normalized query: '{normalized_query}'")

        # Step 2: Generate variants for fuzzy matching
        variants = generate_word_variants(query)
        vprint(f"Generated variants: {variants}")

        # Step 3: Try each variant with providers
        for variant in variants:
            vprint(f"Trying variant: '{variant}'")
            provider_data = await self._try_providers(variant, providers or [])
            if provider_data:
                vprint(f"Found definitions for variant: '{variant}'")
                return variant, provider_data

        # Step 4: Search fallback using exact -> fuzzy -> semantic order
        if self.search_engine:
            try:
                vprint("No direct matches found, trying search fallback")

                # Try exact search first, then fuzzy (semantic disabled to prevent timeouts)
                from ...search.core import SearchMethod

                search_methods = [SearchMethod.EXACT, SearchMethod.FUZZY]

                for method in search_methods:
                    vprint(f"Trying search method: {method.value}")
                    search_results = await self.search_engine.search(
                        query=normalized_query,
                        max_results=3,
                        min_score=0.6,
                        methods=[method],
                    )

                    if search_results:
                        # Try the best search result
                        best_match = search_results[0]
                        vprint(
                            f"Found match with {method.value}: '{best_match.word}' (score: {best_match.score})"
                        )

                        provider_data = await self._try_providers(
                            best_match.word, providers or []
                        )
                        if provider_data:
                            vprint(
                                f"Found definitions for search result: '{best_match.word}'"
                            )
                            return best_match.word, provider_data

                        # If this word didn't have provider data, try the next search result
                        for result in search_results[1:]:
                            vprint(
                                f"Trying alternate match: '{result.word}' (score: {result.score})"
                            )
                            provider_data = await self._try_providers(
                                result.word, providers or []
                            )
                            if provider_data:
                                vprint(
                                    f"Found definitions for alternate search result: '{result.word}'"
                                )
                                return result.word, provider_data

                        # If we found search results but no provider data, continue to next method
                        vprint(
                            f"No provider data for {method.value} results, trying next method"
                        )
                    else:
                        vprint(f"No results from {method.value} search")

            except Exception as e:
                vprint(f"Search fallback failed: {e}")

        # Step 5: AI fallback generation
        if self.openai_connector:
            vprint("No matches found in database/search, trying AI generation")
            ai_data = await self._generate_ai_fallback(query)
            if ai_data:
                vprint(f"Generated AI fallback definition for: '{query}'")
                return normalized_query, [ai_data]

        vprint(f"No definitions found for: '{query}'")
        return None, []

    async def _try_providers(
        self, word: str, providers: list[Any]
    ) -> list[ProviderData]:
        """Try fetching definitions from providers.

        Args:
            word: Word to lookup
            providers: List of provider connectors

        Returns:
            List of provider data
        """
        provider_data_list = []

        # First check if we have this word in our database
        existing_entry = await self.storage.get_entry(word)
        if existing_entry:
            vprint(f"Found existing entry for '{word}' in database")
            for provider_name, provider_data in existing_entry.providers.items():
                if provider_data.definitions:
                    provider_data_list.append(provider_data)
            if provider_data_list:
                return provider_data_list

        # Try external providers
        tasks = []
        for provider in providers:
            if hasattr(provider, "fetch_definition"):
                tasks.append(provider.fetch_definition(word))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, ProviderData) and result.definitions:
                    provider_data_list.append(result)

        return provider_data_list

    async def _generate_ai_fallback(self, query: str) -> ProviderData | None:
        """Generate AI fallback definition when no other sources are found.

        Args:
            query: Original query

        Returns:
            AI-generated provider data or None
        """
        if not self.openai_connector:
            return None

        try:
            vprint(f"Generating AI fallback definition for: '{query}'")

            # Create a system message for generating definitions
            system_message = """You are an expert lexicographer creating comprehensive dictionary entries.
Generate complete dictionary entries with definitions, word types, and example sentences."""

            user_prompt = f"""Create a comprehensive dictionary entry for "{query}".

Include:
1. Accurate definition(s) with appropriate word type (noun, verb, adjective, phrase, etc.)
2. Clear, accessible language for modern readers  
3. Proper word type classification
4. If this is a foreign phrase, include the source language context

For phrases like "en coulisses":
- Classify as "phrase" word type
- Include the original language context
- Provide clear English definition
- Show typical usage contexts

Return 1-2 definitions maximum with the most important meanings."""

            # Build request parameters
            request_params = self.openai_connector._build_request_params(
                system_message=system_message,
                user_prompt=user_prompt,
                response_schema=DefinitionSynthesisResponse,
            )

            response = await self.openai_connector.client.chat.completions.create(
                **request_params
            )

            if response.choices[0].message.content:
                try:
                    parsed_response = DefinitionSynthesisResponse.model_validate_json(
                        response.choices[0].message.content
                    )

                    # Convert AI definitions to internal format and generate examples
                    definitions = []
                    for ai_def in parsed_response.definitions:
                        # Map word type
                        word_type = self.openai_connector._map_word_type(
                            ai_def.word_type
                        )
                        if word_type:
                            definition = Definition(
                                word_type=word_type,
                                definition=ai_def.definition,
                                examples=Examples(),
                            )

                            # Generate examples for this definition
                            vprint(
                                f"Generating examples for AI fallback: {query} ({word_type.value})"
                            )
                            examples = await self.openai_connector._generate_examples_structured(
                                query, definition
                            )
                            definition.examples = examples

                            definitions.append(definition)

                    if definitions:
                        # Store phonetic pronunciation in raw_metadata for retrieval
                        phonetic = generate_phonetic_pronunciation(query)

                        return ProviderData(
                            provider_name="ai_fallback",
                            definitions=definitions,
                            is_synthetic=True,
                            raw_metadata={"phonetic_pronunciation": phonetic},
                        )

                except Exception as e:
                    vprint(f"Error parsing AI fallback response: {e}")

        except Exception as e:
            vprint(f"Error generating AI fallback: {e}")

        return None

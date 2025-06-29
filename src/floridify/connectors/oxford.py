"""Oxford Dictionary API connector."""

from __future__ import annotations

import asyncio

from typing import Any

import httpx

from ..models import Definition, Examples, GeneratedExample, ProviderData, WordType
from .base import DictionaryConnector


class OxfordConnector(DictionaryConnector):
    """Connector for Oxford Dictionary API."""

    def __init__(self, app_id: str, api_key: str, rate_limit: float = 10.0) -> None:
        """Initialize Oxford connector.

        Args:
            app_id: Oxford API application ID
            api_key: Oxford API key
            rate_limit: Requests per second (max varies by plan)
        """
        super().__init__(rate_limit=rate_limit)
        self.app_id = app_id
        self.api_key = api_key
        self.base_url = "https://od-api.oxforddictionaries.com/api/v2"
        self.session = httpx.AsyncClient(
            headers={"app_id": self.app_id, "app_key": self.api_key, "Accept": "application/json"},
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        return "oxford"

    async def fetch_definition(self, word: str) -> ProviderData | None:
        """Fetch definition data for a word from Oxford API.

        Args:
            word: The word to look up

        Returns:
            ProviderData if successful, None if not found or error
        """
        await self._enforce_rate_limit()

        try:
            # Fetch both entries and pronunciation if available
            url = f"{self.base_url}/entries/en-us/{word.lower()}"

            response = await self.session.get(url)

            if response.status_code == 404:
                return None  # Word not found
            elif response.status_code == 429:
                # Rate limited - wait and retry once
                await asyncio.sleep(1)
                response = await self.session.get(url)

            response.raise_for_status()
            data = response.json()

            return self._parse_oxford_response(word, data)

        except Exception as e:
            print(f"Error fetching {word} from Oxford: {e}")
            return None

    def _parse_oxford_response(self, word: str, data: dict[str, Any]) -> ProviderData:
        """Parse Oxford API response.

        Args:
            word: The word being looked up
            data: Raw API response

        Returns:
            Parsed ProviderData
        """
        definitions = []

        try:
            results = data.get("results", [])
            if not results:
                return ProviderData(provider_name=self.provider_name)

            for result in results:
                lexical_entries = result.get("lexicalEntries", [])

                for lexical_entry in lexical_entries:
                    # Map Oxford part of speech to our enum
                    oxford_pos = lexical_entry.get("lexicalCategory", {}).get("id", "").lower()
                    word_type = self._map_oxford_pos_to_word_type(oxford_pos)

                    if not word_type:
                        continue

                    entries = lexical_entry.get("entries", [])

                    for entry in entries:
                        senses = entry.get("senses", [])

                        for sense in senses:
                            definition_texts = sense.get("definitions", [])

                            for def_text in definition_texts:
                                # Extract examples if available
                                examples = Examples()

                                oxford_examples = sense.get("examples", [])
                                for example in oxford_examples:
                                    example_text = example.get("text", "")
                                    if example_text:
                                        examples.generated.append(
                                            GeneratedExample(
                                                sentence=example_text,
                                                regenerable=False,  # Oxford examples are real
                                            )
                                        )

                                definitions.append(
                                    Definition(
                                        word_type=word_type,
                                        definition=def_text,
                                        examples=examples,
                                        raw_metadata=sense,  # Store full sense data
                                    )
                                )

        except Exception as e:
            print(f"Error parsing Oxford response for {word}: {e}")

        return ProviderData(
            provider_name=self.provider_name, definitions=definitions, raw_metadata=data
        )

    def _map_oxford_pos_to_word_type(self, oxford_pos: str) -> WordType | None:
        """Map Oxford part of speech to our WordType enum.

        Args:
            oxford_pos: Oxford API part of speech identifier

        Returns:
            Corresponding WordType or None if not recognized
        """
        mapping = {
            "noun": WordType.NOUN,
            "verb": WordType.VERB,
            "adjective": WordType.ADJECTIVE,
            "adverb": WordType.ADVERB,
            "pronoun": WordType.PRONOUN,
            "preposition": WordType.PREPOSITION,
            "conjunction": WordType.CONJUNCTION,
            "interjection": WordType.INTERJECTION,
            "exclamation": WordType.INTERJECTION,
        }

        return mapping.get(oxford_pos)

    async def close(self) -> None:
        """Close the HTTP session."""
        await self.session.aclose()

"""OpenAI API connector for AI comprehension and embeddings."""

from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from ..config import OpenAIConfig
from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    ProviderData,
    Word,
    WordType,
)
from ..prompts import PromptLoader
from ..prompts.formatters import format_provider_context, format_template_variables


class OpenAIConnector:
    """Connector for OpenAI API to generate definitions, examples, and embeddings."""

    def __init__(self, config: OpenAIConfig, prompt_loader: PromptLoader | None = None) -> None:
        """Initialize OpenAI connector.

        Args:
            config: OpenAI configuration with API key and model settings
            prompt_loader: Optional prompt loader (creates default if None)
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        self._rate_limiter = asyncio.Semaphore(5)  # Limit concurrent requests

        # Initialize prompt loader
        self.prompt_loader = prompt_loader or PromptLoader()

    async def generate_comprehensive_definition(
        self, word: str, provider_definitions: dict[str, ProviderData]
    ) -> ProviderData:
        """Generate AI-synthesized definition from multiple provider data.

        Args:
            word: The word to generate definition for
            provider_definitions: Dictionary of provider data to synthesize

        Returns:
            ProviderData with AI-synthesized definitions and examples
        """
        async with self._rate_limiter:
            # Prepare context from all providers
            context = self._prepare_synthesis_context(word, provider_definitions)

            # Generate synthesized definitions
            definitions = await self._generate_definitions(word, context)

            # Generate modern examples for each definition
            for definition in definitions:
                examples = await self._generate_examples(word, definition)
                definition.examples = examples

            return ProviderData(
                provider_name="ai_synthesis",
                definitions=definitions,
                is_synthetic=True,
            )

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate text embedding using OpenAI's embedding model.

        Args:
            text: Text to generate embedding for

        Returns:
            Vector embedding as list of floats
        """
        async with self._rate_limiter:
            try:
                response = await self.client.embeddings.create(
                    model=self.config.embedding_model,
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"Error generating embedding for '{text}': {e}")
                return []

    async def generate_word_embedding(self, word: Word) -> Word:
        """Generate embedding for a word and update the word object.

        Args:
            word: Word object to generate embedding for

        Returns:
            Updated Word object with embedding
        """
        embedding = await self.generate_embedding(word.text)
        if embedding:
            word.embedding[self.config.embedding_model] = embedding
        return word

    def _prepare_synthesis_context(
        self, word: str, provider_definitions: dict[str, ProviderData]
    ) -> str:
        """Prepare context string from all provider definitions.

        Args:
            word: The word being defined
            provider_definitions: Dictionary of provider data

        Returns:
            Formatted context string for AI synthesis
        """
        return format_provider_context(word, provider_definitions)

    async def _generate_definitions(self, word: str, context: str) -> list[Definition]:
        """Generate AI definitions using the synthesis prompt template.

        Args:
            word: The word to define
            context: Context from provider definitions

        Returns:
            List of AI-generated definitions
        """
        try:
            # Load synthesis template
            template = self.prompt_loader.load_template("synthesis")

            # Prepare template variables
            variables = format_template_variables(word=word, context=context)

            # Render template
            system_message, user_prompt = template.render(variables)

            # Get AI settings from template
            ai_settings = template.get_ai_settings()

            # Build request parameters
            model = ai_settings.get("model", self.config.model)
            request_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt},
                ],
            }

            # Only add temperature for non-o3 models
            if not model.startswith("o3"):
                request_params["temperature"] = ai_settings.get("temperature", 0.3)

            # Add max_tokens if specified
            if "max_tokens" in ai_settings:
                request_params["max_tokens"] = ai_settings["max_tokens"]

            response = await self.client.chat.completions.create(**request_params)

            content = response.choices[0].message.content
            if not content:
                print(f"Warning: Empty response from AI for word '{word}'")
                return []

            print(f"AI response for '{word}': {content}")
            parsed_defs = self._parse_ai_definitions(content)
            print(f"Parsed {len(parsed_defs)} definitions from AI response")
            return parsed_defs

        except Exception as e:
            print(f"Error generating definitions for '{word}': {e}")
            return []

    async def _generate_examples(self, word: str, definition: Definition) -> Examples:
        """Generate modern usage examples for a definition using prompt template.

        Args:
            word: The word to generate examples for
            definition: The definition to create examples for

        Returns:
            Examples object with generated sentences
        """
        try:
            # Load examples template
            template = self.prompt_loader.load_template("examples")

            # Prepare template variables
            variables = format_template_variables(
                word=word,
                word_type=definition.word_type.value,
                definition=definition.definition,
                num_examples=2,  # Default number of examples
            )

            # Render template
            system_message, user_prompt = template.render(variables)

            # Get AI settings from template
            ai_settings = template.get_ai_settings()

            # Build request parameters
            model = ai_settings.get("model", self.config.model)
            request_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt},
                ],
            }

            # Only add temperature for non-o3 models
            if not model.startswith("o3"):
                request_params["temperature"] = ai_settings.get("temperature", 0.7)

            # Add max_tokens if specified
            if "max_tokens" in ai_settings:
                request_params["max_tokens"] = ai_settings["max_tokens"]

            response = await self.client.chat.completions.create(**request_params)

            content = response.choices[0].message.content
            if not content:
                return Examples()

            examples = Examples()
            sentences = self._parse_example_sentences(content)

            for sentence in sentences:
                examples.generated.append(GeneratedExample(sentence=sentence, regenerable=True))

            return examples

        except Exception as e:
            print(f"Error generating examples for '{word}': {e}")
            return Examples()

    def _parse_ai_definitions(self, content: str) -> list[Definition]:
        """Parse AI response into Definition objects.

        Args:
            content: Raw AI response content

        Returns:
            List of parsed Definition objects
        """
        definitions = []
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue

            try:
                # Parse format: "PART_OF_SPEECH: definition"
                pos_str, definition_text = line.split(":", 1)
                pos_str = pos_str.strip().upper()
                definition_text = definition_text.strip()

                # Map part of speech to WordType
                word_type = self._map_pos_to_word_type(pos_str)
                if word_type and definition_text:
                    definitions.append(
                        Definition(
                            word_type=word_type,
                            definition=definition_text,
                            examples=Examples(),  # Will be filled separately
                        )
                    )
            except ValueError:
                continue

        return definitions

    def _parse_example_sentences(self, content: str) -> list[str]:
        """Parse AI response into example sentences.

        Args:
            content: Raw AI response content

        Returns:
            List of example sentences
        """
        sentences = []
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            # Look for numbered format: "1. sentence" or "• sentence"
            if line and (line[0].isdigit() or line.startswith("•") or line.startswith("-")):
                # Remove numbering and clean up
                if "." in line:
                    sentence = line.split(".", 1)[1].strip()
                else:
                    sentence = line[1:].strip()

                if sentence:
                    sentences.append(sentence)

        return sentences

    def _map_pos_to_word_type(self, pos_str: str) -> WordType | None:
        """Map part of speech string to WordType enum.

        Args:
            pos_str: Part of speech string from AI response

        Returns:
            Corresponding WordType or None if not recognized
        """
        mapping = {
            "NOUN": WordType.NOUN,
            "VERB": WordType.VERB,
            "ADJECTIVE": WordType.ADJECTIVE,
            "ADVERB": WordType.ADVERB,
            "PRONOUN": WordType.PRONOUN,
            "PREPOSITION": WordType.PREPOSITION,
            "CONJUNCTION": WordType.CONJUNCTION,
            "INTERJECTION": WordType.INTERJECTION,
        }

        return mapping.get(pos_str)

    async def close(self) -> None:
        """Close the OpenAI client connection."""
        await self.client.close()

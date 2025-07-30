"""Apple Dictionary connector using macOS Dictionary Services via PyObjC."""

from __future__ import annotations

import platform
import re
from typing import Any

from beanie import PydanticObjectId

from ..constants import Language
from ..core.state_tracker import Stages, StateTracker
from ..models import Definition, Etymology, Example, Pronunciation, ProviderData, Word
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
from .base import DictionaryConnector

logger = get_logger(__name__)


class AppleDictionaryError(Exception):
    """Base exception for Apple Dictionary Service errors."""

    pass


class PlatformError(AppleDictionaryError):
    """Raised when platform doesn't support Dictionary Services."""

    pass


class ImportError(AppleDictionaryError):
    """Raised when required PyObjC modules cannot be imported."""

    pass


class AppleDictionaryConnector(DictionaryConnector):
    """Apple Dictionary connector using macOS Dictionary Services."""

    def __init__(self, rate_limit: float = 10.0) -> None:
        """Initialize Apple Dictionary connector.

        Args:
            rate_limit: Maximum requests per second (default 10.0 for local API)
        """
        super().__init__(rate_limit=rate_limit)
        self._dictionary_service = None
        self._platform_compatible = self._check_platform_compatibility()
        self._initialize_service()

    @property
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        return "apple_dictionary"

    def _check_platform_compatibility(self) -> bool:
        """Check if running on macOS (Darwin)."""
        if platform.system() != "Darwin":
            logger.warning(f"Apple Dictionary Services not available on {platform.system()}")
            return False
        return True

    def _initialize_service(self) -> None:
        """Initialize macOS Dictionary Services."""
        if not self._platform_compatible:
            self._dictionary_service = None
            return

        try:
            from CoreServices import DCSCopyTextDefinition  # type: ignore[import-not-found]

            self._dictionary_service = DCSCopyTextDefinition
            logger.info("Apple Dictionary Services initialized successfully")
        except ImportError as e:
            logger.warning(
                f"Failed to import CoreServices.DictionaryServices: {e}. "
                "Install PyObjC with: pip install pyobjc-framework-CoreServices"
            )
            self._dictionary_service = None

    def _is_available(self) -> bool:
        """Check if Dictionary Services is available."""
        return self._platform_compatible and self._dictionary_service is not None

    def _lookup_definition(self, word: str) -> str | None:
        """Look up definition using macOS Dictionary Services.

        Args:
            word: The word to look up

        Returns:
            Definition text or None if not found
        """
        if not self._is_available():
            return None

        try:
            if not self._dictionary_service:
                return None

            # Create CFRange for the entire word
            word_range = (0, len(word))

            # Call Dictionary Services
            definition = self._dictionary_service(None, word, word_range)
            return str(definition) if definition else None
        except Exception as e:
            logger.error(f"Dictionary lookup failed for '{word}': {e}")
            return None

    def _clean_definition_text(self, text: str) -> str:
        """Clean raw definition text from Apple Dictionary.

        Args:
            text: Raw definition text

        Returns:
            Cleaned definition text
        """
        # Remove pronunciation markers like |ˈæpəl|
        text = re.sub(r"\|[^|]+\|", "", text)

        # Remove extra whitespace and normalize
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    def _extract_main_definition(self, text: str) -> str:
        """Extract the main definition from a text block.

        Args:
            text: Text block that may contain definition

        Returns:
            Main definition text
        """
        # Look for text after word type indicators
        pattern = r"(?:noun|verb|adjective|adverb|preposition|conjunction|interjection|pronoun|determiner)\s+(.*?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: return the whole text if no pattern found
        return text.strip()

    def _extract_examples(self, definition_text: str) -> list[str]:
        """Extract examples from definition text.

        Args:
            definition_text: Definition text that may contain examples

        Returns:
            List of example strings
        """
        examples = []

        # Look for quoted examples or examples in specific formats
        example_patterns = [
            r'"([^"]+)"',  # Quoted examples
            r":\s*([A-Z][^.!?]*[.!?])",  # Examples after colons
            r"e\.g\.(?:,)?\s*([^.!?]*[.!?])",  # Examples after "e.g."
        ]

        for pattern in example_patterns:
            matches = re.findall(pattern, definition_text)
            for match in matches:
                if len(match.strip()) > 5:  # Filter out very short matches
                    examples.append(match.strip())

        return examples

    def _remove_examples_from_definition(self, definition_text: str) -> str:
        """Remove example text from definition to get clean definition.

        Args:
            definition_text: Definition text with examples

        Returns:
            Clean definition text without examples
        """
        # Remove quoted examples
        text = re.sub(r'"[^"]*"', "", definition_text)

        # Remove examples after colons that look like sentences
        text = re.sub(r":\s*[A-Z][^.!?]*[.!?]", ".", text)

        # Remove "e.g." sections
        text = re.sub(r"e\.g\.(?:,)?\s*[^.!?]*[.!?]", "", text, flags=re.IGNORECASE)

        # Clean up extra whitespace and punctuation
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s*,\s*\.$", ".", text)  # Fix trailing comma-period
        text = text.strip()

        return text

    def _normalize_part_of_speech(self, part_of_speech: str) -> str:
        """Normalize part of speech to standard format.

        Args:
            part_of_speech: Raw part of speech from parsing

        Returns:
            Normalized part of speech
        """
        part_of_speech = part_of_speech.lower().strip()

        # Normalize common variations
        normalizations = {
            "n": "noun",
            "v": "verb",
            "adj": "adjective",
            "adv": "adverb",
            "prep": "preposition",
            "conj": "conjunction",
            "interj": "interjection",
            "pron": "pronoun",
            "det": "determiner",
        }

        return normalizations.get(part_of_speech, part_of_speech)

    async def fetch_definition(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definition data for a word from Apple Dictionary.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for progress updates

        Returns:
            ProviderData if successful, None if not found or error
        """
        if not word or not isinstance(word, str):
            return None

        # Update state tracker
        if state_tracker:
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

        # Check if service is available
        if not self._is_available():
            error_msg = (
                "Apple Dictionary Services not available. "
                f"Platform: {platform.system()}, "
                f"Service initialized: {self._dictionary_service is not None}"
            )
            if state_tracker:
                await state_tracker.update_error(error_msg)
            logger.warning(error_msg)
            return None

        try:
            # Get or create Word document
            storage = await get_storage()
            word_obj = await storage.get_word(word)
            if not word_obj:
                word_obj = Word(
                    text=word,
                    normalized=word.lower(),
                    language=Language.ENGLISH,
                )
                await word_obj.save()

            # Enforce rate limiting
            await self._enforce_rate_limit()

            # Update progress
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_HTTP_CONNECTING)

            # Look up the word
            raw_definition = self._lookup_definition(word.strip())

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_HTTP_PARSING)

            if not raw_definition:
                logger.debug(f"No definition found for '{word}' in Apple Dictionary")
                if state_tracker:
                    await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)
                return None

            # For the lookup method, we'll return the raw data to be processed later
            # The actual parsing and Definition creation should happen in extract_definitions

            # Create raw data for base class processing
            raw_data = {
                "platform": platform.system(),
                "platform_version": platform.mac_ver()[0]
                if platform.system() == "Darwin"
                else None,
                "raw_definition": raw_definition,
                "word_processed": word,
                "definitions_count": 1 if raw_definition else 0,
            }

            # Use base class method to normalize and save
            provider_data = await self._normalize_response(raw_data, word_obj)

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

            logger.info(f"Successfully fetched definition for '{word}' from Apple Dictionary")
            return provider_data

        except Exception as e:
            error_msg = f"Apple Dictionary lookup failed for '{word}': {str(e)}"
            logger.error(error_msg)
            if state_tracker:
                await state_tracker.update_error(error_msg)
            return None

    def get_service_info(self) -> dict[str, Any]:
        """Get information about the Apple Dictionary service.

        Returns:
            Dictionary with service information
        """
        return {
            "provider_name": self.provider_name,
            "platform": platform.system(),
            "platform_version": platform.mac_ver()[0] if platform.system() == "Darwin" else None,
            "is_available": self._is_available(),
            "service_initialized": self._dictionary_service is not None,
            "rate_limit": self.rate_limit,
        }

    async def extract_pronunciation(
        self, raw_data: dict[str, Any], word_id: PydanticObjectId
    ) -> Pronunciation | None:
        """Extract pronunciation from Apple Dictionary data.

        Args:
            raw_data: Raw response containing definition text

        Returns:
            Pronunciation if found, None otherwise
        """
        if "raw_definition" not in raw_data:
            return None

        # Apple Dictionary includes IPA in format |ˈæpəl|
        ipa_match = re.search(r"\|([^|]+)\|", raw_data["raw_definition"])
        if ipa_match:
            ipa = ipa_match.group(1)
            # Convert IPA to simple phonetic
            phonetic = self._ipa_to_phonetic(ipa)

            return Pronunciation(
                word_id=word_id,
                phonetic=phonetic,
                ipa=ipa,  # Apple typically provides American pronunciation
                syllables=[],
                stress_pattern=None,
            )

        return None

    async def extract_definitions(
        self, raw_data: dict[str, Any], word_id: PydanticObjectId
    ) -> list[Definition]:
        """Extract definitions from Apple Dictionary data.

        Args:
            raw_data: Raw response containing definition text
            word_id: ID of the word these definitions belong to

        Returns:
            List of Definition objects
        """
        if "raw_definition" not in raw_data:
            return []

        raw_definition = raw_data["raw_definition"]

        # Parse raw definition text into structured definitions
        # Since _parse_apple_definition doesn't exist, we'll do simple parsing
        parsed_defs: list[Definition] = []

        # Extract basic information from raw definition
        # Default to noun if can't determine part of speech
        try:
            part_of_speech = self._normalize_part_of_speech(raw_definition)
        except Exception:
            part_of_speech = "noun"  # Default fallback

        definition_text = self._clean_definition_text(raw_definition)
        # If definition is empty, try extracting main definition
        if not definition_text:
            definition_text = self._extract_main_definition(raw_definition)
        examples = self._extract_examples(definition_text)

        if definition_text:
            # Create definition (meaning_cluster will be added by AI synthesis)
            definition = Definition(
                word_id=word_id,
                part_of_speech=part_of_speech,
                text=definition_text,
                sense_number="1",
                synonyms=[],  # Apple Dictionary doesn't provide structured synonyms
                antonyms=[],
                example_ids=[],
                frequency_band=None,  # Will be enriched later
            )

            # Save definition to get ID
            await definition.save()
            assert definition.id is not None  # After save(), id is guaranteed to be not None

            # Create and save examples
            for example_text in examples:
                example = Example(
                    definition_id=definition.id,
                    text=example_text,
                    type="generated",  # Apple examples are typically generated
                )
                await example.save()
                assert example.id is not None  # After save(), id is guaranteed to be not None
                definition.example_ids.append(example.id)

            # Update definition with example IDs if any were added
            if definition.example_ids:
                await definition.save()

            parsed_defs.append(definition)

        return parsed_defs

    async def extract_etymology(self, raw_data: dict[str, Any]) -> Etymology | None:
        """Extract etymology from Apple Dictionary data.

        Args:
            raw_data: Raw response containing definition text

        Returns:
            Etymology if found, None otherwise
        """
        # Apple Dictionary sometimes includes etymology in the definition
        # Look for patterns like "ORIGIN" or "Etymology:"
        if "raw_definition" not in raw_data:
            return None

        text = raw_data["raw_definition"]

        # Common etymology patterns
        etym_match = re.search(
            r"(?:ORIGIN|Etymology:?|from)\s+(.+?)(?=\n|$)", text, re.IGNORECASE | re.MULTILINE
        )

        if etym_match:
            etym_text = etym_match.group(1).strip()
            return Etymology(
                text=etym_text,
                origin_language=None,  # Could parse from text
                root_words=[],
            )

        return None

    def _ipa_to_phonetic(self, ipa: str) -> str:
        """Convert IPA notation to simple phonetic spelling."""
        # Basic IPA to phonetic mapping
        mappings = {
            "æ": "a",
            "ə": "uh",
            "ɪ": "i",
            "ʊ": "u",
            "ɛ": "e",
            "ɔ": "aw",
            "ɑ": "ah",
            "ʌ": "u",
            "ˈ": "",  # Remove stress marks
            "ˌ": "",
        }

        phonetic = ipa
        for ipa_char, simple in mappings.items():
            phonetic = phonetic.replace(ipa_char, simple)

        return phonetic

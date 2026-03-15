"""Apple Dictionary connector using macOS Dictionary Services via PyObjC."""

from __future__ import annotations

import platform
import re
import traceback
from typing import Any

from ....core.state_tracker import Stages, StateTracker
from ....models.dictionary import DictionaryProvider
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector
from ..models import DictionaryProviderEntry

logger = get_logger(__name__)

try:
    from CoreServices import (
        DCSCopyTextDefinition as CORE_SERVICES_COPY_TEXT_DEFINITION,  # type: ignore[import-untyped]
    )
except ImportError:
    CORE_SERVICES_COPY_TEXT_DEFINITION = None


# Part-of-speech labels recognized by Apple Dictionary
_POS_LABELS = (
    "noun",
    "verb",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "interjection",
    "pronoun",
    "determiner",
    "exclamation",
    "abbreviation",
    "prefix",
    "suffix",
    "combining form",
    "modal verb",
    "auxiliary verb",
    "phrasal verb",
)

_POS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _POS_LABELS) + r")\b",
    re.IGNORECASE,
)


class AppleDictionaryError(Exception):
    """Base exception for Apple Dictionary Service errors."""


class PlatformError(AppleDictionaryError):
    """Raised when platform doesn't support Dictionary Services."""


class DependencyImportError(AppleDictionaryError):
    """Raised when required PyObjC modules cannot be imported."""


class AppleDictionaryConnector(DictionaryConnector):
    """Apple Dictionary connector using macOS Dictionary Services."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        """Initialize Apple Dictionary connector.

        Args:
            config: Connector configuration

        """
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.LOCAL.value)
        super().__init__(provider=DictionaryProvider.APPLE_DICTIONARY, config=config)
        self._dictionary_service = None
        self._platform_compatible = self._check_platform_compatibility()
        self._initialize_service()

    def _check_platform_compatibility(self) -> bool:
        """Check if running on macOS (Darwin).

        Raises:
            ServiceUnavailableException: If not running on macOS
        """
        if platform.system() != "Darwin":
            from ....api.core.exceptions import ServiceUnavailableException

            raise ServiceUnavailableException(
                "Apple Dictionary", f"Only available on macOS (current: {platform.system()})"
            )
        return True

    def _initialize_service(self) -> None:
        """Initialize macOS Dictionary Services."""
        if not self._platform_compatible:
            self._dictionary_service = None
            return

        if CORE_SERVICES_COPY_TEXT_DEFINITION is None:
            from ....api.core.exceptions import ServiceUnavailableException

            raise ServiceUnavailableException(
                "Apple Dictionary",
                "CoreServices.DictionaryServices not available. "
                "Install PyObjC with: pip install pyobjc-framework-CoreServices",
            )

        self._dictionary_service = CORE_SERVICES_COPY_TEXT_DEFINITION
        logger.info("Apple Dictionary Services initialized successfully")

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
        if not self._is_available() or not self._dictionary_service:
            from ....api.core.exceptions import ProviderFetchError

            raise ProviderFetchError("apple", "Dictionary service not available")

        try:
            # Create CFRange for the entire word
            word_range = (0, len(word))

            # Call Dictionary Services
            definition = self._dictionary_service(None, word, word_range)
            return str(definition) if definition else None
        except Exception as e:
            from ....api.core.exceptions import ProviderFetchError

            logger.error(f"Dictionary lookup failed for '{word}': {e}")
            raise ProviderFetchError("apple", str(e)) from e

    # ------------------------------------------------------------------
    # Text cleaning helpers
    # ------------------------------------------------------------------

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

        Apple Dictionary uses two example formats:
          - Quoted: "Hello below!" he cried
          - Inline after colon: definition text: example text.
        """
        examples: list[str] = []

        # 1. Quoted examples: "some example text"
        for m in re.finditer(r'\u201c([^\u201d]+)\u201d|"([^"]+)"', definition_text):
            ex = (m.group(1) or m.group(2)).strip()
            if len(ex) > 5:
                examples.append(ex)

        # 2. Inline examples after colon (the primary Apple Dictionary format)
        #    e.g. "used as a greeting: hello there, Katie!."
        #    Take everything after the last colon as an example
        if not examples:
            colon_match = re.search(r":\s*(.+?)\.?\s*$", definition_text)
            if colon_match:
                ex = colon_match.group(1).strip().rstrip(".")
                if len(ex) > 5:
                    examples.append(ex)

        # 3. e.g. examples
        for m in re.finditer(r"e\.g\.(?:,)?\s*([^.!?]*[.!?])", definition_text, re.IGNORECASE):
            ex = m.group(1).strip()
            if len(ex) > 5:
                examples.append(ex)

        return examples

    def _remove_examples_from_definition(self, definition_text: str) -> str:
        """Remove example text from definition to get clean definition text.

        Strips inline examples (after colon) and quoted examples, then
        cleans up trailing punctuation artifacts.
        """
        text = definition_text

        # Remove quoted examples (curly and straight quotes)
        text = re.sub(r'\u201c[^\u201d]*\u201d', "", text)
        text = re.sub(r'"[^"]*"', "", text)

        # Remove inline example after colon (takes everything after last colon)
        text = re.sub(r":\s*[^:]+$", "", text)

        # Remove "e.g." sections
        text = re.sub(r"e\.g\.(?:,)?\s*[^.!?]*[.!?]", "", text, flags=re.IGNORECASE)

        # Clean up punctuation and whitespace
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[.,;:]+\s*$", "", text)  # Strip trailing punctuation
        text = text.strip()

        return text

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

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _split_block_into_senses(
        self, block: str, pos: str
    ) -> list[dict[str, Any]]:
        """Split a POS block into individual sense definitions.

        Handles numbered definitions (1, 2, 3...) and bullet sub-senses (•).
        Each becomes a separate definition entry.
        """
        senses: list[dict[str, Any]] = []

        # First try to split by numbered definitions (1, 2, 3 ...)
        numbered = re.split(r"\b(\d+)\s+", block)
        sub_defs: list[str] = []
        if len(numbered) > 2:
            idx = 1
            while idx + 1 < len(numbered):
                sub_defs.append(numbered[idx + 1].strip())
                idx += 2
        else:
            sub_defs.append(block)

        sense_num = 0
        for def_text in sub_defs:
            if not def_text:
                continue

            # Split on bullet points (•) to separate sub-senses
            # Apple Dictionary uses • to delimit distinct sub-meanings
            bullet_parts = re.split(r"\s*•\s*", def_text)

            for part in bullet_parts:
                part = part.strip()
                if not part:
                    continue

                sense_num += 1
                examples = self._extract_examples(part)
                clean_text = self._remove_examples_from_definition(part)
                clean_text = self._clean_definition_text(clean_text)

                if clean_text:
                    senses.append(
                        {
                            "part_of_speech": pos,
                            "text": clean_text,
                            "sense_number": str(sense_num),
                            "examples": examples,
                            "synonyms": [],
                            "antonyms": [],
                        }
                    )

        return senses

    def _parse_definition_text(
        self, raw_text: str
    ) -> tuple[list[dict[str, Any]], str | None, str | None]:
        """Parse raw definition text into structured data.

        Returns:
            Tuple of (definitions_list, pronunciation_ipa, etymology_text)
        """
        pronunciation: str | None = None
        etymology: str | None = None

        # 1. Extract pronunciation (|...|)
        ipa_match = re.search(r"\|([^|]+)\|", raw_text)
        if ipa_match:
            pronunciation = ipa_match.group(1)

        # 2. Extract ORIGIN / Etymology section
        etym_match = re.search(
            r"(?:ORIGIN|Etymology:?)\s+(.+?)(?=\n(?:DERIVATIVES|PHRASES|$)|\Z)",
            raw_text,
            re.IGNORECASE | re.DOTALL,
        )
        if etym_match:
            etymology = re.sub(r"\s+", " ", etym_match.group(1)).strip()

        # 3. Remove special sections from the text before splitting by POS
        working_text = raw_text

        # Remove pronunciation markers
        working_text = re.sub(r"\|[^|]+\|", "", working_text)

        # Remove ORIGIN/DERIVATIVES/PHRASES sections for definition extraction
        working_text = re.sub(
            r"(?:ORIGIN|DERIVATIVES|PHRASES)\s+.*",
            "",
            working_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        working_text = re.sub(r"\s+", " ", working_text).strip()

        # 4. Split by POS headers
        definitions: list[dict[str, Any]] = []

        # Find all POS occurrences and their positions
        pos_matches = list(_POS_PATTERN.finditer(working_text))

        if pos_matches:
            for i, pos_match in enumerate(pos_matches):
                pos = pos_match.group(1).lower()
                start = pos_match.end()
                end = pos_matches[i + 1].start() if i + 1 < len(pos_matches) else len(working_text)
                block = working_text[start:end].strip()

                if not block:
                    continue

                definitions.extend(self._split_block_into_senses(block, pos))
        else:
            # No POS found — treat the entire text as a single definition
            definitions.extend(self._split_block_into_senses(working_text, "unknown"))

        return definitions, pronunciation, etymology

    # ------------------------------------------------------------------
    # Provider fetch
    # ------------------------------------------------------------------

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        """Fetch definition data for a word from Apple Dictionary.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for progress updates

        Returns:
            DictionaryProviderEntry if successful, None if not found or error

        """
        if not word:
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

            # Parse the raw text into structured data
            definitions, pronunciation_ipa, etymology = self._parse_definition_text(raw_definition)

            # Build pronunciation string (IPA preferred, phonetic fallback)
            pronunciation_str: str | None = None
            if pronunciation_ipa:
                pronunciation_str = pronunciation_ipa

            raw_data: dict[str, Any] = {
                "platform": platform.system(),
                "platform_version": (
                    platform.mac_ver()[0] if platform.system() == "Darwin" else None
                ),
                "raw_definition": raw_definition,
                "word_processed": word,
                "definitions_count": len(definitions),
            }

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

            logger.info(
                f"Successfully fetched definition for '{word}' from Apple Dictionary",
            )

            return DictionaryProviderEntry(
                word=word,
                provider=self.provider.value,
                definitions=definitions,
                pronunciation=pronunciation_str,
                etymology=etymology,
                raw_data=raw_data,
            )

        except Exception as e:
            error_msg = f"Apple Dictionary lookup failed for '{word}': {e!s}"
            logger.error(error_msg)
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            if state_tracker:
                await state_tracker.update_error(error_msg)
            return None

    def get_service_info(self) -> dict[str, Any]:
        """Get information about the Apple Dictionary service.

        Returns:
            Dictionary with service information

        """
        return {
            "provider_name": self.provider.value,
            "platform": platform.system(),
            "platform_version": platform.mac_ver()[0] if platform.system() == "Darwin" else None,
            "is_available": self._is_available(),
            "service_initialized": self._dictionary_service is not None,
            "rate_limit_config": self.config.rate_limit_config.model_dump()
            if self.config.rate_limit_config
            else None,
        }

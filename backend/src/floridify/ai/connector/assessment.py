"""Connector mixin for assessment: CEFR, frequency, register, domain, grammar, collocations, etc."""

from ...utils.logging import get_logger
from ..models import (
    CEFRLevelResponse,
    CollocationResponse,
    DomainIdentificationResponse,
    FrequencyBandResponse,
    GrammarPatternResponse,
    RegionalVariantResponse,
    RegisterClassificationResponse,
    UsageNoteResponse,
)

logger = get_logger(__name__)


class AssessmentMixin:
    """Mixin providing assessment methods for AIConnector."""

    async def assess_frequency_band(
        self,
        word: str,
        definition: str,
    ) -> FrequencyBandResponse:
        """Assess frequency band (1-5) for a word.

        Args:
            word: The word
            definition: The definition for context

        Returns:
            FrequencyBandResponse with band assessment

        """
        prompt = self.prompt_manager.render(
            "assess/frequency",
            word=word,
            definition=definition,
        )

        result = await self._make_structured_request(
            prompt,
            FrequencyBandResponse,
            task_name="assess_frequency",
        )
        logger.info(f"Assessed frequency band {result.band} for '{word}'")
        return result

    async def classify_register(
        self,
        definition: str,
    ) -> RegisterClassificationResponse:
        """Classify register (formal, informal, etc.) of a definition.

        Args:
            definition: The definition text

        Returns:
            RegisterClassificationResponse with classification

        """
        prompt = self.prompt_manager.render("assess/register", definition=definition)

        result = await self._make_structured_request(
            prompt,
            RegisterClassificationResponse,
            task_name="classify_register",
        )
        logger.info(f"Classified register as '{result.language_register}'")
        return result

    async def assess_domain(
        self,
        definition: str,
    ) -> DomainIdentificationResponse:
        """Identify domain/field of a definition.

        Args:
            definition: The definition text

        Returns:
            DomainIdentificationResponse with domain

        """
        prompt = self.prompt_manager.render("assess/domain", definition=definition)

        result = await self._make_structured_request(
            prompt,
            DomainIdentificationResponse,
            task_name="classify_domain",
        )
        logger.info(f"Identified domain as '{result.domain}'")
        return result

    async def assess_cefr_level(
        self,
        word: str,
        definition: str,
    ) -> CEFRLevelResponse:
        """Assess CEFR level (A1-C2) for a word.

        Args:
            word: The word
            definition: The definition for context

        Returns:
            CEFRLevelResponse with level assessment

        """
        prompt = self.prompt_manager.render(
            "assess/cefr",
            word=word,
            definition=definition,
        )

        result = await self._make_structured_request(
            prompt,
            CEFRLevelResponse,
            task_name="assess_cefr_level",
        )
        logger.info(f"Assessed CEFR level {result.level} for '{word}'")
        return result

    async def assess_grammar_patterns(
        self,
        definition: str,
        part_of_speech: str,
    ) -> GrammarPatternResponse:
        """Extract grammar patterns from a definition.

        Args:
            definition: The definition text
            part_of_speech: Part of speech

        Returns:
            GrammarPatternResponse with patterns

        """
        prompt = self.prompt_manager.render(
            "assess/grammar_patterns",
            definition=definition,
            part_of_speech=part_of_speech,
        )

        result = await self._make_structured_request(
            prompt,
            GrammarPatternResponse,
            task_name="identify_grammar_patterns",
        )
        logger.info(f"Extracted {len(result.patterns)} grammar patterns")
        return result

    async def assess_collocations(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
    ) -> CollocationResponse:
        """Identify common collocations for a word.

        Args:
            word: The word
            definition: The definition for context
            part_of_speech: Part of speech

        Returns:
            CollocationResponse with collocations

        """
        prompt = self.prompt_manager.render(
            "assess/collocations",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
        )

        result = await self._make_structured_request(
            prompt,
            CollocationResponse,
            task_name="generate_collocations",
        )
        logger.info(f"Identified {len(result.collocations)} collocations for '{word}'")
        return result

    async def usage_note_generation(
        self,
        word: str,
        definition: str,
    ) -> UsageNoteResponse:
        """Generate usage notes for a definition.

        Args:
            word: The word
            definition: The definition text

        Returns:
            UsageNoteResponse with usage guidance

        """
        prompt = self.prompt_manager.render(
            "misc/usage_note_generation",
            word=word,
            definition=definition,
        )

        result = await self._make_structured_request(
            prompt,
            UsageNoteResponse,
            task_name="generate_usage_notes",
        )
        logger.info(f"Generated {len(result.notes)} usage notes for '{word}'")
        return result

    async def assess_regional_variants(
        self,
        definition: str,
    ) -> RegionalVariantResponse:
        """Detect regional variants for a definition.

        Args:
            definition: The definition text

        Returns:
            RegionalVariantResponse with regions

        """
        prompt = self.prompt_manager.render("assess/regional_variants", definition=definition)

        result = await self._make_structured_request(
            prompt,
            RegionalVariantResponse,
            task_name="identify_regional_variants",
        )
        logger.info(f"Detected regional variants: {', '.join(result.regions)}")
        return result

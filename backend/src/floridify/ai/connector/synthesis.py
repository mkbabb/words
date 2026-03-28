"""Connector mixin for synthesis: definitions, etymology, synonyms, antonyms, dedup, WOTD."""

import time
from typing import Any

from ...models.dictionary import Definition
from ...utils.logging import get_logger, log_metrics
from ..models import (
    AntonymResponse,
    ClusterMappingResponse,
    DeduplicationResponse,
    EtymologyResponse,
    SynonymGenerationResponse,
    SynthesisResponse,
    WordOfTheDayResponse,
)

logger = get_logger(__name__)


class SynthesisMixin:
    """Mixin providing synthesis methods for AIConnector."""

    async def synthesize_definitions(
        self,
        word: str,
        definitions: list[Definition],
        meaning_cluster: str | None = None,
    ) -> SynthesisResponse:
        """Synthesize definitions from multiple providers using full Definition objects.

        Args:
            word: The word to synthesize definitions for.
            definitions: List of Definition objects serialized as dictionaries.
            meaning_cluster: The meaning cluster this definition belongs to.

        """
        prompt = self.prompt_manager.render(
            "synthesize/definitions",
            word=word,
            definitions=definitions,
            meaning_cluster=meaning_cluster,
        )

        # Use tournament for higher quality synthesis
        from ..tournament import TournamentConfig, run_tournament
        from .config import AIConfig

        config = AIConfig()
        if config.enable_tournament:
            tournament_config = TournamentConfig(n=config.tournament_n)
            result = await run_tournament(
                ai=self,
                prompt=prompt,
                response_model=SynthesisResponse,
                task_name="synthesize_definitions",
                config=tournament_config,
                rank_prompt_builder=lambda candidates: self.prompt_manager.render(
                    "misc/rank_candidates",
                    word=word,
                    candidates=candidates,
                    task="definition_synthesis",
                ),
            )
            return result.response

        result = await self._make_structured_request(
            prompt,
            SynthesisResponse,
            task_name="synthesize_definitions",
        )
        return result

    async def extract_etymology(
        self,
        word: str,
        provider_data: list[dict[str, Any]],
    ) -> EtymologyResponse:
        """Extract etymology from provider data.

        Args:
            word: The word
            provider_data: Raw data from providers

        Returns:
            EtymologyResponse with etymology information

        """
        prompt = self.prompt_manager.render(
            "synthesize/etymology",
            word=word,
            provider_data=provider_data,
        )

        result = await self._make_structured_request(
            prompt,
            EtymologyResponse,
            task_name="synthesize_etymology",
        )
        logger.info(f"Extracted etymology for '{word}' (origin: {result.origin_language})")
        return result

    async def synthesize_synonyms(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        existing_synonyms: list[str],
        count: int = 10,
        language: str = "English",
    ) -> SynonymGenerationResponse:
        """Generate synonyms with efflorescence ranking."""
        logger.debug(f"🔗 Generating {count} synonyms for '{word}' ({part_of_speech}, {language})")

        prompt = self.prompt_manager.render(
            "synthesize/synonyms",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_synonyms=existing_synonyms,
            count=count,
            language=language,
        )

        result = await self._make_structured_request(
            prompt,
            SynonymGenerationResponse,
            task_name="generate_synonyms",
        )

        synonym_count = len(result.synonyms)
        logger.success(
            f"✨ Generated {synonym_count} synonyms for '{word}' (confidence: {result.confidence:.1%})",
        )
        return result

    async def synthesize_antonyms(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        existing_antonyms: list[str],
        count: int = 5,
        language: str = "English",
    ) -> AntonymResponse:
        """Generate antonyms for a definition."""
        prompt = self.prompt_manager.render(
            "synthesize/antonyms",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_antonyms=existing_antonyms,
            count=count,
            language=language,
        )

        result = await self._make_structured_request(
            prompt,
            AntonymResponse,
            task_name="generate_antonyms",
        )
        logger.info(f"Generated {len(result.antonyms)} antonyms for '{word}'")
        return result

    async def deduplicate_definitions(
        self,
        word: str,
        definitions: list[Definition],
        part_of_speech: str | None = None,
    ) -> DeduplicationResponse:
        """Deduplicate near-duplicate definitions using semantic similarity.

        Args:
            word: The word being defined
            definitions: List of Definition objects to deduplicate
            part_of_speech: Optional specific part of speech to focus on

        Returns:
            DeduplicationResponse with deduplicated definitions

        """
        logger.info(
            f"🔍 Deduplicating {len(definitions)} definitions for '{word}'"
            f"{f' ({part_of_speech})' if part_of_speech else ''}",
        )

        prompt = self.prompt_manager.render(
            "synthesize/deduplicate",
            word=word,
            definitions=definitions,
            part_of_speech=part_of_speech,
        )

        result = await self._make_structured_request(
            prompt,
            DeduplicationResponse,
            task_name="deduplicate_definitions",
        )

        logger.success(
            f"✨ Deduplicated {len(definitions)} → {len(result.deduplicated_definitions)} "
            f"definitions (removed {result.removed_count}, confidence: {result.confidence:.1%})",
        )
        return result

    async def generate_word_of_the_day(
        self,
        context: str | None = None,
        previous_words: list[str] | None = None,
    ) -> WordOfTheDayResponse:
        """Generate a compelling Word of the Day.

        Args:
            context: Optional context to steer word selection
            previous_words: Previously used words to avoid

        Returns:
            WordOfTheDayResponse with educational word content

        """
        logger.info(
            f"📖 Generating Word of the Day"
            f"{f' with context: {context}' if context else ''}"
            f"{f' avoiding {len(previous_words)} previous words' if previous_words else ''}",
        )

        prompt = self.prompt_manager.render(
            "wotd/word_of_the_day",
            context=context,
            previous_words=previous_words,
        )

        result = await self._make_structured_request(
            prompt,
            WordOfTheDayResponse,
            task_name="generate_word_of_the_day",
        )

        logger.success(
            f"✨ Generated Word of the Day: '{result.word}' "
            f"({result.difficulty_level}, confidence: {result.confidence:.1%})",
        )
        return result

    async def extract_cluster_mapping(
        self,
        word: str,
        definitions: list[tuple[str, str, str]],
    ) -> ClusterMappingResponse:
        """Extract numerical mapping of clusters to definition IDs.

        Args:
            word: The word to extract mappings for.
            definitions: list of: (provider, part_of_speech, definition) tuples from providers.

        """
        start_time = time.perf_counter()
        def_count = len(definitions)

        logger.info(f"🔢 Extracting cluster mappings for '{word}' from {def_count} definitions")

        prompt = self.prompt_manager.render(
            "misc/meaning_extraction",
            word=word,
            definitions=definitions,
        )

        result = await self._make_structured_request(
            prompt,
            ClusterMappingResponse,
            task_name="extract_cluster_mapping",
        )
        duration = time.perf_counter() - start_time

        # Log detailed cluster information
        total_defs_mapped = sum(len(cm.definition_indices) for cm in result.cluster_mappings)
        logger.success(
            f"🧮 Extracted {len(result.cluster_mappings)} meaning clusters for '{word}' "
            f"in {duration:.2f}s (mapped {total_defs_mapped}/{def_count} definitions)",
        )

        # Log each cluster for debugging
        for cluster in result.cluster_mappings:
            logger.debug(
                f"  • Cluster '{cluster.cluster_slug}': {cluster.cluster_description} "
                f"({len(cluster.definition_indices)} definitions)",
            )

        log_metrics(
            stage="cluster_extraction",
            word=word,
            cluster_count=len(result.cluster_mappings),
            definition_count=def_count,
            mapped_count=total_defs_mapped,
            confidence=result.confidence,
            duration=duration,
        )
        return result

"""Connector mixin for generation: examples, pronunciation, facts, text, literature, anki."""

from ...utils.logging import get_logger
from ..model_selection import ModelTier
from ..models import (
    AnkiFillBlankResponse,
    AnkiMultipleChoiceResponse,
    DictionaryEntryResponse,
    ExampleGenerationResponse,
    FactGenerationResponse,
    LiteratureAnalysisResponse,
    LiteratureAugmentationRequest,
    LiteratureAugmentationResponse,
    PronunciationResponse,
    SuggestionsResponse,
    SyntheticCorpusResponse,
    TextGenerationRequest,
    TextGenerationResponse,
    WordFormResponse,
)

logger = get_logger(__name__)


class GenerationMixin:
    """Mixin providing generation methods for OpenAIConnector."""

    async def generate_examples(
        self,
        word: str,
        part_of_speech: str,
        definition: str,
        count: int = 1,
    ) -> ExampleGenerationResponse:
        """Generate modern usage examples."""
        logger.debug(f"📝 Generating {count} example sentence(s) for '{word}' ({part_of_speech})")

        prompt = self.prompt_manager.render(
            "generate/examples",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            count=count,
        )

        result = await self._make_structured_request(
            prompt,
            ExampleGenerationResponse,
            task_name="generate_examples",
        )
        if result.example_sentences:
            first_example = result.example_sentences[0]
            truncated = first_example[:50] + "..." if len(first_example) > 50 else first_example
            logger.debug(f"✏️  Generated example for '{word}': \"{truncated}\"")
        return result

    async def pronunciation(self, word: str, language: str = "en") -> PronunciationResponse:
        """Generate pronunciation data."""
        language_names = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ja": "Japanese",
            "zh": "Mandarin Chinese",
            "hi": "Hindi",
        }
        prompt = self.prompt_manager.render(
            "synthesize/pronunciation",
            word=word,
            language=language,
            language_name=language_names.get(language, "English"),
        )

        return await self._make_structured_request(
            prompt,
            PronunciationResponse,
            task_name="generate_pronunciation",
        )

    async def lookup_fallback(self, word: str) -> DictionaryEntryResponse | None:
        """Generate AI fallback provider data."""
        logger.info(f"🤖 Generating AI fallback definition for '{word}'")

        prompt = self.prompt_manager.render("misc/lookup", word=word)

        result = await self._make_structured_request(
            prompt,
            DictionaryEntryResponse,
            task_name="lookup_word",
        )

        if result.definitions:
            def_count = len(result.definitions)
            logger.success(
                f"✨ Generated {def_count} definitions for '{word}' "
                f"(confidence: {result.confidence:.1%})",
            )
        else:
            logger.warning(f"⚠️  AI generated empty response for '{word}'")

        return result

    async def identify_word_forms(
        self,
        word: str,
        part_of_speech: str,
    ) -> WordFormResponse:
        """Identify word forms (plural, past tense, etc.).

        Args:
            word: The word
            part_of_speech: Part of speech

        Returns:
            WordFormResponse with word forms

        """
        prompt = self.prompt_manager.render(
            "generate/word_forms",
            word=word,
            part_of_speech=part_of_speech,
        )

        result = await self._make_structured_request(
            prompt,
            WordFormResponse,
            task_name="generate_word_forms",
        )
        logger.info(f"Identified {len(result.forms)} word forms for '{word}'")
        return result

    async def generate_facts(
        self,
        word: str,
        definition: str,
        count: int = 5,
        previous_words: list[str] | None = None,
    ) -> FactGenerationResponse:
        """Generate interesting facts about a word.

        Args:
            word: The word to generate facts about
            definition: Main definition of the word for context
            count: Number of facts to generate (3-8)
            previous_words: Previously searched words for connections

        Returns:
            FactGenerationResponse with facts and metadata

        """
        fact_count = max(3, min(8, count))
        limited_previous = previous_words[:20] if previous_words else []

        logger.info(
            f"📚 Generating {fact_count} facts for '{word}' with {len(limited_previous)} previous words",
        )

        prompt = self.prompt_manager.render(
            "generate/facts",
            word=word,
            definition=definition,
            count=fact_count,
            previous_words=limited_previous,
        )

        result = await self._make_structured_request(
            prompt,
            FactGenerationResponse,
            task_name="generate_facts",
        )

        facts_count = len(result.facts)
        categories_str = ", ".join(result.categories) if result.categories else "general"
        logger.success(
            f"✨ Generated {facts_count} facts for '{word}' "
            f"({categories_str}, confidence: {result.confidence:.1%})",
        )
        return result

    async def generate_text(
        self,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """Generate text from a prompt.

        Args:
            request: Text generation request with prompt and parameters

        Returns:
            TextGenerationResponse with generated text

        """
        logger.info(
            f"📝 Generating text (max_tokens: {request.max_tokens}, temp: {request.temperature})",
        )

        result = await self._make_structured_request(
            request.prompt,
            TextGenerationResponse,
            task_name="text_generation",
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        logger.success(f"✨ Generated {len(result.text)} characters of text")
        return result

    async def generate_synthetic_corpus(
        self,
        style: str,
        complexity: str,
        era: str,
        num_words: int,
        theme: str | None = None,
        avoid_words: list[str] | None = None,
    ) -> SyntheticCorpusResponse:
        """Generate a synthetic corpus for WOTD training.

        Args:
            style: Target style category (classical, modern, romantic, neutral)
            complexity: Target complexity level (beautiful, simple, complex, plain)
            era: Target era (shakespearean, victorian, modernist, contemporary)
            num_words: Number of words to generate
            theme: Optional thematic focus
            avoid_words: Words to avoid in generation

        Returns:
            SyntheticCorpusResponse with generated corpus

        """
        logger.info(
            f"🧬 Generating synthetic corpus: {style}/{complexity}/{era} "
            f"({num_words} words)"
            f"{f' themed: {theme}' if theme else ''}",
        )

        prompt = self.prompt_manager.render(
            "wotd/synthetic_corpus",
            style=style,
            complexity=complexity,
            era=era,
            num_words=num_words,
            theme=theme,
            avoid_words=avoid_words,
        )

        result = await self._make_structured_request(
            prompt,
            SyntheticCorpusResponse,
            task_name="generate_synthetic_corpus",
            tier=ModelTier.HIGH,  # Use GPT-5 or best available model
        )

        logger.success(
            f"✨ Generated {result.total_generated} words for {style}/{complexity}/{era} corpus "
            f"(quality: {result.quality_score:.1%})",
        )
        return result

    async def augment_literature_vocabulary(
        self,
        request: LiteratureAugmentationRequest,
    ) -> LiteratureAugmentationResponse:
        """Generate augmented vocabulary based on literary samples.

        Args:
            request: Literature augmentation request

        Returns:
            LiteratureAugmentationResponse with augmented words

        """
        logger.info(
            f"📚 Augmenting {request.author}'s vocabulary: {len(request.sample_words)} samples → "
            f"{request.target_count} variants",
        )

        # Ultra-lean prompt - minimal tokens, maximum efficiency
        words = ", ".join(request.sample_words[:10])  # Use only 10 words max
        prompt = f"{request.transformation_prompt}: {words}\n{request.target_count} words:"

        result = await self._make_structured_request(
            prompt,
            LiteratureAugmentationResponse,
            task_name="literature_augmentation",
            max_tokens=50,  # Ultra-lean output
            # Temperature handled automatically for GPT-5 series models
        )

        logger.success(
            f"✨ Generated {len(result.words)} augmented words for {request.author} "
            f"(confidence: {result.confidence:.1%})",
        )
        return result

    async def analyze_literature_corpus(
        self,
        author: str,
        words: list[str],
        period: str | None = None,
        genre: str | None = None,
        word_frequencies: dict[str, int] | None = None,
    ) -> LiteratureAnalysisResponse:
        """Analyze literature corpus and generate semantic ID using template system.

        This method uses the literature_analysis.md prompt template to perform
        comprehensive analysis of a literary corpus and generate semantic IDs.

        Args:
            author: Author name
            words: List of words to analyze
            period: Literary period (optional)
            genre: Primary genre (optional)
            word_frequencies: Word frequency data (optional)

        Returns:
            LiteratureAnalysisResponse with complete analysis and semantic ID

        """
        logger.info(f"📚 Analyzing literature corpus for {author}: {len(words)} words")

        # Use the ultra-lean literature analysis prompt template
        prompt = self.prompt_manager.render(
            "wotd/literature_analysis_lean",
            author=author,
            words=words,
        )

        result = await self._make_structured_request(
            prompt,
            LiteratureAnalysisResponse,
            task_name="literature_analysis",
            max_tokens=30,  # Ultra-lean semantic ID output
            # Temperature handled automatically based on model type (reasoning models don't use temperature)
        )

        logger.success(
            f"✨ Analyzed {author} corpus: semantic ID [{result.semantic_id.style},"
            f"{result.semantic_id.complexity},{result.semantic_id.era},"
            f"{result.semantic_id.variation}] (quality: {result.quality_score:.1%})",
        )
        return result

    async def generate_anki_fill_blank(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        examples: str | None = None,
    ) -> AnkiFillBlankResponse:
        """Generate fill-in-the-blank flashcard using structured output."""
        prompt = self.prompt_manager.render(
            "misc/anki_fill_blank",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            examples=examples or "",
        )
        result = await self._make_structured_request(
            prompt,
            AnkiFillBlankResponse,
            task_name="generate_anki_fill_blank",
        )
        logger.debug(f"Generated fill-blank card for '{word}'")
        return result

    async def generate_anki_best_describes(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        examples: str | None = None,
    ) -> AnkiMultipleChoiceResponse:
        """Generate best describes flashcard using structured output."""
        prompt = self.prompt_manager.render(
            "misc/anki_best_describes",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            examples=examples or "",
        )
        result = await self._make_structured_request(
            prompt,
            AnkiMultipleChoiceResponse,
            task_name="generate_anki_best_describes",
        )
        logger.debug(f"Generated best describes card for '{word}'")
        return result

    async def suggestions(
        self,
        input_words: list[str] | None,
        count: int = 10,
    ) -> SuggestionsResponse:
        """Generate word suggestions based on input words.

        Args:
            input_words: List of up to 10 input words to base suggestions on
            count: Number of suggestions to generate (8-12)

        Returns:
            SuggestionsResponse with suggestions and analysis

        """
        limited_words = input_words[:10] if input_words else None
        suggestion_count = max(8, min(12, count))

        logger.info(
            f"🌸 Generating {suggestion_count} suggestions from {len(limited_words) if limited_words else 0} words",
        )

        prompt = self.prompt_manager.render(
            "misc/suggestions",
            input_words=limited_words,
            count=suggestion_count,
        )

        result = await self._make_structured_request(
            prompt,
            SuggestionsResponse,
            task_name="generate_suggestions",
        )

        suggestions_count = len(result.suggestions)
        logger.success(
            f"✨ Generated {suggestions_count} suggestions (confidence: {result.confidence:.1%})",
        )
        return result

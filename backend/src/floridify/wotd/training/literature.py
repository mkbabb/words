"""Literature-based corpus augmentation and semantic ID analysis.

Handles AI-powered corpus augmentation, semantic ID extraction from
literary texts, and default semantic ID generation. Extracted from
pipeline.py for cohesion — these are literature-specific operations
independent of pipeline orchestration.
"""

from __future__ import annotations

import asyncio

from ...ai import get_ai_connector
from ...utils.logging import get_logger
from ..core import WOTDCorpus, WOTDWord

logger = get_logger(__name__)


async def augment_corpus_with_ai(
    corpus: WOTDCorpus,
    author: str,
) -> dict[str, WOTDCorpus]:
    """Generate synthetic variations of a corpus using AI.

    This function uses the OpenAI connector to create variations of
    the literary corpus with different semantic attributes. This
    augmentation helps the model learn the relationship between
    semantic IDs and vocabulary characteristics.

    Variations Generated:
        - Style shifts (formal -> casual, poetic -> technical)
        - Complexity adjustments (simple -> complex)
        - Era transformations (archaic -> modern)
        - Thematic variations

    Args:
        corpus: Original literary corpus
        author: Author name for context

    Returns:
        Dictionary of augmented corpora with variation IDs

    """
    from ..core import Complexity, Era, Style

    ai_connector = get_ai_connector()
    augmented_corpora = {}

    # Sample words for AI context
    sample_words = [w.word for w in corpus.words[:30]]

    # Define variations to generate
    variations = [
        {
            "id": f"{author.lower()}_classical",
            "style": Style.CLASSICAL,
            "prompt": f"Transform these {author} words to be more classical and formal",
        },
        {
            "id": f"{author.lower()}_simple",
            "complexity": Complexity.SIMPLE,
            "prompt": f"Simplify these {author} words for general audiences",
        },
        {
            "id": f"{author.lower()}_modern",
            "era": Era.CONTEMPORARY,
            "prompt": f"Modernize these {author} words for today's usage",
        },
        {
            "id": f"{author.lower()}_neutral",
            "style": Style.NEUTRAL,
            "prompt": f"Create neutral variations of these {author} words",
        },
    ]

    # Process variations in batches for efficiency

    from ...ai.models import LiteratureAugmentationRequest

    async def process_variation(variation):
        try:
            request = LiteratureAugmentationRequest(
                author=author,
                sample_words=sample_words,
                transformation_prompt=variation["prompt"],
                target_count=50,
            )

            response_obj = await ai_connector.augment_literature_vocabulary(request)
            generated_words = response_obj.words[:50]  # Ensure we have max 50 words

            return variation, generated_words
        except Exception as e:
            logger.error(f"Failed to generate {variation['id']}: {e}")
            return variation, []

    # Execute all variations concurrently for speed
    batch_results = await asyncio.gather(
        *[process_variation(v) for v in variations],
        return_exceptions=True,
    )

    for result in batch_results:
        if isinstance(result, Exception):
            logger.error(f"Batch processing error: {result}")
            continue

        variation, generated_words = result
        if not generated_words:
            continue

        # Create augmented corpus
        augmented_corpus = WOTDCorpus(
            id=variation["id"],
            style=variation.get("style", corpus.style),
            complexity=variation.get("complexity", corpus.complexity),
            era=variation.get("era", corpus.era),
            author=corpus.author,  # Use corpus author, not string
            words=[
                WOTDWord(
                    word=word,
                    definition=f"AI-augmented from {author}",
                    pos="noun",
                    style=variation.get("style", corpus.style),
                    complexity=variation.get("complexity", corpus.complexity),
                    era=variation.get("era", corpus.era),
                )
                for word in generated_words
            ],
        )

        augmented_corpora[variation["id"]] = augmented_corpus
        logger.info(f"  Generated {len(generated_words)} words for {variation['id']}")

    return augmented_corpora


async def analyze_literature_semantic_ids(
    corpora_dict: dict[str, WOTDCorpus],
) -> dict[str, tuple[int, int, int, int]]:
    """Analyze literature corpora to get semantic IDs using the template system.

    This function uses the literature analysis prompt template to get semantic IDs
    directly from AI analysis instead of training an encoder. This is simpler
    and more direct for literature-based training.

    Args:
        corpora_dict: Dictionary of corpus ID to WOTDCorpus

    Returns:
        Dictionary mapping corpus IDs to semantic ID tuples

    """
    ai_connector = get_ai_connector()
    semantic_ids = {}

    for corpus_id, corpus in corpora_dict.items():
        logger.info(f"Analyzing {corpus_id} for semantic characteristics")

        # Extract words and metadata
        words = [w.word for w in corpus.words]

        # Determine period and genre from corpus metadata
        period = "Elizabethan" if "shakespeare" in corpus_id.lower() else "Modernist"
        genre = "mixed" if "shakespeare" in corpus_id.lower() else "novel"

        # Get word frequencies
        word_frequencies = {w.word: w.frequency for w in corpus.words[:20]}

        try:
            # Use the new literature analysis method
            analysis_result = await ai_connector.analyze_literature_corpus(
                author=corpus.author.value if corpus.author else "Unknown",
                words=words,
                period=period,
                genre=genre,
                word_frequencies=word_frequencies,
            )

            # Convert semantic ID to tuple format
            semantic_id = (
                analysis_result.semantic_id.style,
                analysis_result.semantic_id.complexity,
                analysis_result.semantic_id.era,
                analysis_result.semantic_id.variation,
            )

            semantic_ids[corpus_id] = semantic_id

            logger.info(
                f"  {corpus_id} -> semantic ID {semantic_id} "
                f"(quality: {analysis_result.quality_score:.1%})",
            )

        except Exception as e:
            logger.warning(f"  Failed to analyze {corpus_id}: {e}")
            # Fallback to default semantic ID based on corpus metadata
            semantic_id = get_default_semantic_id(corpus)
            semantic_ids[corpus_id] = semantic_id
            logger.info(f"  Using default semantic ID {semantic_id} for {corpus_id}")

    return semantic_ids


def get_default_semantic_id(corpus: WOTDCorpus) -> tuple[int, int, int, int]:
    """Get default semantic ID based on corpus metadata."""
    # Map enum values to semantic dimensions
    style_map = {
        "classical": 0,
        "modern": 1,
        "romantic": 2,
        "neutral": 3,
    }
    complexity_map = {
        "beautiful": 1,
        "simple": 0,
        "complex": 3,
        "plain": 0,
    }
    era_map = {
        "shakespearean": 2,
        "victorian": 5,
        "modernist": 6,
        "contemporary": 7,
    }

    style = style_map.get(corpus.style.value, 0)
    complexity = complexity_map.get(corpus.complexity.value, 1)
    era = era_map.get(corpus.era.value, 6)
    variation = 0  # Default variation

    return (style, complexity, era, variation)

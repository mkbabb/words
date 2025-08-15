"""Synthetic corpus generation using OpenAI - clean and performance-focused."""

from __future__ import annotations

import asyncio
import time

from ..ai.factory import get_openai_connector
from ..utils.logging import get_logger
from .core import (
    Author,
    Complexity,
    Era,
    Style,
    WOTDCorpus,
    WOTDWord,
)
from .storage import WOTDStorage, get_wotd_storage

logger = get_logger(__name__)


class SyntheticGenerator:
    """Generate synthetic WOTD training corpora using OpenAI."""

    def __init__(self) -> None:
        self._ai_connector = get_openai_connector()
        self._storage: WOTDStorage | None = None

    async def _get_storage(self) -> WOTDStorage:
        """Get storage instance."""
        if self._storage is None:
            self._storage = await get_wotd_storage()
        return self._storage

    def _make_corpus_id(self, style: Style, complexity: Complexity, era: Era) -> str:
        """Create corpus ID from semantic categories."""
        return f"{style.value}_{complexity.value}_{era.value}"

    async def generate_corpus(
        self,
        style: Style,
        complexity: Complexity,
        era: Era,
        num_words: int = 100,
        theme: str | None = None,
        author: Author | None = None,
    ) -> WOTDCorpus:
        """Generate single semantic corpus with optional authorial influence."""
        corpus_id = self._make_corpus_id(style, complexity, era)
        author_context = f" (influenced by {author.value})" if author else ""

        logger.info(f"🧬 Generating {corpus_id} corpus ({num_words} words){author_context}")

        # Create enhanced thematic context with authorship
        base_contexts = {
            (Style.CLASSICAL, Complexity.BEAUTIFUL): "literature and aesthetic beauty",
            (Style.CLASSICAL, Complexity.COMPLEX): "philosophy and formal discourse",
            (Style.MODERN, Complexity.SIMPLE): "contemporary life and technology",
            (Style.MODERN, Complexity.COMPLEX): "innovation and scientific advancement",
            (Style.ROMANTIC, Complexity.BEAUTIFUL): "love, nature, and emotions",
            (Style.ROMANTIC, Complexity.COMPLEX): "deep psychology and relationships",
            (Style.NEUTRAL, Complexity.SIMPLE): "general education and communication",
            (Style.NEUTRAL, Complexity.COMPLEX): "academic and professional domains",
        }

        base_context = theme or base_contexts.get((style, complexity), "general vocabulary")

        # Enhance context with authorial influence
        if author:
            author_influences = {
                Author.SHAKESPEARE: "with Shakespearean eloquence and dramatic depth",
                Author.DANTE: "with Dantean philosophical gravitas and spiritual imagery",
                Author.HOMER: "with Homeric epic grandeur and mythological resonance",
                Author.JOYCE: "with Joycean linguistic innovation and stream-of-consciousness",
                Author.WOOLF: "with Woolfian psychological subtlety and modernist sensibility",
                Author.DICKENS: "with Dickensian social observation and character richness",
                Author.TOLSTOY: "with Tolstoyan moral complexity and existential depth",
                Author.GOETHE: "with Goethean romantic idealism and intellectual breadth",
                Author.CERVANTES: "with Cervantean wit and narrative sophistication",
                Author.MILTON: "with Miltonic sublime grandeur and theological depth",
                Author.CHAUCER: "with Chaucerian earthy humor and social insight",
                Author.VIRGIL: "with Virgilian pastoral elegance and classical refinement",
                Author.OVID: "with Ovidian metamorphic imagination and mythic transformation",
                Author.PETRARCH: "with Petrarchan lyrical beauty and emotional intensity",
                Author.BOCCACCIO: "with Boccaccian narrative charm and human comedy",
                Author.SPENSER: "with Spenserian allegorical richness and poetic music",
                Author.DUMAS: "with Dumasian adventure and heroic romanticism",
                Author.PROUST: "with Proustian memory-laden introspection and temporal depth",
            }
            authorial_flavor = author_influences.get(
                author,
                f"with {author.value}'s distinctive style",
            )
            context = f"{base_context} {authorial_flavor}"
        else:
            context = base_context

        # Generate using OpenAI
        ai_response = await self._ai_connector.generate_synthetic_corpus(
            style=style.value,
            complexity=complexity.value,
            era=era.value,
            num_words=num_words,
            theme=context,
        )

        # Convert AI response to WOTD words
        words = []
        for ai_word in ai_response.generated_words:
            word = WOTDWord(
                word=ai_word.word,
                definition=ai_word.definition,
                pos=ai_word.part_of_speech,
                style=style,
                complexity=complexity,
                era=era,
            )
            words.append(word)

        corpus = WOTDCorpus(
            id=corpus_id,
            style=style,
            complexity=complexity,
            era=era,
            author=author,  # Include authorial influence in corpus
            words=words,
        )

        logger.success(f"✅ Generated {corpus_id}: {len(words)} words")
        return corpus

    async def generate_complete_training_set(
        self,
        words_per_corpus: int = 100,
        save: bool = True,
    ) -> dict[str, WOTDCorpus]:
        """Generate complete training set with balanced semantic coverage and authorial influence."""
        logger.info(f"🚀 Generating complete WOTD training set ({words_per_corpus} words/corpus)")

        # Define semantic combinations with strategic authorial influences
        combinations = [
            # Classical + Author combinations
            (Style.CLASSICAL, Complexity.BEAUTIFUL, Era.SHAKESPEAREAN, Author.SHAKESPEARE),
            (Style.CLASSICAL, Complexity.COMPLEX, Era.VICTORIAN, Author.DANTE),
            (Style.CLASSICAL, Complexity.BEAUTIFUL, Era.VICTORIAN, Author.PETRARCH),
            # Modern combinations with modernist authors
            (Style.MODERN, Complexity.SIMPLE, Era.CONTEMPORARY, None),  # Pure modern
            (Style.MODERN, Complexity.COMPLEX, Era.MODERNIST, Author.JOYCE),
            (Style.MODERN, Complexity.BEAUTIFUL, Era.MODERNIST, Author.WOOLF),
            # Romantic combinations with romantic authors
            (Style.ROMANTIC, Complexity.BEAUTIFUL, Era.VICTORIAN, Author.GOETHE),
            (Style.ROMANTIC, Complexity.COMPLEX, Era.SHAKESPEAREAN, Author.DUMAS),
            # Neutral combinations (baseline without strong authorial influence)
            (Style.NEUTRAL, Complexity.SIMPLE, Era.CONTEMPORARY, None),
            (Style.NEUTRAL, Complexity.COMPLEX, Era.MODERNIST, None),
            # Mixed era/author combinations for complexity
            (Style.CLASSICAL, Complexity.SIMPLE, Era.CONTEMPORARY, Author.CHAUCER),
            (Style.ROMANTIC, Complexity.SIMPLE, Era.MODERNIST, Author.DICKENS),
        ]

        start_time = time.time()
        corpora = {}

        # Generate corpora in parallel batches for performance
        batch_size = 4
        for i in range(0, len(combinations), batch_size):
            batch = combinations[i : i + batch_size]

            # Generate batch concurrently with authorial influences
            tasks = [
                self.generate_corpus(style, complexity, era, words_per_corpus, author=author)
                for style, complexity, era, author in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    style, complexity, era, author = batch[j]
                    author_info = f" ({author.value})" if author else ""
                    logger.error(
                        f"❌ Failed to generate {style}/{complexity}/{era}{author_info}: {result}",
                    )
                elif isinstance(result, WOTDCorpus):
                    corpora[result.id] = result

        duration = time.time() - start_time
        total_words = sum(len(corpus.words) for corpus in corpora.values())

        logger.success(
            f"🎯 Generated {len(corpora)} corpora with {total_words} words in {duration:.2f}s",
        )

        # Save to storage
        if save:
            storage = await self._get_storage()
            corpus_list = [c for c in corpora.values() if isinstance(c, WOTDCorpus)]
            await storage.save_multiple_corpora(corpus_list)
            logger.info("💾 Saved corpora to storage")

        return corpora

    async def regenerate_corpus(
        self,
        corpus_id: str,
        num_words: int = 100,
        theme: str | None = None,
    ) -> WOTDCorpus:
        """Regenerate specific corpus."""
        # Parse corpus ID
        parts = corpus_id.split("_")
        if len(parts) != 3:
            raise ValueError(f"Invalid corpus ID format: {corpus_id}")

        style = Style(parts[0])
        complexity = Complexity(parts[1])
        era = Era(parts[2])

        corpus = await self.generate_corpus(style, complexity, era, num_words, theme)

        # Save to storage
        storage = await self._get_storage()
        await storage.save_corpus(corpus)

        return corpus


# Convenience functions
async def generate_training_data(
    words_per_corpus: int = 100,
    use_cached: bool = True,
) -> dict[str, WOTDCorpus]:
    """Generate or load training data."""
    storage = await get_wotd_storage()
    generator = SyntheticGenerator()

    # Try to load from cache/storage first
    if use_cached:
        corpora = await storage.load_corpora_dict()
        if corpora and all(len(c.words) >= words_per_corpus * 0.8 for c in corpora.values()):
            logger.info("📋 Using cached training data")
            return corpora

    # Generate fresh data
    logger.info("🔄 Generating fresh training data")
    return await generator.generate_complete_training_set(
        words_per_corpus=words_per_corpus,
        save=True,
    )


async def get_corpus_for_training(corpus_id: str) -> list[str] | None:
    """Get corpus words as list for training."""
    storage = await get_wotd_storage()
    corpus = await storage.get_corpus(corpus_id)

    if corpus:
        return [word.word for word in corpus.words]
    return None

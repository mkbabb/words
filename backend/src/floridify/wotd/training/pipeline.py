"""WOTD training system - four-stage pipeline for semantic preference learning.

This module implements a complete training pipeline for learning semantic
representations of text preferences. The system transforms high-dimensional
embeddings into discrete semantic IDs that enable controlled text generation.

Pipeline Architecture:
    Stage 1: Synthetic Corpus Generation
        - Samples semantic attribute combinations
        - Prompts LLMs to generate coherent word lists
        - Creates balanced training data across semantic space

    Stage 2: Embedding Extraction
        - Encodes words using transformer models (GTE-Qwen2, E5, etc.)
        - Supports Matryoshka truncation for multi-resolution
        - Optional quantization (binary, INT8) for efficiency

    Stage 3: Semantic Encoder Training
        - Learns mapping from embeddings to 4D semantic IDs
        - Uses FSQ or HVQ for discrete quantization
        - Optimizes reconstruction and entropy losses

    Stage 4: Language Model Fine-tuning
        - Conditions generation on semantic IDs
        - Uses LoRA for parameter-efficient training
        - Learns to generate words matching semantic patterns

Key Insight:
    Semantic preferences can be compressed from thousands of dimensions
    to just 4 interpretable dimensions (style, complexity, era, variation)
    while preserving essential semantic information. This compression
    enables efficient storage, retrieval, and generation.

Mathematical Foundation:
    The system implements an information bottleneck where:
    - Input: High-dimensional continuous embeddings (4096D)
    - Bottleneck: Discrete 4D semantic IDs (2560 unique codes)
    - Output: Generated text matching semantic attributes

    This forces the model to learn only the most salient features.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import torch

from ...utils.logging import get_logger
from ...utils.paths import get_cache_directory
from ..core import (
    Author,
    SemanticIDDict,
    TrainingConfig,
    TrainingResults,
    WOTDCorpus,
    WOTDWord,
)
from ..encoders import get_semantic_encoder
from ..generator import generate_training_data
from ..storage import get_wotd_storage
from .dsl_trainer import DSLTrainer
from .embedder import WOTDEmbedder
from .encoder_training import train_semantic_encoder, train_semantic_encoder_with_targets
from .literature import (
    analyze_literature_semantic_ids,
    augment_corpus_with_ai,
    get_default_semantic_id,
)

logger = get_logger(__name__)


class WOTDTrainer:
    """WOTD training orchestrator - manages the complete pipeline.

    This is the main orchestrator class that coordinates all four stages
    of the training pipeline. It manages data flow between stages, handles
    caching, and tracks training progress.

    Pipeline Overview:
        1. Generate synthetic training data using LLMs
        2. Extract embeddings from generated corpora
        3. Train semantic encoder (FSQ/HVQ) to learn discrete codes
        4. Fine-tune language model for controlled generation

    The pipeline implements an end-to-end system for learning semantic
    representations and using them for controlled text generation.

    Key Components:
        - WOTDEmbedder: Handles embedding extraction (Stage 2)
        - Semantic Encoder: Learns discrete codes (Stage 3)
        - DSLTrainer: Fine-tunes language models (Stage 4)
        - Storage: Manages caching and persistence

    Configuration:
        The TrainingConfig controls all aspects of training including:
        - Model selection (embeddings and language models)
        - Training hyperparameters (epochs, learning rate, batch size)
        - Encoder type (FSQ vs HVQ)
        - Data generation parameters
    """

    # File constants
    SEMANTIC_ENCODER_FILE = "semantic_encoder.pt"
    SEMANTIC_IDS_FILE = "semantic_ids.json"

    def get_models_dir(self) -> Path:
        """Get the proper models directory using cache utilities."""
        return get_cache_directory("wotd_models")

    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig()

        # Initialize components
        self.embedder = WOTDEmbedder(model_name=self.config.embedding_model)

        # Get actual embedding dimensions from the embedder based on current mode
        input_dim = self.embedder.current_dim
        self.encoder = get_semantic_encoder(input_dim=input_dim)

        self.dsl_trainer = DSLTrainer(self.config)

    async def train_complete_pipeline(self, output_dir: str | None = None) -> TrainingResults:
        """Execute complete four-stage training pipeline.

        This method orchestrates the entire training process from data
        generation to model fine-tuning. Each stage builds upon the
        previous, creating a complete system for semantic text generation.

        Stage Details:

        **Stage 1: Synthetic Data Generation**
            - Samples semantic attribute combinations
            - Prompts GPT-4/Qwen to generate coherent word lists
            - Creates balanced dataset across semantic space
            - Results cached for reuse across experiments

        **Stage 2: Embedding Extraction**
            - Encodes each word using transformer models
            - Applies optional quantization for efficiency
            - Aggregates to corpus-level representations
            - Caches embeddings to avoid recomputation

        **Stage 3: Semantic Encoder Training**
            - Learns mapping from embeddings to 4D semantic IDs
            - Uses FSQ or HVQ for discrete quantization
            - Optimizes reconstruction + entropy losses
            - Saves trained encoder for inference

        **Stage 4: Language Model Fine-tuning**
            - Creates instruction-response training pairs
            - Fine-tunes LLM with LoRA for efficiency
            - Learns to generate words from semantic IDs
            - Saves adapter weights for deployment

        Args:
            output_dir: Directory to save trained models and artifacts
                       Defaults to ./models/wotd/

        Returns:
            TrainingResults containing:
                - Performance metrics for each stage
                - Paths to saved models
                - Semantic ID mappings
                - Training duration and statistics

        """
        start_time = time.time()
        logger.info("🚀 Starting WOTD training pipeline")

        # Stage 1: Generate/load semantic corpora
        # This creates the foundation dataset by sampling the semantic space
        # and generating coherent word lists for each combination
        logger.info("🧬 Stage 1: Loading semantic training corpora")
        corpora_dict = await generate_training_data(
            words_per_corpus=self.config.words_per_corpus,
            use_cached=True,  # Reuse existing corpora for faster iteration
        )

        # Stage 2: Extract preference vectors via embeddings
        logger.info(f"🧠 Stage 2: Computing {self.config.embedding_model} preference vectors")
        preference_vectors = {}

        for corpus_id, corpus in corpora_dict.items():
            pref_vector = await self.embedder.encode_corpus(corpus)
            if not isinstance(pref_vector, torch.Tensor):
                pref_vector = torch.tensor(pref_vector, dtype=torch.float32)
            preference_vectors[corpus_id] = pref_vector

        # Stage 3: Train semantic encoder (high-D -> 4D compression using FSQ)
        logger.info("🔢 Stage 3: Training FSQ semantic encoder")
        semantic_ids = await self._train_semantic_encoder(preference_vectors)

        # Stage 4: Generate DSL training examples (semantic IDs -> word generation)
        logger.info("📚 Stage 4: Creating DSL training examples")
        training_examples = self.dsl_trainer.create_training_examples(corpora_dict, semantic_ids)
        logger.info(f"Created {len(training_examples)} DSL training examples")

        # Step 5: Save models and results
        logger.info("💾 Saving models and results")
        model_paths = await self._save_models(output_dir, semantic_ids)

        # Create training results
        duration = time.time() - start_time
        total_words = sum(len(corpus.words) for corpus in corpora_dict.values())

        results = TrainingResults(
            config=self.config,
            duration_seconds=duration,
            num_corpora=len(corpora_dict),
            total_words=total_words,
            semantic_ids=semantic_ids,
            model_paths=model_paths,
        )

        # Save results to storage
        storage = await get_wotd_storage()
        await storage.save_training_results(results)
        await storage.save_semantic_ids(semantic_ids)

        logger.success(
            f"🎯 Training completed in {duration:.2f}s "
            f"({len(corpora_dict)} corpora, {total_words} words)",
        )

        return results

    async def _train_semantic_encoder(
        self,
        preference_vectors: dict[str, torch.Tensor],
    ) -> SemanticIDDict:
        """Train semantic encoder with enhanced optimization for lower loss."""
        return await train_semantic_encoder(self.encoder, self.config, preference_vectors)

    async def _save_models(
        self,
        output_dir: str | None,
        semantic_ids: SemanticIDDict,
    ) -> dict[str, str]:
        """Save trained models."""
        if output_dir:
            models_dir = Path(output_dir)
        else:
            # Use unified cache directory structure
            await get_wotd_storage()
            models_dir = self.get_models_dir()

        models_dir.mkdir(parents=True, exist_ok=True)

        # Save semantic encoder
        encoder_path = models_dir / self.SEMANTIC_ENCODER_FILE
        encoder_module = self.encoder.encoder
        torch.save(
            {
                "model_state_dict": encoder_module.state_dict(),
                "config": self.config.model_dump(),
                "encoder_type": self.encoder.encoding_type,
            },
            encoder_path,
        )

        # Save semantic IDs as JSON
        semantic_ids_path = models_dir / self.SEMANTIC_IDS_FILE

        with open(semantic_ids_path, "w") as f:
            # Convert tuples to lists for JSON serialization
            serializable_ids = {k: list(v) for k, v in semantic_ids.items()}
            json.dump(serializable_ids, f, indent=2)

        model_paths = {
            "semantic_encoder": str(encoder_path),
            "semantic_ids": str(semantic_ids_path),
            "models_directory": str(models_dir),
        }

        logger.info(f"💾 Models saved to {models_dir}")
        return model_paths

    async def train_from_literature(
        self,
        authors: list[Author],
        output_dir: str | None = None,
        use_lightweight_model: bool = False,
        max_works_per_author: int | None = None,
        max_words_per_corpus: int = 200,
    ) -> TrainingResults:
        """Train WOTD pipeline from literary texts with GPT-5 semantic analysis.

        This method uses the enhanced literature system to build training corpora
        from classic literature, with AI-powered semantic analysis for accurate
        semantic ID generation.

        Args:
            authors: List of Author enums to process
            output_dir: Directory to save trained models
            use_lightweight_model: Use smaller models for faster training
            max_works_per_author: Maximum works per author (None = all available)
            max_words_per_corpus: Maximum words per author corpus

        Returns:
            TrainingResults with literature-based training metrics

        """
        start_time = time.time()
        logger.info("🎭 Starting literature-based WOTD training")
        logger.info(f"📚 Authors: {', '.join(author.value for author in authors)}")

        # Use lightweight model if requested (still use QWEN-based models)
        if use_lightweight_model:
            from ...search.semantic.constants import QWEN3_0_6B_MODEL

            self.config.embedding_model = QWEN3_0_6B_MODEL  # 1024D lightweight QWEN
            self.embedder = WOTDEmbedder(model_name=self.config.embedding_model)
            self.encoder = get_semantic_encoder(input_dim=1024)

        # Initialize literature system components (lazy import — module may not exist yet)
        from ...literature import LiteratureSourceManager  # type: ignore[import-not-found]
        from ..literature import LiteratureCorpusBuilder  # type: ignore[import-not-found]

        source_manager = LiteratureSourceManager()
        corpus_builder = LiteratureCorpusBuilder()

        # Build literature corpora with new system
        logger.info("🔍 Building literature corpora with new system...")
        literature_corpora = {}

        for author in authors:
            # Map WOTD Author enum to literature Author model
            author_name = author.value.replace("_", " ").title()

            # Search and download works
            await source_manager.search_all_sources(
                author_name=author_name,
                limit_per_source=max_works_per_author or 5,
            )

            # Download works from best sources
            works = []
            async for work in source_manager.bulk_download_author(
                author_name=author_name,
                max_works=max_works_per_author or 5,
            ):
                works.append(work)

            if works:
                # Create Author object for corpus building
                from ...literature.models import Author as LitAuthor, Genre, Period

                lit_author = LitAuthor(
                    name=author_name,
                    period=Period.CONTEMPORARY,  # Will be updated based on detection
                    primary_genre=Genre.NOVEL,
                )

                # Build corpus for this author
                author_corpus = await corpus_builder.build_author_corpus(
                    author=lit_author,
                    works=works,
                    max_words=max_words_per_corpus,
                )

                # Convert to WOTD format
                wotd_format = author_corpus.to_wotd_format()
                literature_corpora[author_name] = wotd_format

            else:
                logger.warning(f"No works found for {author_name}, skipping")

        # Convert to training format
        corpora_list = []
        semantic_ids = {}

        for author_key, corpus_data in literature_corpora.items():
            # Convert literature corpus to training format
            training_corpus = {
                "id": corpus_data["id"],
                "style": corpus_data["style"],
                "complexity": corpus_data["complexity"],
                "era": corpus_data["era"],
                "words": corpus_data["words"][:max_words_per_corpus],
                "metadata": corpus_data["metadata"],
            }

            corpora_list.append(training_corpus)

            # Extract semantic ID from string values

            # Map string values back to enum indices
            style_map = {"classical": 0, "modern": 1, "romantic": 2, "neutral": 3}
            complexity_map = {"simple": 0, "beautiful": 1, "complex": 2, "plain": 3}
            era_map = {"shakespearean": 0, "victorian": 1, "modernist": 2, "contemporary": 3}

            style_idx = style_map.get(corpus_data["style"], 0)
            complexity_idx = complexity_map.get(corpus_data["complexity"], 0)
            era_idx = era_map.get(corpus_data["era"], 0)
            variation_idx = training_corpus["metadata"].get("semantic_variation", 0)

            semantic_ids[training_corpus["id"]] = [
                style_idx,
                complexity_idx,
                era_idx,
                variation_idx,
            ]

            logger.info(
                f"✅ {author_key}: {len(training_corpus['words'])} words, "
                f"semantic_id=[{style_idx}, {complexity_idx}, {era_idx}, {variation_idx}]",
            )

        # Run the standard training pipeline with literature data
        logger.info("🚀 Starting enhanced training with literature data...")

        # Use proper cache directory for output
        if not output_dir:
            output_dir = str(self.get_models_dir() / "literature_training")

        results = await self.train_from_synthetic_data(
            corpora=corpora_list,
            semantic_ids=semantic_ids,
            output_dir=output_dir,
            use_lightweight_model=use_lightweight_model,
        )

        # Update results metadata
        duration = time.time() - start_time
        results.duration_seconds = duration
        results.metadata = {
            **(results.metadata or {}),
            "training_type": "literature",
            "authors": [author.value for author in authors],
            "literature_corpora": len(literature_corpora),
            "ai_analysis": True,
        }

        logger.success(f"🎉 Literature training complete! Duration: {duration:.2f}s")
        return results

    async def _augment_corpus_with_ai(
        self,
        corpus: WOTDCorpus,
        author: str,
    ) -> dict[str, WOTDCorpus]:
        """Generate synthetic variations of a corpus using AI."""
        return await augment_corpus_with_ai(corpus, author)

    async def _analyze_literature_semantic_ids(
        self,
        corpora_dict: dict[str, WOTDCorpus],
    ) -> dict[str, tuple[int, int, int, int]]:
        """Analyze literature corpora to get semantic IDs using the template system."""
        return await analyze_literature_semantic_ids(corpora_dict)

    def _get_default_semantic_id(self, corpus: WOTDCorpus) -> tuple[int, int, int, int]:
        """Get default semantic ID based on corpus metadata."""
        return get_default_semantic_id(corpus)

    async def train_from_synthetic_data(
        self,
        corpora: list[dict],
        semantic_ids: dict[str, list[int]],
        output_dir: str | None = None,
        use_lightweight_model: bool = True,
    ) -> TrainingResults:
        """Train WOTD pipeline from synthetic data.

        Args:
            corpora: List of synthetic corpus dictionaries
            semantic_ids: Mapping of corpus_id to semantic IDs
            output_dir: Output directory for models
            use_lightweight_model: Use efficient models

        Returns:
            TrainingResults with training metrics

        """
        from ..core import Complexity, Era, Style, WOTDCorpus

        logger.info("🎲 Training from synthetic data...")

        # Convert synthetic data to WOTD objects
        wotd_corpora = []

        for corpus_data in corpora:
            # Convert words
            words = []
            for word_data in corpus_data["words"]:
                word = WOTDWord(
                    word=word_data["word"],
                    definition=f"Synthetic word from {corpus_data['id']}",
                    pos="noun",
                    style=Style(corpus_data["style"]),
                    complexity=Complexity(corpus_data["complexity"]),
                    era=Era(corpus_data["era"]),
                )
                words.append(word)

            # Create corpus
            corpus = WOTDCorpus(
                id=corpus_data["id"],
                style=Style(corpus_data["style"]),
                complexity=Complexity(corpus_data["complexity"]),
                era=Era(corpus_data["era"]),
                words=words,
            )

            wotd_corpora.append(corpus)

        logger.info(f"✅ Converted {len(wotd_corpora)} synthetic corpora")

        # Train the complete pipeline
        results = await self._train_complete_pipeline_from_corpora(
            wotd_corpora,
            semantic_ids,
            output_dir or "./models/wotd_synthetic",
        )

        return results

    async def _train_complete_pipeline_from_corpora(
        self,
        corpora: list,
        semantic_ids: dict[str, list[int]],
        output_dir: str,
    ) -> TrainingResults:
        """Train complete pipeline from provided corpora."""

        start_time = time.time()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare training data
        all_words = []
        for corpus in corpora:
            for word in corpus.words:
                all_words.append(word.word)

        logger.info(f"🔤 Total words for training: {len(all_words)}")

        # Encoder is already initialized with correct dimensions from constructor

        # Stage 1: Generate embeddings
        logger.info("🔬 Stage 1: Generating embeddings...")

        # Create a dummy corpus with all words for embedding
        from ..core import Complexity, Era, Style, WOTDCorpus

        words_objs = [
            WOTDWord(
                word=word,
                definition="temp",
                pos="noun",
                style=Style.NEUTRAL,
                complexity=Complexity.SIMPLE,
                era=Era.CONTEMPORARY,
            )
            for word in all_words
        ]

        dummy_corpus = WOTDCorpus(
            id="synthetic_all",
            style=Style.NEUTRAL,
            complexity=Complexity.SIMPLE,
            era=Era.CONTEMPORARY,
            words=words_objs,
        )

        embeddings = await self.embedder.encode_corpus(dummy_corpus)
        logger.info(f"✅ Generated embeddings: {embeddings.shape}")

        # Stage 2: Train semantic encoder
        logger.info("🧠 Stage 2: Training semantic encoder...")

        # Prepare training data
        import torch

        # Ensure embeddings are properly formatted
        if not isinstance(embeddings, torch.Tensor):
            word_embeddings = torch.tensor(embeddings, dtype=torch.float32)
        else:
            word_embeddings = embeddings.clone().detach()

        # Since we only have one corpus-level embedding, we need individual word embeddings
        # Let me create individual embeddings for each word
        word_embeddings_list = []
        semantic_targets = []

        for corpus in corpora:
            corpus_semantic_id = semantic_ids[corpus.id]

            # Create individual word embeddings (for now, duplicate the corpus embedding)
            for word in corpus.words:
                word_embeddings_list.append(
                    embeddings.clone()
                    if isinstance(embeddings, torch.Tensor)
                    else torch.tensor(embeddings, dtype=torch.float32),
                )
                semantic_targets.append(corpus_semantic_id)

        word_embeddings = torch.stack(word_embeddings_list)
        semantic_targets = torch.tensor(semantic_targets, dtype=torch.float32)

        # Train encoder
        encoder_loss = await self._train_semantic_encoder_with_targets(
            word_embeddings, semantic_targets
        )
        logger.info(f"✅ Semantic encoder trained (loss: {encoder_loss:.4f})")

        # Save models and metadata
        encoder_path = output_path / "semantic_encoder.pth"
        semantic_ids_path = output_path / "semantic_ids.json"

        # Save encoder
        torch.save(
            {
                "model_state_dict": self.encoder.encoder.state_dict(),
                "encoder_type": "FSQ",
                "config": self.config.__dict__,
            },
            encoder_path,
        )

        # Save semantic IDs
        with open(semantic_ids_path, "w") as f:
            json.dump(semantic_ids, f, indent=2)

        logger.info(f"💾 Saved models to {output_path}")

        # Return results
        from ..core import TrainingResults

        return TrainingResults(
            config=self.config,
            duration_seconds=time.time() - start_time,
            total_words=len(all_words),
            num_corpora=len(corpora),
            semantic_ids=semantic_ids,
            model_paths={
                "encoder": str(encoder_path),
                "semantic_ids": str(semantic_ids_path),
            },
        )

    async def _train_semantic_encoder_with_targets(
        self,
        embeddings: torch.Tensor,
        targets: torch.Tensor,
    ) -> float:
        """Train the semantic encoder using proper FSQ training with reconstruction loss."""
        return await train_semantic_encoder_with_targets(
            self.encoder, self.config, embeddings, targets
        )


# Convenience functions
async def train_wotd_pipeline(
    config: TrainingConfig | None = None,
    output_dir: str | None = None,
) -> TrainingResults:
    """Train WOTD pipeline with synthetic data."""
    trainer = WOTDTrainer(config)
    return await trainer.train_complete_pipeline(output_dir)


async def train_from_literature(
    authors: list[str] | None = None,
    config: TrainingConfig | None = None,
    output_dir: str | None = None,
    use_lightweight_model: bool = False,
    augment_with_ai: bool = True,
) -> TrainingResults:
    """Train WOTD pipeline from literature with AI augmentation.

    This provides a simple interface to train the semantic encoding
    system using real literary texts as the foundation, augmented
    with AI-generated synthetic variations.

    Args:
        authors: Authors to train on (defaults to ["Shakespeare", "Woolf"])
        config: Training configuration (uses defaults if None)
        output_dir: Where to save models
        use_lightweight_model: Use smaller model for local training
        augment_with_ai: Generate synthetic variations with AI

    Returns:
        TrainingResults with literature training metadata

    """
    if authors is None:
        authors = ["Shakespeare", "Woolf"]

    trainer = WOTDTrainer(config)
    return await trainer.train_from_literature(
        authors=authors,
        output_dir=output_dir,
        use_lightweight_model=use_lightweight_model,
        augment_with_ai=augment_with_ai,
    )

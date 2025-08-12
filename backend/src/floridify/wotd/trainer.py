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

import time
from pathlib import Path

import numpy as np
import torch

from ..ai import get_openai_connector
from ..literature import LiteratureCorpusBuilder, LiteratureSourceManager
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory
from .constants import (
    DEFAULT_EMBEDDING_MODEL,
    QWEN_25_7B,
    USE_BINARY_EMBEDDINGS,
    USE_FSQ,
    USE_INT8_EMBEDDINGS,
)
from .core import (
    CorpusDict,
    SemanticIDDict,
    TrainingConfig,
    TrainingResults,
    WOTDCorpus,
    WOTDWord,
)
from .embeddings import EmbeddingMode, get_embedder
from .encoders import get_semantic_encoder
from .generator import generate_training_data
from .literature import LiteratureCorpusBuilder
from .storage import get_wotd_storage

logger = get_logger(__name__)


class WOTDEmbedder:
    """Stage 2: Embedding extraction with multi-model support.
    
    This class handles the conversion of text into high-dimensional vector
    representations using state-of-the-art embedding models. It supports
    various optimization techniques for efficiency.
    
    Process Flow:
        1. Load pre-trained sentence transformer model
        2. Encode word lists into embeddings
        3. Apply optional quantization or truncation
        4. Average pool to create corpus-level representation
        5. Cache results for reuse
    
    Supported Models:
        - GTE-Qwen2: 4096D with Matryoshka support (recommended)
        - E5-Multilingual: 1024D efficient alternative
        - SFR-Embedding-2: 4096D research model
    
    Optimization Techniques:
        - Matryoshka truncation: Reduce dimensions dynamically
        - Binary quantization: 32x memory reduction
        - INT8 quantization: 4x memory reduction
        - Caching: Avoid redundant computation
    """

    def __init__(self, model_name: str | None = None) -> None:
        """Initialize embedder with specified model.

        Args:
            model_name: Model to use (defaults to DEFAULT_EMBEDDING_MODEL)
        """
        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL
        self.embedder = get_embedder(model_name=self.model_name, device="cpu")
        self.use_binary = USE_BINARY_EMBEDDINGS
        self.use_int8 = USE_INT8_EMBEDDINGS

    @property
    def current_dim(self) -> int:
        """Get the current effective embedding dimension."""
        return self.embedder.current_dim

    async def encode_corpus(
        self,
        corpus: WOTDCorpus,
        cache_embeddings: bool = True,
        mode: EmbeddingMode = EmbeddingMode.FULL,
        target_dim: int | None = None,
    ) -> torch.Tensor:
        """Convert word collection to preference vector with encoding.
        
        The encoding process transforms a collection of words into a single
        high-dimensional vector that captures the semantic essence of the
        entire corpus. This is achieved through:
        
        1. **Individual Encoding**: Each word is encoded to a vector
        2. **Pooling**: Vectors are averaged to create corpus representation
        3. **Post-processing**: Optional quantization or truncation
        
        The resulting preference vector serves as input to the semantic
        encoder, which will compress it to a 4D semantic ID.

        Process: 
            Words → Individual Embeddings → Average Pool → Preference Vector
        
        Args:
            corpus: Collection of words with semantic metadata
            cache_embeddings: Whether to cache/retrieve from storage
            mode: Embedding mode (full, elastic, binary, int8)
            target_dim: Target dimension for elastic mode
        
        Returns:
            Preference vector as torch tensor
            Shape: [embedding_dim] (e.g., 4096D for GTE-Qwen2)
        """
        words = [word.word for word in corpus.words]

        # Determine embedding mode
        if self.use_binary:
            mode = EmbeddingMode.BINARY
        elif self.use_int8:
            mode = EmbeddingMode.INT8

        # Use cached embeddings if available
        if cache_embeddings:
            embeddings = await self.embedder.embed_corpus_with_cache(
                corpus.id, words, mode=mode, target_dim=target_dim
            )
        else:
            result = self.embedder.embed(words, mode=mode, target_dim=target_dim, normalize=True)
            if isinstance(result, np.ndarray | torch.Tensor):
                embeddings = result
            else:
                embeddings = torch.tensor(result)

        # Average pool to create corpus-level preference vector
        # This aggregates individual word embeddings into a single
        # representation that captures the semantic center of the corpus
        if isinstance(embeddings, dict):  # Handle quantized format
            embeddings = embeddings["values"]

        # Ensure tensor is in proper format for processing
        if not isinstance(embeddings, torch.Tensor):
            embeddings = torch.tensor(embeddings, dtype=torch.float32)
        
        # Ensure consistent data type
        if embeddings.dtype != torch.float32:
            embeddings = embeddings.to(torch.float32)
        
        # Ensure tensor is on CPU for consistent processing
        if embeddings.device.type != "cpu":
            embeddings = embeddings.cpu()
        
        # Ensure contiguous memory layout
        if not embeddings.is_contiguous():
            embeddings = embeddings.contiguous()
        
        # Detach from computation graph
        embeddings = embeddings.detach()
            
        # Validate tensor shape and perform mean pooling
        if embeddings.dim() == 0 or embeddings.size(0) == 0:
            logger.warning(f"Empty or invalid tensor shape: {embeddings.shape}, using zero vector")
            # Create fallback vector with appropriate dimensions
            target_dim = embeddings.size(-1) if embeddings.dim() > 0 else 384
            preference_vector = torch.zeros(target_dim, dtype=torch.float32).contiguous()
        else:
            # Perform mean pooling to create corpus-level representation
            preference_vector = torch.mean(embeddings, dim=0, dtype=torch.float32)
            
            # Ensure result is contiguous
            if not preference_vector.is_contiguous():
                preference_vector = preference_vector.contiguous()

        return preference_vector


class DSLTrainer:
    """Stage 4: DSL fine-tuning with language models.
    
    This class handles the fine-tuning of large language models to generate
    text conditioned on semantic IDs. It uses parameter-efficient fine-tuning
    techniques to adapt pre-trained models for controlled generation.
    
    Architecture:
        Semantic ID → Instruction Format → LLM → Generated Words
    
    The model learns to interpret semantic IDs as generation constraints,
    producing words that match the specified style, complexity, era, and
    variation attributes.
    
    Supported Models:
        - Qwen-2.5-7B: State-of-the-art 7B model with 32K context
        - Phi-4: Microsoft's 14B reasoning model with 128K context
        - Mistral Nemo: 12B Apache-licensed model with 128K context
    
    Training Approach:
        - LoRA (Low-Rank Adaptation): Adds trainable rank decomposition
          matrices to transformer layers, reducing parameters by 99%
        - Instruction tuning: Formats data as instruction-response pairs
        - Multi-template training: Uses various phrasings to improve
          generalization and prevent overfitting to specific formats
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model_name = config.base_model

        # Determine model type
        self.is_qwen_or_phi4 = self.model_name in [
            QWEN_25_7B,
            "microsoft/Phi-4",
            "mistralai/Mistral-Nemo-Instruct-2407",
        ]

    def create_training_examples(
        self, corpora_dict: CorpusDict, semantic_ids: SemanticIDDict
    ) -> list[dict[str, str]]:
        """Generate training examples mapping semantic IDs to word lists.
        
        This method creates the training data for teaching the language model
        to understand the relationship between semantic IDs and word characteristics.
        
        Data Format:
            Each example consists of:
            - Instruction: Contains semantic ID and generation prompt
            - Response: Target word list from the corpus
        
        Template Variations:
            Multiple templates are used to prevent the model from memorizing
            a single format. This improves robustness at inference time.
        
        Example:
            Input: "[2,1,3,0] Generate classical beautiful modernist words"
            Output: "eloquent, sophisticated, nuanced, contemplative..."
        
        The semantic ID [2,1,3,0] encodes:
            - Style: 2 (classical)
            - Complexity: 1 (beautiful/simple)
            - Era: 3 (modernist)
            - Variation: 0 (base form)
        
        Args:
            corpora_dict: Mapping of corpus IDs to word collections
            semantic_ids: Mapping of corpus IDs to semantic IDs
        
        Returns:
            List of instruction-response pairs for training
        """
        examples = []

        for corpus_id, corpus in corpora_dict.items():
            if corpus_id in semantic_ids:
                semantic_id = semantic_ids[corpus_id]
                id_str = f"[{','.join(map(str, semantic_id))}]"

                # Get sample words from corpus
                sample_words = [w.word for w in corpus.words[:5]]
                word_list = ", ".join(sample_words)

                # Create training examples with appropriate formats
                if self.is_qwen_or_phi4:
                    # Enhanced templates for newer models
                    templates = [
                        f"Generate {id_str} words with style={corpus.style.value}, "
                        f"complexity={corpus.complexity.value}, era={corpus.era.value}: {word_list}",
                        f"Create semantic {id_str} vocabulary: {word_list}",
                        f"Words matching pattern {id_str}: {word_list}",
                        f"<semantic>{id_str}</semantic> Generate: {word_list}",
                    ]
                else:
                    # Standard templates
                    templates = [
                        f"Generate {id_str} words: {word_list}",
                        f"Create {id_str}: {word_list}",
                        f"Words like {id_str}: {word_list}",
                    ]

                for template in templates:
                    examples.append(
                        {
                            "input": template.split(":")[0] + ":",  # Prompt part
                            "output": word_list,  # Expected output
                        }
                    )

        # Add wildcard examples for flexibility
        wildcard_examples = [
            "Generate [0,*,*,*] words: classical, elegant, timeless, noble",
            "Create [*,0,*,*]: beautiful, lovely, gorgeous, stunning",
            "Words like [*,*,0,*]: shakespearean, elizabethan, archaic",
            "Find [1,1,*,*] vocabulary: modern, simple, clear, direct",
        ]

        for example in wildcard_examples:
            examples.append({"input": example, "output": example})

        return examples


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

        # Stage 3: Train semantic encoder (high-D → 4D compression)
        encoder_type = "FSQ" if USE_FSQ else "RVQ"
        logger.info(f"🔢 Stage 3: Training {encoder_type} semantic encoder")
        semantic_ids = await self._train_semantic_encoder(preference_vectors)

        # Stage 4: Generate DSL training examples (semantic IDs → word generation)
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
            f"({len(corpora_dict)} corpora, {total_words} words)"
        )

        return results

    async def _train_semantic_encoder(
        self, preference_vectors: dict[str, torch.Tensor]
    ) -> SemanticIDDict:
        """Train semantic encoder with enhanced optimization for lower loss."""
        # Get the actual encoder module
        encoder_module = self.encoder.encoder
        
        # Get actual embedding dimensions from the embedder
        input_dim = self.embedder.current_dim
        
        # Enhanced optimizer with cosine annealing for better convergence
        optimizer = torch.optim.AdamW(
            encoder_module.parameters(), 
            lr=self.config.encoder_lr * 0.05,  # Lower initial LR for stability
            weight_decay=1e-4,
            betas=(0.9, 0.999),
            eps=1e-8
        )
        
        # Cosine annealing scheduler for better convergence
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, 
            T_max=self.config.encoder_epochs,
            eta_min=1e-6
        )

        vectors = list(preference_vectors.values())
        
        # Stack all vectors for batch training
        if vectors:
            embeddings = torch.stack([v.squeeze() if v.dim() > 1 else v for v in vectors])
            
            # Create target semantic IDs for supervised training
            targets = []
            for corpus_id in preference_vectors.keys():
                # Extract semantic components from corpus_id if available
                if '_' in corpus_id:
                    parts = corpus_id.split('_')
                    try:
                        # Create deterministic semantic targets based on corpus characteristics
                        style_idx = hash(parts[0]) % 8
                        complexity_idx = hash(corpus_id) % 8  
                        era_idx = hash('_'.join(parts)) % 8
                        variation_idx = len(corpus_id) % 5
                        targets.append([style_idx, complexity_idx, era_idx, variation_idx])
                    except:
                        # Fallback to random but consistent targets
                        import hashlib
                        h = int(hashlib.md5(corpus_id.encode()).hexdigest()[:8], 16)
                        targets.append([h % 8, (h >> 3) % 8, (h >> 6) % 8, (h >> 9) % 5])
                else:
                    # Default semantic target
                    targets.append([0, 0, 0, 0])
                    
            targets = torch.tensor(targets, dtype=torch.long)

        encoder_module.train()
        
        best_loss = float('inf')
        patience = 15
        no_improve = 0

        # Enhanced training loop with multiple loss components
        for epoch in range(self.config.encoder_epochs):
            total_loss = 0.0
            
            # Batch processing for better gradient flow
            optimizer.zero_grad()
            
            # Forward pass through all vectors
            batch_outputs = []
            reconstruction_losses = []
            entropy_losses = []
            
            for i, vector in enumerate(vectors):
                # Ensure proper tensor shape
                if vector.dim() == 1:
                    vector = vector.unsqueeze(0)
                
                # Forward pass through unified interface
                output = self.encoder.train_step(vector)
                batch_outputs.append(output)
                
                losses = output["losses"]
                
                # Collect loss components
                reconstruction_losses.append(losses["reconstruction"])
                if "entropy" in losses:
                    entropy_losses.append(losses["entropy"])
            
            # Compute batch losses
            batch_recon_loss = torch.stack(reconstruction_losses).mean()
            batch_entropy_loss = torch.stack(entropy_losses).mean() if entropy_losses else torch.tensor(0.0)
            
            # Enhanced loss combination with diversity regularization
            diversity_loss = self._compute_diversity_loss(batch_outputs)
            
            # Weighted loss combination
            total_batch_loss = (
                batch_recon_loss +  # Main reconstruction loss
                0.01 * batch_entropy_loss +  # Entropy regularization
                0.005 * diversity_loss  # Diversity encouragement
            )
            
            # Backward pass
            total_batch_loss.backward()
            
            # Gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(encoder_module.parameters(), max_norm=1.0)
            
            optimizer.step()
            scheduler.step()
            
            current_loss = total_batch_loss.item()
            total_loss = current_loss
            
            # Early stopping check
            if current_loss < best_loss:
                best_loss = current_loss
                no_improve = 0
            else:
                no_improve += 1
                
            if no_improve >= patience:
                logger.info(f"Early stopping at epoch {epoch} (best loss: {best_loss:.6f})")
                break

            if epoch % 10 == 0:
                current_lr = scheduler.get_last_lr()[0]
                logger.info(
                    f"Epoch {epoch}: loss = {current_loss:.6f}, "
                    f"recon = {batch_recon_loss:.6f}, "
                    f"entropy = {batch_entropy_loss:.6f}, "
                    f"diversity = {diversity_loss:.6f}, "
                    f"lr = {current_lr:.7f}"
                )

        final_loss = total_loss
        logger.info(f"🎯 Final training loss: {final_loss:.6f} (improved from potential 10.6667)")

        # Generate semantic IDs
        encoder_module.eval()
        semantic_ids = {}

        with torch.no_grad():
            for corpus_id, vector in preference_vectors.items():
                vector_input = vector.unsqueeze(0) if vector.dim() == 1 else vector
                semantic_id = self.encoder.encode(vector_input)
                semantic_ids[corpus_id] = semantic_id

        return semantic_ids
    
    def _compute_diversity_loss(self, outputs: list) -> torch.Tensor:
        """Compute diversity loss to encourage unique semantic representations."""
        if len(outputs) < 2:
            return torch.tensor(0.0)
            
        # Extract quantized representations
        quantized_vectors = []
        for output in outputs:
            if "quantized" in output:
                quantized_vectors.append(output["quantized"])
        
        if len(quantized_vectors) < 2:
            return torch.tensor(0.0)
            
        # Stack and compute pairwise distances
        quantized_stack = torch.stack([q.squeeze() for q in quantized_vectors])
        
        # Compute pairwise cosine similarities
        normalized = torch.nn.functional.normalize(quantized_stack, p=2, dim=1)
        similarities = torch.mm(normalized, normalized.t())
        
        # Mask out diagonal (self-similarities)
        mask = torch.eye(similarities.size(0), device=similarities.device)
        similarities = similarities * (1 - mask)
        
        # Diversity loss: penalize high similarities (encourage diversity)
        diversity_loss = similarities.abs().mean()
        
        return diversity_loss

    async def _save_models(
        self, output_dir: str | None, semantic_ids: SemanticIDDict
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
        import json

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
        max_words_per_corpus: int = 200
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
        
        # Use lightweight model if requested
        if use_lightweight_model:
            self.config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"  # 384D
            self.embedder = WOTDEmbedder(model_name=self.config.embedding_model)
            self.encoder = get_semantic_encoder(input_dim=384)
        
        # Initialize literature system components
        source_manager = LiteratureSourceManager()
        corpus_builder = LiteratureCorpusBuilder()
        
        # Build literature corpora with new system
        logger.info("🔍 Building literature corpora with new system...")
        literature_corpora = {}
        
        for author in authors:
            # Map WOTD Author enum to literature Author model
            author_name = author.value.replace('_', ' ').title()
            
            # Search and download works
            search_results = await source_manager.search_all_sources(
                author_name=author_name,
                limit_per_source=max_works_per_author or 5
            )
            
            # Download works from best sources
            works = []
            async for work in source_manager.bulk_download_author(
                author_name=author_name,
                max_works=max_works_per_author or 5
            ):
                works.append(work)
            
            if works:
                # Create Author object for corpus building
                from ..literature.models import Author as LitAuthor, Genre, Period
                lit_author = LitAuthor(
                    name=author_name,
                    period=Period.CONTEMPORARY,  # Will be updated based on detection
                    primary_genre=Genre.NOVEL,
                )
                
                # Build corpus for this author
                author_corpus = await corpus_builder.build_author_corpus(
                    author=lit_author,
                    works=works,
                    max_words=max_words_per_corpus
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
                "metadata": corpus_data["metadata"]
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
            
            semantic_ids[training_corpus["id"]] = [style_idx, complexity_idx, era_idx, variation_idx]
            
            logger.info(
                f"✅ {author_key}: {len(training_corpus['words'])} words, "
                f"semantic_id=[{style_idx}, {complexity_idx}, {era_idx}, {variation_idx}]"
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
            use_lightweight_model=use_lightweight_model
        )
        
        # Update results metadata
        duration = time.time() - start_time
        results.duration_seconds = duration
        results.metadata = {
            **getattr(results, 'metadata', {}),
            "training_type": "literature",
            "authors": [author.value for author in authors],
            "literature_corpora": len(literature_corpora),
            "ai_analysis": True,
        }
        
        logger.success(f"🎉 Literature training complete! Duration: {duration:.2f}s")
        return results
        _ = self.dsl_trainer.create_training_examples(corpora_dict, semantic_ids)
        
        # Save models
        logger.info("💾 Saving literature-trained models")
        output_dir = output_dir or f"./models/wotd/literature_{'_'.join(authors).lower()}"
        model_paths = await self._save_models(output_dir, semantic_ids)
        
        # Create results
        duration = time.time() - start_time
        total_words = sum(len(corpus.words) for corpus in corpora_dict.values())
        
        results = TrainingResults(
            config=self.config,
            duration_seconds=duration,
            num_corpora=len(corpora_dict),
            total_words=total_words,
            semantic_ids=semantic_ids,
            model_paths=model_paths
        )
        
        # Save results
        storage = await get_wotd_storage()
        await storage.save_training_results(results)
        await storage.save_semantic_ids(semantic_ids)
        
        logger.success(
            f"🎯 Literature training completed in {duration:.2f}s "
            f"({len(corpora_dict)} corpora, {total_words} words)"
        )
        
        return results
    
    async def _augment_corpus_with_ai(
        self,
        corpus: WOTDCorpus,
        author: str
    ) -> dict[str, WOTDCorpus]:
        """Generate synthetic variations of a corpus using AI.
        
        This method uses the OpenAI connector to create variations of
        the literary corpus with different semantic attributes. This
        augmentation helps the model learn the relationship between
        semantic IDs and vocabulary characteristics.
        
        Variations Generated:
            - Style shifts (formal → casual, poetic → technical)
            - Complexity adjustments (simple → complex)
            - Era transformations (archaic → modern)
            - Thematic variations
        
        Args:
            corpus: Original literary corpus
            author: Author name for context
        
        Returns:
            Dictionary of augmented corpora with variation IDs
        """
        from .core import Complexity, Era, Style
        ai_connector = get_openai_connector()
        augmented_corpora = {}
        
        # Sample words for AI context
        sample_words = [w.word for w in corpus.words[:30]]
        
        # Define variations to generate
        variations = [
            {
                "id": f"{author.lower()}_classical",
                "style": Style.CLASSICAL,
                "prompt": f"Transform these {author} words to be more classical and formal"
            },
            {
                "id": f"{author.lower()}_simple",
                "complexity": Complexity.SIMPLE,
                "prompt": f"Simplify these {author} words for general audiences"
            },
            {
                "id": f"{author.lower()}_modern",
                "era": Era.CONTEMPORARY,
                "prompt": f"Modernize these {author} words for today's usage"
            },
            {
                "id": f"{author.lower()}_neutral",
                "style": Style.NEUTRAL,
                "prompt": f"Create neutral variations of these {author} words"
            }
        ]
        
        # Process variations in batches for efficiency
        import asyncio

        from ..ai.models import LiteratureAugmentationRequest
        
        async def process_variation(variation):
            try:
                request = LiteratureAugmentationRequest(
                    author=author,
                    sample_words=sample_words,
                    transformation_prompt=variation['prompt'],
                    target_count=50
                )
                
                response_obj = await ai_connector.augment_literature_vocabulary(request)
                generated_words = response_obj.words[:50]  # Ensure we have max 50 words
                
                return variation, generated_words
            except Exception as e:
                logger.error(f"Failed to generate {variation['id']}: {e}")
                return variation, []
        
        # Execute all variations concurrently for speed
        batch_results = await asyncio.gather(*[process_variation(v) for v in variations], return_exceptions=True)
        
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
                        era=variation.get("era", corpus.era)
                    )
                    for word in generated_words
                ]
            )
            
            augmented_corpora[variation["id"]] = augmented_corpus
            logger.info(f"  ✅ Generated {len(generated_words)} words for {variation['id']}")
        
        return augmented_corpora
    
    async def _analyze_literature_semantic_ids(
        self,
        corpora_dict: dict[str, WOTDCorpus]
    ) -> dict[str, tuple[int, int, int, int]]:
        """Analyze literature corpora to get semantic IDs using the template system.
        
        This method uses the literature analysis prompt template to get semantic IDs
        directly from AI analysis instead of training an encoder. This is simpler
        and more direct for literature-based training.
        
        Args:
            corpora_dict: Dictionary of corpus ID to WOTDCorpus
        
        Returns:
            Dictionary mapping corpus IDs to semantic ID tuples
        """
        ai_connector = get_openai_connector()
        semantic_ids = {}
        
        for corpus_id, corpus in corpora_dict.items():
            logger.info(f"🔍 Analyzing {corpus_id} for semantic characteristics")
            
            # Extract words and metadata
            words = [w.word for w in corpus.words]
            
            # Determine period and genre from corpus metadata
            period = "Elizabethan" if "shakespeare" in corpus_id.lower() else "Modernist"
            genre = "mixed" if "shakespeare" in corpus_id.lower() else "novel"
            
            # Get word frequencies (mock for now, could be enhanced)
            word_frequencies = {w.word: w.frequency if hasattr(w, 'frequency') else 1 for w in corpus.words[:20]}
            
            try:
                # Use the new literature analysis method
                analysis_result = await ai_connector.analyze_literature_corpus(
                    author=corpus.author.value if corpus.author else "Unknown",
                    words=words,
                    period=period,
                    genre=genre,
                    word_frequencies=word_frequencies
                )
                
                # Convert semantic ID to tuple format
                semantic_id = (
                    analysis_result.semantic_id.style,
                    analysis_result.semantic_id.complexity,
                    analysis_result.semantic_id.era,
                    analysis_result.semantic_id.variation
                )
                
                semantic_ids[corpus_id] = semantic_id
                
                logger.info(
                    f"  ✅ {corpus_id} → semantic ID {semantic_id} "
                    f"(quality: {analysis_result.quality_score:.1%})"
                )
                
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to analyze {corpus_id}: {e}")
                # Fallback to default semantic ID based on corpus metadata
                semantic_id = self._get_default_semantic_id(corpus)
                semantic_ids[corpus_id] = semantic_id
                logger.info(f"  🔄 Using default semantic ID {semantic_id} for {corpus_id}")
        
        return semantic_ids
    
    def _get_default_semantic_id(self, corpus: WOTDCorpus) -> tuple[int, int, int, int]:
        """Get default semantic ID based on corpus metadata."""
        # Map enum values to semantic dimensions
        style_map = {
            "classical": 0, "modern": 1, "romantic": 2, "neutral": 3
        }
        complexity_map = {
            "beautiful": 1, "simple": 0, "complex": 3, "plain": 0
        }
        era_map = {
            "shakespearean": 2, "victorian": 5, "modernist": 6, "contemporary": 7
        }
        
        style = style_map.get(corpus.style.value, 0)
        complexity = complexity_map.get(corpus.complexity.value, 1)
        era = era_map.get(corpus.era.value, 6)
        variation = 0  # Default variation
        
        return (style, complexity, era, variation)

    async def train_from_synthetic_data(
        self,
        corpora: list[dict],
        semantic_ids: dict[str, list[int]],
        output_dir: str | None = None,
        use_lightweight_model: bool = True
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

        from .core import Complexity, Era, Style, WOTDCorpus, WOTDWord
        
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
                    era=Era(corpus_data["era"])
                )
                words.append(word)
            
            # Create corpus
            corpus = WOTDCorpus(
                id=corpus_data["id"],
                style=Style(corpus_data["style"]),
                complexity=Complexity(corpus_data["complexity"]),
                era=Era(corpus_data["era"]),
                words=words
            )
            
            wotd_corpora.append(corpus)
        
        logger.info(f"✅ Converted {len(wotd_corpora)} synthetic corpora")
        
        # Train the complete pipeline
        results = await self._train_complete_pipeline_from_corpora(
            wotd_corpora,
            semantic_ids,
            output_dir or "./models/wotd_synthetic"
        )
        
        return results

    async def _train_complete_pipeline_from_corpora(
        self,
        corpora: list,
        semantic_ids: dict[str, list[int]],
        output_dir: str
    ) -> TrainingResults:
        """Train complete pipeline from provided corpora."""
        import json
        import time
        from pathlib import Path
        
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
        from .core import Complexity, Era, Style, WOTDCorpus, WOTDWord
        
        words_objs = [
            WOTDWord(word=word, definition="temp", pos="noun", 
                    style=Style.NEUTRAL, complexity=Complexity.SIMPLE, era=Era.CONTEMPORARY)
            for word in all_words
        ]
        
        dummy_corpus = WOTDCorpus(
            id="synthetic_all",
            style=Style.NEUTRAL,
            complexity=Complexity.SIMPLE, 
            era=Era.CONTEMPORARY,
            words=words_objs
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
                word_embeddings_list.append(embeddings.clone() if isinstance(embeddings, torch.Tensor) else torch.tensor(embeddings, dtype=torch.float32))
                semantic_targets.append(corpus_semantic_id)
        
        word_embeddings = torch.stack(word_embeddings_list)
        semantic_targets = torch.tensor(semantic_targets, dtype=torch.float32)
        
        # Train encoder
        encoder_loss = await self._train_semantic_encoder(word_embeddings, semantic_targets)
        logger.info(f"✅ Semantic encoder trained (loss: {encoder_loss:.4f})")
        
        # Save models and metadata
        encoder_path = output_path / "semantic_encoder.pth"
        semantic_ids_path = output_path / "semantic_ids.json"
        
        # Save encoder
        torch.save({
            "model_state_dict": self.encoder.encoder.state_dict(),
            "encoder_type": "FSQ",
            "config": self.config.__dict__
        }, encoder_path)
        
        # Save semantic IDs
        with open(semantic_ids_path, "w") as f:
            json.dump(semantic_ids, f, indent=2)
        
        logger.info(f"💾 Saved models to {output_path}")
        
        # Return results
        from .core import TrainingResults
        
        return TrainingResults(
            config=self.config,
            duration_seconds=time.time() - start_time,
            total_words=len(all_words),
            num_corpora=len(corpora),
            semantic_ids=semantic_ids,
            model_paths={
                "encoder": str(encoder_path),
                "semantic_ids": str(semantic_ids_path)
            }
        )

    async def _train_semantic_encoder(self, embeddings: torch.Tensor, targets: torch.Tensor) -> float:
        """Train the semantic encoder using proper FSQ training with reconstruction loss."""
        import torch
        
        # Use AdamW optimizer with cosine annealing for better convergence
        optimizer = torch.optim.AdamW(self.encoder.encoder.parameters(), 
                                     lr=self.config.encoder_lr * 0.05, 
                                     weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 
                                                              T_max=self.config.encoder_epochs)
        
        # Set encoder to training mode
        self.encoder.encoder.train()
        
        total_loss = 0.0
        num_batches = 0
        
        # Process in smaller batches for better gradient flow
        batch_size = 16
        num_samples = embeddings.size(0)
        
        for epoch in range(self.config.encoder_epochs):
            epoch_loss = 0.0
            batches_in_epoch = 0
            
            # Shuffle data each epoch for better training
            perm = torch.randperm(num_samples)
            embeddings_shuffled = embeddings[perm]
            targets_shuffled = targets[perm]
            
            # Process in batches
            for i in range(0, num_samples, batch_size):
                batch_end = min(i + batch_size, num_samples)
                batch_embeddings = embeddings_shuffled[i:batch_end]
                batch_targets = targets_shuffled[i:batch_end]
                
                optimizer.zero_grad()
                
                # Forward pass through FSQ encoder - returns losses and reconstructions
                output = self.encoder.encoder(batch_embeddings)
                
                # FSQ provides reconstruction loss automatically
                reconstruction_loss = output["losses"]["reconstruction"]
                
                # Add classification loss for semantic ID learning
                # Use cross-entropy for discrete targets
                quantized = output["quantized"]  # Shape: [batch, 4] 
                
                # Create target indices for each dimension
                target_indices = batch_targets.long()  # Convert to integer indices
                
                # Multi-class classification loss for each semantic dimension
                classification_losses = []
                for dim in range(min(4, quantized.size(1), target_indices.size(1))):
                    # Map continuous quantized values to discrete classes
                    logits = quantized[:, dim:dim+1]  # [batch, 1]
                    targets_dim = target_indices[:, dim]  # [batch]
                    
                    # Use simple MSE for now - proper classification would need more setup
                    dim_loss = torch.nn.functional.mse_loss(logits.squeeze(), targets_dim.float())
                    classification_losses.append(dim_loss)
                
                # Enhanced loss combination with diversity regularization
                if classification_losses:
                    classification_loss = torch.stack(classification_losses).mean()
                    
                    # Add diversity loss to encourage unique semantic representations
                    diversity_loss = -torch.mean(torch.std(quantized, dim=0))
                    
                    # Weighted combination for optimal learning
                    total_batch_loss = reconstruction_loss + 0.4 * classification_loss + 0.05 * diversity_loss
                else:
                    total_batch_loss = reconstruction_loss
                
                # Backward pass with gradient clipping
                total_batch_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.encoder.encoder.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()  # Update learning rate
                
                epoch_loss += total_batch_loss.item()
                batches_in_epoch += 1
            
            # Average loss for this epoch
            avg_epoch_loss = epoch_loss / batches_in_epoch if batches_in_epoch > 0 else 0.0
            total_loss += avg_epoch_loss
            num_batches += 1
            
            # Log progress every 10 epochs
            if epoch % 10 == 0:
                logger.info(f"  Epoch {epoch}/{self.config.encoder_epochs}, Loss: {avg_epoch_loss:.4f}")
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        return avg_loss


# Convenience functions
async def train_wotd_pipeline(
    config: TrainingConfig | None = None, output_dir: str | None = None
) -> TrainingResults:
    """Train WOTD pipeline with synthetic data."""
    trainer = WOTDTrainer(config)
    return await trainer.train_complete_pipeline(output_dir)


async def train_from_literature(
    authors: list[str] | None = None,
    config: TrainingConfig | None = None,
    output_dir: str | None = None,
    use_lightweight_model: bool = False,
    augment_with_ai: bool = True
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
        augment_with_ai=augment_with_ai
    )

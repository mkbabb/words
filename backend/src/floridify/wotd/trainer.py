"""WOTD ML training system - four-stage pipeline for semantic preference learning.

Pipeline Architecture:
    Stage 1: Synthetic corpus generation (SyntheticGenerator)
    Stage 2: BGE embedding extraction (BGEEmbedder) 
    Stage 3: Semantic encoder training (SemanticEncoder)
    Stage 4: DSL fine-tuning (DSLTrainer)

Key Insight: User preferences compress into 4D semantic IDs via RVQ,
enabling efficient preference matching and personalized word generation.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer

from .constants import BGE_M3_MODEL, MODEL_DIMENSIONS
from ..utils.logging import get_logger
from .core import (
    CorpusDict,
        SemanticID,
    SemanticIDDict,
    TrainingConfig,
    TrainingResults,
    WOTDCorpus,
)
from .generator import generate_training_data
from .storage import get_wotd_storage

logger = get_logger(__name__)


class BGEEmbedder:
    """Stage 2: BGE-M3 embedding extraction for preference vector creation.
    
    Converts word collections into 1024D dense preference vectors using
    the same BGE-M3 model as semantic search for architectural consistency.
    Cached embeddings enable efficient retraining and experimentation.
    """
    
    def __init__(self) -> None:
        """Initialize BGE-M3 with CPU optimization."""
        self.model = SentenceTransformer(BGE_M3_MODEL, device="cpu")
        # Enable half-precision for memory efficiency
        if hasattr(self.model, 'half'):
            self.model = self.model.half()
    
    async def encode_corpus(
        self, 
        corpus: WOTDCorpus,
        cache_embeddings: bool = True
    ) -> list[float]:
        """Convert word collection to preference vector via mean pooling.
        
        Process: Words → BGE embeddings → Mean pooled vector → L2 normalized
        Result: 1024D preference vector representing semantic preferences
        """
        words = [word.word for word in corpus.words]
        
        # Check cache first
        if cache_embeddings:
            storage = await get_wotd_storage()
            cached = await storage.get_cached_embeddings(corpus.id)
            if cached:
                logger.debug(f"📋 Using cached embeddings for {corpus.id}")
                return cached
        
        # Generate embeddings using BGE-M3 (same as semantic search)
        embeddings = self.model.encode(
            words,
            batch_size=32,  # Optimized batch size
            show_progress_bar=False,
            convert_to_tensor=True,
            normalize_embeddings=True  # L2 normalize
        )
        
        # Average to preference vector
        preference_vector = torch.mean(embeddings, dim=0).tolist()
        
        # Cache for performance
        if cache_embeddings:
            await storage.cache_embeddings(corpus.id, preference_vector)
        
        return preference_vector


class SemanticEncoder(nn.Module):
    """Stage 3: Residual Vector Quantizer for semantic ID compression.
    
    Compresses 1024D preference vectors into 4D semantic IDs using RVQ.
    Each dimension represents: [style, complexity, era, variation] with
    5-bit quantization (0-31 range) for 20-bit total preference space.
    """
    
    def __init__(self, config: TrainingConfig):
        super().__init__()
        self.config = config
        self.input_dim = MODEL_DIMENSIONS[BGE_M3_MODEL]  # 1024 for BGE-M3
        
        # RVQ layers
        self.quantizers = nn.ModuleList([
            nn.ModuleList([
                nn.Linear(self.input_dim, config.codebook_size, bias=False),
                nn.Parameter(torch.randn(config.codebook_size, self.input_dim) * 0.02)
            ]) for _ in range(config.num_levels)
        ])
    
    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, list[int], dict[str, torch.Tensor]]:
        """RVQ forward pass."""
        residual = x
        quantized_out = torch.zeros_like(x)
        indices = []
        losses = {}
        
        for i, (proj, codebook) in enumerate(self.quantizers):
            # Project and quantize
            projected = proj(residual)
            distances = torch.cdist(projected.unsqueeze(0), codebook.unsqueeze(0))
            nearest_idx = torch.argmin(distances, dim=-1).item()
            
            # Get quantized vector
            quantized = codebook[nearest_idx]
            quantized_out += quantized
            residual = residual - quantized.detach()
            
            indices.append(nearest_idx)
            
            # Commitment loss
            losses[f'commit_{i}'] = torch.mean((quantized.detach() - x) ** 2)
        
        # Reconstruction loss
        losses['recon'] = torch.mean((quantized_out - x) ** 2)
        
        return quantized_out, indices, losses
    
    def encode(self, x: torch.Tensor) -> SemanticID:
        """Encode to semantic ID."""
        with torch.no_grad():
            _, indices, _ = self.forward(x)
            return tuple(indices)  # Convert to SemanticID tuple


class DSLTrainer:
    """Stage 4: Domain Specific Language fine-tuning for word generation.
    
    LoRA fine-tunes Phi-3.5 to generate words from semantic ID patterns.
    Maps discrete semantic IDs back to natural language through learned
    associations between preference space and word characteristics.
    """
    
    def __init__(self, config: TrainingConfig):
        self.config = config
    
    def create_training_examples(
        self, 
        corpora_dict: CorpusDict,
        semantic_ids: SemanticIDDict
    ) -> list[dict[str, str]]:
        """Generate training examples mapping semantic IDs to word lists.
        
        Creates instruction-response pairs for LoRA fine-tuning:
        Input: "[2,1,3,0] Generate classical beautiful modernist words"
        Output: "eloquent, sophisticated, nuanced, contemplative..."
        """
        examples = []
        
        for corpus_id, corpus in corpora_dict.items():
            if corpus_id in semantic_ids:
                semantic_id = semantic_ids[corpus_id]
                id_str = f"[{','.join(map(str, semantic_id))}]"
                
                # Get sample words from corpus
                sample_words = [w.word for w in corpus.words[:5]]
                word_list = ', '.join(sample_words)
                
                # Create training examples
                templates = [
                    f"Generate {id_str} words: {word_list}",
                    f"Create {id_str}: {word_list}",
                    f"Words like {id_str}: {word_list}",
                ]
                
                for template in templates:
                    examples.append({
                        "input": template,
                        "output": template
                    })
        
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
    """Complete WOTD training orchestrator - manages four-stage pipeline.
    
    Coordinates: Corpus generation → BGE embedding → RVQ compression → LoRA fine-tuning
    Result: Trained models that generate personalized words from semantic preferences.
    Caches intermediates for efficient retraining and experimentation.
    """
    
    # Path constants
    DEFAULT_MODELS_DIR = "./models/wotd"
    SEMANTIC_ENCODER_FILE = "semantic_encoder.pt"
    SEMANTIC_IDS_FILE = "semantic_ids.json"
    
    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig()
        self.embedder = BGEEmbedder()
        self.encoder = SemanticEncoder(self.config)
        self.dsl_trainer = DSLTrainer(self.config)
    
    async def train_complete_pipeline(self, output_dir: str | None = None) -> TrainingResults:
        """Execute complete four-stage training pipeline.
        
        Stage 1: Generate semantic corpora (cached for reuse)
        Stage 2: Extract BGE preference vectors (cached per corpus)  
        Stage 3: Train RVQ semantic encoder (maps 1024D → 4D IDs)
        Stage 4: Fine-tune DSL generator (maps IDs → words)
        
        Returns: TrainingResults with performance metrics and model paths
        """
        start_time = time.time()
        logger.info("🚀 Starting WOTD training pipeline")
        
        # Stage 1: Generate/load semantic corpora (cached for efficiency)
        logger.info("🧬 Stage 1: Loading semantic training corpora")
        corpora_dict = await generate_training_data(
            words_per_corpus=self.config.words_per_corpus,
            use_cached=True  # Reuse existing corpora for faster iteration
        )
        
        # Stage 2: Extract preference vectors via BGE embeddings (cached per corpus)
        logger.info("🧠 Stage 2: Computing BGE-M3 preference vectors")
        preference_vectors = {}
        
        for corpus_id, corpus in corpora_dict.items():
            pref_vector = await self.embedder.encode_corpus(corpus)  # 1024D dense vector
            preference_vectors[corpus_id] = torch.tensor(pref_vector, dtype=torch.float32)
        
        # Stage 3: Train RVQ semantic encoder (1024D → 4D compression)  
        logger.info("🔢 Stage 3: Training RVQ semantic encoder")
        semantic_ids = await self._train_semantic_encoder(preference_vectors)
        
        # Stage 4: Generate DSL training examples (semantic IDs → word generation)
        logger.info("📚 Stage 4: Creating DSL training examples")
        training_examples = self.dsl_trainer.create_training_examples(
            corpora_dict, semantic_ids
        )
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
            model_paths=model_paths
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
        self, 
        preference_vectors: dict[str, torch.Tensor]
    ) -> SemanticIDDict:
        """Train semantic encoder with RVQ."""
        optimizer = torch.optim.AdamW(
            self.encoder.parameters(), 
            lr=self.config.encoder_lr
        )
        
        vectors = list(preference_vectors.values())
        corpus_ids = list(preference_vectors.keys())
        
        self.encoder.train()
        
        # Training loop
        for epoch in range(self.config.encoder_epochs):
            total_loss = 0.0
            
            for vector in vectors:
                optimizer.zero_grad()
                
                # Forward pass
                _, _, losses = self.encoder(vector)
                
                # Combined loss
                loss = losses['recon'] + sum(
                    losses[k] for k in losses if 'commit' in k
                )
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if epoch % 20 == 0:
                avg_loss = total_loss / len(vectors)
                logger.info(f"Encoder epoch {epoch}: loss = {avg_loss:.4f}")
        
        # Generate semantic IDs
        self.encoder.eval()
        semantic_ids = {}
        
        for corpus_id, vector in preference_vectors.items():
            semantic_id = self.encoder.encode(vector)
            semantic_ids[corpus_id] = semantic_id
        
        return semantic_ids
    
    async def _save_models(
        self, 
        output_dir: str | None,
        semantic_ids: SemanticIDDict
    ) -> dict[str, str]:
        """Save trained models."""
        if output_dir:
            models_dir = Path(output_dir)
        else:
            # Use unified cache directory structure
            cache = await get_wotd_storage()
            stats = await cache.get_cache_stats()
            models_dir = Path(self.DEFAULT_MODELS_DIR)
        
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Save semantic encoder
        encoder_path = models_dir / self.SEMANTIC_ENCODER_FILE
        torch.save({
            'model_state_dict': self.encoder.state_dict(),
            'config': self.config.model_dump()
        }, encoder_path)
        
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
            "models_directory": str(models_dir)
        }
        
        logger.info(f"💾 Models saved to {models_dir}")
        return model_paths


# Convenience functions
async def train_wotd_pipeline(
    config: TrainingConfig | None = None,
    output_dir: str | None = None
) -> TrainingResults:
    """Train WOTD pipeline with default or custom config."""
    trainer = WOTDTrainer(config)
    return await trainer.train_complete_pipeline(output_dir)
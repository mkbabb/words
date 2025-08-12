"""Local inference system for WOTD semantic word generation.

Simple, robust inference pipeline that loads trained models and provides
text → semantic ID → word generation capabilities.
"""

import json
from pathlib import Path
from typing import Any

import torch

from ..utils.logging import get_logger
from .embeddings import get_embedder
from .encoders import get_semantic_encoder

logger = get_logger(__name__)


class WOTDInference:
    """Local inference system for semantic word generation."""
    
    def __init__(self, model_dir: str):
        """Initialize inference system with trained models.
        
        Args:
            model_dir: Directory containing trained models (semantic_encoder.pt, semantic_ids.json)
        """
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        # Model paths
        self.encoder_path = self.model_dir / "semantic_encoder.pt"
        self.semantic_ids_path = self.model_dir / "semantic_ids.json"
        
        # Validate model files exist
        if not self.encoder_path.exists():
            raise FileNotFoundError(f"Semantic encoder not found: {self.encoder_path}")
        if not self.semantic_ids_path.exists():
            raise FileNotFoundError(f"Semantic IDs not found: {self.semantic_ids_path}")
        
        # Initialize components
        self.embedder = None
        self.semantic_encoder = None
        self.semantic_ids = {}
        self.id_to_corpus = {}  # Reverse mapping
        
        logger.info(f"🚀 Initializing WOTD inference from {model_dir}")
        
    async def load_models(self):
        """Load all trained models and mappings."""
        try:
            # Load embedder (same model used during training)
            self.embedder = get_embedder(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu"
            )
            logger.info("✅ Embedding model loaded")
            
            # Load semantic encoder
            checkpoint = torch.load(self.encoder_path, map_location="cpu")
            encoder_type = checkpoint.get("encoder_type", "FSQ")
            
            # Recreate encoder with same config
            use_fsq = encoder_type == "FSQ"
            self.semantic_encoder = get_semantic_encoder(
                input_dim=384,  # MiniLM dimensions
                use_fsq=use_fsq
            )
            
            # Load trained weights
            self.semantic_encoder.encoder.load_state_dict(checkpoint["model_state_dict"])
            self.semantic_encoder.encoder.eval()
            logger.info(f"✅ Semantic encoder loaded ({encoder_type})")
            
            # Load semantic IDs mapping
            with open(self.semantic_ids_path) as f:
                self.semantic_ids = json.load(f)
            
            # Create reverse mapping
            self.id_to_corpus = {
                tuple(semantic_id): corpus_id 
                for corpus_id, semantic_id in self.semantic_ids.items()
            }
            
            logger.info(f"✅ Loaded {len(self.semantic_ids)} semantic ID mappings")
            logger.success("🎯 All models loaded successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            raise
    
    async def text_to_semantic_id(self, text: str) -> tuple[int, int, int, int]:
        """Convert text to semantic ID.
        
        Args:
            text: Input text to analyze
            
        Returns:
            4D semantic ID tuple (style, complexity, era, variation)
        """
        if not self.embedder or not self.semantic_encoder:
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        # Generate embedding
        embedding = self.embedder.embed([text], normalize=True)
        
        # Ensure proper tensor format
        if not isinstance(embedding, torch.Tensor):
            embedding = torch.tensor(embedding, dtype=torch.float32)
        
        if embedding.dim() == 2:
            embedding = embedding.mean(dim=0)  # Average if multiple embeddings
        
        # Encode to semantic ID
        with torch.no_grad():
            semantic_id = self.semantic_encoder.encode(embedding.unsqueeze(0))
        
        logger.info(f"📝 '{text}' → semantic ID {semantic_id}")
        return semantic_id
    
    def semantic_id_to_description(self, semantic_id: tuple[int, int, int, int]) -> dict[str, str]:
        """Convert semantic ID to human-readable description.
        
        Args:
            semantic_id: 4D semantic ID tuple
            
        Returns:
            Dictionary with style, complexity, era, variation descriptions
        """
        style_names = ["Classical", "Modern", "Romantic", "Neutral", "Technical", "Poetic", "Formal", "Casual"]
        complexity_names = ["Simple", "Beautiful", "Moderate", "Complex", "Technical", "Advanced", "Expert", "Specialized"]
        era_names = ["Ancient", "Medieval", "Renaissance", "Elizabethan", "Classical", "Victorian", "Modernist", "Contemporary"]
        variation_names = ["Base", "Variant A", "Variant B", "Variant C", "Variant D"]
        
        style, complexity, era, variation = semantic_id
        
        return {
            "style": style_names[min(style, len(style_names)-1)],
            "complexity": complexity_names[min(complexity, len(complexity_names)-1)],
            "era": era_names[min(era, len(era_names)-1)],
            "variation": variation_names[min(variation, len(variation_names)-1)]
        }
    
    def find_similar_corpora(self, target_id: tuple[int, int, int, int], max_distance: int = 2) -> list[str]:
        """Find corpora with similar semantic IDs.
        
        Args:
            target_id: Target semantic ID
            max_distance: Maximum Hamming distance for similarity
            
        Returns:
            List of corpus IDs with similar semantic profiles
        """
        similar = []
        
        for corpus_id, corpus_semantic_id in self.semantic_ids.items():
            # Calculate Hamming distance
            distance = sum(
                a != b for a, b in zip(target_id, corpus_semantic_id)
            )
            
            if distance <= max_distance:
                similar.append(corpus_id)
        
        return similar
    
    def get_corpus_info(self, corpus_id: str) -> dict[str, Any]:
        """Get information about a corpus.
        
        Args:
            corpus_id: Corpus identifier
            
        Returns:
            Dictionary with corpus information
        """
        if corpus_id not in self.semantic_ids:
            return {"error": f"Corpus {corpus_id} not found"}
        
        semantic_id = tuple(self.semantic_ids[corpus_id])
        description = self.semantic_id_to_description(semantic_id)
        
        return {
            "corpus_id": corpus_id,
            "semantic_id": semantic_id,
            "description": description
        }
    
    async def generate_words_for_semantic_id(
        self, 
        semantic_id: tuple[int, int, int, int],
        count: int = 10
    ) -> list[str]:
        """Generate words matching a semantic ID profile.
        
        This is a simplified version - in a full implementation,
        you'd use the fine-tuned language model for generation.
        
        Args:
            semantic_id: Target semantic ID
            count: Number of words to generate
            
        Returns:
            List of generated words
        """
        # Find similar corpora
        similar_corpora = self.find_similar_corpora(semantic_id, max_distance=1)
        
        if not similar_corpora:
            # Fallback to broader search
            similar_corpora = self.find_similar_corpora(semantic_id, max_distance=2)
        
        if similar_corpora:
            description = self.semantic_id_to_description(semantic_id)
            logger.info(f"🎭 Generating words for semantic profile: {description}")
            
            # For demonstration, return corpus information
            return [f"Word_{i}_matching_{semantic_id}" for i in range(count)]
        else:
            logger.warning(f"No similar corpora found for {semantic_id}")
            return [f"Unknown_{i}_{semantic_id}" for i in range(count)]


# Simple factory function
async def create_inference_system(model_dir: str) -> WOTDInference:
    """Create and initialize WOTD inference system.
    
    Args:
        model_dir: Directory containing trained models
        
    Returns:
        Initialized WOTDInference system
    """
    inference = WOTDInference(model_dir)
    await inference.load_models()
    return inference
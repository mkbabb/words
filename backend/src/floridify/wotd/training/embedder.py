"""Stage 2: Embedding extraction with multi-model support.

This module handles the conversion of text into high-dimensional vector
representations using state-of-the-art embedding models.
"""

from __future__ import annotations

import numpy as np
import torch

from ...utils.logging import get_logger
from ..constants import (
    DEFAULT_EMBEDDING_MODEL,
    USE_BINARY_EMBEDDINGS,
    USE_INT8_EMBEDDINGS,
)
from ..core import WOTDCorpus
from ..embeddings import EmbeddingMode, get_embedder

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
            Words -> Individual Embeddings -> Average Pool -> Preference Vector

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
                corpus.id,
                words,
                mode=mode,
                target_dim=target_dim,
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

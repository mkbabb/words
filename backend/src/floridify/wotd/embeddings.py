"""Embedding system with multi-model support and Matryoshka capabilities.

This module provides a unified interface for computing text embeddings using
state-of-the-art transformer models. It supports multiple embedding modes,
including Matryoshka truncation for efficient multi-resolution representations
and various quantization schemes for memory optimization.

Key Concepts:
    1. **Matryoshka Embeddings**: Hierarchical representations where prefix
       dimensions contain the most important information. Enables dynamic
       dimension reduction with minimal performance loss.

    2. **Quantization**: Reduces embedding precision for memory efficiency:
       - Binary: 1 bit per dimension (32x compression)
       - INT8: 8 bits per dimension (4x compression)

    3. **L2 Normalization**: Projects embeddings onto unit hypersphere,
       making cosine similarity equivalent to dot product.

    4. **Hierarchical Encoding**: Maps different dimension ranges to
       semantic attributes (style, complexity, era, variation).

Supported Models:
    - GTE-Qwen2 (Alibaba): 4096D with Matryoshka support
    - E5-Multilingual (Microsoft): 1024D efficient alternative
    - SFR-Embedding-2 (Salesforce): 4096D research model
"""

from __future__ import annotations

import multiprocessing
import os
import platform
from enum import Enum

# Apple Silicon specific configuration
if platform.machine() == "arm64" and platform.system() == "Darwin":
    # Apple Silicon: Use optimized threading for M-series chips
    # These settings work with Apple's Accelerate framework
    os.environ["VECLIB_MAXIMUM_THREADS"] = "4"  # Optimal for M-series efficiency cores
    os.environ["OMP_NUM_THREADS"] = "4"  # Match VECLIB setting
    os.environ["MKL_NUM_THREADS"] = "1"  # Disable Intel MKL on Apple Silicon
    os.environ["OPENBLAS_NUM_THREADS"] = "1"  # Not used on Apple Silicon
else:
    # Intel/AMD: Standard multi-threading

    num_cores = multiprocessing.cpu_count()
    os.environ["OMP_NUM_THREADS"] = str(min(4, num_cores))  # Cap at 4 for stability
    os.environ["MKL_NUM_THREADS"] = str(min(4, num_cores))
    os.environ["OPENBLAS_NUM_THREADS"] = str(min(4, num_cores))

# Disable problematic parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Don't disable CUDA completely - let PyTorch decide
if "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Enable MPS fallback on Apple Silicon

import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812

# Import sentence transformers after environment configuration
try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise ImportError(
        "sentence-transformers is required for embedding computation. "
        "Install with: pip install sentence-transformers",
    ) from e


from ..utils.logging import get_logger
from .constants import (
    DEFAULT_EMBEDDING_MODEL,
    MATRYOSHKA_MODELS,
    MODEL_DIMENSIONS,
)

# from .storage import get_wotd_storage  # Import lazily to avoid circular imports

logger = get_logger(__name__)


class EmbeddingMode(str, Enum):
    """Embedding computation modes.

    Different modes provide trade-offs between quality and efficiency:

    - FULL: Maximum fidelity, highest memory usage
    - ELASTIC: Reduced dimensions via Matryoshka, good quality/speed balance
    - BINARY: Extreme compression for fast similarity, ~90% quality retention
    - INT8: Moderate compression, ~98% quality retention
    """

    FULL = "full"  # Full dimensionality (e.g., 4096D)
    ELASTIC = "elastic"  # Matryoshka/truncated (e.g., 256-2048D)
    BINARY = "binary"  # Binary quantization (1 bit/dim)
    INT8 = "int8"  # Int8 quantization (8 bits/dim)


class Embedder:
    """Multi-model embedder with Matryoshka and quantization support.

    This class provides a unified interface for computing embeddings from text
    using various transformer models. It supports multiple optimization techniques
    including Matryoshka truncation and quantization.

    Architecture:
        Text → Tokenization → Transformer → Pooling → Post-processing

    The transformer models use bi-encoder architecture:
        1. Encode text to token embeddings
        2. Apply self-attention layers
        3. Pool token embeddings (mean pooling)
        4. Optionally normalize to unit sphere

    Matryoshka Support:
        Models trained with Matryoshka loss organize information hierarchically.
        Early dimensions capture coarse semantics, later dimensions add details.
        This allows truncation without retraining: embed_4096[:256] ≈ embed_256
    """

    def __init__(self, model_name: str | None = None, device: str = "cpu", use_fp16: bool = False):
        """Initialize embedder with specified model.

        Args:
            model_name: Model to use (defaults to DEFAULT_EMBEDDING_MODEL)
            device: Device for computation (cpu/cuda/mps)
            use_fp16: Use half precision for efficiency (disabled by default for stability)

        """
        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL

        # Smart device selection
        if device == "cpu" or not torch.cuda.is_available():
            # On Apple Silicon, check for MPS availability
            mps_available = False
            if platform.machine() == "arm64":
                try:
                    mps_available = torch.backends.mps.is_available()
                except AttributeError:
                    # MPS not available on this PyTorch version
                    pass

            if mps_available:
                self.device = "mps"  # Use Metal Performance Shaders on Apple Silicon
                logger.info("🍎 Using Apple Silicon MPS acceleration")
            else:
                self.device = "cpu"
        else:
            self.device = device

        # Disable fp16 on CPU and MPS for numerical stability
        self.use_fp16 = use_fp16 and self.device not in ["cpu", "mps"]

        # Model dimensions and capabilities
        self.full_dim = (
            MODEL_DIMENSIONS.get(self.model_name, 1024)
            if isinstance(self.model_name, str)
            else 1024
        )  # type: ignore
        self.elastic_dims = (
            MATRYOSHKA_MODELS.get(self.model_name, [self.full_dim])
            if isinstance(self.model_name, str)
            else [self.full_dim]
        )  # type: ignore
        self.supports_matryoshka = self.model_name in MATRYOSHKA_MODELS

        # Initialize current dimension to full dimension
        self._current_dim = self.full_dim

        # Load model with careful device and precision handling
        try:
            self.model = SentenceTransformer(
                self.model_name, device=self.device, trust_remote_code=True
            )

            # Only use fp16 on CUDA devices
            if self.use_fp16:
                try:
                    self.model = self.model.half()
                except (AttributeError, RuntimeError) as e:
                    logger.warning(f"Half precision not supported: {e}")

            logger.info(f"✅ Loaded {self.model_name} ({self.full_dim}D) on {self.device}")
        except Exception as e:
            logger.error(f"❌ Failed to load model {self.model_name} on {self.device}: {e}")
            # Fallback to CPU
            if self.device != "cpu":
                logger.info("🔄 Falling back to CPU device")
                self.device = "cpu"
                self.use_fp16 = False
                self.model = SentenceTransformer(
                    self.model_name, device="cpu", trust_remote_code=True
                )
                logger.info(f"✅ Loaded {self.model_name} ({self.full_dim}D) on CPU (fallback)")
            else:
                raise

    @property
    def current_dim(self) -> int:
        """Get the current effective embedding dimension based on the last operation."""
        return self._current_dim

    def _update_current_dim(self, mode: EmbeddingMode, target_dim: int | None = None) -> int:
        """Update and return the current dimension based on mode and target."""
        if mode == EmbeddingMode.ELASTIC and target_dim:
            self._current_dim = target_dim
        elif mode == EmbeddingMode.BINARY:
            self._current_dim = self.full_dim  # Binary still uses full dimensions
        elif mode == EmbeddingMode.INT8:
            self._current_dim = self.full_dim  # INT8 still uses full dimensions
        else:  # FULL mode
            self._current_dim = self.full_dim
        return self._current_dim

    def embed(
        self,
        texts: list[str] | str,
        mode: EmbeddingMode = EmbeddingMode.FULL,
        target_dim: int | None = None,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> np.ndarray | torch.Tensor:
        """Compute embeddings with specified mode and dimension.

        The embedding pipeline:
        1. Tokenize text into subword tokens
        2. Pass through transformer encoder
        3. Pool token embeddings (usually mean pooling)
        4. Apply post-processing based on mode:
           - ELASTIC: Truncate to target dimension
           - BINARY: Quantize to {-1, +1}
           - INT8: Quantize to [-128, 127]
        5. Optionally L2 normalize

        Args:
            texts: Input texts to embed (single string or list)
            mode: Embedding mode controlling output format
            target_dim: Target dimension for elastic mode (must be in model's elastic_dims)
            normalize: Whether to L2 normalize (recommended for similarity)
            batch_size: Processing batch size (trade-off memory vs speed)

        Returns:
            Embeddings as numpy array or torch tensor
            Shape: [num_texts, embedding_dim]

        """
        if isinstance(texts, str):
            texts = [texts]

        # Update current dimension tracking
        self._update_current_dim(mode, target_dim)

        # Compute base embeddings using sentence transformers
        # The model handles tokenization, encoding, and pooling internally

        # Determine optimal batch size based on device and number of texts
        if self.device == "mps":
            # Apple Silicon MPS: small batches work best
            optimal_batch_size = min(batch_size, 8, len(texts))
        elif self.device == "cuda":
            # CUDA: can handle larger batches
            optimal_batch_size = batch_size
        else:
            # CPU: moderate batch size
            optimal_batch_size = min(batch_size, 16, len(texts))

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=optimal_batch_size,
                show_progress_bar=False,
                convert_to_tensor=True,  # Return as torch tensor
                normalize_embeddings=False,  # We'll normalize after processing if needed
                device=self.device,  # Use the selected device
                convert_to_numpy=False,  # Keep as tensor
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Embedding computation failed with batch_size={optimal_batch_size}: {e}",
            )
            logger.info("🔄 Retrying with batch_size=1")
            # Fallback to single-item processing
            embeddings = self.model.encode(
                texts,
                batch_size=1,
                show_progress_bar=False,
                convert_to_tensor=True,
                normalize_embeddings=False,
                device=self.device,
                convert_to_numpy=False,
            )

        # Ensure tensor is in the correct format and device
        if not isinstance(embeddings, torch.Tensor):
            # Convert to tensor if needed
            embeddings = torch.tensor(embeddings, dtype=torch.float32)

        # Ensure consistent data type
        if embeddings.dtype != torch.float32:
            embeddings = embeddings.to(torch.float32)

        # Move to CPU for consistent processing (other operations expect CPU tensors)
        if embeddings.device.type != "cpu":
            embeddings = embeddings.cpu()

        # Ensure tensor is contiguous in memory
        if not embeddings.is_contiguous():
            embeddings = embeddings.contiguous()

        # Detach from computation graph to prevent gradient tracking issues
        embeddings = embeddings.detach()

        # Apply mode-specific processing with memory safety
        if mode == EmbeddingMode.ELASTIC and self.supports_matryoshka:
            embeddings = self._apply_matryoshka(embeddings, target_dim)
        elif mode == EmbeddingMode.BINARY:
            embeddings = self._binarize(embeddings)
        elif mode == EmbeddingMode.INT8:
            embeddings = self._quantize_int8(embeddings)

        # Normalize if requested (skip for quantized modes)
        if normalize and mode not in [EmbeddingMode.BINARY, EmbeddingMode.INT8]:
            embeddings = F.normalize(embeddings, p=2, dim=-1)
            # Ensure contiguous memory after normalization
            embeddings = embeddings.contiguous()

        return embeddings

    def _apply_matryoshka(
        self,
        embeddings: torch.Tensor,
        target_dim: int | None = None,
    ) -> torch.Tensor:
        """Apply Matryoshka truncation to embeddings.

        Matryoshka embeddings are trained such that prefix dimensions
        form valid representations at multiple scales. This is achieved
        through a special training loss that optimizes similarity at
        multiple truncation points simultaneously.

        Mathematical property:
            For Matryoshka-trained model M and dimensions d1 < d2:
            sim(M(x)[:d1], M(y)[:d1]) ≈ sim(M(x)[:d2], M(y)[:d2])

        This means we can truncate without significant quality loss,
        enabling dynamic compute/accuracy trade-offs at inference time.

        Args:
            embeddings: Full embeddings to truncate
            target_dim: Target dimension (must be ≤ full dimension)

        Returns:
            Truncated and renormalized embeddings

        """
        if target_dim is None:
            # Use middle dimension as default
            target_dim = self.elastic_dims[len(self.elastic_dims) // 2]

        # Validate dimension
        if target_dim > embeddings.shape[-1]:
            logger.warning(f"Target dim {target_dim} > embedding dim, using full")
            return embeddings

        # Truncate to target dimension
        truncated = embeddings[..., :target_dim]

        # Re-normalize after truncation (critical for similarity)
        truncated = F.normalize(truncated, p=2, dim=-1)

        return truncated

    def _binarize(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Convert embeddings to binary (1-bit per dimension).

        Binary quantization uses the sign function:
            b_i = sign(e_i) = {+1 if e_i > 0, -1 if e_i ≤ 0}

        Similarity computation becomes Hamming distance:
            sim_binary(x, y) = (d - hamming_dist(x, y)) / d

        Where d is the dimension. This can be computed with XOR and popcount,
        making it extremely fast on modern hardware.

        Trade-offs:
            - 32x memory reduction (float32 → 1 bit)
            - 100x+ faster similarity computation
            - ~90% quality retention for many tasks
            - Best for large-scale approximate search

        Massive compression for ultra-fast similarity computation.
        """
        # Simple sign binarization
        binary = (embeddings > 0).float() * 2 - 1  # Convert to +1/-1
        return binary

    def _quantize_int8(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Quantize embeddings to int8.

        INT8 quantization linearly maps floating point to 8-bit integers:
            1. Find scale: s = 127 / max(|embeddings|)
            2. Quantize: q = round(embeddings * s)
            3. Clip: q = clip(q, -128, 127)

        To dequantize: embeddings ≈ q / s

        This preserves relative magnitudes while reducing precision.
        Modern CPUs/GPUs have optimized INT8 operations, providing
        both memory and compute benefits.

        Trade-offs:
            - 4x memory reduction (float32 → int8)
            - 2-4x faster operations on compatible hardware
            - ~98% quality retention
            - Good balance of compression and quality

        4x memory reduction with minimal accuracy loss.
        """
        # Scale to int8 range
        scale = 127.0 / torch.abs(embeddings).max(dim=-1, keepdim=True)[0]
        quantized = (embeddings * scale).round().clamp(-128, 127).to(torch.int8)

        # Return quantized values directly
        return quantized  # type: ignore

    async def encode_hierarchical(
        self,
        texts: list[str],
        hierarchy_dims: list[int] | None = None,
    ) -> dict[int, torch.Tensor]:
        """Encode texts at multiple dimensional resolutions.

        Creates hierarchical representations for coarse-to-fine retrieval.

        Args:
            texts: Input texts
            hierarchy_dims: Dimensions to compute (defaults to elastic_dims)

        Returns:
            Dict mapping dimension to embeddings

        """
        if hierarchy_dims is None:
            hierarchy_dims = self.elastic_dims if self.supports_matryoshka else [self.full_dim]

        # Compute full embeddings once
        full_embeddings = self.embed(texts, mode=EmbeddingMode.FULL)

        # Generate hierarchy
        hierarchy = {}
        for dim in sorted(hierarchy_dims):
            if dim == self.full_dim:
                hierarchy[dim] = full_embeddings
            elif self.supports_matryoshka and isinstance(full_embeddings, torch.Tensor):
                hierarchy[dim] = self._apply_matryoshka(full_embeddings, dim)
            else:
                # Model doesn't support this dimension
                raise ValueError(
                    f"Model {self.model_name} doesn't support dimension {dim}. "
                    f"Available dimensions: {self.elastic_dims}",
                )

        return hierarchy

    async def embed_corpus_with_cache(
        self,
        corpus_id: str,
        texts: list[str],
        mode: EmbeddingMode = EmbeddingMode.FULL,
        target_dim: int | None = None,
    ) -> torch.Tensor:
        """Embed corpus with caching support.

        Checks cache first, computes if needed, stores result.
        """
        from .storage import get_wotd_storage

        storage = await get_wotd_storage()

        # Check cache
        cache_key = f"{corpus_id}:{mode.value}:{target_dim or 'full'}"
        cached = await storage.get_cached_embeddings(cache_key)
        if cached:
            logger.debug(f"📋 Using cached embeddings for {cache_key}")
            # Ensure cached tensor is properly aligned for Apple Silicon
            tensor = torch.tensor(cached, dtype=torch.float32)
            return tensor.contiguous()

        # Compute embeddings - ensure thread safety for Apple Silicon
        embeddings = self.embed(texts, mode=mode, target_dim=target_dim)

        # Ensure tensor is on CPU and properly formatted for caching
        if isinstance(embeddings, torch.Tensor):
            # Move to CPU and ensure contiguous memory for safe serialization
            cpu_embeddings = embeddings.cpu().contiguous()
            await storage.cache_embeddings(
                cache_key,
                cpu_embeddings.numpy().tolist(),
                ttl_hours=48,
            )
            # Return the original embeddings, not the CPU copy
            return embeddings.contiguous() if not embeddings.is_contiguous() else embeddings
        try:
            embeddings_list = embeddings.tolist()
        except AttributeError:
            embeddings_list = list(embeddings)
        await storage.cache_embeddings(
            cache_key,
            embeddings_list,
            ttl_hours=48,
        )
        # Convert to properly aligned tensor
        return torch.tensor(embeddings, dtype=torch.float32).contiguous()


class SemanticHierarchyEncoder:
    """Encodes semantic attributes hierarchically using Matryoshka dimensions.

    Maps different dimensional segments to semantic attributes:
        - Dims 0-256: Style (coarse semantic category)
        - Dims 256-512: Complexity (linguistic sophistication)
        - Dims 512-1024: Era (temporal/cultural context)
        - Dims 1024-4096: Variation (fine-grained distinctions)
    """

    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self.dimension_mapping = {
            "style": (0, 256),
            "complexity": (256, 512),
            "era": (512, 1024),
            "variation": (1024, 4096),
        }

    def extract_semantic_components(self, embedding: torch.Tensor) -> dict[str, torch.Tensor]:
        """Extract semantic components from hierarchical embedding.

        Returns:
            Dict mapping semantic attribute to embedding segment

        """
        components = {}

        for attr, (start, end) in self.dimension_mapping.items():
            if end <= embedding.shape[-1]:
                segment = embedding[..., start:end]
                components[attr] = F.normalize(segment, p=2, dim=-1)

        return components

    def compute_semantic_similarity(
        self,
        embedding1: torch.Tensor,
        embedding2: torch.Tensor,
        weights: dict[str, float] | None = None,
    ) -> float:
        """Compute weighted semantic similarity across attributes.

        Args:
            embedding1: First embedding
            embedding2: Second embedding
            weights: Attribute weights (defaults to uniform)

        Returns:
            Weighted similarity score

        """
        if weights is None:
            weights = {"style": 0.3, "complexity": 0.2, "era": 0.2, "variation": 0.3}

        components1 = self.extract_semantic_components(embedding1)
        components2 = self.extract_semantic_components(embedding2)

        total_similarity = 0.0
        total_weight = 0.0

        for attr, weight in weights.items():
            if attr in components1 and attr in components2:
                sim = (
                    F.cosine_similarity(components1[attr], components2[attr], dim=-1).mean().item()
                )
                total_similarity += sim * weight
                total_weight += weight

        return total_similarity / total_weight if total_weight > 0 else 0.0


# Factory functions
def get_embedder(model_name: str | None = None, device: str = "cpu") -> Embedder:
    """Get embedder instance with specified model."""
    return Embedder(model_name=model_name, device=device)


def get_hierarchy_encoder(embedder: Embedder | None = None) -> SemanticHierarchyEncoder:
    """Get semantic hierarchy encoder."""
    if embedder is None:
        embedder = get_embedder()
    return SemanticHierarchyEncoder(embedder)

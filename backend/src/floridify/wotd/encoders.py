"""Semantic encoders - FSQ and hierarchical VQ for discrete representations.

This module implements advanced quantization techniques for converting continuous
high-dimensional embeddings into discrete semantic representations. The primary
goal is to create interpretable, compressed codes that capture semantic attributes
of natural language.

Key Concepts:
    1. **Finite Scalar Quantization (FSQ)**: Directly quantizes each dimension
       to a fixed number of levels without using codebooks. This eliminates
       codebook collapse issues and provides interpretable indices.

    2. **Hierarchical Vector Quantization (HVQ)**: Multi-level quantization
       where each level refines the previous, creating a hierarchy of
       increasingly fine-grained representations.

    3. **Semantic ID**: A 4-tuple (style, complexity, era, variation) that
       uniquely identifies semantic characteristics of text.

    4. **Straight-Through Estimator**: Enables gradient flow through discrete
       quantization by using quantized values in forward pass but continuous
       gradients in backward pass.

Mathematical Background:
    - Quantization reduces continuous values to discrete levels
    - Information bottleneck principle forces learning of essential features
    - Reconstruction loss ensures reversibility of encoding
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F  # noqa: N812
from torch import nn

from ..utils.logging import get_logger
from .constants import (
    FSQ_LATENT_DIM,
    FSQ_LEVELS_PER_DIM,
    FSQ_USE_L2_NORM,
    USE_FSQ,
    USE_HIERARCHICAL_VQ,
)
from .core import SemanticID

logger = get_logger(__name__)


class FSQEncoder(nn.Module):
    """Finite Scalar Quantization encoder for discrete semantic IDs.

    FSQ is a quantization method that directly maps continuous values to discrete
    levels without maintaining explicit codebooks. Each dimension is independently
    quantized to a predetermined number of levels.

    Architecture:
        Input (4096D) → Projection Network → Latent Space (4D) → Quantization → Semantic ID

    Semantic Dimensions:
        - Dim 0: Style (8 levels) - Literary genre/register (formal, casual, technical)
        - Dim 1: Complexity (8 levels) - Linguistic sophistication
        - Dim 2: Era (8 levels) - Temporal/cultural context
        - Dim 3: Variation (5 levels) - Fine-grained distinctions

    Total Unique Codes: 8 × 8 × 8 × 5 = 2,560 semantic IDs

    Mathematical Formulation:
        For each dimension i with L_i levels and bounds [a_i, b_i]:
        1. Normalize: z_norm = (z_i - a_i) / (b_i - a_i) ∈ [0, 1]
        2. Quantize: q_i = round(z_norm * (L_i - 1))
        3. Dequantize: z_q = q_i / (L_i - 1) * (b_i - a_i) + a_i

    Advantages over Vector Quantization:
        - No codebook storage or lookup required
        - No codebook collapse (all codes always accessible)
        - Interpretable indices (direct semantic meaning)
        - Simpler training (no commitment or codebook losses)
        - Faster inference (no nearest neighbor search)
    """

    def __init__(
        self,
        input_dim: int = 4096,
        latent_dim: int = FSQ_LATENT_DIM,
        levels: list[int] = FSQ_LEVELS_PER_DIM,
        use_l2_norm: bool = FSQ_USE_L2_NORM,
    ):
        """Initialize FSQ encoder.

        Args:
            input_dim: Input embedding dimension
            latent_dim: Number of latent dimensions (4 for semantic ID)
            levels: Quantization levels per dimension
            use_l2_norm: L2 normalize before quantization

        """
        super().__init__()

        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.levels = levels
        self.use_l2_norm = use_l2_norm

        # Projection to latent space
        self.projection = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Linear(256, latent_dim),
        )

        # Bounds for quantization (learnable for flexibility)
        self.bounds: torch.Tensor
        self.register_buffer("bounds", torch.tensor([[-1.0, 1.0] for _ in range(latent_dim)]))

        # Reconstruction decoder (for training)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Linear(256, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Linear(512, input_dim),
        )

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, SemanticID]:
        """Encode embeddings to discrete semantic IDs.

        Args:
            x: Input embeddings (batch_size, input_dim)

        Returns:
            Tuple of (quantized latents, semantic ID)

        """
        # Project to latent space
        z = self.projection(x)

        # Normalize if requested
        if self.use_l2_norm:
            z = F.normalize(z, p=2, dim=-1) * 2.0  # Scale to [-2, 2]

        # Quantize each dimension
        quantized = torch.zeros_like(z)
        indices = []

        for i in range(self.latent_dim):
            # Scale to [0, levels[i]-1]
            bounds_i = self.bounds[i]
            scaled = (z[:, i] - bounds_i[0]) / (bounds_i[1] - bounds_i[0])
            scaled = scaled.clamp(0, 1) * (self.levels[i] - 1)

            # Round to nearest level
            level = scaled.round().long()
            if z.shape[0] == 1:
                indices.append(int(level.item()))
            else:
                level_list = level.tolist()
                if isinstance(level_list, list):
                    indices.append(level_list[0] if len(level_list) == 1 else level_list)  # type: ignore
                else:
                    indices.append(int(level_list))

            # Dequantize for gradient flow
            bounds_i = self.bounds[i]
            quantized[:, i] = (level.float() / (self.levels[i] - 1)) * (
                bounds_i[1] - bounds_i[0]
            ) + bounds_i[0]

        # Create semantic ID - ensure it's a 4-tuple of ints
        if z.shape[0] == 1:
            # Single batch - indices should be list of ints
            id_list = [int(idx) if not isinstance(idx, int) else idx for idx in indices[:4]]
        # Multiple batch - take first item's indices
        elif isinstance(indices[0], list):
            id_list = [int(idx) for idx in indices[0][:4]]
        else:
            id_list = [int(idx) for idx in indices[:4]]

        # Ensure exactly 4 elements
        while len(id_list) < 4:
            id_list.append(0)
        semantic_id: tuple[int, int, int, int] = (id_list[0], id_list[1], id_list[2], id_list[3])

        return quantized, semantic_id

    def forward(self, x: torch.Tensor) -> dict[str, Any]:
        """Forward pass with straight-through estimator.

        The straight-through estimator allows gradients to flow through
        discrete quantization. In the forward pass, we use quantized values.
        In the backward pass, gradients flow as if no quantization occurred.

        This is achieved by: z_q = z + (quantize(z) - z).detach()
        The detach() stops gradients from the quantization operation.

        Returns dict with:
            - quantized: Quantized latent codes
            - semantic_id: Discrete semantic ID tuple
            - reconstruction: Reconstructed embedding from decoder
            - losses: Dictionary of training losses
                - reconstruction: MSE between input and reconstruction
                - entropy: Encourages uniform code usage
                - total: Weighted sum of all losses
        """
        # Encode to discrete representation
        z = self.projection(x)

        if self.use_l2_norm:
            z = F.normalize(z, p=2, dim=-1) * 2.0

        # Quantize with straight-through
        z_quantized = self._quantize_straight_through(z)

        # Decode
        x_recon = self.decoder(z_quantized)

        # Compute losses
        recon_loss = F.mse_loss(x_recon, x)

        # Entropy regularization (encourage use of all levels)
        entropy_loss = self._compute_entropy_loss(z)

        # Get semantic ID
        _, semantic_id = self.encode(x)

        return {
            "quantized": z_quantized,
            "semantic_id": semantic_id,
            "reconstruction": x_recon,
            "losses": {
                "reconstruction": recon_loss,
                "entropy": entropy_loss * 0.01,  # Small weight
                "total": recon_loss + entropy_loss * 0.01,
            },
        }

    def _quantize_straight_through(self, z: torch.Tensor) -> torch.Tensor:
        """Quantize with straight-through gradient estimator.

        Straight-through estimator formula:
            z_quantized = z + (quantize(z) - z).detach()

        This allows:
        - Forward pass: Uses quantized values (discrete)
        - Backward pass: Gradients flow through z (continuous)

        The .detach() operation stops gradients from flowing through
        the quantization operation, treating it as a constant.
        """
        z_quantized = torch.zeros_like(z)

        for i in range(self.latent_dim):
            # Scale to [0, levels[i]-1]
            bounds_i = self.bounds[i]
            scaled = (z[:, i] - bounds_i[0]) / (bounds_i[1] - bounds_i[0])
            scaled = scaled.clamp(0, 1) * (self.levels[i] - 1)

            # Round and dequantize
            level = scaled.round().float()
            bounds_i = self.bounds[i]
            dequantized = (level / (self.levels[i] - 1)) * (bounds_i[1] - bounds_i[0]) + bounds_i[0]

            # Straight-through: forward = quantized, backward = continuous
            z_quantized[:, i] = z[:, i] + (dequantized - z[:, i]).detach()

        return z_quantized

    def _compute_entropy_loss(self, z: torch.Tensor) -> torch.Tensor:
        """Compute entropy loss to encourage diverse quantization.

        Entropy maximization prevents mode collapse where the model
        only uses a subset of available quantization levels.

        H = -Σ p(i) log p(i)

        Where p(i) is the soft assignment probability to level i.
        We use soft assignments (continuous) rather than hard assignments
        (discrete) to maintain differentiability.

        Returns negative entropy (to minimize for maximum entropy).
        """
        total_entropy = torch.tensor(0.0, device=z.device)

        for i in range(self.latent_dim):
            # Compute soft assignment probabilities
            bounds_i = self.bounds[i]
            scaled = (z[:, i] - bounds_i[0]) / (bounds_i[1] - bounds_i[0])
            scaled = scaled.clamp(0, 1) * (self.levels[i] - 1)

            # Soft assignment using Gumbel-softmax style
            probs = F.softmax(
                -torch.abs(scaled.unsqueeze(-1) - torch.arange(self.levels[i], device=z.device)),
                dim=-1,
            )

            # Entropy
            entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()
            total_entropy = total_entropy + entropy

        # Return negative entropy (minimize for maximum entropy)
        return -total_entropy / self.latent_dim


class HierarchicalVQEncoder(nn.Module):
    """Hierarchical Vector Quantization for multi-level semantic encoding.

    HVQ performs quantization at multiple scales, with each level refining
    the representation from the previous level. This creates a hierarchy
    from coarse to fine-grained features.

    Architecture:
        Input → Level 0 (coarse) → Residual → Level 1 (medium) → ... → Level N (fine)

    Each level:
        1. Quantizes the residual from previous levels
        2. Has its own codebook with different granularity
        3. Contributes to the final representation

    Semantic Hierarchy:
        - Level 0: Coarse semantic category (style/era) - 32 codes
        - Level 1: Refinement (complexity) - 16 codes
        - Level 2: Fine details (variations) - 8 codes
        - Level 3: Residual nuances - 4 codes

    Mathematical Formulation:
        x_0 = input
        For level i:
            q_i, idx_i = quantize(residual_{i-1}, codebook_i)
            residual_i = residual_{i-1} - q_i
        reconstruction = Σ q_i

    Inspired by neural audio codecs (SoundStream, EnCodec) but adapted
    for semantic text representations.
    """

    def __init__(
        self,
        input_dim: int = 4096,
        num_levels: int = 4,
        codebook_sizes: list[int] | None = None,
        hidden_dim: int = 256,
    ):
        """Initialize hierarchical VQ encoder.

        Args:
            input_dim: Input embedding dimension
            num_levels: Number of hierarchy levels
            codebook_sizes: Size of codebook at each level
            hidden_dim: Hidden dimension for projections

        """
        super().__init__()

        self.input_dim = input_dim
        self.num_levels = num_levels
        self.codebook_sizes = codebook_sizes or [32, 16, 8, 4]
        self.hidden_dim = hidden_dim

        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # Hierarchical quantizers and codebooks
        # Each level has its own projection and codebook
        self.quantizers = nn.ModuleList()  # Projection layers
        self.codebooks = nn.ParameterList()  # Learnable codebook vectors

        for level, codebook_size in enumerate(self.codebook_sizes):
            # Projection for this level
            proj: nn.Module
            if level == 0:
                proj = nn.Identity()
            else:
                proj = nn.Linear(hidden_dim, hidden_dim)

            self.quantizers.append(proj)

            # Codebook for this level
            # Initialize with small random values for stable training
            # Each row is a prototype vector in the codebook
            codebook = nn.Parameter(torch.randn(codebook_size, hidden_dim) * 0.02)
            self.codebooks.append(codebook)

        # Output projection
        self.output_proj = nn.Linear(hidden_dim, input_dim)

    def encode_level(self, z: torch.Tensor, level: int) -> tuple[torch.Tensor, int]:
        """Encode at specific hierarchy level.

        Vector quantization process:
        1. Project input to level-specific space
        2. Find nearest codebook entry (L2 distance)
        3. Return codebook entry and its index

        This is similar to k-means clustering where codebook
        entries are cluster centers.

        Returns:
            Tuple of (quantized vector from codebook, codebook index)

        """
        # Project for this level
        z_proj = self.quantizers[level](z)

        # Find nearest codebook entry using L2 distance
        # cdist computes pairwise distances between all vectors
        codebook = self.codebooks[level]
        distances = torch.cdist(
            z_proj.unsqueeze(0),
            codebook.unsqueeze(0),
        )  # [1, batch, codebook_size]
        indices = distances.argmin(dim=-1).squeeze(0)  # Get index of nearest codebook entry

        # Get quantized vector
        quantized = codebook[indices]

        result_idx = indices.item() if indices.numel() == 1 else indices.tolist()
        return quantized, result_idx  # type: ignore

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, SemanticID]:
        """Encode to hierarchical discrete representation.

        Returns:
            Tuple of (reconstructed embedding, semantic ID)

        """
        # Initial projection
        z = self.input_proj(x)

        residual = z
        quantized_sum = torch.zeros_like(z)
        indices = []

        # Hierarchical quantization
        for level in range(self.num_levels):
            # Quantize residual
            quantized, idx = self.encode_level(residual, level)
            quantized_sum += quantized

            # Update residual
            residual = residual - quantized

            indices.append(idx)

        # Reconstruct
        x_recon = self.output_proj(quantized_sum)

        # Create semantic ID from indices - ensure 4-tuple of ints
        id_list: list[int] = []
        for i, idx in enumerate(indices[:4]):
            if isinstance(idx, int):
                id_list.append(idx)
            elif isinstance(idx, list) and len(idx) > 0:
                id_list.append(int(idx[0]))
            else:
                id_list.append(0)

        # Pad with zeros if needed
        while len(id_list) < 4:
            id_list.append(0)

        semantic_id: tuple[int, int, int, int] = (id_list[0], id_list[1], id_list[2], id_list[3])

        return x_recon, semantic_id

    def forward(self, x: torch.Tensor) -> dict[str, Any]:
        """Forward pass with hierarchical quantization.

        Returns dict with:
            - reconstruction: Reconstructed embedding
            - semantic_id: Hierarchical discrete code
            - losses: Training losses per level
        """
        z = self.input_proj(x)

        residual = z
        quantized_sum = torch.zeros_like(z)
        indices = []
        losses = {}

        # Hierarchical encoding
        for level in range(self.num_levels):
            # Project and quantize
            z_proj = self.quantizers[level](residual)

            # Compute distances to codebook
            codebook = self.codebooks[level]
            distances = torch.cdist(z_proj.unsqueeze(0), codebook.unsqueeze(0))
            min_indices = distances.argmin(dim=-1).squeeze(0)

            # Get quantized vectors
            quantized = codebook[min_indices]

            # Straight-through estimator
            quantized_st = residual + (quantized - residual).detach()
            quantized_sum += quantized_st

            # Commitment loss for this level
            commit_loss = F.mse_loss(quantized.detach(), residual)
            losses[f"commit_{level}"] = commit_loss

            # Update residual
            residual = residual - quantized_st.detach()
            idx_result = min_indices.item() if min_indices.numel() == 1 else min_indices.tolist()
            indices.append(idx_result)

        # Reconstruct
        x_recon = self.output_proj(quantized_sum)

        # Total reconstruction loss
        recon_loss = F.mse_loss(x_recon, x)
        losses["reconstruction"] = recon_loss
        losses["total"] = recon_loss + sum(losses[k] for k in losses if "commit" in k) * 0.25

        # Create semantic ID - ensure it's a 4-tuple of ints
        id_list = []
        for idx in indices[:4]:
            if isinstance(idx, int):
                id_list.append(idx)
            elif isinstance(idx, list) and len(idx) > 0:
                id_list.append(int(idx[0]))
            else:
                id_list.append(0)
        while len(id_list) < 4:
            id_list.append(0)
        semantic_id: tuple[int, int, int, int] = (id_list[0], id_list[1], id_list[2], id_list[3])

        return {"reconstruction": x_recon, "semantic_id": semantic_id, "losses": losses}


# Unified encoder interface
class UnifiedSemanticEncoder:
    """Unified interface for different semantic encoding strategies.

    Automatically selects between FSQ, Hierarchical VQ, or standard RVQ
    based on configuration.
    """

    def __init__(
        self,
        input_dim: int = 4096,
        encoding_type: str = "fsq",  # "fsq", "hvq", or "rvq"
    ):
        """Initialize encoder with specified type.

        Args:
            input_dim: Input embedding dimension
            encoding_type: Type of encoder to use

        """
        self.input_dim = input_dim
        self.encoding_type = encoding_type
        self.encoder: FSQEncoder | HierarchicalVQEncoder

        # Initialize appropriate encoder
        if encoding_type == "fsq":
            self.encoder = FSQEncoder(input_dim=input_dim)
            logger.info("📊 Using FSQ encoder for discrete semantic IDs")
        elif encoding_type == "hvq":
            self.encoder = HierarchicalVQEncoder(input_dim=input_dim)
            logger.info("🎯 Using Hierarchical VQ encoder")
        else:
            raise ValueError(f"Unknown encoder type: {encoding_type}. Use 'fsq' or 'hvq'")

    def encode(self, embedding: torch.Tensor) -> tuple[int, int, int, int]:
        """Encode embedding to semantic ID.

        Args:
            embedding: Input embedding

        Returns:
            4-tuple semantic ID

        """
        _, semantic_id = self.encoder.encode(embedding)
        return semantic_id

    def train_step(self, embedding: torch.Tensor) -> dict[str, Any]:
        """Single training step.

        Returns:
            Dict with losses and outputs

        """
        return self.encoder(embedding)  # type: ignore


# Factory function
def get_semantic_encoder(
    input_dim: int = 4096,
    use_fsq: bool | None = None,
) -> UnifiedSemanticEncoder:
    """Get appropriate semantic encoder based on configuration.

    Args:
        input_dim: Input embedding dimension
        use_fsq: Override USE_FSQ constant

    Returns:
        Unified semantic encoder instance

    """
    if use_fsq is None:
        use_fsq = USE_FSQ

    encoding_type = "fsq" if use_fsq else "hvq" if USE_HIERARCHICAL_VQ else "fsq"

    return UnifiedSemanticEncoder(input_dim=input_dim, encoding_type=encoding_type)

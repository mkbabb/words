"""Visualization-specific API models for series approximation."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class VisualizationRequest(BaseModel):
    """Request for series visualization data."""
    samples: list[str] = Field(..., description="Complex samples as strings")
    method: Literal["fourier", "legendre"] = Field(..., description="Approximation method")
    n_terms: int = Field(..., ge=1, le=100, description="Number of terms to compute")
    resolution: int = Field(default=200, ge=50, le=1000, description="Animation resolution")


class FourierVisualizationTerm(BaseModel):
    """Single term in Fourier series for visualization."""
    index: int
    coefficient: str  # Complex as string like "1.5+2.3j"
    magnitude: float
    phase: float
    frequency: int


class LegendreVisualizationTerm(BaseModel):
    """Single term in Legendre series for visualization."""
    index: int
    coefficient: str  # Complex as string
    degree: int
    x_values: list[float]  # Domain points
    y_values: list[str]    # Basis function values as complex strings


class VisualizationResponse(BaseModel):
    """Response containing all data needed for animation."""
    method: str
    n_terms: int
    original_samples: list[str]
    approximation: list[str]
    mse: float
    
    # Method-specific data
    fourier_terms: list[FourierVisualizationTerm] = Field(default_factory=list)
    legendre_terms: list[LegendreVisualizationTerm] = Field(default_factory=list)
    
    # Animation metadata
    animation_domain: tuple[float, float] = Field(default=(-1.0, 1.0))
    recommended_duration: float = Field(default=3.0)
"""Legendre API models."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class LegendrePolynomialRequest(BaseModel):
    """Request for computing Legendre polynomial values."""
    degree: int = Field(..., ge=0, le=100, description="Polynomial degree (0-100)")
    points: list[float] = Field(..., description="Points at which to evaluate (-1 <= x <= 1)")


class LegendrePolynomialResponse(BaseModel):
    """Response with Legendre polynomial values."""
    degree: int
    points: list[float]
    values: list[float]


class LegendreSeriesRequest(BaseModel):
    """Request for Legendre series approximation."""
    samples: list[complex] = Field(..., description="Complex samples to approximate")
    n_harmonics: int = Field(..., ge=1, le=100, description="Number of harmonics (1-100)")


class LegendreSeriesResponse(BaseModel):
    """Response with Legendre series approximation."""
    coefficients: list[complex]
    approximated_values: list[complex]
    n_harmonics: int
    mse: float = Field(..., description="Mean squared error of approximation")


class LegendreImageRequest(BaseModel):
    """Request for image-based Legendre approximation."""
    encoding_method: str = Field(
        default="luminance", 
        description="Encoding method: luminance, hilbert, or rgb_complex"
    )
    n_harmonics: int = Field(default=50, ge=1, le=100, description="Number of harmonics")
    visualization_method: str = Field(
        default="magnitude",
        description="Visualization method: magnitude, phase, real, or rgb_complex"
    )


class LegendreImageResponse(BaseModel):
    """Response with image Legendre approximation results."""
    coefficients: list[complex]
    n_harmonics: int
    original_size: tuple[int, int]
    approximation_quality: float = Field(..., description="Quality metric (0-1)")
    reconstructed_image: str = Field(..., description="Base64-encoded PNG image")
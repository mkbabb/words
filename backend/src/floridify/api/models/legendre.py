"""Legendre API models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Any, Union


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


class FourierSeriesRequest(BaseModel):
    """Request for Fourier series approximation."""
    samples: list[complex] = Field(..., description="Complex samples to approximate")
    n_coeffs: int = Field(..., ge=1, le=100, description="Number of Fourier coefficients (1-100)")


class FourierSeriesResponse(BaseModel):
    """Response with Fourier series approximation."""
    coefficients: list[complex]
    approximated_values: list[complex]
    n_coeffs: int
    mse: float = Field(..., description="Mean squared error of approximation")


class UnifiedSeriesRequest(BaseModel):
    """Request for unified series approximation (supports both Fourier and Legendre)."""
    samples: list[str] = Field(..., description="Complex samples as strings (e.g., '1+2j', '3.5', '-2j')")
    n_coeffs: int = Field(..., ge=1, le=200, description="Number of coefficients (1-200)")
    method: str = Field(..., description="Approximation method: 'fourier' or 'legendre'")
    type: str = Field(default="fft", description="For Legendre: 'fft' or 'quadrature'")
    
    @field_validator('samples')
    @classmethod
    def convert_samples_to_complex(cls, v):
        """Convert string samples to complex numbers."""
        converted = []
        for sample in v:
            try:
                converted.append(complex(sample))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid complex number format: {sample}")
        return converted


class UnifiedSeriesResponse(BaseModel):
    """Response with unified series approximation."""
    coefficients: list[str]
    approximated_values: list[str]
    n_coeffs: int
    method: str
    type: str | None
    basis_data: list[dict] = Field(default_factory=list, description="Basis function data for animation")
    mse: float = Field(..., description="Mean squared error of approximation")
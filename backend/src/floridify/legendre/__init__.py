"""Legendre polynomial computation and series approximation."""

from .core import PolynomialComputer, SeriesApproximator, UnifiedApproximator

__all__ = [
    "PolynomialComputer", "SeriesApproximator", "UnifiedApproximator"
]

# Lazy import for image processor to avoid dependency issues
def get_image_processor():
    from .image_processor import ImageToComplexArrayProcessor
    return ImageToComplexArrayProcessor
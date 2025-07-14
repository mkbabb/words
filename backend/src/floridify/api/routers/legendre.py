"""Legendre polynomial API endpoints."""

from __future__ import annotations

import base64
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Annotated, Any

from ...legendre.core import PolynomialComputer, UnifiedApproximator
from ...legendre import get_image_processor
from ...utils.logging import get_logger
from ..models.legendre import (
    LegendrePolynomialRequest,
    LegendrePolynomialResponse,
    LegendreSeriesRequest,
    LegendreSeriesResponse,
    LegendreImageRequest,
    LegendreImageResponse,
    FourierSeriesRequest,
    FourierSeriesResponse,
    UnifiedSeriesRequest,
    UnifiedSeriesResponse,
)
from ..models.visualization import (
    VisualizationRequest,
    VisualizationResponse,
)
from ...legendre.visualizer import SeriesVisualizer

logger = get_logger(__name__)
router = APIRouter()


@router.post("/legendre/polynomial", response_model=LegendrePolynomialResponse)
async def compute_legendre_polynomial(request: LegendrePolynomialRequest) -> LegendrePolynomialResponse:
    """Compute Legendre polynomial values at specified points.
    
    Evaluates P_n(x) for the given degree n at the specified points.
    Points must be in the interval [-1, 1].
    """
    try:
        # Validate points are in [-1, 1]
        points_array = np.array(request.points)
        if np.any(np.abs(points_array) > 1.0):
            raise HTTPException(400, "All points must be in the interval [-1, 1]")
        
        # Compute polynomial values
        values = PolynomialComputer.legendre(request.degree, points_array)
        
        return LegendrePolynomialResponse(
            degree=request.degree,
            points=request.points,
            values=values.tolist()
        )
    except Exception as e:
        logger.error(f"Error computing Legendre polynomial: {e}")
        raise HTTPException(500, f"Computation error: {str(e)}")


@router.post("/legendre/series", response_model=LegendreSeriesResponse)
async def compute_legendre_series(request: LegendreSeriesRequest) -> LegendreSeriesResponse:
    """Compute Legendre series approximation for complex samples.
    
    Approximates the input samples using a Legendre series with the specified
    number of harmonics. Returns coefficients and approximated values.
    """
    try:
        # Convert to numpy array
        samples = np.array(request.samples, dtype=complex)
        
        # Create approximator and compute coefficients
        approximator = UnifiedApproximator(max_degree=request.n_harmonics)
        fit_result = approximator.fit(samples, request.n_harmonics, method="legendre", type="quadrature")
        
        # Evaluate approximation at sample points
        x_eval = np.linspace(-1, 1, len(samples))
        approx_values = approximator.evaluate(fit_result, x_eval)
        
        # Compute mean squared error
        mse = float(np.mean(np.abs(samples - approx_values)**2))
        
        return LegendreSeriesResponse(
            coefficients=fit_result["coefficients"].tolist(),
            approximated_values=approx_values.tolist(),
            n_harmonics=request.n_harmonics,
            mse=mse
        )
    except Exception as e:
        logger.error(f"Error computing Legendre series: {e}")
        raise HTTPException(500, f"Computation error: {str(e)}")


@router.post("/legendre/image", response_model=LegendreImageResponse)
async def process_image_legendre(
    file: Annotated[UploadFile, File(description="Image file to process")],
    encoding_method: Annotated[str, Form()] = "luminance",
    n_harmonics: Annotated[int, Form(ge=1, le=100)] = 50,
    visualization_method: Annotated[str, Form()] = "magnitude"
) -> LegendreImageResponse:
    """Process an image through Legendre series approximation.
    
    Converts the image to a complex array, computes Legendre coefficients,
    and returns a reconstructed image along with approximation metrics.
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(400, "File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Convert to complex array
        ImageToComplexArrayProcessor = get_image_processor()
        complex_array = ImageToComplexArrayProcessor.image_to_complex_1d(
            image_data, method=encoding_method
        )
        
        # Get original image dimensions
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(image_data))
        original_size = img.size
        
        # Compute Legendre approximation
        approximator = UnifiedApproximator(max_degree=n_harmonics)
        fit_result = approximator.fit(complex_array, n_harmonics, method="legendre", type="quadrature")
        
        # Evaluate approximation
        x_eval = np.linspace(-1, 1, len(complex_array))
        approx_values = approximator.evaluate(fit_result, x_eval)
        
        # Convert back to image
        reconstructed_bytes = ImageToComplexArrayProcessor.complex_1d_to_image(
            approx_values, original_size[0], original_size[1], method=visualization_method
        )
        
        # Encode as base64
        reconstructed_b64 = base64.b64encode(reconstructed_bytes).decode("utf-8")
        
        # Compute quality metric (1 - normalized MSE)
        mse = np.mean(np.abs(complex_array - approx_values)**2)
        signal_power = np.mean(np.abs(complex_array)**2)
        quality = float(1 - min(1, mse / (signal_power + 1e-10)))
        
        return LegendreImageResponse(
            coefficients=fit_result["coefficients"].tolist(),
            n_harmonics=n_harmonics,
            original_size=original_size,
            approximation_quality=quality,
            reconstructed_image=f"data:image/png;base64,{reconstructed_b64}"
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(500, f"Processing error: {str(e)}")


@router.get("/legendre/polynomials/{max_degree}")
async def get_polynomial_data(max_degree: int) -> dict[str, Any]:
    """Get polynomial data for visualization.
    
    Returns polynomial values for degrees 0 to max_degree evaluated
    at 200 points in [-1, 1].
    """
    try:
        if max_degree < 0 or max_degree > 20:
            raise HTTPException(400, "max_degree must be between 0 and 20")
        
        # Evaluation points
        x = np.linspace(-1, 1, 200)
        
        # Compute all polynomials
        polynomials = []
        for n in range(max_degree + 1):
            values = PolynomialComputer.legendre(n, x)
            polynomials.append({
                "degree": n,
                "x": x.tolist(),
                "y": values.tolist()
            })
        
        return {
            "polynomials": polynomials,
            "max_degree": max_degree
        }
        
    except Exception as e:
        logger.error(f"Error getting polynomial data: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/fourier/series", response_model=FourierSeriesResponse)
async def compute_fourier_series(request: FourierSeriesRequest) -> FourierSeriesResponse:
    """Compute Fourier series approximation for complex samples.
    
    Approximates the input samples using a Fourier series with the specified
    number of coefficients. Returns coefficients and approximated values.
    """
    try:
        # Convert to numpy array
        samples = np.array(request.samples, dtype=complex)
        
        # Create approximator and compute coefficients
        approximator = UnifiedApproximator(max_degree=request.n_coeffs)
        fit_result = approximator.fit(samples, request.n_coeffs, method="fourier")
        
        # Evaluate approximation at sample points
        x_eval = np.linspace(-1, 1, len(samples))
        approx_values = approximator.evaluate(fit_result, x_eval)
        
        # Compute mean squared error
        mse = float(np.mean(np.abs(samples - approx_values)**2))
        
        return FourierSeriesResponse(
            coefficients=fit_result["coefficients"].tolist(),
            approximated_values=approx_values.tolist(),
            n_coeffs=request.n_coeffs,
            mse=mse
        )
    except Exception as e:
        logger.error(f"Error computing Fourier series: {e}")
        raise HTTPException(500, f"Computation error: {str(e)}")


@router.post("/series/unified", response_model=UnifiedSeriesResponse)
async def compute_unified_series(request: UnifiedSeriesRequest) -> UnifiedSeriesResponse:
    """Compute unified series approximation supporting both Fourier and Legendre methods.
    
    This endpoint provides basis function data for animation purposes and supports
    both approximation methods with their respective options.
    """
    try:
        # Convert to numpy array
        samples = np.array(request.samples, dtype=complex)
        
        # Create approximator and compute coefficients
        approximator = UnifiedApproximator(max_degree=request.n_coeffs)
        fit_result = approximator.fit(
            samples, 
            request.n_coeffs, 
            method=request.method,
            type=request.type if request.method == "legendre" else "fft"
        )
        
        # Evaluate approximation at sample points
        x_eval = np.linspace(-1, 1, len(samples))
        approx_values = approximator.evaluate(fit_result, x_eval)
        
        # Generate basis function data for animation
        basis_data = []
        x_basis = np.linspace(-1, 1, 100)  # High resolution for smooth animation
        
        for n in range(request.n_coeffs):  # Use all requested coefficients
            basis_func = approximator.get_basis_function(n, fit_result["basis"])
            basis_values = basis_func(x_basis)
            
            # For Fourier, include magnitude and phase data for epicycle animation
            if request.method == "fourier":
                coeff = fit_result["coefficients"][n]
                basis_data.append({
                    "index": n,
                    "coefficient": str(complex(coeff)),
                    "magnitude": float(np.abs(coeff)),
                    "phase": float(np.angle(coeff)),
                    "frequency": n,
                    "x": x_basis.tolist(),
                    "values": [str(complex(v)) for v in basis_values]
                })
            else:  # Legendre
                coeff = fit_result["coefficients"][n]
                basis_data.append({
                    "index": n,
                    "coefficient": str(complex(coeff)),
                    "degree": n,
                    "x": x_basis.tolist(),
                    "values": [str(complex(v)) for v in basis_values]
                })
        
        # Compute mean squared error
        mse = float(np.mean(np.abs(samples - approx_values)**2))
        
        return UnifiedSeriesResponse(
            coefficients=[str(complex(c)) for c in fit_result["coefficients"]],
            approximated_values=[str(complex(v)) for v in approx_values],
            n_coeffs=request.n_coeffs,
            method=request.method,
            type=fit_result["type"],
            basis_data=basis_data,
            mse=mse
        )
    except Exception as e:
        logger.error(f"Error computing unified series: {e}")
        raise HTTPException(500, f"Computation error: {str(e)}")


@router.post("/visualization/series", response_model=VisualizationResponse)
async def compute_series_visualization(request: VisualizationRequest) -> VisualizationResponse:
    """Compute series visualization data optimized for animation.
    
    This endpoint provides clean, efficient data specifically designed for
    frontend visualization with proper complex number serialization.
    """
    try:
        # Convert string samples to complex
        samples = np.array([complex(s) for s in request.samples])
        
        # Create visualizer and compute
        visualizer = SeriesVisualizer(max_terms=request.n_terms)
        result = visualizer.compute_visualization(
            samples, request.method, request.n_terms, request.resolution
        )
        
        return VisualizationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error computing visualization: {e}")
        raise HTTPException(500, f"Visualization error: {str(e)}")
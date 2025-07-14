"""Optimized series computation and visualization data preparation."""

from __future__ import annotations
import numpy as np
from numpy.typing import NDArray
from scipy import fft
from .core import PolynomialComputer, SeriesApproximator


def complex_to_string(c: complex) -> str:
    """Convert complex number to clean string representation."""
    if abs(c.imag) < 1e-12:
        return str(c.real)
    elif abs(c.real) < 1e-12:
        return f"{c.imag}j"
    else:
        sign = "+" if c.imag >= 0 else ""
        return f"{c.real}{sign}{c.imag}j"


class SeriesVisualizer:
    """High-performance series computation with visualization data."""
    
    def __init__(self, max_terms: int = 100):
        self.max_terms = max_terms
        self.approximator = SeriesApproximator(max_terms)
    
    def compute_fourier_visualization(self, samples: NDArray[np.complex128], 
                                    n_terms: int, resolution: int = 200) -> dict:
        """Compute Fourier series with visualization data."""
        n_terms = min(n_terms, len(samples), self.max_terms)
        
        # Compute FFT coefficients
        coeffs = fft.fft(samples) / len(samples)
        
        # Arrange coefficients for epicycle visualization
        # DC component first, then positive/negative frequency pairs
        vis_coeffs = np.zeros(n_terms, dtype=complex)
        vis_freqs = np.zeros(n_terms, dtype=int)
        
        vis_coeffs[0] = coeffs[0]  # DC component
        vis_freqs[0] = 0
        
        # Interleave positive and negative frequencies
        for k in range(1, (n_terms + 1) // 2):
            if 2*k - 1 < n_terms:
                vis_coeffs[2*k - 1] = coeffs[k]
                vis_freqs[2*k - 1] = k
            if 2*k < n_terms and len(samples) - k < len(samples):
                vis_coeffs[2*k] = coeffs[len(samples) - k]
                vis_freqs[2*k] = -k
        
        # Evaluate approximation
        x_eval = np.linspace(0, 2*np.pi, len(samples))
        approximation = np.zeros_like(samples)
        for k in range(n_terms):
            approximation += vis_coeffs[k] * np.exp(1j * vis_freqs[k] * x_eval)
        
        # Prepare visualization terms
        fourier_terms = []
        for k in range(n_terms):
            coeff = vis_coeffs[k]
            fourier_terms.append({
                "index": k,
                "coefficient": complex_to_string(coeff),
                "magnitude": float(abs(coeff)),
                "phase": float(np.angle(coeff)),
                "frequency": int(vis_freqs[k])
            })
        
        # Sort by magnitude (largest first) for better visualization
        fourier_terms.sort(key=lambda x: x["magnitude"], reverse=True)
        
        # Compute MSE
        mse = float(np.mean(np.abs(samples - approximation)**2))
        
        return {
            "method": "fourier",
            "n_terms": n_terms,
            "original_samples": [complex_to_string(s) for s in samples],
            "approximation": [complex_to_string(a) for a in approximation],
            "mse": mse,
            "fourier_terms": fourier_terms,
            "legendre_terms": [],
            "animation_domain": (0.0, 2*np.pi),
            "recommended_duration": 6.0
        }
    
    def compute_legendre_visualization(self, samples: NDArray[np.complex128], 
                                     n_terms: int, resolution: int = 200) -> dict:
        """Compute Legendre series with visualization data."""
        n_terms = min(n_terms, self.max_terms)
        
        # Compute Legendre coefficients using quadrature
        coeffs = self.approximator.legendre_coefficients(samples, n_terms, "quadrature")
        
        # Evaluate approximation
        x_eval = np.linspace(-1, 1, len(samples))
        approximation = self.approximator.evaluate_series(coeffs, x_eval, "legendre")
        
        # Prepare high-resolution basis functions for smooth animation
        x_basis = np.linspace(-1, 1, resolution)
        legendre_terms = []
        
        for n in range(n_terms):
            # Compute nth Legendre polynomial
            basis_values = PolynomialComputer.legendre(n, x_basis)
            
            legendre_terms.append({
                "index": n,
                "coefficient": complex_to_string(coeffs[n]),
                "degree": n,
                "x_values": x_basis.tolist(),
                "y_values": [complex_to_string(complex(v)) for v in basis_values]
            })
        
        # Compute MSE
        mse = float(np.mean(np.abs(samples - approximation)**2))
        
        return {
            "method": "legendre", 
            "n_terms": n_terms,
            "original_samples": [complex_to_string(s) for s in samples],
            "approximation": [complex_to_string(a) for a in approximation],
            "mse": mse,
            "fourier_terms": [],
            "legendre_terms": legendre_terms,
            "animation_domain": (-1.0, 1.0),
            "recommended_duration": 3.0
        }
    
    def compute_visualization(self, samples: NDArray[np.complex128], 
                            method: str, n_terms: int, resolution: int = 200) -> dict:
        """Unified visualization computation."""
        if method == "fourier":
            return self.compute_fourier_visualization(samples, n_terms, resolution)
        elif method == "legendre":
            return self.compute_legendre_visualization(samples, n_terms, resolution)
        else:
            raise ValueError(f"Unknown method: {method}")
"""Unified polynomial series approximation with FFT-based transforms."""

from __future__ import annotations
from typing import Callable, Tuple
import numpy as np
from numpy.typing import NDArray
from scipy import special, fft
from scipy.integrate import quad
from functools import lru_cache


class PolynomialComputer:
    """Efficient polynomial evaluation using recurrence relations."""
    
    @staticmethod
    def legendre(n: int, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Compute Legendre polynomial P_n(x) using three-term recurrence."""
        if n == 0:
            return np.ones_like(x)
        elif n == 1:
            return x
        
        p_prev, p_curr = np.ones_like(x), x
        for k in range(2, n + 1):
            p_next = ((2*k - 1) * x * p_curr - (k - 1) * p_prev) / k
            p_prev, p_curr = p_curr, p_next
        return p_curr
    
    
    @staticmethod
    def legendre_derivative(n: int, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Compute dP_n/dx using stable recurrence."""
        if n == 0:
            return np.zeros_like(x)
        
        # Avoid singularity at x = ±1
        mask = np.abs(x) < 1 - 1e-10
        result = np.zeros_like(x)
        
        if np.any(mask):
            p_n = PolynomialComputer.legendre(n, x[mask])
            p_n_minus_1 = PolynomialComputer.legendre(n - 1, x[mask])
            result[mask] = n * (x[mask] * p_n - p_n_minus_1) / (x[mask]**2 - 1)
        
        # Boundary values
        result[x >= 1 - 1e-10] = n * (n + 1) / 2
        result[x <= -1 + 1e-10] = (-1)**(n + 1) * n * (n + 1) / 2
        
        return result


class SeriesApproximator:
    """Generalized series approximation for Fourier and Legendre bases."""
    
    def __init__(self, max_degree: int = 100):
        self.max_degree = max_degree
        # Gauss-Legendre quadrature for accurate integration
        self.quad_points, self.quad_weights = np.polynomial.legendre.leggauss(
            min(2 * max_degree + 1, 200)
        )
    
    def fourier_coefficients(self, samples: NDArray[np.complex128], n_coeffs: int) -> NDArray[np.complex128]:
        """Compute Fourier coefficients using FFT."""
        n_coeffs = min(n_coeffs, len(samples))
        # Use FFT for efficiency
        coeffs = fft.fft(samples, n=n_coeffs) / len(samples)
        return coeffs[:n_coeffs]
    
    def legendre_coefficients(self, samples: NDArray[np.complex128], n_coeffs: int, 
                            type: str = "quadrature") -> NDArray[np.complex128]:
        """Compute Legendre coefficients using specified method."""
        n_coeffs = min(n_coeffs, self.max_degree + 1)
        
        if type == "quadrature":
            # Direct quadrature method
            # Interpolate samples to quadrature points
            x_samples = np.linspace(-1, 1, len(samples))
            f_real = np.interp(self.quad_points, x_samples, samples.real)
            f_imag = np.interp(self.quad_points, x_samples, samples.imag)
            f_quad = f_real + 1j * f_imag
            
            # Compute coefficients using quadrature
            coeffs = np.zeros(n_coeffs, dtype=complex)
            for n in range(n_coeffs):
                p_n = PolynomialComputer.legendre(n, self.quad_points)
                coeffs[n] = (2*n + 1) / 2 * np.sum(f_quad * p_n * self.quad_weights)
            
            return coeffs
            
        elif type == "fft":
            # Fast Legendre transform using Chebyshev intermediate
            # Map samples to Chebyshev points
            n = len(samples)
            theta = np.pi * np.arange(n) / (n - 1)
            x_cheb = np.cos(theta)
            
            # Interpolate to Chebyshev grid
            x_uniform = np.linspace(-1, 1, n)
            f_cheb = np.interp(x_cheb, x_uniform, samples.real) + \
                     1j * np.interp(x_cheb, x_uniform, samples.imag)
            
            # DCT for Chebyshev coefficients
            cheb_coeffs = fft.dct(f_cheb, type=1) / (n - 1)
            cheb_coeffs[1:-1] *= 2
            
            # Convert Chebyshev to Legendre (truncated for efficiency)
            n_convert = min(n_coeffs, len(cheb_coeffs))
            leg_coeffs = self._cheb_to_leg(cheb_coeffs[:n_convert])
            
            return leg_coeffs[:n_coeffs]
        else:
            raise ValueError(f"Unknown type: {type}")
    
    def _cheb_to_leg(self, cheb_coeffs: NDArray[np.complex128]) -> NDArray[np.complex128]:
        """Convert Chebyshev to Legendre coefficients."""
        n = len(cheb_coeffs)
        leg_coeffs = np.zeros_like(cheb_coeffs)
        
        # Conversion matrix (sparse, only compute non-zero entries)
        for k in range(n):
            for j in range(k % 2, min(k + 1, n), 2):
                if j == 0:
                    factor = 1.0
                else:
                    factor = 2.0
                # Simplified conversion formula
                coeff = factor * (2*j + 1) * special.eval_legendre(j, 0) / (k + j + 1)
                leg_coeffs[j] += cheb_coeffs[k] * coeff
        
        return leg_coeffs
    
    def evaluate_series(self, coeffs: NDArray[np.complex128], x: NDArray[np.float64], 
                       basis: str = "legendre") -> NDArray[np.complex128]:
        """Evaluate series at given points."""
        result = np.zeros_like(x, dtype=complex)
        
        if basis == "legendre":
            for n, c_n in enumerate(coeffs):
                result += c_n * PolynomialComputer.legendre(n, x)
        elif basis == "fourier":
            # Map x from [-1, 1] to [0, 2π]
            theta = np.pi * (x + 1)
            for n, c_n in enumerate(coeffs):
                result += c_n * np.exp(1j * n * theta)
        
        return result
    
    def extract_basis_functions(self, n_basis: int, basis: str = "legendre") -> Callable:
        """Return callable for nth basis function."""
        if basis == "legendre":
            return lambda x: PolynomialComputer.legendre(n_basis, x)
        elif basis == "fourier":
            return lambda x: np.exp(1j * n_basis * np.pi * (x + 1))
        else:
            raise ValueError(f"Unknown basis: {basis}")


class UnifiedApproximator:
    """High-level interface for polynomial approximation."""
    
    def __init__(self, max_degree: int = 100):
        self.approximator = SeriesApproximator(max_degree)
    
    def fit(self, samples: NDArray[np.complex128], n_coeffs: int, 
            method: str = "legendre", type: str = "fft") -> dict:
        """Fit series approximation to samples.
        
        Args:
            samples: Complex-valued samples to approximate
            n_coeffs: Number of coefficients to compute
            method: 'fourier' or 'legendre'
            type: For Legendre, 'fft' or 'quadrature'
        """
        if method == "fourier":
            coeffs = self.approximator.fourier_coefficients(samples, n_coeffs)
            basis = "fourier"
        elif method == "legendre":
            coeffs = self.approximator.legendre_coefficients(samples, n_coeffs, type)
            basis = "legendre"
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return {
            "coefficients": coeffs,
            "basis": basis,
            "method": method,
            "type": type if method == "legendre" else None,
            "degree": len(coeffs) - 1
        }
    
    def evaluate(self, fit_result: dict, x: NDArray[np.float64]) -> NDArray[np.complex128]:
        """Evaluate fitted approximation."""
        return self.approximator.evaluate_series(
            fit_result["coefficients"], x, fit_result["basis"]
        )
    
    def get_basis_function(self, n: int, basis: str = "legendre") -> Callable:
        """Get nth basis function for visualization."""
        return self.approximator.extract_basis_functions(n, basis)


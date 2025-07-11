"""Test Legendre polynomial computation and API endpoints."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.floridify.legendre import LegendreComputer, LegendreSeriesApproximator


class TestLegendreComputer:
    """Test Legendre polynomial computation."""
    
    def test_polynomial_values(self):
        """Test known polynomial values."""
        x = np.array([-1, 0, 1])
        
        # P_0(x) = 1
        p0 = LegendreComputer.compute_polynomial(0, x)
        np.testing.assert_allclose(p0, [1, 1, 1])
        
        # P_1(x) = x
        p1 = LegendreComputer.compute_polynomial(1, x)
        np.testing.assert_allclose(p1, [-1, 0, 1])
        
        # P_2(x) = (3x^2 - 1)/2
        p2 = LegendreComputer.compute_polynomial(2, x)
        np.testing.assert_allclose(p2, [1, -0.5, 1])
        
    def test_orthogonality(self):
        """Test orthogonality property of Legendre polynomials."""
        # Use Gauss-Legendre quadrature for accurate integration
        x, w = np.polynomial.legendre.leggauss(50)
        
        # Test P_2 and P_3 are orthogonal
        p2 = LegendreComputer.compute_polynomial(2, x)
        p3 = LegendreComputer.compute_polynomial(3, x)
        
        integral = np.sum(p2 * p3 * w)
        assert abs(integral) < 1e-10
        
    def test_normalization(self):
        """Test normalization property: ∫P_n^2 dx = 2/(2n+1)."""
        x, w = np.polynomial.legendre.leggauss(50)
        
        for n in range(5):
            p_n = LegendreComputer.compute_polynomial(n, x)
            integral = np.sum(p_n**2 * w)
            expected = 2 / (2 * n + 1)
            np.testing.assert_allclose(integral, expected, rtol=1e-10)


class TestLegendreSeriesApproximator:
    """Test Legendre series approximation."""
    
    def test_simple_function_approximation(self):
        """Test approximation of simple functions."""
        approximator = LegendreSeriesApproximator(max_degree=20)
        
        # Test approximation of x^2
        def f(x):
            return x**2
        
        coeffs = approximator.compute_coefficients(f, 10)
        
        # For x^2, only P_0 and P_2 should have non-zero coefficients
        # x^2 = 1/3 * P_0(x) + 2/3 * P_2(x)
        assert abs(coeffs[0] - 1/3) < 1e-10
        assert abs(coeffs[1]) < 1e-10
        assert abs(coeffs[2] - 2/3) < 1e-10
        
    def test_series_evaluation(self):
        """Test series evaluation."""
        approximator = LegendreSeriesApproximator()
        
        # Simple coefficients
        coeffs = np.array([1, 0, 0.5])  # P_0 + 0.5*P_2
        x = np.array([0])
        
        result = approximator.evaluate_series(coeffs, x)
        # At x=0: P_0(0)=1, P_2(0)=-0.5
        expected = 1 + 0.5 * (-0.5)
        np.testing.assert_allclose(result, expected)


@pytest.mark.asyncio
async def test_legendre_api_endpoints():
    """Test Legendre API endpoints."""
    from src.floridify.api.main import app
    
    client = TestClient(app)
    
    # Test polynomial computation endpoint
    response = client.post(
        "/api/v1/legendre/polynomial",
        json={"degree": 2, "points": [-1, 0, 1]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["degree"] == 2
    assert len(data["values"]) == 3
    np.testing.assert_allclose(data["values"], [1, -0.5, 1], rtol=1e-10)
    
    # Test series approximation endpoint
    response = client.post(
        "/api/v1/legendre/series",
        json={"samples": [1, 0.5, 0, 0.5, 1], "n_harmonics": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["coefficients"]) == 5
    assert "mse" in data
    
    # Test polynomial data endpoint
    response = client.get("/api/v1/legendre/polynomials/3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["polynomials"]) == 4  # P_0 through P_3
    assert data["max_degree"] == 3
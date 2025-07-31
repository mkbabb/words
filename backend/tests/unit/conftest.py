"""
Unit test configuration without MongoDB dependencies.
"""

import pytest


# Override the global fixtures for unit tests to avoid MongoDB dependencies
@pytest.fixture
def test_db():
    """Mock database fixture for unit tests."""
    return None


@pytest.fixture
def test_storage():
    """Mock storage fixture for unit tests."""
    return None


@pytest.fixture
def async_client():
    """Mock async client for unit tests."""
    return None
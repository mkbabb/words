"""
Basic unit tests to verify test infrastructure is working.
"""

import pytest


class TestBasicInfrastructure:
    """Basic tests to verify test setup."""

    def test_basic_assertion(self):
        """Test that basic assertions work."""
        assert True
        assert 1 + 1 == 2
        assert "hello" == "hello"

    def test_imports_work(self):
        """Test that basic imports work."""
        import json
        
        data = {"test": True}
        assert json.dumps(data) == '{"test": true}'

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test that async test functionality works."""
        import asyncio
        
        async def async_function():
            await asyncio.sleep(0.001)
            return "async_result"
        
        result = await async_function()
        assert result == "async_result"

    def test_pytest_markers(self):
        """Test that pytest markers work."""
        # This test should not be marked as slow
        assert True

    @pytest.mark.slow
    def test_slow_marker(self):
        """Test marked as slow (should be skipped in quick tests)."""
        import time
        time.sleep(0.1)  # Simulate slow operation
        assert True
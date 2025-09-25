"""Shared fixtures for provider tests.

Provider-specific tests rely on the global MongoDB fixtures defined in
``tests/conftest.py``. No additional fixtures are required here; the module
exists to keep pytest discovery behavior consistent across the test suite.
"""

from __future__ import annotations

# Intentionally left minimal.

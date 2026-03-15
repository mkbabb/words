"""Performance test configuration — no MongoDB required."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "performance: reproducible performance microbenchmarks")
    config.addinivalue_line("markers", "search: search pipeline benchmarks")
    config.addinivalue_line("markers", "semantic: semantic search benchmarks")
    config.addinivalue_line("markers", "versioning: versioning/cache pipeline benchmarks")
    config.addinivalue_line("markers", "provider: provider pipeline benchmarks")
    config.addinivalue_line("markers", "timemachine: timemachine diff benchmarks")

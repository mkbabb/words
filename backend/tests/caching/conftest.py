"""Shared fixtures for caching tests."""

import tempfile
from pathlib import Path

import pytest_asyncio

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.manager import VersionedDataManager


@pytest_asyncio.fixture
async def cache_manager():
    """Create a cache manager with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = FilesystemBackend(Path(tmpdir))
        manager = GlobalCacheManager(backend)
        await manager.initialize()
        yield manager


@pytest_asyncio.fixture
async def version_manager(test_db) -> VersionedDataManager:
    """Create a versioned data manager instance."""
    return VersionedDataManager()

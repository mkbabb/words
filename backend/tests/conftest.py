"""Main test configuration with MongoDB setup and async fixture handling."""

import os
import time
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

# Test configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mongodb://localhost:27017")
TEST_DATABASE_NAME = "test_floridify"


def get_document_models():
    """Import all Beanie document models."""
    from floridify.corpus.core import Corpus
    from floridify.providers.dictionary.models import DictionaryProviderEntry
    from floridify.providers.language.models import LanguageEntry
    from floridify.providers.literature.models import LiteratureEntry
    from floridify.search.models import SearchIndex, TrieIndex
    from floridify.search.semantic.models import SemanticIndex
    
    return [
        Corpus.Metadata,
        DictionaryProviderEntry.Metadata,
        LanguageEntry.Metadata,
        LiteratureEntry.Metadata,
        SearchIndex.Metadata,
        SemanticIndex.Metadata,
        TrieIndex.Metadata,
    ]


@pytest_asyncio.fixture(scope="session")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create MongoDB client for test session."""
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongodb_client: AsyncIOMotorClient):
    """Create isolated test database with Beanie initialization."""
    # Use unique database name for each test
    db_name = f"{TEST_DATABASE_NAME}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    db = mongodb_client[db_name]
    
    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=get_document_models(),
    )
    
    yield db
    
    # Clean up - drop database after test
    await mongodb_client.drop_database(db_name)


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio"
    )
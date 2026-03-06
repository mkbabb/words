"""Main test configuration with MongoDB setup and async fixture handling."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from floridify.utils.threading_config import configure_threading

configure_threading()

os.environ["LOG_LEVEL"] = "ERROR"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["FLORIDIFY_DB_TARGET"] = "test"

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from floridify.utils.config import Config

# Model registry is now handled via simple switch statement
# No initialization needed

# Load shared fixture factories (async_client, word_factory, etc.) for all test packages.
pytest_plugins = ("tests.fixtures.conftest",)


def _database_name_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise RuntimeError("database.test_url must include a database name")
    return db_name


def _database_host_signature(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.netloc.rsplit("@", 1)[-1].lower()


def _validate_test_database_urls(runtime_url: str, test_url: str) -> str:
    runtime_db = _database_name_from_uri(runtime_url)
    test_db = _database_name_from_uri(test_url)
    if not test_db.startswith("test_"):
        raise RuntimeError(
            f"Refusing to run tests against non-test DB '{test_db}'. "
            "database.test_url must use a test_ prefix."
        )

    same_cluster = _database_host_signature(runtime_url) == _database_host_signature(test_url)
    if same_cluster and runtime_db == test_db:
        raise RuntimeError(
            "database.test_url resolves to the same database name as runtime_url; "
            "tests aborted to avoid production data mutation."
        )
    return test_db


@pytest.fixture(scope="session")
def mongodb_server() -> str:
    """Provide a remote MongoDB test URI from strict config."""
    config = Config.from_file()
    runtime_url = config.database.get_url("runtime")
    test_url = config.database.get_url("test")
    _validate_test_database_urls(runtime_url, test_url)
    return test_url


@pytest.fixture(scope="session")
def test_db_base_name(mongodb_server: str) -> str:
    """Base test DB name derived from database.test_url."""
    return _database_name_from_uri(mongodb_server)


def get_document_models():
    """Import all Beanie document models."""
    from floridify.caching.models import BaseVersionedData
    from floridify.corpus.core import Corpus
    from floridify.models.base import AudioMedia, ImageMedia
    from floridify.models.dictionary import (
        Definition,
        DictionaryEntry,
        Example,
        Fact,
        Pronunciation,
        Word,
    )
    from floridify.models.relationships import WordRelationship
    from floridify.providers.batch import BatchOperation
    from floridify.providers.dictionary.models import DictionaryProviderEntry
    from floridify.providers.language.models import LanguageEntry
    from floridify.providers.literature.models import LiteratureEntry
    from floridify.search.search_index import SearchIndex
    from floridify.search.semantic.models import SemanticIndex
    from floridify.search.trie_index import TrieIndex
    from floridify.wordlist.models import WordList

    return [
        # Core dictionary models
        Word,
        Definition,
        DictionaryEntry,
        Pronunciation,
        Example,
        Fact,
        # Media models
        AudioMedia,
        ImageMedia,
        # Relationship models
        WordRelationship,
        # WordList models
        WordList,
        # Versioning models
        BaseVersionedData,
        # Batch models
        BatchOperation,
        # Metadata models
        Corpus.Metadata,
        DictionaryProviderEntry.Metadata,
        LanguageEntry.Metadata,
        LiteratureEntry.Metadata,
        SearchIndex.Metadata,
        SemanticIndex.Metadata,
        TrieIndex.Metadata,
    ]


@pytest_asyncio.fixture(scope="function")
async def mongodb_client(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient]:
    """Create MongoDB client for test."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except PyMongoError as e:
        pytest.skip(f"Remote MongoDB test cluster unavailable: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mongodb_client_session(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient]:
    """Create session-scoped MongoDB client for expensive setup (like semantic indices)."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except PyMongoError as e:
        pytest.skip(f"Remote MongoDB test cluster unavailable: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongodb_client: AsyncIOMotorClient, test_db_base_name: str):
    """Create isolated test database with Beanie initialization."""
    db_name = f"{test_db_base_name}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    if not db_name.startswith("test_"):
        raise RuntimeError(f"Refusing to use non-test database name '{db_name}'")
    db = mongodb_client[db_name]

    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=get_document_models(),
    )

    yield db

    # Clean up - drop database after test
    await mongodb_client.drop_database(db_name)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_db_session(mongodb_client_session: AsyncIOMotorClient, test_db_base_name: str):
    """Create session-scoped test database for expensive setup (like semantic indices).

    This database persists for the entire test session to enable:
    - Pre-warming semantic indices once
    - Reusing expensive corpus builds
    - Sharing test data across tests
    """
    db_name = f"{test_db_base_name}_session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    if not db_name.startswith("test_"):
        raise RuntimeError(f"Refusing to use non-test database name '{db_name}'")
    db = mongodb_client_session[db_name]

    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=get_document_models(),
    )

    yield db

    # Clean up - drop database after entire session
    await mongodb_client_session.drop_database(db_name)


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio markers."""
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio")


# Helper functions for API tests
def assert_response_structure(response: dict, required_fields: list[str]) -> None:
    """Assert that response contains all required fields."""
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def assert_valid_object_id(value: str) -> None:
    """Assert that value is a valid MongoDB ObjectId string."""
    assert isinstance(value, str), "ObjectId must be a string"
    assert len(value) == 24, "ObjectId must be 24 characters"
    assert all(c in "0123456789abcdef" for c in value.lower()), "ObjectId must be hexadecimal"

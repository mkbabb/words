"""Main test configuration with MongoDB setup and async fixture handling."""

from __future__ import annotations

# Set OpenMP threading limits BEFORE any library imports to prevent conflicts
# These settings work universally (local development and Docker)
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import shutil
import subprocess
import time
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

# Model registry is now handled via simple switch statement
# No initialization needed

# Test configuration
TEST_DATABASE_NAME = "test_floridify"
DEFAULT_MONGODB_PORT = int(os.getenv("TEST_MONGODB_PORT", "27017"))


@pytest.fixture(scope="session")
def mongodb_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Launch a real mongod instance for the duration of the test session."""
    mongod_bin = shutil.which(os.getenv("MONGOD_BIN", "mongod"))
    if not mongod_bin:
        pytest.skip("mongod binary not available on PATH")

    data_dir = tmp_path_factory.mktemp("mongo-data")
    log_path = Path(data_dir) / "mongod.log"
    port = DEFAULT_MONGODB_PORT

    args = [
        mongod_bin,
        "--dbpath",
        str(data_dir),
        "--port",
        str(port),
        "--bind_ip",
        "127.0.0.1",
        "--nounixsocket",
        "--quiet",
    ]

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)

        try:
            client = MongoClient(f"mongodb://127.0.0.1:{port}", serverSelectionTimeoutMS=500)
            deadline = time.time() + 20
            while True:
                try:
                    client.admin.command("ping")
                    break
                except Exception as exc:  # pragma: no cover - startup delay only
                    if time.time() > deadline:
                        process.terminate()
                        process.wait(timeout=10)
                        pytest.skip(f"MongoDB server failed to start: {exc}")
                    time.sleep(0.2)
            client.close()
            yield f"mongodb://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
                process.kill()
                process.wait(timeout=10)


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
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
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


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_db_session(mongodb_client_session: AsyncIOMotorClient):
    """Create session-scoped test database for expensive setup (like semantic indices).

    This database persists for the entire test session to enable:
    - Pre-warming semantic indices once
    - Reusing expensive corpus builds
    - Sharing test data across tests
    """
    # Use unique database name for this session
    db_name = f"{TEST_DATABASE_NAME}_session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
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

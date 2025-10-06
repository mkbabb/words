"""Main test configuration with MongoDB setup and async fixture handling."""

from __future__ import annotations

# Fix for pytest segfault on Apple Silicon with GTE-Qwen2 model and OpenMP threading
import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import torch
torch.set_default_device("cpu")
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
    from floridify.search.models import SearchIndex, TrieIndex
    from floridify.search.semantic.models import SemanticIndex
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
async def mongodb_client(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create MongoDB client for test session."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="session")
async def mongodb_client_session(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient, None]:
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


@pytest_asyncio.fixture(scope="session")
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


# Additional fixtures for API tests
@pytest_asyncio.fixture
async def async_client(test_db):
    """Create async FastAPI test client."""
    from httpx import ASGITransport, AsyncClient

    from floridify.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for various operations."""
    return {
        "lookup_single": 2.0,  # seconds
        "lookup_batch": 10.0,
        "search_fuzzy": 1.0,
        "search_semantic": 3.0,
        "ai_synthesis": 5.0,
        "corpus_build": 15.0,
        "provider_fetch": 3.0,
    }


# Test data factories for API tests
@pytest_asyncio.fixture
async def word_factory(test_db):
    """Factory for creating Word instances."""
    from floridify.models.dictionary import Language, Word

    created_words = []

    async def _create_word(text: str, language: str = "en", **kwargs):
        """Create and persist a Word instance."""
        lang_enum = Language.ENGLISH if language == "en" else Language(language)
        word = Word(
            text=text,
            language=lang_enum,
            **kwargs,
        )
        await word.save()
        created_words.append(word)
        return word

    yield _create_word

    # Cleanup
    for word in created_words:
        try:
            await word.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def definition_factory(test_db):
    """Factory for creating Definition instances."""
    from floridify.models.dictionary import Definition, DictionaryProvider

    created_definitions = []

    async def _create_definition(
        word_instance,
        text: str = "A test definition",
        part_of_speech: str = "noun",
        **kwargs,
    ):
        """Create and persist a Definition instance."""
        definition = Definition(
            word_id=word_instance.id,
            text=text,
            part_of_speech=part_of_speech,
            providers=[DictionaryProvider.FREE_DICTIONARY],
            **kwargs,
        )
        await definition.save()
        created_definitions.append(definition)
        return definition

    yield _create_definition

    # Cleanup
    for definition in created_definitions:
        try:
            await definition.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def wordlist_factory(test_db):
    """Factory for creating WordList instances."""
    from floridify.models.dictionary import Language, Word
    from floridify.wordlist.models import WordList, WordListItem

    created_wordlists = []
    created_words = []

    async def _create_wordlist(
        name: str = "Test Wordlist",
        description: str = "Test description",
        words: list[str] | None = None,
        is_public: bool = False,
        tags: list[str] | None = None,
        **kwargs,
    ):
        """Create and persist a WordList instance with words."""
        # Create Word documents for each word text if provided
        word_items = []
        if words:
            for word_text in words:
                # Create Word document
                word_doc = Word(
                    text=word_text,
                    language=Language.ENGLISH,
                )
                await word_doc.save()
                created_words.append(word_doc)

                # Create WordListItem
                word_item = WordListItem(word_id=word_doc.id)
                word_items.append(word_item)

        # Create WordList
        wordlist = WordList(
            name=name,
            description=description,
            hash_id=f"test_{name.lower().replace(' ', '_')}_{len(created_wordlists)}",
            words=word_items,
            total_words=len(word_items),
            unique_words=len(word_items),
            is_public=is_public,
            tags=tags or [],
            **kwargs,
        )
        await wordlist.save()
        created_wordlists.append(wordlist)
        return wordlist

    yield _create_wordlist

    # Cleanup
    for wordlist in created_wordlists:
        try:
            await wordlist.delete()
        except Exception:
            pass

    for word in created_words:
        try:
            await word.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def mock_dictionary_providers():
    """Mock dictionary provider setup for API tests."""
    from unittest.mock import AsyncMock, patch

    # Create mock providers
    mock_free_dict = AsyncMock()
    mock_wiktionary = AsyncMock()
    mock_oxford = AsyncMock()

    # Setup default return values
    mock_free_dict.fetch.return_value = {
        "word": "test",
        "phonetic": "/test/",
        "meanings": [
            {
                "partOfSpeech": "noun",
                "definitions": [
                    {
                        "definition": "A procedure for critical evaluation",
                        "example": "The test was difficult",
                    }
                ],
            }
        ],
    }

    mock_wiktionary.fetch.return_value = {
        "word": "test",
        "definitions": [
            {
                "partOfSpeech": "noun",
                "text": "An examination or quiz",
            }
        ],
    }

    mock_oxford.fetch.return_value = None  # Simulate not found

    # Patch the provider imports
    with (
        patch(
            "floridify.providers.dictionary.api.free_dictionary.FreeDictionaryConnector",
            return_value=mock_free_dict,
        ),
        patch(
            "floridify.providers.dictionary.scraper.wiktionary.WiktionaryConnector",
            return_value=mock_wiktionary,
        ),
        patch(
            "floridify.providers.dictionary.api.oxford.OxfordConnector", return_value=mock_oxford
        ),
    ):
        yield {
            "free_dictionary": mock_free_dict,
            "wiktionary": mock_wiktionary,
            "oxford": mock_oxford,
        }


@pytest_asyncio.fixture
async def mock_openai_client():
    """Mock OpenAI client for API tests."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Setup ChatCompletion response
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="This is a synthesized definition for the word.",
            ),
        ),
    ]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Setup embeddings response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [
        MagicMock(embedding=[0.1] * 768),  # Standard embedding dimension
    ]
    mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

    with patch("floridify.ai.connector.OpenAIConnector", return_value=mock_client):
        yield mock_client


@pytest.fixture
def test_words():
    """Common test words for search and lookup tests."""
    return [
        "apple",
        "banana",
        "cherry",
        "date",
        "elderberry",
        "fig",
        "grape",
        "honeydew",
        "kiwi",
        "lemon",
    ]

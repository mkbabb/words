"""Global test configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.floridify.models.dictionary import APIResponseCache, DictionaryEntry


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Initialize test database connection."""
    # Use test database
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["floridify_test"]

    try:
        # Initialize Beanie with test database
        await init_beanie(
            database=database,
            document_models=[DictionaryEntry, APIResponseCache],
        )

        yield database

    finally:
        # Clean up test database
        await database.drop_collection("dictionary_entries")
        await database.drop_collection("api_response_cache")
        client.close()


@pytest.fixture
def mock_database():
    """Mock database operations for unit tests."""
    mock_db = MagicMock()
    
    # Mock Beanie document operations
    mock_entry = MagicMock()
    mock_entry.save = AsyncMock()
    mock_entry.find = AsyncMock(return_value=[])
    mock_entry.find_one = AsyncMock(return_value=None)
    
    mock_db.dictionary_entries = mock_entry
    mock_db.api_response_cache = mock_entry
    
    return mock_db


@pytest.fixture
async def clean_database(test_database):
    """Ensure clean database state for each test."""
    # Clear all collections before each test
    await DictionaryEntry.delete_all()
    await APIResponseCache.delete_all()
    yield test_database
    # Clean up after test
    await DictionaryEntry.delete_all()
    await APIResponseCache.delete_all()


@pytest.fixture
def skip_if_no_mongodb():
    """Skip test if MongoDB is not available."""
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        client.close()
    except Exception:
        pytest.skip("MongoDB not available")


@pytest.fixture
def mock_cache_dir() -> Path:
    """Temporary cache directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with structured responses."""
    client = MagicMock()
    
    # Mock successful completion response
    completion_response = MagicMock()
    completion_response.choices = [MagicMock()]
    completion_response.choices[0].message.content = '''{
        "word": "test",
        "definitions": [{
            "word_type": "noun",
            "definition": "A test definition",
            "examples": ["This is a test."]
        }]
    }'''
    
    client.chat.completions.create = AsyncMock(return_value=completion_response)
    
    # Mock embeddings response
    embedding_response = MagicMock()
    embedding_response.data = [MagicMock()]
    embedding_response.data[0].embedding = [0.1] * 1536  # Standard OpenAI embedding size
    
    client.embeddings.create = AsyncMock(return_value=embedding_response)
    
    return client


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API requests."""
    client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock successful response
    response = MagicMock()
    response.status_code = 200
    response.text = "Mock response content"
    response.json.return_value = {"mock": "data"}
    
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    
    return client


@pytest.fixture
def mock_wiktionary_response():
    """Mock Wiktionary API response structure."""
    return {
        "query": {
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "test",
                    "revisions": [{
                        "*": """==English==\n===Noun===\n{{en-noun}}\n# A test definition.\n#: {{ux|en|This is a '''test'''.}}"""
                    }]
                }
            }
        }
    }


@pytest.fixture
def sample_word_data():
    """Sample word data for testing."""
    return {
        "word": "test",
        "definitions": [{
            "word_type": "noun",
            "definition": "A procedure intended to establish the quality, performance, or reliability of something.",
            "examples": ["This is a test sentence."]
        }],
        "pronunciation": "/test/"
    }

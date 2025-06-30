"""Global test configuration and fixtures."""

import asyncio

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

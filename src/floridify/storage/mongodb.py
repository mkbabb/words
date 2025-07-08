"""MongoDB storage implementation using Beanie."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from ..list.models import WordList
from ..models.models import DictionaryEntry, SynthesizedDictionaryEntry
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Global storage instance for lazy initialization
_storage: MongoDBStorage | None = None


class MongoDBStorage:
    """MongoDB storage for dictionary entries using Beanie ODM."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        database_name: str = "floridify",
    ) -> None:
        """Initialize MongoDB storage.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
        self._initialized = False

    async def connect(self) -> None:
        """Connect to MongoDB and initialize Beanie."""
        self.client = AsyncIOMotorClient(self.connection_string)
        database: Any = self.client[self.database_name]

        # Initialize Beanie with our document models
        await init_beanie(
            database=database,
            document_models=[DictionaryEntry, SynthesizedDictionaryEntry, WordList],
        )

        self._initialized = True

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self._initialized = False

    async def save_entry(self, entry: DictionaryEntry) -> bool:
        """Save a dictionary entry to MongoDB.

        Args:
            entry: DictionaryEntry to save

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False

        try:
            # Use Beanie's upsert functionality
            existing = await DictionaryEntry.find_one(
                DictionaryEntry.word == entry.word
            )

            if existing:
                # Update existing entry
                existing.pronunciation = entry.pronunciation
                existing.provider_data.update(entry.provider_data)
                existing.last_updated = datetime.now()
                await existing.save()
            else:
                # Create new entry
                await entry.create()

            return True

        except Exception as e:
            logger.error(f"Error saving entry for {entry.word}: {e}")
            return False

    async def get_entry(self, word: str) -> DictionaryEntry | None:
        """Retrieve a dictionary entry by word.

        Args:
            word: The word to look up

        Returns:
            DictionaryEntry if found, None otherwise
        """
        if not self._initialized:
            return None

        try:
            return await DictionaryEntry.find_one(DictionaryEntry.word == word)
        except Exception as e:
            logger.error(f"Error retrieving entry for {word}: {e}")
            return None

    async def entry_exists(self, word: str) -> bool:
        """Check if an entry exists for a word.

        Args:
            word: The word to check

        Returns:
            True if entry exists, False otherwise
        """
        if not self._initialized:
            return False

        try:
            count = await DictionaryEntry.find(DictionaryEntry.word == word).count()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence for {word}: {e}")
            return False

    # cache_api_response removed - using modern caching system

    # get_cached_response removed - using modern caching system

    # cleanup_old_cache removed - using modern caching system


# Helper functions for AI module
async def _ensure_initialized() -> None:
    """Ensure MongoDB is initialized."""
    global _storage
    if _storage is None:
        _storage = MongoDBStorage()
        try:
            await _storage.connect()
        except Exception as e:
            logger.warning(f"MongoDB initialization failed: {e}")


async def get_synthesized_entry(word: str) -> SynthesizedDictionaryEntry | None:
    """Get synthesized dictionary entry by word."""
    try:
        await _ensure_initialized()
        return await SynthesizedDictionaryEntry.find_one(
            SynthesizedDictionaryEntry.word == word
        )
    except Exception:
        return None


async def save_synthesized_entry(entry: SynthesizedDictionaryEntry) -> None:
    """Save synthesized dictionary entry."""
    try:
        await _ensure_initialized()
        existing = await SynthesizedDictionaryEntry.find_one(
            SynthesizedDictionaryEntry.word == entry.word
        )

        if existing:
            existing.pronunciation = entry.pronunciation
            existing.definitions = entry.definitions
            existing.last_updated = entry.last_updated
            await existing.save()
        else:
            await entry.create()
    except Exception as e:
        logger.error(f"Error saving synthesized entry: {e}")

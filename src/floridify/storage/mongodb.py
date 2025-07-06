"""MongoDB storage implementation using Beanie."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from ..models.models import APIResponseCache, DictionaryEntry, SynthesizedDictionaryEntry
from ..utils.logging import get_logger
from ..list.models import WordList

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
            document_models=[DictionaryEntry, APIResponseCache, SynthesizedDictionaryEntry, WordList],
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
            existing = await DictionaryEntry.find_one(DictionaryEntry.word == entry.word)

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

    async def cache_api_response(
        self, word: str, provider: str, response_data: dict[str, Any]
    ) -> bool:
        """Cache an API response.

        Args:
            word: The word that was looked up
            provider: The provider name
            response_data: The raw response data

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False

        try:
            # Check if cache entry exists
            existing = await APIResponseCache.find_one(
                APIResponseCache.word == word, APIResponseCache.provider == provider
            )

            if existing:
                # Update existing cache
                existing.response_data = response_data
                existing.timestamp = datetime.now()
                await existing.save()
            else:
                # Create new cache entry
                cache_entry = APIResponseCache(
                    word=word, provider=provider, response_data=response_data
                )
                await cache_entry.create()

            return True

        except Exception as e:
            logger.error(f"Error caching response for {word} from {provider}: {e}")
            return False

    async def get_cached_response(
        self, word: str, provider: str, max_age_hours: int = 24
    ) -> dict[str, Any] | None:
        """Retrieve a cached API response.

        Args:
            word: The word to look up
            provider: The provider name
            max_age_hours: Maximum age of cache entry in hours

        Returns:
            Cached response data if found and fresh, None otherwise
        """
        if not self._initialized:
            return None

        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            cache_entry = await APIResponseCache.find_one(
                APIResponseCache.word == word,
                APIResponseCache.provider == provider,
                APIResponseCache.timestamp >= cutoff_time,
            )

            return cache_entry.response_data if cache_entry else None

        except Exception as e:
            logger.error(f"Error retrieving cached response for {word} from {provider}: {e}")
            return None

    async def cleanup_old_cache(self, max_age_hours: int = 48) -> int:
        """Clean up old cache entries.

        Args:
            max_age_hours: Maximum age to keep cache entries

        Returns:
            Number of deleted entries
        """
        if not self._initialized:
            return 0

        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            result = await APIResponseCache.find(APIResponseCache.timestamp < cutoff_time).delete()

            return result.deleted_count if result else 0

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            return 0


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


async def get_cache_entry(provider: str, cache_key: str) -> dict[str, Any] | None:
    """Get cached AI response by provider and key."""
    try:
        await _ensure_initialized()
        cache_entry = await APIResponseCache.find_one(
            APIResponseCache.provider == provider,
            APIResponseCache.word == cache_key,
        )
        return cache_entry.response_data if cache_entry else None
    except Exception:
        return None


async def save_cache_entry(provider: str, cache_key: str, data: dict[str, Any]) -> None:
    """Save AI response to cache."""
    try:
        await _ensure_initialized()
        existing = await APIResponseCache.find_one(
            APIResponseCache.provider == provider,
            APIResponseCache.word == cache_key,
        )
        
        if existing:
            existing.response_data = data
            existing.timestamp = datetime.now()
            await existing.save()
        else:
            cache_entry = APIResponseCache(
                word=cache_key,
                provider=provider,
                response_data=data,
            )
            await cache_entry.create()
    except Exception as e:
        logger.error(f"Error saving cache entry: {e}")


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

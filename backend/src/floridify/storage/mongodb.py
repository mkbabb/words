"""MongoDB storage implementation using Beanie."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..caching.models import BaseVersionedData
from ..corpus.core import Corpus
from ..models.base import AudioMedia, ImageMedia
from ..models.dictionary import (
    Definition,
    DictionaryEntry,
    Example,
    Fact,
    Pronunciation,
    Word,
)
from ..models.relationships import WordRelationship
from ..providers.batch import BatchOperation
from ..utils.config import Config
from ..utils.logging import get_logger
from ..wordlist.models import WordList

logger = get_logger(__name__)

# Global storage instance for lazy initialization
_storage: MongoDBStorage | None = None


class MongoDBStorage:
    """MongoDB storage for dictionary entries using Beanie ODM."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        database_name: str = "floridify",
        cert_path: Path | None = None,
    ) -> None:
        """Initialize MongoDB storage.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
            cert_path: Path to TLS certificate file

        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.cert_path = cert_path
        self.client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
        self._initialized = False

    async def connect(self) -> None:
        """Connect to MongoDB and initialize Beanie with optimized connection pool."""
        # Detect if connecting to localhost (no TLS needed)
        is_localhost = "localhost:27017" in self.connection_string

        # Build connection kwargs
        connection_kwargs = {
            # Connection Pool Settings
            "maxPoolSize": 50,  # Increase max connections for concurrent load
            "minPoolSize": 10,  # Maintain warm connections
            "maxIdleTimeMS": 30000,  # Close idle connections after 30s
            # Performance Settings
            "serverSelectionTimeoutMS": 3000,  # Fast server selection (3s)
            "socketTimeoutMS": 20000,  # Socket timeout (20s)
            "connectTimeoutMS": 10000,  # Connection timeout (10s)
            # Reliability Settings
            "retryWrites": False,  # Disable retry writes for Docker MongoDB compatibility
            "waitQueueTimeoutMS": 5000,  # Queue timeout for connection pool
        }

        # Only add TLS settings for non-localhost connections
        if not is_localhost and self.cert_path:
            connection_kwargs["tlsCAFile"] = str(self.cert_path)  # type: ignore[assignment]

        # Optimized connection pool configuration for production performance
        self.client = AsyncIOMotorClient(
            self.connection_string,
            **connection_kwargs,
        )
        database: Any = self.client[self.database_name]

        # Initialize Beanie with all document models
        await init_beanie(
            database=database,
            document_models=[
                # New models
                Word,
                Definition,
                Example,
                Fact,
                Pronunciation,
                AudioMedia,
                ImageMedia,
                WordRelationship,
                WordList,
                # Versioning models
                BaseVersionedData,
                DictionaryEntry,
                BatchOperation,
                # Cache models
                # CorpusCacheEntry removed - using unified caching
                Corpus.Metadata,
            ],
        )

        self._initialized = True
        logger.info("MongoDB connection established with optimized pool settings")

    async def ensure_healthy_connection(self) -> bool:
        """Ensure MongoDB connection is healthy and reconnect if needed.

        Returns:
            True if connection is healthy, False otherwise

        """
        if not self.client:
            return False

        try:
            # Ping the database to check connection health
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.warning(f"MongoDB connection unhealthy: {e}")
            try:
                await self.reconnect()
                return True
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to MongoDB: {reconnect_error}")
                return False

    async def reconnect(self) -> None:
        """Reconnect to MongoDB with fresh connection."""
        logger.info("Reconnecting to MongoDB...")
        await self.disconnect()
        await self.connect()

    def get_connection_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics for monitoring.

        Returns:
            Dictionary with connection pool statistics

        """
        if not self.client:
            return {"status": "disconnected"}

        try:
            # Basic stats that should be available
            stats = {
                "status": "connected",
                "initialized": self._initialized,
                "database_name": self.database_name,
            }

            # Try to get pool options if available
            if hasattr(self.client, "options") and hasattr(self.client.options, "pool_options"):
                pool_options = self.client.options.pool_options
                if hasattr(pool_options, "max_pool_size"):
                    stats["max_pool_size"] = pool_options.max_pool_size
                if hasattr(pool_options, "min_pool_size"):
                    stats["min_pool_size"] = pool_options.min_pool_size

            return stats
        except Exception as e:
            logger.debug(f"Could not get full pool stats: {e}")
            return {"status": "connected", "initialized": self._initialized}

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self._initialized = False

    async def save_word(self, word: Word) -> bool:
        """Save a word to MongoDB.

        Args:
            word: Word to save

        Returns:
            True if successful, False otherwise

        """
        if not self._initialized:
            return False

        try:
            # Use Beanie's upsert functionality
            existing = await Word.find_one(Word.text == word.text)

            if existing:
                # Update existing word
                existing.word_forms = word.word_forms
                existing.offensive_flag = word.offensive_flag
                existing.first_known_use = word.first_known_use
                existing.updated_at = datetime.now()
                existing.version += 1
                await existing.save()
            else:
                # Create new word
                await word.create()

            return True

        except Exception as e:
            logger.error(f"Error saving word {word.text}: {e}")
            return False

    async def get_word(self, text: str) -> Word | None:
        """Retrieve a word by text.

        Args:
            text: The word text to look up

        Returns:
            Word if found, None otherwise

        """
        if not self._initialized:
            return None

        try:
            return await Word.find_one(Word.text == text)
        except Exception as e:
            logger.error(f"Error retrieving word {text}: {e}")
            return None

    async def word_exists(self, text: str) -> bool:
        """Check if a word exists.

        Args:
            text: The word text to check

        Returns:
            True if word exists, False otherwise

        """
        if not self._initialized:
            return False

        try:
            count = await Word.find(Word.text == text).count()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence for {text}: {e}")
            return False

    async def get_word_definitions(self, word_id: str) -> list[Definition]:
        """Get all definitions for a word.

        Args:
            word_id: The word ID

        Returns:
            List of definitions

        """
        if not self._initialized:
            return []

        try:
            return await Definition.find(Definition.word_id == word_id).to_list()
        except Exception as e:
            logger.error(f"Error retrieving definitions for word {word_id}: {e}")
            return []


# Helper functions for AI module
async def init_db() -> None:
    """Initialize database connection (alias for _ensure_initialized)."""
    await _ensure_initialized()


async def _ensure_initialized() -> None:
    """Ensure MongoDB is initialized with environment-aware configuration."""
    global _storage
    if _storage is None:
        try:
            # Get database configuration
            config = Config.from_file()
            mongodb_url = config.database.get_url()
            database_name = config.database.name
            cert_path = config.database.cert_path

            logger.info(f"Initializing MongoDB: {database_name} at {mongodb_url[:50]}...")

            _storage = MongoDBStorage(
                connection_string=mongodb_url,
                database_name=database_name,
                cert_path=cert_path,
            )
            await _storage.connect()
            logger.info("MongoDB initialized successfully")
        except Exception as e:
            logger.error(f"MongoDB initialization failed: {type(e).__name__}: {e}")
            logger.error("Stack trace:", exc_info=True)
            _storage = None  # Reset storage on failure
            raise


async def get_storage() -> MongoDBStorage:
    """Get the global MongoDB storage instance."""
    await _ensure_initialized()
    assert _storage is not None, "Storage not initialized"
    return _storage


async def get_database() -> AsyncIOMotorDatabase[Any]:
    """Get the MongoDB database instance."""
    storage = await get_storage()
    if not storage.client:
        raise RuntimeError("MongoDB client not initialized")
    return storage.client[storage.database_name]


async def get_synthesized_entry(word_text: str) -> DictionaryEntry | None:
    """Get synthesized dictionary entry by word text."""
    try:
        await _ensure_initialized()
        # First find the word
        word = await Word.find_one(Word.text == word_text)
        if not word:
            return None
        # Then find the synthesized entry
        return await DictionaryEntry.find_one(
            DictionaryEntry.word_id == word.id,
            DictionaryEntry.provider == "synthesis",
        )
    except Exception:
        return None


async def save_synthesized_entry(entry: DictionaryEntry) -> None:
    """Save synthesized dictionary entry."""
    try:
        await _ensure_initialized()
        existing = await DictionaryEntry.find_one(
            DictionaryEntry.word_id == entry.word_id,
            DictionaryEntry.provider == "synthesis",
        )

        if existing:
            # Update existing entry
            existing.pronunciation_id = entry.pronunciation_id
            existing.definition_ids = entry.definition_ids
            existing.etymology = entry.etymology
            existing.fact_ids = entry.fact_ids
            existing.model_info = entry.model_info
            existing.updated_at = datetime.now()
            existing.version += 1
            await existing.save()
        else:
            await entry.create()
    except Exception as e:
        logger.error(f"Error saving synthesized entry: {e}")

"""MongoDB storage implementation using Beanie."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from ..list.models import WordList
from ..models.models import DictionaryEntry, SynthesizedDictionaryEntry
from ..utils.config import get_database_config
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
        """Connect to MongoDB and initialize Beanie with optimized connection pool."""
        # Optimized connection pool configuration for production performance
        self.client = AsyncIOMotorClient(
            self.connection_string,
            # Connection Pool Settings
            maxPoolSize=50,          # Increase max connections for concurrent load
            minPoolSize=10,          # Maintain warm connections
            maxIdleTimeMS=30000,     # Close idle connections after 30s
            
            # Performance Settings
            serverSelectionTimeoutMS=3000,  # Fast server selection (3s)
            socketTimeoutMS=20000,   # Socket timeout (20s)
            connectTimeoutMS=10000,  # Connection timeout (10s)
            
            # Reliability Settings
            retryWrites=True,        # Enable retry writes for transient failures
            waitQueueTimeoutMS=5000, # Queue timeout for connection pool
        )
        database: Any = self.client[self.database_name]

        # Initialize Beanie with our document models
        await init_beanie(
            database=database,
            document_models=[DictionaryEntry, SynthesizedDictionaryEntry, WordList],
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
            await self.client.admin.command('ping')
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
            pool_options = self.client.options.pool_options
            return {
                "status": "connected",
                "max_pool_size": pool_options.max_pool_size,
                "min_pool_size": pool_options.min_pool_size,
                "max_idle_time_ms": pool_options.max_idle_time_ms,
                "server_selection_timeout_ms": pool_options.server_selection_timeout_ms,
                "socket_timeout_ms": pool_options.socket_timeout_ms,
                "connect_timeout_ms": pool_options.connect_timeout_ms,
                "initialized": self._initialized,
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"status": "error", "error": str(e)}

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




# Helper functions for AI module
async def _ensure_initialized() -> None:
    """Ensure MongoDB is initialized with environment-aware configuration."""
    global _storage
    if _storage is None:
        # Get database configuration from environment + config file
        mongodb_url, database_name = get_database_config()
        logger.info(f"Initializing MongoDB: {database_name} at {mongodb_url[:20]}...")
        
        _storage = MongoDBStorage(
            connection_string=mongodb_url,
            database_name=database_name
        )
        try:
            await _storage.connect()
            logger.info("MongoDB initialized successfully")
        except Exception as e:
            logger.error(f"MongoDB initialization failed: {e}")
            raise


async def get_storage() -> MongoDBStorage:
    """Get the global MongoDB storage instance."""
    await _ensure_initialized()
    return _storage


async def get_synthesized_entry(word: str) -> SynthesizedDictionaryEntry | None:
    """Get synthesized dictionary entry by word."""
    try:
        await _ensure_initialized()
        return await SynthesizedDictionaryEntry.find_one(SynthesizedDictionaryEntry.word == word)
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

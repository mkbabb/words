"""MongoDB storage implementation using Beanie."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..caching.models import BaseVersionedData

from ..corpus.core import Corpus
from ..corpus.language.core import LanguageCorpus
from ..corpus.literature.core import LiteratureCorpus
from ..models.base import AudioMedia, ImageMedia
from ..models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Example,
    Fact,
    Pronunciation,
    Word,
)
from ..models.relationships import WordRelationship
from ..models.user import User, UserHistory
from ..providers.batch import BatchOperation
from ..providers.dictionary.models import DictionaryProviderEntry
from ..providers.language.models import LanguageEntry
from ..providers.literature.models import LiteratureEntry
from ..search.search_index import SearchIndex
from ..search.semantic.models import SemanticIndex
from ..search.trie_index import TrieIndex
from ..utils.config import Config
from ..utils.logging import get_logger
from ..wordlist.models import WordList, WordListItemDoc
from .dictionary import _resolve_word_text, save_entry_versioned

logger = get_logger(__name__)

# Global storage instance for lazy initialization
_storage: MongoDBStorage | None = None


class MongoDBStorage:
    """MongoDB storage for dictionary entries using Beanie ODM."""

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        cert_path: Path | None = None,
        tls_required: bool | None = None,
    ) -> None:
        """Initialize MongoDB storage.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
            cert_path: Path to TLS certificate file
            tls_required: Explicit TLS policy for this target (None = URI-driven)

        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.cert_path = cert_path
        self.tls_required = tls_required
        self.client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
        self._initialized = False

    @staticmethod
    def _parse_tls_from_uri(connection_string: str) -> bool | None:
        """Parse TLS/SSL option from Mongo URI query params."""
        parsed = urlparse(connection_string)
        query_params = {key.lower(): value for key, value in parse_qs(parsed.query).items()}

        def _parse_bool(value: str) -> bool | None:
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes"}:
                return True
            if normalized in {"0", "false", "no"}:
                return False
            return None

        for key in ("tls", "ssl"):
            raw_values = query_params.get(key)
            if not raw_values:
                continue
            parsed_value = _parse_bool(raw_values[-1])
            if parsed_value is not None:
                return parsed_value
        return None

    async def connect(self) -> None:
        """Connect to MongoDB and initialize Beanie with optimized connection pool."""
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
            "retryWrites": True,  # Hosted MongoDB supports retryable writes
            "waitQueueTimeoutMS": 5000,  # Queue timeout for connection pool
        }

        uri_tls = self._parse_tls_from_uri(self.connection_string)
        if self.tls_required is not None and uri_tls is not None and uri_tls != self.tls_required:
            raise ValueError(
                "MongoDB TLS mismatch: configured tls_required="
                f"{self.tls_required} but URI sets tls={uri_tls}"
            )

        effective_tls = self.tls_required if self.tls_required is not None else uri_tls
        if effective_tls is True:
            connection_kwargs["tls"] = True  # type: ignore[assignment]
            if self.cert_path:
                connection_kwargs["tlsCAFile"] = str(self.cert_path)  # type: ignore[assignment]
        elif effective_tls is False:
            connection_kwargs["tls"] = False  # type: ignore[assignment]

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
                WordListItemDoc,
                # Versioning models - Base class provides collection, subclasses inherit
                BaseVersionedData,
                # CRITICAL: All Metadata subclasses must be registered for polymorphic deserialization
                # BaseVersionedData owns the "versioned_data" collection with is_root=True
                # All subclasses share this collection and need proper _class_id handling
                Corpus.Metadata,
                LanguageCorpus.Metadata,  # DISCRIMINATOR FIX: Register LanguageCorpus.Metadata
                LiteratureCorpus.Metadata,  # DISCRIMINATOR FIX: Register LiteratureCorpus.Metadata
                DictionaryProviderEntry.Metadata,
                LanguageEntry.Metadata,
                LiteratureEntry.Metadata,
                SearchIndex.Metadata,
                TrieIndex.Metadata,
                SemanticIndex.Metadata,
                # User models
                User,
                UserHistory,
                # Backward-compatible query models
                DictionaryEntry,
                BatchOperation,
            ],
        )

        self._initialized = True
        logger.info("MongoDB connection established with optimized pool settings")

    async def ensure_healthy_connection(self, max_retries: int = 3) -> bool:
        """Ensure MongoDB connection is healthy and reconnect if needed.

        Args:
            max_retries: Maximum number of reconnection attempts before giving up.

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
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Reconnect attempt {attempt}/{max_retries}...")
                    await self.reconnect()
                    return True
                except Exception as reconnect_error:
                    logger.error(
                        f"Reconnect attempt {attempt}/{max_retries} failed: {reconnect_error}"
                    )
            logger.error(f"All {max_retries} reconnect attempts failed")
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

        return {
            "status": "connected",
            "initialized": self._initialized,
            "database_name": self.database_name,
        }

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


async def _ensure_initialized() -> None:
    """Ensure MongoDB is initialized with environment-aware configuration."""
    global _storage
    if _storage is None:
        try:
            # Get database configuration
            config = Config.from_file()
            db_target = os.getenv("FLORIDIFY_DB_TARGET", "runtime")
            mongodb_url = config.database.get_url(db_target)
            database_name = config.database.name
            cert_path = config.database.cert_path
            tls_required = config.database.runtime_tls_required if db_target == "runtime" else None

            logger.info(f"Initializing MongoDB: {database_name} at {mongodb_url[:50]}...")

            _storage = MongoDBStorage(
                connection_string=mongodb_url,
                database_name=database_name,
                cert_path=cert_path,
                tls_required=tls_required,
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
    """Get synthesized dictionary entry by word text.

    Returns:
        DictionaryEntry if found, None if word doesn't exist or no synthesis exists

    Raises:
        Exception: Database errors propagate to caller for proper error handling
    """
    await _ensure_initialized()

    # First find the word
    word = await Word.find_one(Word.text == word_text)
    if not word:
        return None

    return await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )


async def get_best_existing_entry(
    word_text: str,
) -> tuple[DictionaryEntry | None, bool]:
    """Find the best existing DictionaryEntry for a word, regardless of provider.

    Sorts by definition count descending — synthesis entries (highest quality)
    naturally float to the top, followed by wiktionary, then apple_dict.

    Returns:
        (entry, is_synthesis) — the best entry and whether it's a SYNTHESIS entry.
        (None, False) if no entry with definitions exists.
    """
    await _ensure_initialized()

    word = await Word.find_one(Word.text == word_text)
    if not word:
        return None, False

    # Find all entries with definitions for this word (typically 1-3 entries)
    entries = await DictionaryEntry.find(
        DictionaryEntry.word_id == word.id,
        {"definition_ids": {"$exists": True, "$ne": []}},
    ).to_list()

    if not entries:
        return None, False

    # Pick the entry with the most definitions (synthesis > wiktionary > apple_dict)
    best = max(entries, key=lambda e: len(e.definition_ids) if e.definition_ids else 0)
    is_synthesis = best.provider == DictionaryProvider.SYNTHESIS
    return best, is_synthesis


async def save_synthesized_entry(entry: DictionaryEntry) -> None:
    """Save synthesized dictionary entry with version history."""
    try:
        await _ensure_initialized()
        word_text = await _resolve_word_text(entry.word_id)
        await save_entry_versioned(entry, word_text)
    except Exception as e:
        logger.error(f"Error saving synthesized entry: {e}")

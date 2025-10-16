"""Repository for managing versioned provider data.

Provides high-level interface for querying and managing
versioned dictionary provider data with support for
historical queries and version management.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel

from ...models.dictionary import DictionaryEntry, DictionaryProvider, Language
from ...providers.batch import BatchOperation, BatchStatus
from ...providers.config import ProviderConfiguration
from ...utils.logging import get_logger
from ..core.base import BaseRepository
from datetime import timedelta

logger = get_logger(__name__)


# Schema classes for provider data CRUD
class ProviderDataCreate(BaseModel):
    """Schema for creating provider data."""

    word_id: PydanticObjectId
    provider: DictionaryProvider
    provider_data: dict[str, Any]
    language: Language


class ProviderDataUpdate(BaseModel):
    """Schema for updating provider data."""

    provider_data: dict[str, Any] | None = None
    is_latest: bool | None = None


class ProviderDataRepository(
    BaseRepository[DictionaryEntry, ProviderDataCreate, ProviderDataUpdate],
):
    """Repository for versioned provider data operations."""

    model = DictionaryEntry

    async def get_latest(
        self,
        word_id: PydanticObjectId,
        provider: DictionaryProvider,
    ) -> DictionaryEntry | None:
        """Get latest version of provider data for a word.

        Args:
            word_id: Word ID
            provider: Dictionary provider

        Returns:
            Latest DictionaryEntry or None

        """
        return await self.model.find_one(
            {
                "word_id": word_id,
                "provider": provider,
                "version_info.is_latest": True,
            },
        )

    async def get_by_version(
        self,
        word_id: PydanticObjectId,
        provider: DictionaryProvider,
        version: str,
    ) -> DictionaryEntry | None:
        """Get specific version of provider data.

        Args:
            word_id: Word ID
            provider: Dictionary provider
            version: Provider version string

        Returns:
            DictionaryEntry for specific version or None

        """
        return await self.model.find_one(
            {
                "word_id": word_id,
                "provider": provider,
                "version_info.provider_version": version,
            },
        )

    async def get_history(
        self,
        word_id: PydanticObjectId,
        provider: DictionaryProvider | None = None,
        limit: int = 10,
    ) -> list[DictionaryEntry]:
        """Get version history for a word.

        Args:
            word_id: Word ID
            provider: Optional provider filter
            limit: Maximum versions to return

        Returns:
            List of versions, newest first

        """
        query = {"word_id": word_id}
        if provider:
            query["provider"] = provider

        return await self.model.find(query).sort("-created_at").limit(limit).to_list()

    async def get_by_date(
        self,
        word_id: PydanticObjectId,
        provider: DictionaryProvider,
        date: datetime,
    ) -> DictionaryEntry | None:
        """Get provider data as of a specific date.

        Args:
            word_id: Word ID
            provider: Dictionary provider
            date: Point in time to query

        Returns:
            DictionaryEntry active at that date

        """
        result = (
            await self.model.find(
                {
                    "word_id": word_id,
                    "provider": provider,
                    "created_at": {"$lte": date},
                },
            )
            .sort("-created_at")
            .limit(1)
            .to_list()
        )
        return result[0] if result else None

    async def get_words_with_provider(
        self,
        provider: DictionaryProvider,
        language: Language = Language.ENGLISH,
        limit: int = 100,
    ) -> list[str]:
        """Get list of words that have data from a provider.

        Args:
            provider: Dictionary provider
            language: Language filter
            limit: Maximum words to return

        Returns:
            List of word texts

        """
        pipeline = [
            {
                "$match": {
                    "provider": provider,
                    "language": language,
                    "version_info.is_latest": True,
                },
            },
            {"$group": {"_id": "$word_text"}},
            {"$limit": limit},
        ]

        results = await self.model.aggregate(pipeline).to_list()
        return [r["_id"] for r in results]

    async def mark_as_latest(
        self,
        data_id: PydanticObjectId,
    ) -> bool:
        """Mark a version as the latest for its word/provider combo.

        Args:
            data_id: ID of DictionaryEntry to mark as latest

        Returns:
            True if successful

        """
        data = await self.get(data_id)
        if not data:
            return False

        # Unmark current latest
        await self.model.find(
            {
                "word_id": data.word_id,
                "provider": data.provider,
                "version_info.is_latest": True,
                "_id": {"$ne": data_id},
            },
        ).update_many({"$set": {"version_info.is_latest": False}})

        # Mark this as latest
        data.version_info.is_latest = True
        await data.save()

        return True

    async def cleanup_old_versions(
        self,
        provider: DictionaryProvider,
        keep_versions: int = 3,
        older_than_days: int = 30,
    ) -> int:
        """Clean up old versions, keeping recent ones.

        Args:
            provider: Provider to clean up
            keep_versions: Number of versions to keep per word
            older_than_days: Only delete versions older than this

        Returns:
            Number of documents deleted

        """
        cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

        # Get all words with this provider
        pipeline = [
            {"$match": {"provider": provider}},
            {"$group": {"_id": "$word_id"}},
        ]

        word_ids = await self.model.aggregate(pipeline).to_list()
        total_deleted = 0

        for word_doc in word_ids:
            word_id = word_doc["_id"]

            # Get all versions for this word, sorted by date
            versions = (
                await self.model.find(
                    {"word_id": word_id, "provider": provider},
                )
                .sort("-created_at")
                .to_list()
            )

            # Keep the latest N versions and any recent ones
            to_delete = []
            for idx, version in enumerate(versions):
                if idx >= keep_versions and version.created_at < cutoff_date:
                    to_delete.append(version.id)

            # Delete old versions
            if to_delete:
                result = await self.model.find(
                    {"_id": {"$in": to_delete}},
                ).delete()
                total_deleted += result.deleted_count

        logger.info(f"Cleaned up {total_deleted} old versions for {provider.value}")
        return total_deleted


# Schema classes for batch operations
class BatchOperationCreate(BaseModel):
    """Schema for creating batch operation."""

    provider: DictionaryProvider
    status: BatchStatus
    word_ids: list[PydanticObjectId]


class BatchOperationUpdate(BaseModel):
    """Schema for updating batch operation."""

    status: BatchStatus | None = None
    completed_count: int | None = None
    failed_count: int | None = None
    completed_at: datetime | None = None


class BatchOperationRepository(
    BaseRepository[BatchOperation, BatchOperationCreate, BatchOperationUpdate],
):
    """Repository for batch operation management."""

    model = BatchOperation

    async def get_active_operations(
        self,
        provider: DictionaryProvider | None = None,
    ) -> list[BatchOperation]:
        """Get all active (in-progress) operations.

        Args:
            provider: Optional provider filter

        Returns:
            List of active operations

        """
        query: dict[str, Any] = {"status": BatchStatus.IN_PROGRESS}
        if provider:
            query["provider"] = provider

        return await self.model.find(query).to_list()

    async def get_resumable_operations(
        self,
        provider: DictionaryProvider | None = None,
    ) -> list[BatchOperation]:
        """Get operations that can be resumed.

        Args:
            provider: Optional provider filter

        Returns:
            List of resumable operations

        """
        query: dict[str, Any] = {
            "status": {"$in": [BatchStatus.IN_PROGRESS, BatchStatus.PARTIAL]},
        }
        if provider:
            query["provider"] = provider

        return await self.model.find(query).to_list()

    async def get_operation_stats(
        self,
        operation_id: str,
    ) -> dict[str, Any]:
        """Get statistics for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Statistics dictionary

        """
        operation = await self.model.find_one({"operation_id": operation_id})
        if not operation:
            return {}

        stats = {
            "status": operation.status.value,
            "total_items": operation.total_items,
            "processed_items": operation.processed_items,
            "failed_items": operation.failed_items,
            "success_rate": (
                (operation.processed_items - operation.failed_items)
                / operation.processed_items
                * 100
                if operation.processed_items > 0
                else 0
            ),
            "duration_seconds": operation.statistics.get("duration_seconds"),
            "errors_sample": operation.errors[:10],  # First 10 errors
        }

        # Add operation-specific stats
        stats.update(operation.statistics)

        return stats

    async def cleanup_old_operations(
        self,
        older_than_days: int = 90,
        keep_failed: bool = True,
    ) -> int:
        """Clean up old completed operations.

        Args:
            older_than_days: Delete operations older than this
            keep_failed: Whether to keep failed operations

        Returns:
            Number of operations deleted

        """

        cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

        query: dict[str, Any] = {
            "created_at": {"$lt": cutoff_date},
            "status": BatchStatus.COMPLETED,
        }

        if not keep_failed:
            query["status"] = {"$in": [BatchStatus.COMPLETED, BatchStatus.FAILED]}

        result = await self.model.find(query).delete()

        logger.info(f"Cleaned up {result.deleted_count} old batch operations")
        return result.deleted_count


# Schema classes for provider configuration
class ProviderConfigCreate(BaseModel):
    """Schema for creating provider configuration."""

    provider: DictionaryProvider
    enabled: bool = True
    api_key: str | None = None
    rate_limit: float = 1.0


class ProviderConfigUpdate(BaseModel):
    """Schema for updating provider configuration."""

    enabled: bool | None = None
    api_key: str | None = None
    rate_limit: float | None = None


class ProviderConfigurationRepository(
    BaseRepository[ProviderConfiguration, ProviderConfigCreate, ProviderConfigUpdate],
):
    """Repository for provider configuration management."""

    model = ProviderConfiguration

    async def get_active_providers(
        self,
    ) -> list[ProviderConfiguration]:
        """Get all active provider configurations.

        Returns:
            List of active provider configurations

        """
        return await self.model.find({"active": True}).to_list()

    async def get_provider_config(
        self,
        provider: DictionaryProvider,
    ) -> ProviderConfiguration | None:
        """Get configuration for a specific provider.

        Args:
            provider: Dictionary provider

        Returns:
            Provider configuration or None

        """
        return await self.model.find_one({"provider": provider})

    async def update_rate_limit(
        self,
        provider: DictionaryProvider,
        requests: int,
        period: str,
    ) -> bool:
        """Update rate limit for a provider.

        Args:
            provider: Dictionary provider
            requests: Number of requests allowed
            period: Time period (second, minute, hour)

        Returns:
            True if updated successfully

        """
        config = await self.get_provider_config(provider)
        if not config:
            return False

        config.rate_limit_requests = requests
        config.rate_limit_period = period
        await config.save()

        return True

    async def mark_bulk_download(
        self,
        provider: DictionaryProvider,
    ) -> bool:
        """Mark that a bulk download was performed.

        Args:
            provider: Dictionary provider

        Returns:
            True if updated successfully

        """
        config = await self.get_provider_config(provider)
        if not config:
            return False

        config.last_bulk_download = datetime.now(UTC)
        await config.save()

        return True

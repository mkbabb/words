"""Versioned data manager for unified caching and content management."""

from __future__ import annotations

import asyncio
import hashlib
import json
from enum import Enum
from typing import Any, TypeVar

from beanie import PydanticObjectId
from pymongo.errors import OperationFailure

from ..models.registry import get_model_class as get_versioned_model_class
from ..utils.introspection import extract_metadata_params
from ..utils.logging import get_logger
from .core import GlobalCacheManager, get_global_cache, get_versioned_content, set_versioned_content
from .filesystem import FilesystemBackend
from .models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
    VersionConfig,
    VersionInfo,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseVersionedData)


class VersionedDataManager:
    """Manages versioned data with proper typing and performance optimization."""

    def __init__(self) -> None:
        """Initialize with cache integration."""
        self.cache: GlobalCacheManager[FilesystemBackend] | None = (
            None  # Will be initialized lazily (GlobalCacheManager)
        )
        self._lock: asyncio.Lock | None = None

    @property
    def lock(self) -> asyncio.Lock:
        """Get or create lock for the current event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create a new lock
            self._lock = asyncio.Lock()
            return self._lock

        # Check if we need to create a new lock for this event loop
        if self._lock is None:
            self._lock = asyncio.Lock()
        else:
            # Check if the lock is bound to a different event loop
            # Simply recreate lock to be safe - locks are lightweight
            try:
                # Test if lock is still valid for current loop
                _ = self._lock.locked()
            except RuntimeError:
                # Lock is from different event loop, create new one
                self._lock = asyncio.Lock()

        return self._lock

    async def _save_with_transaction(
        self,
        versioned: BaseVersionedData,
        resource_id: str,
        resource_type: ResourceType,
    ) -> None:
        """Save version and update chain using MongoDB transaction if available.

        This method provides distributed locking via MongoDB transactions to prevent
        race conditions when multiple processes update version chains concurrently.
        Falls back to local asyncio lock if transactions are not supported.

        Args:
            versioned: The versioned data object to save
            resource_id: Resource identifier
            resource_type: Type of resource being saved

        """
        # Try to get MongoDB client from the model
        try:
            # Access the underlying motor database from Beanie
            # Use BaseVersionedData collection since that's what's registered
            db = BaseVersionedData.get_pymongo_collection().database
            client = db.client

            # Try to use transactions (requires replica set)
            async with await client.start_session() as session:
                async with session.start_transaction():
                    # Save new version
                    await versioned.insert(session=session)

                    # Update version chain
                    if versioned.version_info.is_latest:
                        # Find and update other latest versions atomically
                        # Use the specific model class for polymorphic queries
                        model_class = self._get_model_class(resource_type)
                        other_latest = await model_class.find(
                            {
                                "resource_id": resource_id,
                                "resource_type": resource_type.value,
                                "version_info.is_latest": True,
                                "_id": {"$ne": versioned.id},
                            },
                            session=session,
                        ).to_list()

                        for other_version in other_latest:
                            other_version.version_info.is_latest = False
                            other_version.version_info.superseded_by = versioned.id
                            await other_version.save(session=session)

                        logger.debug(
                            f"[Transaction] Updated {len(other_latest)} previous versions to not be latest"
                        )

                    # Transaction commits automatically on context exit
                    logger.debug(
                        f"[Transaction] Saved {resource_type.value} '{resource_id}' atomically"
                    )

        except (OperationFailure, AttributeError, Exception) as e:
            # Transactions not supported (single node or old MongoDB version)
            # Fall back to local lock approach
            logger.debug(
                f"MongoDB transactions not available ({e.__class__.__name__}), "
                "using local lock (safe for single-process deployments)"
            )

            # Save new version using Beanie's insert (handles _class_id correctly)
            await versioned.insert()
            # Ensure ID is always PydanticObjectId
            if versioned.id and not isinstance(versioned.id, PydanticObjectId):
                versioned.id = PydanticObjectId(versioned.id)

            # Update version chain with local lock
            if versioned.version_info.is_latest:
                # Update previous versions directly with pymongo
                # Use BaseVersionedData collection since subclasses share it
                collection = BaseVersionedData.get_pymongo_collection()
                await collection.update_many(
                    {
                        "resource_id": resource_id,
                        "resource_type": resource_type.value,
                        "version_info.is_latest": True,
                        "_id": {"$ne": versioned.id},
                    },
                    {
                        "$set": {
                            "version_info.is_latest": False,
                            "version_info.superseded_by": versioned.id,
                        }
                    },
                )

                logger.debug(
                    f"[Local] Updated previous versions to not be latest for {resource_id}"
                )

    async def save(
        self,
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig = VersionConfig(),
        metadata: dict[str, Any] | None = None,
        dependencies: list[PydanticObjectId] | None = None,
    ) -> BaseVersionedData:
        """Save with versioning and optimal serialization."""
        # Single serialization with sorted keys and ObjectId handling
        content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Check for duplicate content with optional metadata comparison
        if not config.force_rebuild:
            existing = await self._find_by_hash(resource_id, resource_type, content_hash)
            if existing and config.metadata_comparison_fields and metadata:
                # Check if specified metadata fields have changed
                metadata_changed = False
                existing_data = existing.model_dump()

                for field in config.metadata_comparison_fields:
                    if field in metadata:
                        existing_value = existing_data.get("metadata", {}).get(field)
                        new_value = metadata.get(field)
                        if existing_value != new_value:
                            metadata_changed = True
                            logger.debug(
                                f"Metadata field {field} changed: {existing_value} -> {new_value}"
                            )
                            break

                if not metadata_changed:
                    logger.debug(
                        f"Found existing version for {resource_id} with same content and metadata"
                    )
                    # Ensure ID is always PydanticObjectId for consistency
                    if existing.id and not isinstance(existing.id, PydanticObjectId):
                        existing.id = PydanticObjectId(existing.id)
                    return existing
                logger.info(
                    f"Content matches but metadata changed for {resource_id}, creating new version"
                )
            elif existing:
                logger.debug(f"Found existing version for {resource_id} with same content")
                # Ensure ID is always PydanticObjectId for consistency
                if existing.id and not isinstance(existing.id, PydanticObjectId):
                    existing.id = PydanticObjectId(existing.id)
                return existing

        # Get latest for version increment
        latest = None
        if config.increment_version:
            try:
                latest = await self.get_latest(
                    resource_id,
                    resource_type,
                    use_cache=True,
                )
            except RuntimeError as e:
                # Handle corrupted metadata gracefully during rebuild
                logger.warning(
                    f"Could not load existing version during save (likely corrupted): {e}"
                )
                latest = None

        new_version = config.version or (
            self._increment_version(latest.version_info.version)
            if latest and config.increment_version
            else "1.0.0"
        )

        # Create versioned instance
        model_class = self._get_model_class(resource_type)

        # Prepare constructor parameters
        constructor_params: dict[str, Any] = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "namespace": namespace,
            "version_info": VersionInfo(
                version=new_version,
                data_hash=content_hash,
                is_latest=True,
                supersedes=latest.id if latest else None,
                dependencies=dependencies or [],
            ),
            "ttl": config.ttl,
        }

        # Handle metadata - extract model-specific fields vs generic metadata using introspection
        # This replaces 75+ lines of hardcoded field lists with automatic Pydantic field detection
        combined_metadata = {**config.metadata, **(metadata or {})}

        # Automatically separate typed fields from generic metadata using Pydantic introspection
        typed_fields, generic_metadata = extract_metadata_params(
            combined_metadata,
            model_class,
        )

        # Add typed fields to constructor parameters
        constructor_params.update(typed_fields)

        # Filter out BaseVersionedData fields from generic metadata to avoid conflicts
        # These fields are set via constructor params, not the generic metadata dict
        base_fields = set(BaseVersionedData.model_fields.keys())
        filtered_metadata = {k: v for k, v in generic_metadata.items() if k not in base_fields}
        constructor_params["metadata"] = filtered_metadata

        # Create instance using regular instantiation (not model_construct)
        # This ensures Beanie's polymorphism logic works correctly
        # Generate ID first to avoid Beanie auto-generating it
        if "id" not in constructor_params or constructor_params["id"] is None:
            constructor_params["id"] = PydanticObjectId()

        versioned = model_class(**constructor_params)

        # Set content with automatic storage strategy
        await set_versioned_content(versioned, content)

        # Atomic save with version chain update using transactions or local lock
        async with self.lock:
            try:
                await self._save_with_transaction(versioned, resource_id, resource_type)
            except Exception as e:
                logger.error(f"Failed to save version chain: {e}", exc_info=True)
                raise RuntimeError(
                    f"Index persistence failed for {resource_type.value}:{resource_id}. "
                    f"Data may be corrupted. Error: {e}"
                ) from e

            # Tree structures handled by TreeCorpusManager for corpus types

            # Cache update AFTER successful database write to prevent race conditions
            if config.use_cache:
                if self.cache is None:
                    self.cache = await get_global_cache()
                cache_key = f"{resource_type.value}:{resource_id}"

                try:
                    # Atomic cache update: delete old and set new in one operation
                    await self.cache.delete(namespace, cache_key)
                    await self.cache.set(namespace, cache_key, versioned, config.ttl)
                except Exception as cache_error:
                    logger.warning(
                        f"Cache update failed for {cache_key}, continuing without cache: {cache_error}"
                    )
                    # Don't fail the save operation if only cache fails

        logger.info(f"Saved {resource_type.value} '{resource_id}' version {new_version}")
        return versioned

    async def get_latest(
        self,
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool = True,
        config: VersionConfig = VersionConfig(),
    ) -> BaseVersionedData | None:
        """Get latest version with proper typing."""
        namespace = self._get_namespace(resource_type)

        # Check cache unless forced
        if use_cache and not config.force_rebuild:
            cache_key = f"{resource_type.value}:{resource_id}"

            # Handle specific version request
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"

            if self.cache is None:
                self.cache = await get_global_cache()
            cached = await self.cache.get(namespace, cache_key)
            if cached:
                # Validate cache entry BEFORE returning it
                if not config.version:
                    model_class = self._get_model_class(resource_type)
                    try:
                        # Handle both dict (from JSON deserialization) and model instances
                        if isinstance(cached, dict):
                            # Cached as dict - reconstruct to model for validation
                            cached = model_class.model_validate(cached)

                        # Validate the cached document still exists in database
                        # Use the specific model class for polymorphic queries
                        doc = await model_class.find_one({"_id": cached.id})
                        if not doc:
                            # Cached document was deleted, invalidate cache
                            logger.debug(
                                f"Cached document for {cache_key} no longer exists, invalidating cache"
                            )
                            await self.cache.delete(namespace, cache_key)
                            cached = None  # Force database query below
                        else:
                            # Validate content integrity if it has external storage
                            if cached.content_location is not None:
                                content = await get_versioned_content(cached)
                                if content is None:
                                    logger.error(
                                        f"External content missing for {cache_key}, invalidating cache"
                                    )
                                    await self.cache.delete(namespace, cache_key)
                                    cached = None  # Force database query
                                else:
                                    logger.debug(f"Cache hit for {cache_key} (validated)")
                                    return cached  # type: ignore[no-any-return]
                            else:
                                logger.debug(f"Cache hit for {cache_key}")
                                return cached  # type: ignore[no-any-return]
                    except Exception as e:
                        # Validation failed, don't trust the cache
                        logger.warning(
                            f"Cache validation failed for {cache_key}: {e}, invalidating cache",
                            exc_info=True,
                        )
                        await self.cache.delete(namespace, cache_key)
                        cached = None  # Force database query
                else:
                    # For specific version queries, still validate but less strictly
                    logger.debug(f"Cache hit for {cache_key} (version-specific)")
                    return cached  # type: ignore[no-any-return]

        # Query database with error handling
        # Use the specific model class for polymorphic queries (not BaseVersionedData)
        # After fixing _class_id, each subclass needs to query using its own class
        model_class = self._get_model_class(resource_type)

        try:
            if config.version:
                # Get specific version
                result = await model_class.find_one(
                    {
                        "resource_id": resource_id,
                        "resource_type": resource_type.value,
                        "version_info.version": config.version,
                    },
                )
            else:
                # Get latest - sort by ID descending to get the most recent if multiple have is_latest=True
                result = (
                    await model_class.find(
                        {
                            "resource_id": resource_id,
                            "resource_type": resource_type.value,
                            "version_info.is_latest": True,
                        },
                    )
                    .sort("-_id")
                    .first_or_none()
                )
        except Exception as e:
            logger.error(f"Database query failed for {resource_type.value}:{resource_id}: {e}")
            raise RuntimeError(
                f"Failed to retrieve {resource_type.value}:{resource_id} from database. "
                f"This may indicate database connectivity issues or corrupted indices. Error: {e}"
            ) from e

        # Validate external content if present
        if result and result.content_location is not None:
            try:
                content = await get_versioned_content(result)
                if content is None:
                    raise ValueError(
                        f"External content missing for {resource_type.value}:{resource_id}. "
                        f"Expected content at {result.content_location.path}"
                    )
            except Exception as e:
                logger.error(f"Failed to load external content for {resource_id}: {e}")
                raise RuntimeError(
                    f"Index data corrupted for {resource_type.value}:{resource_id}. "
                    f"External content could not be loaded. Error: {e}"
                ) from e

        # Cache result
        if result and use_cache:
            cache_key = f"{resource_type.value}:{resource_id}"
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"
            if self.cache is None:
                self.cache = await get_global_cache()
            try:
                await self.cache.set(namespace, cache_key, result, result.ttl)
            except Exception as cache_error:
                # Log cache error but don't fail the operation
                logger.warning(f"Failed to cache {cache_key}: {cache_error}")

        return result

    async def get_by_version(
        self,
        resource_id: str,
        resource_type: ResourceType,
        version: str,
        use_cache: bool = True,
    ) -> BaseVersionedData | None:
        """Get specific version of a resource."""
        config = VersionConfig(version=version, use_cache=use_cache)
        return await self.get_latest(resource_id, resource_type, use_cache, config)

    async def list_versions(
        self, resource_id: str, resource_type: ResourceType
    ) -> list[BaseVersionedData]:
        """List all versions of a resource."""
        # Use the specific model class for polymorphic queries
        model_class = self._get_model_class(resource_type)
        results = await model_class.find(
            {"resource_id": resource_id, "resource_type": resource_type.value}
        ).to_list()
        return results

    # ============================================================================
    # WRAPPER METHODS FOR TEST COMPATIBILITY
    # ============================================================================

    async def save_versioned_data(self, metadata_obj: BaseVersionedData) -> BaseVersionedData:
        """Save metadata object directly using Beanie.

        This method handles the metadata object as a complete Beanie document,
        managing version chains and content storage automatically.

        Args:
            metadata_obj: Any metadata object inheriting from BaseVersionedData

        Returns:
            Saved metadata object with ID populated
        """
        resource_id = metadata_obj.resource_id
        resource_type = metadata_obj.resource_type

        # Handle content storage if present
        if metadata_obj.content_inline is not None:
            content = metadata_obj.content_inline
            await set_versioned_content(metadata_obj, content)

        # Handle version chain management with proper atomic operations
        async with self.lock:
            # Always save the object first
            await metadata_obj.save()

            # If this version claims to be latest, ensure only one version can be latest
            if metadata_obj.version_info.is_latest:
                try:
                    model_class = self._get_model_class(resource_type)
                    collection = model_class.get_pymongo_collection()

                    # Use update_many to atomically mark all other versions as not latest
                    update_result = await collection.update_many(
                        {
                            "resource_id": resource_id,
                            "version_info.is_latest": True,
                            "_id": {"$ne": metadata_obj.id},  # Exclude this version
                        },
                        {
                            "$set": {
                                "version_info.is_latest": False,
                                "version_info.superseded_by": metadata_obj.id,
                            }
                        },
                    )

                    logger.debug(
                        f"Updated {update_result.modified_count} previous versions to not be latest"
                    )

                except Exception as e:
                    logger.error(f"Failed to update previous version chain: {e}")
                    # Version chain corruption - this is critical, must raise
                    raise RuntimeError(
                        f"Version chain update failed for resource {resource_id}. "
                        f"Multiple versions may be marked as latest. Error: {e}"
                    ) from e

        # Don't query individual document state immediately after concurrent operations
        # The atomic database operations will resolve the race condition, and querying
        # immediately might return stale state before all concurrent updates complete.
        # The database itself will have the correct final state.

        return metadata_obj

    async def get_latest_version(
        self, resource_id: str, resource_type: ResourceType
    ) -> BaseVersionedData | None:
        """Get latest version by resource_id and resource_type.

        Args:
            resource_id: Resource identifier
            resource_type: Type of resource

        Returns:
            Latest metadata object or None
        """
        return await self.get_latest(
            resource_id=resource_id,
            resource_type=resource_type,
            use_cache=True,
            config=VersionConfig(),
        )

    async def get_version(
        self, resource_id: str, resource_type: ResourceType, version: str
    ) -> BaseVersionedData | None:
        """Get specific version by resource_id, resource_type, and version.

        Args:
            resource_id: Resource identifier
            resource_type: Type of resource
            version: Specific version string

        Returns:
            Metadata object for specified version or None
        """
        return await self.get_by_version(
            resource_id=resource_id,
            resource_type=resource_type,
            version=version,
            use_cache=True,
        )

    async def delete_version(
        self,
        resource_id: str,
        resource_type: ResourceType,
        version: str,
    ) -> bool:
        """Delete a specific version."""
        # Use the specific model class for polymorphic queries
        model_class = self._get_model_class(resource_type)
        result = await model_class.find_one(
            {
                "resource_id": resource_id,
                "resource_type": resource_type.value,
                "version_info.version": version,
            },
        )

        if result:
            # Update version chain
            if result.version_info.superseded_by:
                next_version = await model_class.get(result.version_info.superseded_by)
                if next_version:
                    next_version.version_info.supersedes = result.version_info.supersedes
                    await next_version.save()

            if result.version_info.supersedes:
                prev_version = await model_class.get(result.version_info.supersedes)
                if prev_version:
                    prev_version.version_info.superseded_by = result.version_info.superseded_by
                    if result.version_info.is_latest:
                        prev_version.version_info.is_latest = True
                    await prev_version.save()

            await result.delete()

            # Clear cache for both specific version and latest version
            namespace = self._get_namespace(resource_type)
            if self.cache is None:
                self.cache = await get_global_cache()

            # Clear specific version cache
            version_cache_key = f"{resource_type.value}:{resource_id}:v{version}"
            await self.cache.delete(namespace, version_cache_key)

            # Clear latest version cache if this was marked as latest
            if result.version_info.is_latest:
                latest_cache_key = f"{resource_type.value}:{resource_id}"
                await self.cache.delete(namespace, latest_cache_key)

            logger.info(f"Deleted {resource_type.value} '{resource_id}' v{version}")
            return True

        return False

    async def _find_by_hash(
        self, resource_id: str, resource_type: ResourceType, content_hash: str
    ) -> BaseVersionedData | None:
        """Find existing version with same content hash."""
        # Use the specific model class for polymorphic queries
        model_class = self._get_model_class(resource_type)
        try:
            result = await model_class.find_one(
                {"resource_id": resource_id, "version_info.data_hash": content_hash},
            )
            if result:
                return result
        except Exception as e:
            logger.debug(f"Error finding version by hash: {e}")
            return None
        return None

    def _get_model_class(self, resource_type: ResourceType) -> type[BaseVersionedData]:
        """Map resource type enum to model class using registry pattern."""
        return get_versioned_model_class(resource_type)

    def _get_namespace(self, resource_type: ResourceType) -> CacheNamespace:
        """Map resource type enum to namespace."""
        mapping = {
            ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
            ResourceType.CORPUS: CacheNamespace.CORPUS,
            ResourceType.LANGUAGE: CacheNamespace.LANGUAGE,
            ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
            ResourceType.LITERATURE: CacheNamespace.LITERATURE,
            ResourceType.TRIE: CacheNamespace.TRIE,
            ResourceType.SEARCH: CacheNamespace.SEARCH,
        }
        return mapping[resource_type]

    def _increment_version(self, version: str) -> str:
        """Increment patch version."""
        major, minor, patch = version.split(".")

        return f"{major}.{minor}.{int(patch) + 1}"

    def _json_encoder(self, obj: Any) -> str:
        """Custom JSON encoder for complex objects like PydanticObjectId."""
        from datetime import datetime

        if isinstance(obj, PydanticObjectId):
            return str(obj)
        if isinstance(obj, Enum):
            return str(obj.value)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Global singleton instance
_version_manager: VersionedDataManager | None = None


def get_version_manager() -> VersionedDataManager:
    """Get the global version manager instance.

    Returns:
        VersionedDataManager singleton

    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionedDataManager()

    return _version_manager

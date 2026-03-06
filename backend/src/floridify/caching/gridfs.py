"""GridFS storage backend for large versioned content.

Provides durable storage for content exceeding MongoDB's 16MB BSON limit.
Uses a lazy singleton bucket with 4MB chunks (vs 255KB default) to reduce
chunk count for large blobs (e.g., 400MB SEMANTIC → ~100 chunks).

Content stored here never expires — it survives server restarts and cache
eviction, unlike the transient L1/L2 tiers.
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from gridfs import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from ..utils.logging import get_logger

logger = get_logger(__name__)

_bucket: AsyncIOMotorGridFSBucket | None = None
_bucket_loop_id: int | None = None

# 4MB chunks: a 400MB blob = ~100 chunks instead of ~1600 at default 255KB
_CHUNK_SIZE = 4 * 1024 * 1024


async def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    """Get or create the GridFS bucket, recreating if the event loop changed.

    Uses Beanie's initialized document models to get the database reference,
    which is always valid regardless of whether we're in tests (per-function
    event loops) or production (single event loop).
    """
    global _bucket, _bucket_loop_id
    # TODO[HIGH]: Hoist nested import to module scope unless this is an intentional lazy-init boundary (e.g., CLI or heavyweight model init); document rationale when kept nested.
    import asyncio

    loop_id = id(asyncio.get_running_loop())
    if _bucket is None or _bucket_loop_id != loop_id:
        from .models import BaseVersionedData

        # Get database from Beanie's already-initialized collection
        # This is always bound to the current event loop's client
        db = BaseVersionedData.get_pymongo_collection().database
        _bucket = AsyncIOMotorGridFSBucket(
            db, bucket_name="floridify_blobs", chunk_size_bytes=_CHUNK_SIZE
        )
        _bucket_loop_id = loop_id
    return _bucket


async def gridfs_put(filename: str, data: bytes, metadata: dict[str, Any] | None = None) -> str:
    """Upload bytes to GridFS.

    Args:
        filename: Logical filename for the GridFS entry
        data: Raw bytes to store
        metadata: Optional metadata dict stored alongside the file

    Returns:
        str(ObjectId) suitable for ContentLocation.path
    """
    bucket = await get_gridfs_bucket()
    file_id = await bucket.upload_from_stream(filename, data, metadata=metadata)
    logger.debug(f"GridFS PUT: {filename} ({len(data):,} bytes) -> {file_id}")
    return str(file_id)


async def gridfs_get(file_id_str: str) -> bytes | None:
    """Download bytes from GridFS by ObjectId string.

    Returns None if the file is not found (instead of raising).
    """
    bucket = await get_gridfs_bucket()
    try:
        stream = await bucket.open_download_stream(ObjectId(file_id_str))
        data = await stream.read()
        logger.debug(f"GridFS GET: {file_id_str} ({len(data):,} bytes)")
        return data
    except NoFile:
        logger.warning(f"GridFS GET: {file_id_str} not found")
        # TODO[HIGH]: Replace None-return fallback with explicit missing-blob error handling policy.
        return None
    except Exception:
        logger.exception(f"GridFS GET failed: {file_id_str}")
        # TODO[HIGH]: Replace None-return fallback with explicit storage-read failure handling policy.
        return None


async def gridfs_delete(file_id_str: str) -> None:
    """Delete a GridFS file by ObjectId string. No-op if already gone."""
    bucket = await get_gridfs_bucket()
    try:
        await bucket.delete(ObjectId(file_id_str))
        logger.debug(f"GridFS DELETE: {file_id_str}")
    except Exception:
        # TODO[MEDIUM]: Replace delete no-op swallow with explicit observability/repair signal.
        pass


def reset_bucket() -> None:
    """Reset the singleton bucket (for testing)."""
    global _bucket, _bucket_loop_id
    _bucket = None
    _bucket_loop_id = None

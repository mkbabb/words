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
    # Lazy: heavyweight module
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
        return None
    except Exception as e:
        from ..api.core.exceptions import StorageError

        raise StorageError("read", file_id_str, str(e)) from e


async def gridfs_delete(file_id_str: str) -> None:
    """Delete a GridFS file by ObjectId string. No-op if already gone."""
    bucket = await get_gridfs_bucket()
    try:
        await bucket.delete(ObjectId(file_id_str))
        logger.debug(f"GridFS DELETE: {file_id_str}")
    except Exception as e:
        logger.warning(f"GridFS DELETE failed: {file_id_str}: {e}")


async def gridfs_list_files(prefix: str | None = None) -> list[dict[str, Any]]:
    """List GridFS files, optionally filtered by filename prefix.

    Args:
        prefix: Optional filename prefix to filter by (e.g. "semantic:" or "trie:")

    Returns:
        List of file info dicts with id, filename, length, metadata
    """
    bucket = await get_gridfs_bucket()
    query: dict[str, Any] = {}
    if prefix:
        query["filename"] = {"$regex": f"^{prefix}"}

    files: list[dict[str, Any]] = []
    async for doc in bucket.find(query):
        files.append(
            {
                "id": str(doc._id),
                "filename": doc.filename,
                "length": doc.length,
                "metadata": doc.metadata or {},
            }
        )
    return files


async def gridfs_cleanup_stale(
    corpus_uuid: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Find and optionally delete GridFS files not referenced by any live versioned data.

    A file is "stale" if no BaseVersionedData document with is_latest=True
    references it via content_location.path.

    Args:
        corpus_uuid: Optional filter — only check files whose metadata.corpus_uuid matches
        dry_run: If True, count stale files without deleting them

    Returns:
        Dict with stale_count, stale_bytes, deleted count
    """
    from .models import BaseVersionedData

    # 1. Collect all GridFS file IDs
    all_files = await gridfs_list_files()
    if corpus_uuid:
        all_files = [f for f in all_files if f["metadata"].get("corpus_uuid") == corpus_uuid]

    if not all_files:
        return {"stale_count": 0, "stale_bytes": 0, "deleted": 0}

    # 2. Collect all file IDs referenced by live (is_latest=True) versioned data
    collection = BaseVersionedData.get_pymongo_collection()
    live_refs: set[str] = set()
    async for doc in collection.find(
        {"version_info.is_latest": True, "content_location.path": {"$exists": True}},
        projection={"content_location.path": 1},
    ):
        path = (doc.get("content_location") or {}).get("path")
        if path:
            live_refs.add(str(path))

    # 3. Identify stale files
    stale_files = [f for f in all_files if f["id"] not in live_refs]
    stale_bytes = sum(f["length"] for f in stale_files)

    deleted = 0
    if not dry_run:
        for f in stale_files:
            await gridfs_delete(f["id"])
            deleted += 1
        logger.info(f"GridFS cleanup: deleted {deleted} stale files ({stale_bytes:,} bytes)")
    else:
        logger.info(
            f"GridFS cleanup (dry run): {len(stale_files)} stale files ({stale_bytes:,} bytes)"
        )

    return {
        "stale_count": len(stale_files),
        "stale_bytes": stale_bytes,
        "deleted": deleted,
    }


def reset_bucket() -> None:
    """Reset the singleton bucket (for testing)."""
    global _bucket, _bucket_loop_id
    _bucket = None
    _bucket_loop_id = None

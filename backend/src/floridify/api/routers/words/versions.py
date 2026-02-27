"""Version history endpoints for word definitions.

Provides version listing, specific version retrieval, diff between versions,
and rollback to previous versions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ....caching.delta import compute_diff_between
from ....caching.manager import get_version_manager
from ....caching.models import CacheNamespace, ResourceType, VersionConfig
from ....models.responses import (
    VersionDiffResponse,
    VersionHistoryResponse,
    VersionSummary,
)
from ....utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _make_resource_id(word: str) -> str:
    """Build the version manager resource_id for a word's synthesized entry."""
    return f"{word}:synthesis"


@router.get("/{word}/versions", response_model=VersionHistoryResponse)
async def list_word_versions(word: str) -> VersionHistoryResponse:
    """List all versions of a word's synthesized entry.

    Args:
        word: The word to retrieve version history for

    Returns:
        Version history with summary of each version (newest first)
    """
    resource_id = _make_resource_id(word)
    manager = get_version_manager()

    versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for word: {word}")

    # Sort by version descending (newest first)
    versions.sort(key=lambda v: v.version_info.created_at, reverse=True)

    summaries = [
        VersionSummary(
            version=v.version_info.version,
            created_at=v.version_info.created_at,
            data_hash=v.version_info.data_hash,
            storage_mode=v.version_info.storage_mode,
            is_latest=v.version_info.is_latest,
        )
        for v in versions
    ]

    return VersionHistoryResponse(
        resource_id=resource_id,
        total_versions=len(summaries),
        versions=summaries,
    )


@router.get("/{word}/versions/{version}")
async def get_word_version(word: str, version: str) -> dict[str, Any]:
    """Get a specific historical version of a word's synthesized entry.

    Args:
        word: The word to retrieve
        version: Semantic version string (e.g. "1.0.2")

    Returns:
        Full content of the specified version
    """
    resource_id = _make_resource_id(word)
    manager = get_version_manager()

    result = await manager.get_by_version(
        resource_id, ResourceType.DICTIONARY, version, use_cache=False
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for word: {word}",
        )

    return {
        "resource_id": resource_id,
        "version": result.version_info.version,
        "created_at": result.version_info.created_at.isoformat(),
        "data_hash": result.version_info.data_hash,
        "storage_mode": result.version_info.storage_mode,
        "is_latest": result.version_info.is_latest,
        "content": result.content_inline,
    }


@router.get("/{word}/diff", response_model=VersionDiffResponse)
async def diff_word_versions(
    word: str,
    from_version: str = Query(..., alias="from", description="Source version (e.g. 1.0.0)"),
    to_version: str = Query(..., alias="to", description="Target version (e.g. 1.0.2)"),
) -> VersionDiffResponse:
    """Compute diff between two versions of a word's synthesized entry.

    Args:
        word: The word to diff
        from_version: Source version
        to_version: Target version

    Returns:
        Categorized changes between the two versions
    """
    resource_id = _make_resource_id(word)
    manager = get_version_manager()

    from_result = await manager.get_by_version(
        resource_id, ResourceType.DICTIONARY, from_version, use_cache=False
    )
    to_result = await manager.get_by_version(
        resource_id, ResourceType.DICTIONARY, to_version, use_cache=False
    )

    if from_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {from_version} not found for word: {word}",
        )
    if to_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {to_version} not found for word: {word}",
        )

    from_content = from_result.content_inline or {}
    to_content = to_result.content_inline or {}

    changes = compute_diff_between(from_content, to_content)

    return VersionDiffResponse(
        from_version=from_version,
        to_version=to_version,
        changes=changes,
    )


@router.post("/{word}/rollback")
async def rollback_word_version(
    word: str,
    version: str = Query(..., description="Version to rollback to (e.g. 1.0.1)"),
) -> dict[str, Any]:
    """Rollback a word's synthesized entry to a previous version.

    Creates a new version with the content from the specified historical version.
    Does NOT delete any existing versions — full history is preserved.

    Args:
        word: The word to rollback
        version: Version string to restore

    Returns:
        New version info with the restored content
    """
    resource_id = _make_resource_id(word)
    manager = get_version_manager()

    # Retrieve the target version
    target = await manager.get_by_version(
        resource_id, ResourceType.DICTIONARY, version, use_cache=False
    )
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for word: {word}",
        )

    content = target.content_inline
    if content is None:
        raise HTTPException(
            status_code=422,
            detail=f"Version {version} has no inline content to restore",
        )

    # Save as a new version (with rollback metadata)
    new_version = await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.DICTIONARY,
        namespace=CacheNamespace.DICTIONARY,
        content=content,
        config=VersionConfig(
            force_rebuild=True,  # Always create new version for rollback
            metadata={"rollback_from": version},
        ),
        metadata={"rollback_from": version},
    )

    return {
        "status": "rolled_back",
        "resource_id": resource_id,
        "restored_from_version": version,
        "new_version": new_version.version_info.version,
        "created_at": new_version.version_info.created_at.isoformat(),
    }

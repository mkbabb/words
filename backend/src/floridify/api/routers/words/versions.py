"""Version history endpoints for word definitions.

Provides version listing, specific version retrieval, diff between versions,
and rollback to previous versions.
"""

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
from ...core import AdminDep
from ...services.loaders import DefinitionLoader, PronunciationLoader

logger = get_logger(__name__)
router = APIRouter()


async def _hydrate_version_content(content: dict[str, Any], word: str) -> dict[str, Any]:
    """Hydrate a raw version snapshot into the same shape as a lookup response.

    Resolves definition_ids → full Definition objects with examples/images,
    pronunciation_id → Pronunciation with audio files, and image_ids → ImageMedia.
    """
    from ....models.base import ImageMedia
    from ....models.dictionary import Definition, DictionaryEntry, DictionaryProvider, Word

    hydrated = dict(content)

    # Resolve word text from the Word document
    word_id = content.get("word_id")
    if word_id:
        word_obj = await Word.get(word_id)
        if word_obj:
            hydrated["word"] = word_obj.text
    if "word" not in hydrated:
        hydrated["word"] = word

    # Resolve definitions
    definition_ids = content.get("definition_ids", [])
    if definition_ids:
        # Load provider entries for provider_data linkage
        if word_id:
            provider_entries = await DictionaryEntry.find(
                DictionaryEntry.word_id == word_id,
                DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
            ).to_list()
            provider_entry_ids = (
                [str(pe.id) for pe in provider_entries] if provider_entries else None
            )
        else:
            provider_entry_ids = None

        definitions = []
        for def_id in definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                def_dict = await DefinitionLoader.load_with_relations(
                    definition=definition,
                    include_examples=True,
                    include_images=True,
                    include_provider_data=True,
                    provider_data_ids=provider_entry_ids,
                )
                definitions.append(def_dict)
        hydrated["definitions"] = definitions

    # Resolve pronunciation
    pronunciation_id = content.get("pronunciation_id")
    if pronunciation_id:
        pronunciation = await PronunciationLoader.load_with_audio(str(pronunciation_id))
        if pronunciation:
            hydrated["pronunciation"] = pronunciation

    # Resolve entry-level images
    image_ids = content.get("image_ids", [])
    if image_ids:
        images = []
        for image_id in image_ids:
            image = await ImageMedia.get(image_id)
            if image:
                images.append(image.model_dump(mode="json", exclude={"data"}))
        hydrated["images"] = images

    return hydrated


_NOISY_KEYS = frozenset(
    {
        "id",
        "word_id",
        "definition_ids",
        "pronunciation_id",
        "image_ids",
        "created_at",
        "updated_at",
        "definition_id",
        "entry_id",
        "model_info",
        "last_generated",
        "audio_file_ids",
        "audio_files",
        "fact_ids",
    }
)


def _strip_noisy_fields(obj: Any, depth: int = 0) -> None:
    """Recursively remove timestamp / ID fields that clutter text-level diffs."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in _NOISY_KEYS:
                del obj[key]
            else:
                _strip_noisy_fields(obj[key], depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _strip_noisy_fields(item, depth + 1)


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
async def get_word_version(
    word: str,
    version: str,
    hydrate: bool = Query(
        False, description="Hydrate definition_ids, pronunciation, images into full objects"
    ),
) -> dict[str, Any]:
    """Get a specific historical version of a word's synthesized entry.

    Args:
        word: The word to retrieve
        version: Semantic version string (e.g. "1.0.2")
        hydrate: If True, resolve IDs to full objects (definitions, pronunciation, images)

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

    content = result.content_inline

    if hydrate and content:
        content = await _hydrate_version_content(content, word)

    return {
        "resource_id": resource_id,
        "version": result.version_info.version,
        "created_at": result.version_info.created_at.isoformat(),
        "data_hash": result.version_info.data_hash,
        "storage_mode": result.version_info.storage_mode,
        "is_latest": result.version_info.is_latest,
        "content": content,
    }


@router.get("/{word}/diff", response_model=VersionDiffResponse)
async def diff_word_versions(
    word: str,
    from_version: str = Query(..., alias="from", description="Source version (e.g. 1.0.0)"),
    to_version: str = Query(..., alias="to", description="Target version (e.g. 1.0.2)"),
    hydrate: bool = Query(
        False,
        description="Hydrate IDs to full objects before diffing (gives text-level diffs instead of ID-level)",
    ),
) -> VersionDiffResponse:
    """Compute diff between two versions of a word's synthesized entry.

    Args:
        word: The word to diff
        from_version: Source version
        to_version: Target version
        hydrate: If True, resolve definition_ids/pronunciation/images into full
                 objects before computing the diff, yielding text-level changes
                 rather than raw ObjectId changes.

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

    if hydrate:
        import json

        from_content = await _hydrate_version_content(from_content, word)
        to_content = await _hydrate_version_content(to_content, word)
        # Round-trip through JSON to normalize types (Beanie models → plain dicts)
        from_content = json.loads(json.dumps(from_content, default=str))
        to_content = json.loads(json.dumps(to_content, default=str))
        # Strip noisy fields that aren't meaningful for user-facing diffs
        _strip_noisy_fields(from_content)
        _strip_noisy_fields(to_content)

    changes = compute_diff_between(from_content, to_content)

    return VersionDiffResponse(
        from_version=from_version,
        to_version=to_version,
        changes=changes,
    )


# --- Per-Provider Version Endpoints ---


@router.get("/{word}/providers/{provider}/versions", response_model=VersionHistoryResponse)
async def list_provider_versions(word: str, provider: str) -> VersionHistoryResponse:
    """List all versions of a word's provider entry (e.g. wiktionary, oxford)."""
    resource_id = f"{word}:{provider}"
    manager = get_version_manager()

    versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for {word}:{provider}")

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


@router.get("/{word}/providers/{provider}/versions/{version}")
async def get_provider_version(word: str, provider: str, version: str) -> dict[str, Any]:
    """Get specific version of a provider entry."""
    resource_id = f"{word}:{provider}"
    manager = get_version_manager()

    result = await manager.get_by_version(
        resource_id, ResourceType.DICTIONARY, version, use_cache=False
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for {word}:{provider}",
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


@router.get("/{word}/providers/{provider}/diff", response_model=VersionDiffResponse)
async def diff_provider_versions(
    word: str,
    provider: str,
    from_version: str = Query(..., alias="from", description="Source version"),
    to_version: str = Query(..., alias="to", description="Target version"),
) -> VersionDiffResponse:
    """Diff two versions of a provider entry."""
    resource_id = f"{word}:{provider}"
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
            detail=f"Version {from_version} not found for {word}:{provider}",
        )
    if to_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {to_version} not found for {word}:{provider}",
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
    _admin: AdminDep,
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

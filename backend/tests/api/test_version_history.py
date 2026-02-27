"""Tests for version history API endpoints and definition provenance.

Covers: version listing, specific version retrieval, diff, rollback,
and re-synthesis preserving history.
"""

from __future__ import annotations

import pytest_asyncio

from floridify.caching.manager import get_version_manager
from floridify.caching.models import CacheNamespace, ResourceType


class TestVersionHistoryEndpoints:
    """Integration tests for the /words/{word}/versions endpoints."""

    @pytest_asyncio.fixture
    async def seeded_versions(self, test_db):
        """Seed 3 versions of a word's synthesis into the version manager."""
        manager = get_version_manager()
        resource_id = "test_word:synthesis"

        v1 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "test_word", "definitions": ["first meaning"]},
        )

        v2 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "test_word", "definitions": ["first meaning", "second meaning"]},
        )

        v3 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={
                "word": "test_word",
                "definitions": ["refined first", "second meaning", "third meaning"],
            },
        )

        return {
            "resource_id": resource_id,
            "word": "test_word",
            "versions": [v1, v2, v3],
        }

    async def test_version_history_endpoint(self, async_client, seeded_versions):
        """GET /words/{word}/versions returns correct version list."""
        word = seeded_versions["word"]
        resp = await async_client.get(f"/api/v1/words/{word}/versions")
        assert resp.status_code == 200

        data = resp.json()
        assert data["resource_id"] == f"{word}:synthesis"
        assert data["total_versions"] == 3
        assert len(data["versions"]) == 3

        # Check versions are newest first
        versions = data["versions"]
        assert versions[0]["is_latest"] is True
        assert versions[0]["version"] == "1.0.2"
        assert versions[-1]["version"] == "1.0.0"

        # Each version should have required fields
        for v in versions:
            assert "version" in v
            assert "created_at" in v
            assert "data_hash" in v
            assert "storage_mode" in v

    async def test_version_history_not_found(self, async_client, test_db):
        """GET /words/nonexistent/versions returns 404."""
        resp = await async_client.get("/api/v1/words/nonexistent_word_xyz/versions")
        assert resp.status_code == 404

    async def test_specific_version_retrieval(self, async_client, seeded_versions):
        """GET /words/{word}/versions/{version} returns the specific version content."""
        word = seeded_versions["word"]
        resp = await async_client.get(f"/api/v1/words/{word}/versions/1.0.0")
        assert resp.status_code == 200

        data = resp.json()
        assert data["version"] == "1.0.0"
        assert data["content"]["definitions"] == ["first meaning"]

    async def test_specific_version_not_found(self, async_client, seeded_versions):
        """GET /words/{word}/versions/99.0.0 returns 404."""
        word = seeded_versions["word"]
        resp = await async_client.get(f"/api/v1/words/{word}/versions/99.0.0")
        assert resp.status_code == 404

    async def test_diff_between_versions(self, async_client, seeded_versions):
        """GET /words/{word}/diff?from=X&to=Y returns meaningful diff."""
        word = seeded_versions["word"]
        resp = await async_client.get(
            f"/api/v1/words/{word}/diff",
            params={"from": "1.0.0", "to": "1.0.2"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["from_version"] == "1.0.0"
        assert data["to_version"] == "1.0.2"
        assert data["changes"]  # Should have some changes

    async def test_diff_identical_versions(self, async_client, seeded_versions):
        """Diff of a version with itself returns empty changes."""
        word = seeded_versions["word"]
        resp = await async_client.get(
            f"/api/v1/words/{word}/diff",
            params={"from": "1.0.0", "to": "1.0.0"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["changes"] == {}

    async def test_rollback_restores_content(self, async_client, seeded_versions):
        """POST /words/{word}/rollback creates a new version with old content."""
        word = seeded_versions["word"]

        # Rollback to v1
        resp = await async_client.post(
            f"/api/v1/words/{word}/rollback",
            params={"version": "1.0.0"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "rolled_back"
        assert data["restored_from_version"] == "1.0.0"
        assert data["new_version"] == "1.0.3"  # New version, not overwrite

        # Verify the new latest has the old content
        manager = get_version_manager()
        latest = await manager.get_latest(
            f"{word}:synthesis", ResourceType.DICTIONARY, use_cache=False
        )
        assert latest is not None
        assert latest.content_inline["definitions"] == ["first meaning"]

    async def test_rollback_nonexistent_version(self, async_client, seeded_versions):
        """Rollback to non-existent version returns 404."""
        word = seeded_versions["word"]
        resp = await async_client.post(
            f"/api/v1/words/{word}/rollback",
            params={"version": "99.0.0"},
        )
        assert resp.status_code == 404


class TestDefinitionProvenance:
    """Tests for definition provenance — ensuring old versions survive re-synthesis."""

    async def test_re_synthesis_preserves_history(self, test_db):
        """Old version survives after saving new version (no delete)."""
        manager = get_version_manager()
        resource_id = "provenance_test:synthesis"

        # Save initial version
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "provenance", "defs": ["original"]},
        )

        # Save re-synthesized version (simulates force_refresh)
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "provenance", "defs": ["updated"]},
        )

        # Both versions should exist
        versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)
        assert len(versions) == 2

        # Latest should be v2
        latest = await manager.get_latest(resource_id, ResourceType.DICTIONARY, use_cache=False)
        assert latest is not None
        assert latest.version_info.version == "1.0.1"
        assert latest.content_inline["defs"] == ["updated"]

        # v1 should still be retrievable
        v1_retrieved = await manager.get_by_version(
            resource_id, ResourceType.DICTIONARY, "1.0.0", use_cache=False
        )
        assert v1_retrieved is not None
        assert v1_retrieved.content_inline["defs"] == ["original"]

    async def test_version_info_fields_present(self, test_db):
        """Version info includes storage_mode field."""
        manager = get_version_manager()
        resource_id = "provenance_test:fields"

        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"test": True},
        )

        result = await manager.get_latest(resource_id, ResourceType.DICTIONARY, use_cache=False)
        assert result is not None
        assert result.version_info.storage_mode == "snapshot"
        assert result.version_info.delta_base_id is None

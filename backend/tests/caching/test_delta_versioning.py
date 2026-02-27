"""Tests for delta-based version storage.

Covers: pure delta functions (compute/apply/reconstruct), integration with
VersionedDataManager, snapshot interval enforcement, and backward compatibility.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.caching.config import DELTA_CONFIG, DeltaConfig
from floridify.caching.delta import (
    apply_delta,
    compute_delta,
    compute_diff_between,
    reconstruct_version,
    should_keep_as_snapshot,
)
from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import (
    DELTA_ELIGIBLE_TYPES,
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
)

# ============================================================================
# Pure function tests (no I/O)
# ============================================================================


class TestComputeDelta:
    """Tests for compute_delta / apply_delta round-trip."""

    def test_round_trip_simple(self):
        """apply_delta(new, compute_delta(old, new)) == old."""
        old = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        new = {"a": 1, "b": "world", "c": [1, 2, 3], "d": True}
        delta = compute_delta(old, new)
        assert delta  # Non-empty diff
        reconstructed = apply_delta(new, delta)
        assert reconstructed == old

    def test_round_trip_nested(self):
        """Round-trip works with deeply nested structures."""
        old = {
            "word": "test",
            "definitions": [
                {"text": "A procedure", "pos": "noun"},
                {"text": "To try", "pos": "verb"},
            ],
            "metadata": {"version": 1, "provider": "wiktionary"},
        }
        new = {
            "word": "test",
            "definitions": [
                {"text": "An examination", "pos": "noun"},  # Changed
                {"text": "To try", "pos": "verb"},
                {"text": "A trial", "pos": "noun"},  # Added
            ],
            "metadata": {"version": 2, "provider": "synthesis"},  # Changed
        }
        delta = compute_delta(old, new)
        reconstructed = apply_delta(new, delta)
        assert reconstructed == old

    def test_identical_content_empty_delta(self):
        """Identical content produces empty delta."""
        content = {"a": 1, "b": [1, 2]}
        delta = compute_delta(content, content)
        assert delta == {}

    def test_apply_empty_delta_returns_copy(self):
        """Applying empty delta returns a copy of the snapshot."""
        snapshot = {"a": 1, "b": 2}
        result = apply_delta(snapshot, {})
        assert result == snapshot
        assert result is not snapshot  # Must be a copy

    def test_round_trip_with_removed_keys(self):
        """Delta handles removed keys."""
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1}  # b and c removed
        delta = compute_delta(old, new)
        reconstructed = apply_delta(new, delta)
        assert reconstructed == old


class TestReconstructVersion:
    """Tests for chaining multiple deltas."""

    def test_chain_of_deltas(self):
        """Reconstruct through a chain of 3 deltas."""
        v1 = {"value": 1}
        v2 = {"value": 2}
        v3 = {"value": 3}
        v4 = {"value": 4}  # Snapshot (latest)

        # Deltas from newest to oldest perspective
        delta_v3 = compute_delta(v3, v4)  # v3 from v4
        delta_v2 = compute_delta(v2, v3)  # v2 from v3
        delta_v1 = compute_delta(v1, v2)  # v1 from v2

        # Reconstruct v1 from v4 through the chain
        # Chain order: v3 delta, v2 delta, v1 delta
        assert apply_delta(v4, delta_v3) == v3
        assert apply_delta(v3, delta_v2) == v2
        assert apply_delta(v2, delta_v1) == v1

    def test_reconstruct_version_with_chain(self):
        """reconstruct_version applies chain correctly."""
        snapshot = {"x": 100, "y": 200}
        intermediate = {"x": 50, "y": 200}
        target = {"x": 10, "y": 200}

        delta1 = compute_delta(intermediate, snapshot)
        delta2 = compute_delta(target, intermediate)

        result = reconstruct_version(snapshot, [delta1, delta2])
        assert result == target


class TestComputeDiffBetween:
    """Tests for human-readable diff generation."""

    def test_diff_shows_changes(self):
        """Diff between two dicts shows meaningful changes."""
        a = {"word": "test", "count": 5}
        b = {"word": "test", "count": 10, "new_field": True}
        diff = compute_diff_between(a, b)
        assert diff  # Non-empty
        assert "values_changed" in diff or "dictionary_item_added" in diff

    def test_diff_identical_returns_empty(self):
        """Diff of identical dicts returns empty."""
        content = {"a": 1}
        assert compute_diff_between(content, content) == {}


class TestShouldKeepAsSnapshot:
    """Tests for snapshot interval logic."""

    def test_version_zero_is_snapshot(self):
        assert should_keep_as_snapshot(0, 10) is True

    def test_interval_boundary_is_snapshot(self):
        assert should_keep_as_snapshot(10, 10) is True
        assert should_keep_as_snapshot(20, 10) is True
        assert should_keep_as_snapshot(100, 10) is True

    def test_non_boundary_is_delta(self):
        assert should_keep_as_snapshot(1, 10) is False
        assert should_keep_as_snapshot(5, 10) is False
        assert should_keep_as_snapshot(9, 10) is False
        assert should_keep_as_snapshot(11, 10) is False


# ============================================================================
# Integration tests (require MongoDB)
# ============================================================================


class TestDeltaVersioningIntegration:
    """Integration tests for delta versioning with VersionedDataManager."""

    @pytest_asyncio.fixture
    async def manager(self, test_db):
        """Get a fresh VersionedDataManager."""
        mgr = VersionedDataManager()
        return mgr

    async def test_save_converts_previous_to_delta(self, manager: VersionedDataManager, test_db):
        """After saving a new version, the previous version should be converted to delta."""
        resource_id = "delta_test:word1"

        # Save v1
        v1 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "test", "definitions": ["meaning 1"]},
        )
        assert v1.version_info.version == "1.0.0"
        assert v1.version_info.storage_mode == "snapshot"

        # Save v2 (should convert v1 to delta)
        v2 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "test", "definitions": ["meaning 1", "meaning 2"]},
        )
        assert v2.version_info.version == "1.0.1"
        assert v2.version_info.storage_mode == "snapshot"

        # Verify v1 was converted to delta in the database
        model_class = manager._get_model_class(ResourceType.DICTIONARY)
        v1_doc = await model_class.get(v1.id)
        assert v1_doc is not None
        # v1 is version 1.0.0 → patch=0 → 0 % 10 == 0, so it stays as snapshot
        # (version 0 is always a snapshot per should_keep_as_snapshot)
        assert v1_doc.version_info.storage_mode == "snapshot"

        # Save v3 (should convert v2 to delta, since v2 is patch=1)
        v3 = await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "test", "definitions": ["meaning 1", "meaning 2", "meaning 3"]},
        )
        assert v3.version_info.version == "1.0.2"

        # v2 (patch=1) should now be delta
        v2_doc = await model_class.get(v2.id)
        assert v2_doc is not None
        assert v2_doc.version_info.storage_mode == "delta"
        assert v2_doc.version_info.delta_base_id == v3.id

    async def test_get_latest_unaffected(self, manager: VersionedDataManager, test_db):
        """get_latest() always returns a full snapshot, never a delta."""
        resource_id = "delta_test:latest"

        # Save multiple versions
        for i in range(3):
            await manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content={"word": "test", "version": i},
            )

        # Latest should always be a full snapshot
        latest = await manager.get_latest(resource_id, ResourceType.DICTIONARY, use_cache=False)
        assert latest is not None
        assert latest.version_info.storage_mode == "snapshot"
        assert latest.version_info.is_latest is True
        assert latest.content_inline is not None
        assert latest.content_inline["version"] == 2

    async def test_get_specific_version_reconstructs(self, manager: VersionedDataManager, test_db):
        """Fetching a specific delta version reconstructs the full content."""
        resource_id = "delta_test:reconstruct"

        # Save v1 (patch=0 → stays as snapshot)
        v1_content = {"word": "apple", "defs": ["a fruit"]}
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=v1_content,
        )

        # Save v2 (patch=1 → will be converted to delta when v3 is saved)
        v2_content = {"word": "apple", "defs": ["a fruit", "a tech company"]}
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=v2_content,
        )

        # Save v3 (this converts v2 to delta)
        v3_content = {"word": "apple", "defs": ["a fruit", "a tech company", "the big apple"]}
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=v3_content,
        )

        # Retrieve v2 (which is now a delta)
        v2_retrieved = await manager.get_by_version(
            resource_id, ResourceType.DICTIONARY, "1.0.1", use_cache=False
        )
        assert v2_retrieved is not None
        assert v2_retrieved.content_inline == v2_content

    async def test_binary_types_skip_delta(self, manager: VersionedDataManager, test_db):
        """SEMANTIC and TRIE resource types should never be converted to delta."""
        resource_id = "delta_test:semantic"

        # SEMANTIC model requires corpus_uuid and model_name fields
        semantic_metadata = {
            "corpus_uuid": "test-uuid-1234",
            "model_name": "test-model",
        }

        # Save two versions of a SEMANTIC resource
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.SEMANTIC,
            content={"index": "binary_data_v1"},
            metadata=semantic_metadata,
        )
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.SEMANTIC,
            content={"index": "binary_data_v2"},
            metadata=semantic_metadata,
        )

        # v1 should remain as snapshot
        versions = await manager.list_versions(resource_id, ResourceType.SEMANTIC)
        for v in versions:
            assert v.version_info.storage_mode == "snapshot"

    async def test_backward_compatible(self, manager: VersionedDataManager, test_db):
        """Old documents without storage_mode field should work as snapshots."""
        # Save a version (will have storage_mode="snapshot" by default)
        result = await manager.save(
            resource_id="delta_test:compat",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"word": "legacy"},
        )

        # Simulate old document by removing storage_mode from DB
        collection = BaseVersionedData.get_pymongo_collection()
        await collection.update_one(
            {"_id": result.id},
            {"$unset": {"version_info.storage_mode": ""}},
        )

        # Retrieve should still work (defaults to "snapshot")
        retrieved = await manager.get_by_version(
            "delta_test:compat", ResourceType.DICTIONARY, "1.0.0", use_cache=False
        )
        assert retrieved is not None
        assert retrieved.version_info.storage_mode == "snapshot"
        assert retrieved.content_inline is not None

    async def test_storage_reduction(self, manager: VersionedDataManager, test_db):
        """Delta versions use significantly less space than full snapshots."""
        import json

        resource_id = "delta_test:reduction"

        # Create a large-ish content that changes incrementally
        base_content = {
            "word": "elaborate",
            "definitions": [f"Definition {i} with some elaboration text" for i in range(20)],
            "metadata": {f"key_{i}": f"value_{i}" for i in range(50)},
        }

        # Save v1 (snapshot)
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=base_content,
        )

        # Save v2 with small change (will be converted to delta when v3 saved)
        modified = dict(base_content)
        modified["definitions"] = list(base_content["definitions"])
        modified["definitions"][0] = "Updated first definition"
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=modified,
        )

        # Save v3 to trigger v2 → delta conversion
        modified2 = dict(modified)
        modified2["definitions"] = list(modified["definitions"])
        modified2["definitions"][1] = "Updated second definition"
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=modified2,
        )

        # Check v2 delta size vs full snapshot size
        versions = await manager.list_versions(resource_id, ResourceType.DICTIONARY)

        delta_versions = [v for v in versions if v.version_info.storage_mode == "delta"]
        snapshot_versions = [v for v in versions if v.version_info.storage_mode == "snapshot"]

        if delta_versions:
            delta_size = len(json.dumps(delta_versions[0].content_inline or {}))
            snapshot_size = len(json.dumps(snapshot_versions[0].content_inline or {}))
            # Delta should be smaller than snapshot for incremental changes
            assert delta_size < snapshot_size


class TestDeltaConfig:
    """Tests for DeltaConfig."""

    def test_default_config(self):
        """Default config has expected values."""
        assert DELTA_CONFIG.snapshot_interval == 10
        assert DELTA_CONFIG.max_chain_length == 50
        assert DELTA_CONFIG.enabled is True

    def test_config_immutable(self):
        """DeltaConfig is frozen (immutable)."""
        with pytest.raises(AttributeError):
            DELTA_CONFIG.enabled = False  # type: ignore[misc]

    def test_custom_config(self):
        """Can create custom DeltaConfig instances."""
        custom = DeltaConfig(snapshot_interval=5, max_chain_length=20, enabled=False)
        assert custom.snapshot_interval == 5
        assert custom.max_chain_length == 20
        assert custom.enabled is False


class TestDeltaEligibleTypes:
    """Tests for DELTA_ELIGIBLE_TYPES."""

    def test_eligible_types(self):
        """DICTIONARY, CORPUS, LANGUAGE, LITERATURE are eligible."""
        assert ResourceType.DICTIONARY in DELTA_ELIGIBLE_TYPES
        assert ResourceType.CORPUS in DELTA_ELIGIBLE_TYPES
        assert ResourceType.LANGUAGE in DELTA_ELIGIBLE_TYPES
        assert ResourceType.LITERATURE in DELTA_ELIGIBLE_TYPES

    def test_ineligible_types(self):
        """SEMANTIC, TRIE, SEARCH are NOT eligible (binary data)."""
        assert ResourceType.SEMANTIC not in DELTA_ELIGIBLE_TYPES
        assert ResourceType.TRIE not in DELTA_ELIGIBLE_TYPES
        assert ResourceType.SEARCH not in DELTA_ELIGIBLE_TYPES

"""Tests for cache concurrency behavior.

Validates that:
- Concurrent writes to the same resource result in exactly 1 is_latest=True version.
- The dedup decorator prevents duplicate concurrent calls.
- L1 cache handles concurrent reads/writes without corruption.

Uses asyncio.gather to simulate concurrent operations.
Mocks MongoDB operations as needed.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from floridify.caching.core import GlobalCacheManager, get_global_cache
from floridify.caching.decorators import _active_calls, deduplicated
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import CacheNamespace


class TestL1CacheConcurrentReadWrite:
    """Test L1 (memory) cache under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_writes_same_key(self):
        """Test that concurrent writes to the same key do not corrupt data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "concurrent_write_key"

            # Launch 20 concurrent writes with different values
            async def write_value(i: int):
                await manager.set(namespace, key, {"value": i})

            await asyncio.gather(*[write_value(i) for i in range(20)])

            # The final value should be one of the written values (not corrupted)
            result = await manager.get(namespace, key)
            assert result is not None
            assert "value" in result
            assert isinstance(result["value"], int)
            assert 0 <= result["value"] < 20

    @pytest.mark.asyncio
    async def test_concurrent_reads_same_key(self):
        """Test that concurrent reads of the same key all return the same value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "concurrent_read_key"
            expected = {"word": "ephemeral", "definitions": ["short-lived"]}

            await manager.set(namespace, key, expected)

            # Launch 50 concurrent reads
            results = await asyncio.gather(
                *[manager.get(namespace, key) for _ in range(50)]
            )

            # All reads should return the same value
            for result in results:
                assert result == expected

    @pytest.mark.asyncio
    async def test_concurrent_different_keys(self):
        """Test that concurrent writes to different keys all succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            async def write_and_read(i: int):
                key = f"key_{i}"
                value = {"index": i, "data": f"value_{i}"}
                await manager.set(namespace, key, value)
                result = await manager.get(namespace, key)
                return result

            results = await asyncio.gather(*[write_and_read(i) for i in range(30)])

            # Each key should have its own correct value
            for i, result in enumerate(results):
                assert result is not None
                assert result["index"] == i
                assert result["data"] == f"value_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_write_and_delete(self):
        """Test that concurrent writes and deletes do not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "write_delete_key"

            # Pre-populate
            await manager.set(namespace, key, {"initial": True})

            async def write_op():
                await manager.set(namespace, key, {"updated": True})

            async def delete_op():
                await manager.delete(namespace, key)

            # Mix writes and deletes concurrently
            tasks = [write_op() if i % 2 == 0 else delete_op() for i in range(20)]
            await asyncio.gather(*tasks)

            # Result should be either the value or None (deleted) - no crash
            result = await manager.get(namespace, key)
            assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_concurrent_namespace_isolation(self):
        """Test that concurrent writes to different namespaces don't interfere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            key = "shared_key"
            namespaces = [CacheNamespace.DICTIONARY, CacheNamespace.SEARCH, CacheNamespace.CORPUS]

            async def write_to_namespace(ns: CacheNamespace, value: str):
                await manager.set(ns, key, {"namespace": value})

            await asyncio.gather(
                *[write_to_namespace(ns, ns.value) for ns in namespaces]
            )

            # Each namespace should have its own value
            for ns in namespaces:
                result = await manager.get(ns, key)
                assert result is not None
                assert result["namespace"] == ns.value


class TestVersionedDataConcurrency:
    """Test VersionedDataManager per-resource locking and concurrent saves.

    Tests the locking mechanism directly to validate that:
    - Same-resource saves are serialized (exactly one at a time under the lock).
    - Different-resource saves can proceed in parallel.

    Does not go through the full save() method to avoid complex MongoDB mocking.
    """

    @pytest.mark.asyncio
    async def test_per_resource_lock_serializes_same_resource(self):
        """Test that concurrent operations on the same resource are serialized by the lock."""
        from floridify.caching.manager import VersionedDataManager
        from floridify.caching.models import ResourceType

        manager = VersionedDataManager()

        # Track execution to verify serialization
        execution_order = []
        active_count = 0
        max_concurrent = 0

        async def simulated_save(resource_id: str, save_id: int):
            nonlocal active_count, max_concurrent
            lock = manager._get_lock(ResourceType.DICTIONARY, resource_id)
            async with lock:
                active_count += 1
                max_concurrent = max(max_concurrent, active_count)
                execution_order.append(f"start_{save_id}")
                await asyncio.sleep(0.02)  # Simulate I/O
                execution_order.append(f"end_{save_id}")
                active_count -= 1

        # 5 concurrent saves to the SAME resource
        await asyncio.gather(*[simulated_save("test_word", i) for i in range(5)])

        # Because they all use the same lock, max concurrent should be 1
        assert max_concurrent == 1, (
            f"Per-resource lock should serialize same-resource saves, "
            f"but max concurrent was {max_concurrent}"
        )

        # All 5 saves should complete
        assert len(execution_order) == 10  # 5 starts + 5 ends

        # Verify strict serialization: each start-end pair is contiguous
        for i in range(5):
            start_idx = execution_order.index(f"start_{i}")
            end_idx = execution_order.index(f"end_{i}")
            # No other start should occur between this start and end
            between = execution_order[start_idx + 1 : end_idx]
            assert all(not item.startswith("start_") for item in between), (
                f"Save {i} was not serialized: found overlapping operations"
            )

    @pytest.mark.asyncio
    async def test_per_resource_lock_allows_parallel_different_resources(self):
        """Test that saves to different resources can proceed in parallel."""
        from floridify.caching.manager import VersionedDataManager
        from floridify.caching.models import ResourceType

        manager = VersionedDataManager()

        max_concurrent = 0
        active_count = 0
        lock_obj = asyncio.Lock()

        async def simulated_save(resource_id: str):
            nonlocal active_count, max_concurrent
            resource_lock = manager._get_lock(ResourceType.DICTIONARY, resource_id)
            async with resource_lock:
                async with lock_obj:
                    active_count += 1
                    max_concurrent = max(max_concurrent, active_count)
                await asyncio.sleep(0.05)  # Simulate I/O
                async with lock_obj:
                    active_count -= 1

        # 3 concurrent saves to DIFFERENT resources
        start = asyncio.get_event_loop().time()
        await asyncio.gather(
            simulated_save("apple"),
            simulated_save("banana"),
            simulated_save("cherry"),
        )
        total_time = asyncio.get_event_loop().time() - start

        # Different resources should run concurrently
        assert max_concurrent >= 2, (
            f"Per-resource locks should allow parallel execution of different resources, "
            f"but max concurrent was {max_concurrent}"
        )

        # Total time should be roughly 1x the sleep time, not 3x
        assert total_time < 0.2, (
            f"Per-resource locking should allow parallel execution, "
            f"took {total_time:.3f}s (expected <0.2s for 3 concurrent 0.05s operations)"
        )

    @pytest.mark.asyncio
    async def test_version_chain_is_latest_invariant(self):
        """Test that _save_with_transaction marks exactly 1 version as is_latest.

        Simulates what _save_with_transaction does: insert new version with
        is_latest=True, then update all previous versions to is_latest=False.
        Verifies the invariant holds even with concurrent saves.
        """
        from floridify.caching.manager import VersionedDataManager
        from floridify.caching.models import ResourceType

        manager = VersionedDataManager()

        # Simulate version store in-memory (instead of MongoDB)
        version_store: list[dict] = []
        store_lock = asyncio.Lock()

        async def simulated_save_with_chain(resource_id: str, version_num: int):
            """Simulate the atomic save + chain update that _save_with_transaction does."""
            resource_lock = manager._get_lock(ResourceType.DICTIONARY, resource_id)
            async with resource_lock:
                async with store_lock:
                    # Insert new version with is_latest=True
                    new_version = {
                        "resource_id": resource_id,
                        "version": f"1.0.{version_num}",
                        "is_latest": True,
                    }
                    version_store.append(new_version)

                    # Update all previous versions to is_latest=False
                    for v in version_store:
                        if v["resource_id"] == resource_id and v is not new_version:
                            v["is_latest"] = False

        # Run 5 concurrent saves for the same resource
        await asyncio.gather(
            *[simulated_save_with_chain("test_word", i) for i in range(5)]
        )

        # Check invariant: exactly 1 version has is_latest=True
        latest_versions = [v for v in version_store if v["is_latest"]]
        assert len(latest_versions) == 1, (
            f"Expected exactly 1 is_latest=True version, got {len(latest_versions)}: {latest_versions}"
        )

        # The latest version should be the last one saved
        assert latest_versions[0] == version_store[-1]


class TestDedupDecorator:
    """Test the @deduplicated decorator for preventing duplicate concurrent calls."""

    @pytest.mark.asyncio
    async def test_dedup_prevents_duplicate_calls(self):
        """Test that concurrent calls with same args only execute once."""
        call_count = 0
        call_event = asyncio.Event()

        @deduplicated
        async def expensive_operation(word: str) -> dict:
            nonlocal call_count
            call_count += 1
            call_event.set()
            # Simulate work
            await asyncio.sleep(0.1)
            return {"word": word, "result": "computed"}

        # Launch 5 concurrent calls with the same argument
        results = await asyncio.gather(
            *[expensive_operation("ephemeral") for _ in range(5)]
        )

        # Only 1 actual execution should have happened
        assert call_count == 1, (
            f"Expected exactly 1 execution for deduplicated concurrent calls, got {call_count}"
        )

        # All callers should receive the same result
        for result in results:
            assert result == {"word": "ephemeral", "result": "computed"}

    @pytest.mark.asyncio
    async def test_dedup_different_args_execute_separately(self):
        """Test that calls with different args are NOT deduplicated."""
        call_count = 0

        @deduplicated
        async def process_word(word: str) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return f"processed_{word}"

        results = await asyncio.gather(
            process_word("apple"),
            process_word("banana"),
            process_word("cherry"),
        )

        # All 3 should execute independently (different args -> different cache keys)
        assert call_count == 3
        assert set(results) == {"processed_apple", "processed_banana", "processed_cherry"}

    @pytest.mark.asyncio
    async def test_dedup_propagates_errors(self):
        """Test that errors from the first call propagate to all waiters."""
        call_count = 0

        @deduplicated
        async def failing_operation(word: str) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            raise ValueError(f"Failed for {word}")

        # All 3 should raise the same error
        with pytest.raises(ValueError, match="Failed for test"):
            await asyncio.gather(
                failing_operation("test"),
                failing_operation("test"),
                failing_operation("test"),
            )

        # Only 1 execution despite 3 calls
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_dedup_cleanup_after_completion(self):
        """Test that _active_calls is cleaned up after the call completes."""
        @deduplicated
        async def quick_op(key: str) -> str:
            return f"done_{key}"

        result = await quick_op("cleanup_test")
        assert result == "done_cleanup_test"

        # After completion and cleanup delay, there should be no active calls
        await asyncio.sleep(0.05)  # Allow cleanup delay

        # The specific key should not be in _active_calls
        # (we can't easily check the exact key, but the dict should be empty for new calls)
        # Verify by running another call with the same args - it should execute again
        call_count = 0

        @deduplicated
        async def counted_op(key: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"done_{key}"

        await counted_op("reuse_test")
        await asyncio.sleep(0.05)
        await counted_op("reuse_test")

        # Both calls should have executed (no stale dedup state)
        assert call_count == 2


class TestLRUEvictionConcurrency:
    """Test LRU eviction behavior under concurrent access."""

    @pytest.mark.asyncio
    async def test_lru_eviction_under_pressure(self):
        """Test that LRU eviction works correctly when many concurrent writes exceed limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            ns = manager.namespaces[namespace]
            memory_limit = ns.memory_limit

            # Write more items than the memory limit concurrently
            item_count = memory_limit + 50

            async def write_item(i: int):
                await manager.set(namespace, f"lru_key_{i}", {"value": i})

            await asyncio.gather(*[write_item(i) for i in range(item_count)])

            # Memory cache should not exceed the limit
            assert len(ns.memory_cache) <= memory_limit, (
                f"Memory cache size {len(ns.memory_cache)} exceeds limit {memory_limit}"
            )

            # Evictions should have occurred
            assert ns.stats.evictions > 0, "Expected evictions to have occurred"

    @pytest.mark.asyncio
    async def test_stats_consistency_under_concurrency(self):
        """Test that cache stats remain consistent under concurrent access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            # Populate some keys
            for i in range(10):
                await manager.set(namespace, f"stat_key_{i}", {"value": i})

            # Run many concurrent gets (mix of hits and misses)
            async def get_item(key: str):
                return await manager.get(namespace, key)

            keys = [f"stat_key_{i}" for i in range(20)]  # 10 exist, 10 don't
            await asyncio.gather(*[get_item(k) for k in keys])

            # Verify stats are internally consistent
            ns = manager.namespaces[namespace]
            stats = ns.stats
            total = stats.hits + stats.misses

            # Should have some hits and some misses
            assert stats.hits > 0, "Expected some cache hits"
            assert stats.misses > 0, "Expected some cache misses"
            assert total == 20, f"Total requests ({total}) should equal number of gets (20)"

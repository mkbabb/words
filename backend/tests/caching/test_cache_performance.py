"""Test cache performance and verify speedup targets."""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import CacheNamespace


class TestCachePerformance:
    """Test cache performance meets target specifications."""

    @pytest.mark.asyncio
    async def test_l1_cache_performance_target(self):
        """Verify L1 cache hits are under 0.5ms target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "performance_test"
            data = {"test": "value", "number": 42}

            # Warm up the cache
            await manager.set(namespace, key, data)

            # Test L1 cache hit performance (100 iterations)
            timings = []
            for _ in range(100):
                start = time.perf_counter()
                result = await manager.get(namespace, key)
                elapsed_ms = (time.perf_counter() - start) * 1000
                timings.append(elapsed_ms)
                assert result == data

            avg_time = sum(timings) / len(timings)
            min_time = min(timings)
            max_time = max(timings)

            print(f"\nL1 Cache Performance:")
            print(f"  Average: {avg_time:.4f}ms")
            print(f"  Min:     {min_time:.4f}ms")
            print(f"  Max:     {max_time:.4f}ms")
            print(f"  Target:  0.5ms")

            # L1 cache should be extremely fast (< 0.5ms average)
            assert avg_time < 0.5, f"L1 cache too slow: {avg_time:.4f}ms (target: 0.5ms)"

    @pytest.mark.asyncio
    async def test_l2_cache_performance(self):
        """Verify L2 cache performance is reasonable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "l2_performance_test"
            data = {"test": "value", "number": 42}

            # Set in cache (stores in both L1 and L2)
            await manager.set(namespace, key, data)

            # Clear L1 to force L2 lookup
            ns = manager.namespaces[namespace]
            async with ns.lock:
                ns.memory_cache.clear()

            # Test L2 cache performance (50 iterations)
            timings = []
            for i in range(50):
                # Clear L1 again after first lookup (which promotes to L1)
                if i > 0:
                    async with ns.lock:
                        ns.memory_cache.clear()

                start = time.perf_counter()
                result = await manager.get(namespace, key)
                elapsed_ms = (time.perf_counter() - start) * 1000
                timings.append(elapsed_ms)
                assert result == data

            avg_time = sum(timings) / len(timings)
            min_time = min(timings)
            max_time = max(timings)

            print(f"\nL2 Cache Performance:")
            print(f"  Average: {avg_time:.4f}ms")
            print(f"  Min:     {min_time:.4f}ms")
            print(f"  Max:     {max_time:.4f}ms")
            print(f"  Target:  <10ms")

            # L2 cache should be reasonable (< 10ms average)
            assert avg_time < 10.0, f"L2 cache too slow: {avg_time:.4f}ms"

    @pytest.mark.asyncio
    async def test_cache_speedup_vs_loader(self):
        """Verify cache provides significant speedup vs loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "speedup_test"

            # Simulated expensive operation (50ms)
            async def expensive_loader():
                await asyncio.sleep(0.05)
                return {"expensive": "data"}

            # First call - uses loader
            start = time.perf_counter()
            result1 = await manager.get(namespace, key, loader=expensive_loader)
            uncached_time = (time.perf_counter() - start) * 1000

            # Second call - uses cache
            start = time.perf_counter()
            result2 = await manager.get(namespace, key)
            cached_time = (time.perf_counter() - start) * 1000

            assert result1 == result2

            speedup = uncached_time / cached_time

            print(f"\nCache Speedup Test:")
            print(f"  Uncached: {uncached_time:.2f}ms")
            print(f"  Cached:   {cached_time:.2f}ms")
            print(f"  Speedup:  {speedup:.1f}x")
            print(f"  Target:   >10x")

            # Cache should provide at least 10x speedup
            assert speedup >= 10.0, f"Insufficient speedup: {speedup:.1f}x (target: 10x)"

    @pytest.mark.asyncio
    async def test_cache_hit_rate_tracking(self):
        """Verify cache hit rate is tracked correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            # Populate cache
            for i in range(10):
                await manager.set(namespace, f"key_{i}", {"value": i})

            # Mix of hits and misses
            # 10 hits
            for i in range(10):
                result = await manager.get(namespace, f"key_{i}")
                assert result is not None

            # 5 misses
            for i in range(10, 15):
                result = await manager.get(namespace, f"key_{i}")
                assert result is None

            # Check stats
            stats = manager.get_stats(namespace)
            hits = stats["stats"]["hits"]
            misses = stats["stats"]["misses"]

            assert hits == 10, f"Expected 10 hits, got {hits}"
            assert misses == 5, f"Expected 5 misses, got {misses}"

            hit_rate = hits / (hits + misses)
            assert abs(hit_rate - 0.666) < 0.01, f"Hit rate {hit_rate:.3f} != 0.666"

            print(f"\nCache Hit Rate Test:")
            print(f"  Hits:     {hits}")
            print(f"  Misses:   {misses}")
            print(f"  Hit Rate: {hit_rate:.1%}")

    @pytest.mark.asyncio
    async def test_concurrent_cache_performance(self):
        """Test cache performance under concurrent load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            # Populate cache
            for i in range(100):
                await manager.set(namespace, f"key_{i}", {"value": i})

            # Concurrent reads
            async def concurrent_read(key_id: int):
                start = time.perf_counter()
                result = await manager.get(namespace, f"key_{key_id}")
                elapsed = (time.perf_counter() - start) * 1000
                assert result["value"] == key_id
                return elapsed

            # Run 100 concurrent reads
            start = time.perf_counter()
            tasks = [concurrent_read(i) for i in range(100)]
            timings = await asyncio.gather(*tasks)
            total_time = (time.perf_counter() - start) * 1000

            avg_time = sum(timings) / len(timings)
            throughput = 1000 * len(tasks) / total_time  # ops/sec

            print(f"\nConcurrent Cache Performance:")
            print(f"  Total Time:  {total_time:.2f}ms")
            print(f"  Avg Per Op:  {avg_time:.4f}ms")
            print(f"  Throughput:  {throughput:.0f} ops/sec")

            # Should maintain good performance under load
            assert avg_time < 1.0, f"Concurrent access too slow: {avg_time:.4f}ms"

    @pytest.mark.asyncio
    async def test_cache_compression_performance(self):
        """Test cache performance with compression enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            # Use CORPUS namespace which has ZSTD compression
            namespace = CacheNamespace.CORPUS
            key = "compression_test"

            # Large data that benefits from compression
            large_data = {
                "definitions": [f"This is definition number {i}" * 10 for i in range(100)],
                "examples": [f"Example sentence {i}" * 10 for i in range(100)],
            }

            # Set and get with compression
            start = time.perf_counter()
            await manager.set(namespace, key, large_data)
            set_time = (time.perf_counter() - start) * 1000

            # Clear L1 to test L2 with decompression
            ns = manager.namespaces[namespace]
            async with ns.lock:
                ns.memory_cache.clear()

            start = time.perf_counter()
            result = await manager.get(namespace, key)
            get_time = (time.perf_counter() - start) * 1000

            assert result == large_data

            print(f"\nCompression Performance:")
            print(f"  Set Time: {set_time:.2f}ms")
            print(f"  Get Time: {get_time:.2f}ms")

            # Should still be reasonably fast even with compression
            assert set_time < 50.0, f"Compressed set too slow: {set_time:.2f}ms"
            assert get_time < 50.0, f"Compressed get too slow: {get_time:.2f}ms"

"""Reproducible cache, delta, and diff microbenchmarks."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from floridify.audit import benchmark_sync, build_multi_version_payloads
from floridify.caching.compression import compress_data, decompress_data
from floridify.caching.core import GlobalCacheManager
from floridify.caching.delta import (
    apply_delta,
    compute_delta,
    compute_diff_between,
    reconstruct_version,
)
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import CacheNamespace, CompressionType
from floridify.caching.serialize import compute_content_hash


def _build_payload(version: int) -> dict[str, object]:
    return {
        "word": "audittrail",
        "definitions": [
            {
                "part_of_speech": "noun",
                "text": f"A revision history for debugging ({version}).",
                "examples": [f"Example {version}", f"Rollback {version}"],
            }
        ],
        "etymology": {
            "text": f"From audit + trail ({version})",
            "root_words": ["audit", "trail"],
        },
        "metadata": {
            "revision": version,
            "tags": ["audit", "history", "performance"],
        },
    }


@pytest.mark.performance
@pytest.mark.asyncio
async def test_cache_layer_reads_and_delta_round_trip(tmp_path: Path) -> None:
    manager = GlobalCacheManager(FilesystemBackend(tmp_path))
    await manager.initialize()

    key = "audit-versioning"
    payload = _build_payload(3)
    await manager.set(CacheNamespace.DICTIONARY, key, payload)

    async def _read_l1() -> dict[str, object] | None:
        return await manager.get(CacheNamespace.DICTIONARY, key)

    l1_case, l1_results = await benchmark_sync_async_bridge(
        "cache-l1-read",
        "versioning",
        _read_l1,
        iterations=32,
        warmup=1,
    )

    namespace = manager.namespaces[CacheNamespace.DICTIONARY]

    async def _read_l2() -> dict[str, object] | None:
        async with namespace.lock:
            namespace.memory_cache.clear()
        return await manager.get(CacheNamespace.DICTIONARY, key)

    l2_case, l2_results = await benchmark_sync_async_bridge(
        "cache-l2-read",
        "versioning",
        _read_l2,
        iterations=12,
        warmup=1,
    )

    previous_payload = _build_payload(2)
    delta_case, deltas = benchmark_sync(
        "delta-compute",
        "versioning",
        lambda: compute_delta(previous_payload, payload),
        iterations=24,
        warmup=1,
    )
    apply_case, reconstructed = benchmark_sync(
        "delta-apply",
        "versioning",
        lambda: apply_delta(copy.deepcopy(payload), deltas[-1]),
        iterations=24,
        warmup=1,
    )
    diff_case, diffs = benchmark_sync(
        "timemachine-diff",
        "timemachine",
        lambda: compute_diff_between(previous_payload, payload),
        iterations=16,
        warmup=1,
    )

    assert l1_results[-1] == payload
    assert l2_results[-1] == payload
    assert reconstructed[-1] == previous_payload
    assert "values_changed" in diffs[-1]
    assert l1_case.stats.p95_ms < 1.0
    assert l2_case.stats.p95_ms < 25.0
    assert delta_case.stats.p95_ms < 50.0
    assert apply_case.stats.p95_ms < 50.0
    assert diff_case.stats.p95_ms < 80.0


async def benchmark_sync_async_bridge(
    name: str,
    category: str,
    func,
    *,
    iterations: int,
    warmup: int,
):
    from floridify.audit import benchmark_async

    return await benchmark_async(
        name,
        category,
        func,
        iterations=iterations,
        warmup=warmup,
    )


@pytest.mark.performance
@pytest.mark.versioning
def test_deep_delta_chain_round_trip() -> None:
    """Build a 10-version delta chain, reconstruct oldest from newest + deltas."""
    payloads = build_multi_version_payloads(10)

    # Build delta chain: delta[i] = diff(payloads[i], payloads[i+1])
    deltas = []
    for i in range(len(payloads) - 1):
        deltas.append(compute_delta(payloads[i], payloads[i + 1]))

    # Reconstruct v0 from v9 + reversed delta chain
    case, results = benchmark_sync(
        "deep-chain-reconstruct",
        "versioning",
        lambda: reconstruct_version(copy.deepcopy(payloads[-1]), list(reversed(deltas))),
        iterations=16,
        warmup=2,
    )

    reconstructed = results[-1]
    assert reconstructed == payloads[0], "Reconstruction through 9 deltas should match original"
    assert case.stats.p95_ms < 200.0


@pytest.mark.performance
@pytest.mark.versioning
def test_content_hash_dedup() -> None:
    """Identical content → same hash; different key order → same hash; changed field → different."""
    payload_a = {"word": "hello", "defs": [{"text": "greeting"}], "meta": {"v": 1}}
    payload_b = {"meta": {"v": 1}, "defs": [{"text": "greeting"}], "word": "hello"}
    payload_c = {"word": "hello", "defs": [{"text": "salutation"}], "meta": {"v": 1}}

    hash_a = compute_content_hash(payload_a)
    hash_b = compute_content_hash(payload_b)
    hash_c = compute_content_hash(payload_c)

    assert hash_a == hash_b, "Same content, different key order → same hash"
    assert hash_a != hash_c, "Changed field → different hash"

    case, _ = benchmark_sync(
        "content-hash",
        "versioning",
        lambda: compute_content_hash(payload_a),
        iterations=32,
        warmup=2,
    )
    assert case.stats.p95_ms < 5.0


@pytest.mark.performance
@pytest.mark.versioning
def test_compression_round_trip() -> None:
    """ZSTD/LZ4/GZIP compress+decompress round-trip correctness and ratio."""
    import pickle

    payload = build_multi_version_payloads(1)[0]
    raw_bytes = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)

    for ct in (CompressionType.ZSTD, CompressionType.LZ4, CompressionType.GZIP):
        compressed = compress_data(payload, compression=ct)
        decompressed = decompress_data(compressed, compression=ct)
        assert decompressed == payload, f"{ct.value} round-trip failed"

        ratio = len(compressed) / len(raw_bytes)
        case, _ = benchmark_sync(
            f"compress-{ct.value}",
            "versioning",
            lambda ct=ct: compress_data(payload, compression=ct),
            iterations=16,
            warmup=2,
        )
        # ZSTD should compress well for JSON-like dictionary data
        if ct == CompressionType.ZSTD:
            assert ratio < 0.8, f"ZSTD ratio {ratio:.2f} unexpectedly high"


@pytest.mark.performance
@pytest.mark.timemachine
def test_realistic_entry_diff() -> None:
    """Diff two multi-definition payloads with realistic changes."""
    payloads = build_multi_version_payloads(10)
    old, new = payloads[0], payloads[-1]

    case, diffs = benchmark_sync(
        "realistic-diff",
        "timemachine",
        lambda: compute_diff_between(old, new),
        iterations=16,
        warmup=2,
    )

    diff = diffs[-1]
    assert diff, "Diff between v0 and v9 should be non-empty"
    assert any(
        k in diff for k in ("values_changed", "dictionary_item_added", "iterable_item_added")
    ), f"Expected structural changes in diff, got keys: {list(diff.keys())}"
    assert case.stats.p95_ms < 100.0

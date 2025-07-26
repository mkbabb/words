#!/usr/bin/env python3
"""Test script to demonstrate request deduplication functionality."""

import asyncio
import time
from typing import Any

from src.floridify.caching import cached_api_call_with_dedup, deduplicated
from src.floridify.utils.logging import get_logger

logger = get_logger(__name__)


# Simulate an expensive API call
@deduplicated(key_func=lambda word: f"expensive_lookup:{word}")
async def expensive_lookup(word: str) -> dict[str, Any]:
    """Simulate an expensive lookup operation."""
    logger.info(f"🔍 Starting expensive lookup for: {word}")
    await asyncio.sleep(2)  # Simulate network delay
    result = {
        "word": word,
        "definition": f"The meaning of {word}",
        "timestamp": time.time(),
    }
    logger.info(f"✅ Completed expensive lookup for: {word}")
    return result


# With caching and deduplication combined
@cached_api_call_with_dedup(
    ttl_hours=0.1,  # 6 minutes for testing
    key_func=lambda word: ("cached_lookup", word),
)
async def cached_expensive_lookup(word: str) -> dict[str, Any]:
    """Simulate an expensive lookup with caching and deduplication."""
    logger.info(f"🔍 Starting cached lookup for: {word}")
    await asyncio.sleep(2)  # Simulate network delay
    result = {
        "word": word,
        "definition": f"The cached meaning of {word}",
        "timestamp": time.time(),
    }
    logger.info(f"✅ Completed cached lookup for: {word}")
    return result


async def test_basic_deduplication():
    """Test basic request deduplication."""
    logger.info("\n=== Testing Basic Deduplication ===")
    
    # Launch 5 concurrent requests for the same word
    word = "example"
    start_time = time.time()
    
    tasks = [
        expensive_lookup(word) for _ in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    logger.info(f"⏱️  Total time for 5 concurrent requests: {elapsed:.2f}s")
    logger.info(f"📊 All timestamps are identical: {all(r['timestamp'] == results[0]['timestamp'] for r in results)}")
    
    # Show that all results are the same
    for i, result in enumerate(results):
        logger.info(f"   Result {i+1}: timestamp={result['timestamp']:.3f}")


async def test_different_keys():
    """Test that different keys are not deduplicated."""
    logger.info("\n=== Testing Different Keys ===")
    
    # Launch requests for different words
    words = ["apple", "banana", "cherry"]
    start_time = time.time()
    
    tasks = [
        expensive_lookup(word) for word in words
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    logger.info(f"⏱️  Total time for 3 different words: {elapsed:.2f}s")
    
    # Show that results have different timestamps
    for result in results:
        logger.info(f"   {result['word']}: timestamp={result['timestamp']:.3f}")


async def test_cached_with_deduplication():
    """Test combined caching and deduplication."""
    logger.info("\n=== Testing Cached with Deduplication ===")
    
    word = "python"
    
    # First batch: 3 concurrent requests (will deduplicate)
    logger.info("🔹 First batch: 3 concurrent requests")
    start_time = time.time()
    tasks = [cached_expensive_lookup(word) for _ in range(3)]
    results1 = await asyncio.gather(*tasks)
    elapsed1 = time.time() - start_time
    logger.info(f"   Time: {elapsed1:.2f}s, All same: {all(r['timestamp'] == results1[0]['timestamp'] for r in results1)}")
    
    # Wait a bit
    await asyncio.sleep(0.5)
    
    # Second batch: 3 more requests (will hit cache)
    logger.info("🔹 Second batch: 3 requests (should hit cache)")
    start_time = time.time()
    tasks = [cached_expensive_lookup(word) for _ in range(3)]
    results2 = await asyncio.gather(*tasks)
    elapsed2 = time.time() - start_time
    logger.info(f"   Time: {elapsed2:.2f}s (cache hit, no deduplication needed)")
    
    # Verify cache hit
    logger.info(f"   Cache hit confirmed: {results2[0]['timestamp'] == results1[0]['timestamp']}")


async def test_concurrent_different_words():
    """Test mixed concurrent requests."""
    logger.info("\n=== Testing Mixed Concurrent Requests ===")
    
    # Mix of duplicate and unique requests
    words = ["alpha", "beta", "alpha", "gamma", "beta", "alpha"]
    start_time = time.time()
    
    tasks = [
        expensive_lookup(word) for word in words
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    logger.info(f"⏱️  Total time for {len(words)} requests: {elapsed:.2f}s")
    
    # Group results by word
    word_timestamps = {}
    for i, (word, result) in enumerate(zip(words, results)):
        if word not in word_timestamps:
            word_timestamps[word] = []
        word_timestamps[word].append((i, result['timestamp']))
    
    # Show deduplication results
    for word, timestamps in word_timestamps.items():
        logger.info(f"\n   Word '{word}' ({len(timestamps)} requests):")
        for idx, ts in timestamps:
            logger.info(f"      Request {idx+1}: timestamp={ts:.3f}")
        unique_timestamps = set(ts for _, ts in timestamps)
        logger.info(f"      Deduplicated: {len(unique_timestamps)} unique execution(s)")


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Request Deduplication Tests")
    
    await test_basic_deduplication()
    await test_different_keys()
    await test_cached_with_deduplication()
    await test_concurrent_different_words()
    
    logger.info("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
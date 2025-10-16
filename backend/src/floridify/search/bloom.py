"""Lightweight Bloom filter for fast vocabulary membership checks.

A Bloom filter provides O(1) probabilistic membership testing with:
- False positives possible (says "maybe in set")
- No false negatives (if it says "not in set", it's definitely not)
- Much smaller memory footprint than a full hash set

Perfect for pre-filtering vocabulary lookups before expensive trie searches.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import xxhash  # Fast xxHash implementation (already in dependencies)


class BloomFilter:
    """Lightweight Bloom filter using MurmurHash3 for fast membership testing.

    Performance characteristics:
    - Membership test: O(1) - constant time regardless of set size
    - False positive rate: ~0.1% with default settings (1% of vocabulary size)
    - Memory: ~1.2 bytes per element (vs 8+ bytes for set/dict)
    - Build time: O(n) where n = number of elements

    Example:
        >>> bloom = BloomFilter(capacity=100000, error_rate=0.01)
        >>> bloom.add("test")
        >>> "test" in bloom
        True
        >>> "nonexistent" in bloom
        False  # or rarely True (false positive)
    """

    def __init__(self, capacity: int, error_rate: float = 0.01):
        """Initialize Bloom filter with target capacity and error rate.

        Args:
            capacity: Expected number of elements
            error_rate: Target false positive rate (default 1%)

        """
        # Calculate optimal bit array size and hash function count
        # Based on: m = -n*ln(p) / (ln(2)^2) and k = m/n * ln(2)

        self.capacity = capacity
        self.error_rate = error_rate

        # Bit array size
        self.bit_count = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))

        # Number of hash functions
        self.hash_count = int(self.bit_count / capacity * math.log(2))

        # Ensure at least 1 hash function
        self.hash_count = max(1, self.hash_count)

        # Use bytearray for efficient bit manipulation
        self.bits = bytearray((self.bit_count + 7) // 8)

        self.item_count = 0

    def _get_bit_positions(self, item: str) -> list[int]:
        """Get k bit positions for the item using hash functions.

        Uses xxHash with different seeds for each hash function.

        Args:
            item: String to hash

        Returns:
            List of bit positions (indices in bit array)

        """
        positions = []

        # Encode once for all hash functions
        item_bytes = item.encode("utf-8")

        # Use xxHash with different seeds for each hash function
        # xxHash is extremely fast (C implementation) and has good distribution
        for seed in range(self.hash_count):
            # Use xxh64 for 64-bit hash (faster than xxh32 on 64-bit systems)
            hash_obj = xxhash.xxh64(item_bytes, seed=seed)
            hash_val = hash_obj.intdigest()
            position = hash_val % self.bit_count
            positions.append(position)

        return positions

    def _set_bit(self, position: int) -> None:
        """Set a bit in the bit array.

        Args:
            position: Bit position to set

        """
        byte_idx = position // 8
        bit_idx = position % 8
        self.bits[byte_idx] |= 1 << bit_idx

    def _get_bit(self, position: int) -> bool:
        """Get a bit from the bit array.

        Args:
            position: Bit position to get

        Returns:
            True if bit is set, False otherwise

        """
        byte_idx = position // 8
        bit_idx = position % 8
        return bool(self.bits[byte_idx] & (1 << bit_idx))

    def add(self, item: str) -> None:
        """Add an item to the Bloom filter.

        Args:
            item: String to add

        """
        for position in self._get_bit_positions(item):
            self._set_bit(position)
        self.item_count += 1

    def add_many(self, items: Iterable[str]) -> None:
        """Add multiple items efficiently.

        Args:
            items: Iterable of strings to add

        """
        for item in items:
            self.add(item)

    def __contains__(self, item: str) -> bool:
        """Check if item might be in the set (with false positive rate).

        Args:
            item: String to check

        Returns:
            True if item might be in set, False if definitely not in set

        """
        return all(self._get_bit(pos) for pos in self._get_bit_positions(item))

    def __len__(self) -> int:
        """Return approximate number of items in filter.

        Note: This is approximate due to hash collisions.

        Returns:
            Number of items added to the filter

        """
        return self.item_count

    def get_stats(self) -> dict[str, float]:
        """Get Bloom filter statistics.

        Returns:
            Dictionary with filter statistics

        """
        # Calculate actual fill rate
        set_bits = sum(bin(byte).count("1") for byte in self.bits)
        fill_rate = set_bits / self.bit_count

        # Estimate actual false positive rate based on fill
        # p_fp ≈ (1 - e^(-k*n/m))^k

        if self.item_count > 0:
            estimated_fp_rate = (
                1 - math.exp(-self.hash_count * self.item_count / self.bit_count)
            ) ** self.hash_count
        else:
            estimated_fp_rate = 0.0

        return {
            "capacity": self.capacity,
            "item_count": self.item_count,
            "bit_count": self.bit_count,
            "hash_count": self.hash_count,
            "fill_rate": fill_rate,
            "target_error_rate": self.error_rate,
            "estimated_error_rate": estimated_fp_rate,
            "memory_bytes": len(self.bits),
            "memory_per_item": len(self.bits) / max(1, self.item_count),
        }


__all__ = ["BloomFilter"]

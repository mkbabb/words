"""High-performance compression utilities for caching."""

from __future__ import annotations

import gzip
import pickle
from typing import Any

import lz4.frame  # type: ignore[import-untyped]
import zstandard as zstd

from .models import CompressionType


def compress_data(data: Any, compression: CompressionType | None = None) -> bytes:
    """Compress data with specified algorithm.

    Args:
        data: Data to compress (will be pickled if not bytes)
        compression: Compression algorithm to use

    Returns:
        Compressed bytes

    """
    # Serialize with pickle if needed
    if isinstance(data, bytes):
        serialized = data
    else:
        # Pickle handles everything: Pydantic models, ObjectIds, etc.
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    # Apply compression
    if compression == CompressionType.ZSTD:
        cctx = zstd.ZstdCompressor(level=3)
        return cctx.compress(serialized)
    elif compression == CompressionType.LZ4:
        return lz4.frame.compress(serialized, compression_level=0)
    elif compression == CompressionType.GZIP:
        return gzip.compress(serialized, compresslevel=6)
    else:
        return serialized


def decompress_data(data: bytes, compression: CompressionType | None = None) -> Any:
    """Decompress and deserialize data using pickle.

    Args:
        data: Compressed bytes
        compression: Compression algorithm used

    Returns:
        Decompressed and deserialized data

    """
    # Decompress first if needed
    if compression == CompressionType.ZSTD:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(data)
    elif compression == CompressionType.LZ4:
        decompressed = lz4.frame.decompress(data)
    elif compression == CompressionType.GZIP:
        decompressed = gzip.decompress(data)
    else:
        decompressed = data

    # Deserialize with pickle
    return pickle.loads(decompressed)

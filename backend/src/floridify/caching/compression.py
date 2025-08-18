"""High-performance compression utilities for caching."""

from __future__ import annotations

import gzip
import pickle
from typing import Any

import lz4.frame
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
    # Serialize first if needed
    if isinstance(data, bytes):
        serialized = data
    else:
        # Use pickle for all non-bytes (fastest for complex objects)
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Apply compression
    if compression == CompressionType.ZSTD:
        cctx = zstd.ZstdCompressor(level=3)
        return cctx.compress(serialized)
    elif compression == CompressionType.LZ4:
        return lz4.frame.compress(serialized, compression_level=0)
    elif compression == CompressionType.GZIP:
        return gzip.compress(serialized, compresslevel=6)
    
    return serialized


def decompress_data(data: bytes, compression: CompressionType | None = None) -> Any:
    """Decompress and deserialize data.
    
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
    
    # Deserialize - check for pickle magic bytes
    if len(decompressed) >= 2 and decompressed[:2] in (b'\x80\x04', b'\x80\x05'):
        return pickle.loads(decompressed)
    
    # Return raw bytes if not pickled
    return decompressed


def auto_select_compression(size_bytes: int) -> CompressionType | None:
    """Automatically select compression based on data size.
    
    Args:
        size_bytes: Size of data in bytes
        
    Returns:
        Optimal compression type or None for no compression
    """
    if size_bytes < 1024:  # < 1KB
        return None
    elif size_bytes < 10_000_000:  # < 10MB
        return CompressionType.ZSTD  # Best balance
    else:
        return CompressionType.GZIP  # Best for large files
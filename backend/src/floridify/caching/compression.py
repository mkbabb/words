"""Compression utilities for caching system.

Provides transparent compression/decompression with multiple algorithms.
"""

from __future__ import annotations

import gzip
import json
import pickle
import zlib
from typing import Any

import numpy as np

from .core import CacheMetadata, CompressionType, QuantizationType


def compress_data(
    data: bytes,
    compression_type: CompressionType = CompressionType.ZLIB,
) -> tuple[bytes, CacheMetadata]:
    """Compress data using the specified algorithm.

    Args:
        data: Raw data to compress
        compression_type: Compression algorithm to use

    Returns:
        Tuple of (compressed_data, metadata)

    """
    original_size = len(data)

    if compression_type == CompressionType.NONE:
        compressed_data = data
    elif compression_type == CompressionType.ZLIB:
        compressed_data = zlib.compress(data, level=6)  # Good balance of speed/ratio
    elif compression_type == CompressionType.GZIP:
        compressed_data = gzip.compress(data, compresslevel=6)
    else:
        raise ValueError(f"Unsupported compression type: {compression_type}")

    compressed_size = len(compressed_data)
    compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0

    metadata = CacheMetadata(
        compression_type=compression_type,
        original_size=original_size,
        compressed_size=compressed_size,
        compression_ratio=compression_ratio,
    )

    return compressed_data, metadata


def decompress_data(compressed_data: bytes, metadata: CacheMetadata) -> bytes:
    """Decompress data using metadata information.

    Args:
        compressed_data: Compressed data
        metadata: Compression metadata

    Returns:
        Decompressed data

    """
    if metadata.compression_type == CompressionType.NONE:
        return compressed_data
    if metadata.compression_type == CompressionType.ZLIB:
        return zlib.decompress(compressed_data)
    if metadata.compression_type == CompressionType.GZIP:
        return gzip.decompress(compressed_data)
    raise ValueError(f"Unsupported compression type: {metadata.compression_type}")


def quantize_embeddings(
    embeddings: np.ndarray,
    quantization_type: QuantizationType = QuantizationType.FLOAT32,
) -> tuple[bytes, CacheMetadata]:
    """Quantize embeddings to reduce memory usage.

    Args:
        embeddings: NumPy array of embeddings
        quantization_type: Type of quantization to apply

    Returns:
        Tuple of (quantized_data, metadata)

    """
    original_size = embeddings.nbytes

    if quantization_type == QuantizationType.FLOAT32:
        quantized_embeddings = embeddings.astype(np.float32)
    elif quantization_type == QuantizationType.FLOAT16:
        quantized_embeddings = embeddings.astype(np.float16)
    elif quantization_type == QuantizationType.INT8:
        # Scale to int8 range (-128 to 127)
        min_val, max_val = embeddings.min(), embeddings.max()
        scale = max(abs(min_val), abs(max_val))
        if scale > 0:
            quantized_embeddings = ((embeddings / scale) * 127).astype(np.int8)
        else:
            quantized_embeddings = embeddings.astype(np.int8)
    elif quantization_type == QuantizationType.UINT8:
        # Scale to uint8 range (0 to 255)
        min_val, max_val = embeddings.min(), embeddings.max()
        if max_val > min_val:
            quantized_embeddings = ((embeddings - min_val) / (max_val - min_val) * 255).astype(
                np.uint8,
            )
        else:
            quantized_embeddings = embeddings.astype(np.uint8)
    else:
        raise ValueError(f"Unsupported quantization type: {quantization_type}")

    # Serialize quantized data
    quantized_data = pickle.dumps(
        {
            "data": quantized_embeddings,
            "dtype": quantization_type.value,
            "original_shape": embeddings.shape,
            "original_range": (embeddings.min(), embeddings.max())
            if quantization_type in (QuantizationType.INT8, QuantizationType.UINT8)
            else None,
        },
    )

    quantized_size = len(quantized_data)
    compression_ratio = original_size / quantized_size if quantized_size > 0 else 1.0

    metadata = CacheMetadata(
        quantization_type=quantization_type,
        original_size=original_size,
        compressed_size=quantized_size,
        compression_ratio=compression_ratio,
    )

    return quantized_data, metadata


def dequantize_embeddings(quantized_data: bytes, metadata: CacheMetadata) -> np.ndarray:
    """Dequantize embeddings back to usable form.

    Args:
        quantized_data: Quantized embedding data
        metadata: Quantization metadata

    Returns:
        Dequantized embeddings as numpy array

    """
    data_dict = pickle.loads(quantized_data)
    quantized_embeddings = data_dict["data"]
    quantization_type = QuantizationType(data_dict["dtype"])
    original_range = data_dict.get("original_range")

    if quantization_type == QuantizationType.FLOAT32:
        return np.array(quantized_embeddings, dtype=np.float32)
    if quantization_type == QuantizationType.FLOAT16:
        return np.array(
            quantized_embeddings,
            dtype=np.float32,
        )  # Convert back to float32 for processing
    if quantization_type == QuantizationType.INT8:
        # Restore original scale
        if original_range:
            min_val, max_val = original_range
            scale = max(abs(min_val), abs(max_val))
            int8_result: np.ndarray = (
                np.array(quantized_embeddings, dtype=np.float32) / 127.0 * scale
            )
            return int8_result
        return np.array(quantized_embeddings, dtype=np.float32)
    if quantization_type == QuantizationType.UINT8:
        # Restore original range
        if original_range:
            min_val, max_val = original_range
            uint8_result: np.ndarray = (
                np.array(quantized_embeddings, dtype=np.float32) / 255.0 * (max_val - min_val)
            ) + min_val
            return uint8_result
        return np.array(quantized_embeddings, dtype=np.float32)
    raise ValueError(f"Unsupported quantization type: {quantization_type}")


def serialize_with_compression(
    obj: Any,
    compression_type: CompressionType = CompressionType.ZLIB,
) -> tuple[bytes, CacheMetadata]:
    """Serialize and compress an object.

    Args:
        obj: Object to serialize
        compression_type: Compression type to use

    Returns:
        Tuple of (compressed_data, metadata)

    """
    # Serialize object
    if isinstance(obj, dict | list | str | int | float | bool) or obj is None:
        # Use JSON for basic types (more portable)
        serialized = json.dumps(obj).encode("utf-8")
    else:
        # Use pickle for complex objects
        serialized = pickle.dumps(obj)

    return compress_data(serialized, compression_type)


def deserialize_with_decompression(
    compressed_data: bytes,
    metadata: CacheMetadata,
    use_json: bool = True,
) -> Any:
    """Decompress and deserialize an object.

    Args:
        compressed_data: Compressed serialized data
        metadata: Compression metadata
        use_json: Try JSON deserialization first

    Returns:
        Deserialized object

    """
    decompressed = decompress_data(compressed_data, metadata)

    if use_json:
        try:
            return json.loads(decompressed.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(decompressed)
    else:
        return pickle.loads(decompressed)

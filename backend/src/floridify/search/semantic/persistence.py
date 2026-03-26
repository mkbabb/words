"""Persistence layer for semantic search embeddings and FAISS indices.

Handles serialization and storage of embedding arrays and FAISS indices
using native FAISS I/O and pickle. Compression is delegated to the L2
cache layer (ZSTD) to avoid double compression.
"""

from __future__ import annotations

import gzip
import os
import pickle
import tempfile
from typing import Any

import numpy as np

from ...caching.filesystem import safe_pickle_loads
from ...caching.models import VersionConfig
from ...utils.logging import get_logger
from .index import SemanticIndex

logger = get_logger(__name__)


def load_embeddings_from_binary_data(
    binary_data: dict[str, object],
    corpus_name: str,
) -> np.ndarray:
    """Load and decompress embeddings from binary data.

    Args:
        binary_data: Dictionary containing compressed embedding bytes
        corpus_name: Name of the corpus (for error messages)

    Returns:
        Numpy array of embeddings

    Raises:
        RuntimeError: If data is missing, corrupted, or in an unsupported format
    """
    if "embeddings_bytes" not in binary_data and "embeddings_compressed_bytes" not in binary_data:
        raise RuntimeError(
            f"Invalid semantic index format for '{corpus_name}': "
            f"missing 'embeddings_bytes' or 'embeddings_compressed_bytes'."
        )

    try:
        # Support both new (raw) and old (gzip-compressed) formats
        if "embeddings_bytes" in binary_data:
            raw_bytes = binary_data["embeddings_bytes"]
            logger.debug(f"Loading raw embeddings ({len(raw_bytes) / 1024 / 1024:.1f}MB)")
            embeddings = safe_pickle_loads(raw_bytes)
        else:
            compressed_bytes = binary_data["embeddings_compressed_bytes"]
            logger.debug(
                f"Decompressing gzip embeddings ({len(compressed_bytes) / 1024 / 1024:.1f}MB compressed)"
            )
            raw_bytes = gzip.decompress(compressed_bytes)
            embeddings = safe_pickle_loads(raw_bytes)

        logger.debug(
            f"Loaded embeddings: {len(raw_bytes) / 1024 / 1024:.2f}MB, "
            f"shape={embeddings.shape if embeddings is not None else 'none'}"
        )

        # Detect corrupted embeddings (all zeros)
        if embeddings is not None and embeddings.size > 0 and np.all(embeddings == 0):
            raise RuntimeError(f"Corrupted embeddings for '{corpus_name}': all values are zero")

        return embeddings
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Corrupted embeddings data for '{corpus_name}': {e}") from e


def load_faiss_index_from_binary_data(
    binary_data: dict[str, object],
    corpus_name: str,
) -> Any:  # Returns faiss.Index
    """Load and decompress a FAISS index from binary data.

    Args:
        binary_data: Dictionary containing compressed FAISS index bytes
        corpus_name: Name of the corpus (for error messages)

    Returns:
        FAISS index

    Raises:
        RuntimeError: If data is missing, corrupted, or in an unsupported format
    """
    if "index_bytes" not in binary_data and "index_compressed_bytes" not in binary_data:
        raise RuntimeError(
            f"Invalid semantic index format for '{corpus_name}': "
            f"missing 'index_bytes' or 'index_compressed_bytes'."
        )

    try:
        import faiss

        # Support both new (raw) and old (gzip-compressed) formats
        if "index_bytes" in binary_data:
            raw_index = binary_data["index_bytes"]
            if isinstance(raw_index, str):
                raise RuntimeError(
                    f"Invalid index format for '{corpus_name}': base64-encoded data no longer supported"
                )
            logger.debug(f"Loading raw FAISS index ({len(raw_index) / 1024 / 1024:.1f}MB)")
            index_bytes = raw_index
        else:
            compressed = binary_data["index_compressed_bytes"]
            if isinstance(compressed, str):
                raise RuntimeError(
                    f"Invalid index format for '{corpus_name}': base64-encoded data no longer supported"
                )
            logger.debug("Decompressing gzip FAISS index")
            index_bytes = gzip.decompress(compressed)
            logger.debug(f"Decompressed FAISS index: {len(index_bytes) / 1024 / 1024:.1f}MB")

        # Write bytes to temp file and load with FAISS native read
        with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp_file:
            tmp_file.write(index_bytes)
            tmp_path = tmp_file.name

        try:
            sentence_index = faiss.read_index(tmp_path)
            logger.debug(f"Loaded FAISS index: {len(index_bytes) / 1024 / 1024:.1f}MB")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return sentence_index
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Corrupted FAISS index data for '{corpus_name}': {e}") from e


async def save_embeddings_and_index(
    index: SemanticIndex,
    sentence_embeddings: np.ndarray | None,
    sentence_index: Any | None,  # faiss.Index
    build_time: float,
    corpus_uuid: str,
) -> None:
    """Save embeddings and FAISS index to the index model.

    Compression handled by storage layer. Architecture: MongoDB stores ONLY metadata,
    cache backend stores large content.

    Args:
        index: SemanticIndex model to update
        sentence_embeddings: Embedding array to persist
        sentence_index: FAISS index to persist
        build_time: Time taken to build embeddings (seconds)
        corpus_uuid: UUID of the corpus

    Raises:
        RuntimeError: If persistence fails
    """
    # CRITICAL FIX: Store binary data DIRECTLY to disk, not through JSON
    # User requirement: Metadata ONLY in MongoDB, binary content on disk
    # Architecture: Write raw compressed bytes to cache filesystem using pickle
    binary_data: dict[str, object] = {}

    # Serialize embeddings (compression delegated to L2 cache layer)
    if sentence_embeddings is not None and sentence_embeddings.size > 0:
        embeddings_bytes = pickle.dumps(sentence_embeddings)
        embeddings_size_mb = len(embeddings_bytes) / 1024 / 1024
        logger.info(f"Serialized embeddings: {embeddings_size_mb:.1f}MB")
        binary_data["embeddings_bytes"] = embeddings_bytes

    # CRITICAL FIX (2025-10-22): Use FAISS native disk I/O instead of pickle serialization
    # pickle.dumps(faiss.serialize_index()) does DOUBLE serialization which hangs for 20+ mins
    # FAISS's write_index() writes directly to disk using optimized C++ I/O
    if sentence_index is not None:
        import faiss

        logger.info("Serializing FAISS index using native disk I/O (not pickle)...")

        # Write FAISS index directly to temp file using optimized C++ serialization
        with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp_file:
            tmp_path = tmp_file.name

        try:
            # FAISS native write - fast, optimized C++ disk I/O
            faiss.write_index(sentence_index, tmp_path)

            # Read the serialized bytes from disk
            with open(tmp_path, "rb") as f:
                index_bytes = f.read()

            index_size_mb = len(index_bytes) / 1024 / 1024
            logger.info(f"FAISS index serialized: {index_size_mb:.1f}MB using native disk I/O")
            binary_data["index_bytes"] = index_bytes
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # Update statistics
    index.build_time_seconds = build_time
    memory_usage_mb = (
        (sentence_embeddings.nbytes / (1024 * 1024)) if sentence_embeddings is not None else 0.0
    )

    # Detect and store index type
    if sentence_index is not None:
        index_class_name = sentence_index.__class__.__name__
        if "HNSW" in index_class_name:
            index.index_type = "HNSW"
        elif "IVFPQ" in index_class_name:
            index.index_type = "IVFPQ"
        elif "IVF" in index_class_name:
            index.index_type = "IVF"
        elif "ScalarQuantizer" in index_class_name:
            index.index_type = "ScalarQuantizer"
        else:
            index.index_type = "Flat"

    # CRITICAL FIX: Store large binary data externally via cache manager
    # Architecture: MongoDB stores ONLY metadata, cache backend stores large content
    # This prevents MongoDB size limits and hanging on 392MB compressed data
    try:
        logger.info("Storing semantic index data externally via cache manager...")
        # Use SemanticIndex's own save method which handles versioned storage
        await index.save(
            config=VersionConfig(),
            corpus_uuid=corpus_uuid,
            binary_data=binary_data,
        )
        logger.info(
            "\u2705 Semantic index saved successfully (metadata in MongoDB, data in cache backend)"
        )
    except Exception as e:
        logger.error(f"Failed to save semantic index: {e}")
        raise RuntimeError(
            f"Semantic index persistence failed. This may be due to size limits or corruption. "
            f"Embeddings size: {memory_usage_mb:.2f}MB. Error: {e}"
        ) from e

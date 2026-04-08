"""Persistence layer for semantic search embeddings and FAISS indices.

Serialization uses pickle for embeddings and FAISS native I/O for the
index. The resulting bytes are handed to ``SemanticIndex.save()`` which
routes them through the version manager's ``binary_payload`` hook —
single GridFS upload, no double-compression, no JSON encoding.
"""

from __future__ import annotations

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
    binary_data: dict[str, bytes],
    corpus_name: str,
) -> np.ndarray:
    """Load embeddings from raw pickle bytes.

    Args:
        binary_data: Dictionary containing ``embeddings_bytes`` (pickle bytes).
        corpus_name: Name of the corpus (for error messages).

    Returns:
        Numpy array of embeddings.

    Raises:
        RuntimeError: If data is missing or corrupted.
    """
    raw_bytes = binary_data.get("embeddings_bytes")
    if not raw_bytes:
        raise RuntimeError(
            f"Invalid semantic index format for '{corpus_name}': missing 'embeddings_bytes'."
        )

    try:
        logger.debug(f"Loading raw embeddings ({len(raw_bytes) / 1024 / 1024:.1f}MB)")
        embeddings = safe_pickle_loads(raw_bytes)

        logger.debug(
            f"Loaded embeddings: {len(raw_bytes) / 1024 / 1024:.2f}MB, "
            f"shape={embeddings.shape if embeddings is not None else 'none'}"
        )

        if embeddings is not None and embeddings.size > 0 and np.all(embeddings == 0):
            raise RuntimeError(f"Corrupted embeddings for '{corpus_name}': all values are zero")

        return embeddings
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Corrupted embeddings data for '{corpus_name}': {e}") from e


def load_faiss_index_from_binary_data(
    binary_data: dict[str, bytes],
    corpus_name: str,
) -> Any:  # Returns faiss.Index
    """Load a FAISS index from raw bytes.

    Args:
        binary_data: Dictionary containing ``index_bytes`` (FAISS native bytes).
        corpus_name: Name of the corpus (for error messages).

    Returns:
        FAISS index.

    Raises:
        RuntimeError: If data is missing or corrupted.
    """
    index_bytes = binary_data.get("index_bytes")
    if not index_bytes:
        raise RuntimeError(
            f"Invalid semantic index format for '{corpus_name}': missing 'index_bytes'."
        )

    try:
        import faiss

        logger.debug(f"Loading raw FAISS index ({len(index_bytes) / 1024 / 1024:.1f}MB)")

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

    Serializes embeddings (pickle) and the FAISS index (native C++ I/O)
    into raw bytes, then hands the dict to ``SemanticIndex.save()`` which
    routes it through the version manager's ``binary_payload`` hook —
    one GridFS upload, no JSON, no double-serialization.

    Args:
        index: SemanticIndex model to update.
        sentence_embeddings: Embedding array to persist.
        sentence_index: FAISS index to persist.
        build_time: Time taken to build embeddings (seconds).
        corpus_uuid: UUID of the corpus.

    Raises:
        RuntimeError: If persistence fails.
    """
    binary_data: dict[str, bytes] = {}

    if sentence_embeddings is not None and sentence_embeddings.size > 0:
        embeddings_bytes = pickle.dumps(sentence_embeddings)
        logger.info(f"Serialized embeddings: {len(embeddings_bytes) / 1024 / 1024:.1f}MB")
        binary_data["embeddings_bytes"] = embeddings_bytes

    # FAISS native disk I/O — pickling faiss.serialize_index() double-serializes
    # and hangs for 20+ minutes on large indices.
    if sentence_index is not None:
        import faiss

        logger.info("Serializing FAISS index using native disk I/O")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp_file:
            tmp_path = tmp_file.name

        try:
            faiss.write_index(sentence_index, tmp_path)
            with open(tmp_path, "rb") as f:
                index_bytes = f.read()
            logger.info(f"FAISS index serialized: {len(index_bytes) / 1024 / 1024:.1f}MB")
            binary_data["index_bytes"] = index_bytes
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    index.build_time_seconds = build_time
    memory_usage_mb = (
        (sentence_embeddings.nbytes / (1024 * 1024)) if sentence_embeddings is not None else 0.0
    )

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

    try:
        logger.info("Storing semantic index via versioned manager (GridFS)")
        await index.save(
            config=VersionConfig(),
            corpus_uuid=corpus_uuid,
            binary_data=binary_data,
        )
        logger.info("Semantic index saved successfully (metadata in MongoDB, blob in GridFS)")
    except Exception as e:
        logger.error(f"Failed to save semantic index: {e}")
        raise RuntimeError(
            f"Semantic index persistence failed. Embeddings size: {memory_usage_mb:.2f}MB. "
            f"Error: {e}"
        ) from e

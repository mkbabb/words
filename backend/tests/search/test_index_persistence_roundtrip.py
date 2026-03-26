"""Roundtrip persistence tests for trie/semantic/search indices."""

from __future__ import annotations

import gzip
import pickle
import tempfile

import faiss
import numpy as np
import pytest

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.index import SearchIndex
from floridify.search.semantic.index import SemanticIndex, _build_resource_id
from floridify.search.trie.index import TrieIndex


@pytest.mark.asyncio
async def test_trie_index_roundtrip_persistence(test_db):
    """Trie index should save and load with full content fidelity."""
    corpus = await Corpus.create(
        corpus_name="trie_roundtrip_corpus",
        vocabulary=["apple", "apply", "apt", "banana"],
        language=Language.ENGLISH,
    )
    await corpus.save()

    trie_index = await TrieIndex.create(corpus)
    await trie_index.save()

    loaded = await TrieIndex.get(corpus_uuid=corpus.corpus_uuid, config=VersionConfig(use_cache=False))
    assert loaded is not None
    assert loaded.trie_data == sorted(corpus.vocabulary)
    assert loaded.word_count == len(corpus.vocabulary)
    assert loaded.word_frequencies

    manager = get_version_manager()
    versions = await manager.list_versions(f"{corpus.corpus_uuid}:trie", ResourceType.TRIE)
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_semantic_index_roundtrip_with_binary_data(test_db):
    """Semantic index should persist binary payloads via external storage and reload them."""
    corpus = await Corpus.create(
        corpus_name="semantic_roundtrip_corpus",
        vocabulary=["alpha", "beta", "gamma"],
        language=Language.ENGLISH,
    )
    await corpus.save()

    semantic = await SemanticIndex.create(corpus=corpus, model_name="roundtrip-model")
    semantic.embedding_dimension = 4
    semantic.num_embeddings = len(corpus.vocabulary)

    embeddings = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )

    embeddings_bytes = pickle.dumps(embeddings)
    embeddings_compressed = gzip.compress(embeddings_bytes, compresslevel=1)

    faiss_index = faiss.IndexFlatL2(4)
    faiss_index.add(embeddings)
    with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as tmp:
        faiss.write_index(faiss_index, tmp.name)
        with open(tmp.name, "rb") as f:
            index_bytes = f.read()
    index_compressed = gzip.compress(index_bytes, compresslevel=1)

    binary_data = {
        "embeddings_compressed_bytes": embeddings_compressed,
        "embeddings_compressed": "gzip",
        "index_compressed_bytes": index_compressed,
        "index_compressed": "gzip",
    }

    await semantic.save(binary_data=binary_data)

    loaded = await SemanticIndex.get(
        corpus_uuid=corpus.corpus_uuid,
        model_name="roundtrip-model",
        config=VersionConfig(use_cache=False),
        corpus=corpus,
    )
    assert loaded is not None
    assert loaded.embedding_dimension == 4
    assert loaded.num_embeddings == 3
    assert loaded.binary_data is not None
    assert "embeddings_compressed_bytes" in loaded.binary_data

    restored = pickle.loads(gzip.decompress(loaded.binary_data["embeddings_compressed_bytes"]))
    np.testing.assert_array_almost_equal(restored, embeddings)

    manager = get_version_manager()
    resource_id = _build_resource_id(corpus.corpus_uuid, "roundtrip-model", corpus.vocabulary_hash)
    versions = await manager.list_versions(resource_id, ResourceType.SEMANTIC)
    assert len(versions) == 1
    assert versions[0].content_location is not None


@pytest.mark.asyncio
async def test_search_index_roundtrip_with_component_references(test_db):
    """Search index should persist and reload linked index references."""
    corpus = await Corpus.create(
        corpus_name="search_roundtrip_corpus",
        vocabulary=["delta", "epsilon", "zeta"],
        language=Language.ENGLISH,
    )
    await corpus.save()

    trie_index = await TrieIndex.create(corpus)
    await trie_index.save()
    saved_trie = await TrieIndex.get(corpus_uuid=corpus.corpus_uuid, config=VersionConfig(use_cache=False))
    assert saved_trie is not None

    search_index = await SearchIndex.create(corpus=corpus, semantic=False)
    search_index.trie_index_id = saved_trie.index_id
    await search_index.save(config=VersionConfig(use_cache=False))

    loaded = await SearchIndex.get(
        corpus_uuid=corpus.corpus_uuid,
        config=VersionConfig(use_cache=False),
    )
    assert loaded is not None
    assert loaded.vocabulary_hash == corpus.vocabulary_hash
    assert loaded.trie_index_id == saved_trie.index_id
    assert loaded.has_trie is True
    assert loaded.semantic_enabled is False

    manager = get_version_manager()
    versions = await manager.list_versions(f"{corpus.corpus_uuid}:search", ResourceType.SEARCH)
    assert len(versions) == 1

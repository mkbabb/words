"""Tests for Pydantic introspection utilities.

These tests verify that field extraction and metadata separation work correctly
for all Metadata classes in the system.
"""

import pytest
from pydantic import BaseModel

from floridify.caching.models import BaseVersionedData
from floridify.corpus.core import Corpus
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.utils.introspection import extract_metadata_params, get_subclass_fields


class TestGetSubclassFields:
    """Tests for get_subclass_fields function."""

    def test_semantic_index_fields(self):
        """SemanticIndex.Metadata should have 5 specific fields."""
        fields = get_subclass_fields(SemanticIndex.Metadata, BaseVersionedData)

        # Expected fields from SemanticIndex.Metadata
        assert "corpus_id" in fields
        assert "model_name" in fields
        assert "vocabulary_hash" in fields
        assert "embedding_dimension" in fields
        assert "index_type" in fields

        # Base fields should NOT be included
        assert "resource_id" not in fields
        assert "resource_type" not in fields
        assert "namespace" not in fields
        assert "version_info" not in fields
        assert "metadata" not in fields
        assert "tags" not in fields

    def test_corpus_fields(self):
        """Corpus.Metadata should have 6+ specific fields."""
        fields = get_subclass_fields(Corpus.Metadata, BaseVersionedData)

        # Expected fields from Corpus.Metadata
        assert "corpus_name" in fields
        assert "corpus_type" in fields
        assert "language" in fields
        assert "parent_corpus_id" in fields
        assert "child_corpus_ids" in fields
        assert "is_master" in fields

        # Base fields should NOT be included
        assert "resource_id" not in fields
        assert "metadata" not in fields

    def test_trie_index_fields(self):
        """TrieIndex.Metadata should have corpus_id and vocabulary_hash."""
        fields = get_subclass_fields(TrieIndex.Metadata, BaseVersionedData)

        assert "corpus_id" in fields
        assert "vocabulary_hash" in fields

        # Base fields should NOT be included
        assert "resource_type" not in fields

    def test_search_index_fields(self):
        """SearchIndex.Metadata should have 7 specific fields."""
        fields = get_subclass_fields(SearchIndex.Metadata, BaseVersionedData)

        assert "corpus_id" in fields
        assert "vocabulary_hash" in fields
        assert "has_trie" in fields
        assert "has_fuzzy" in fields
        assert "has_semantic" in fields
        assert "trie_index_id" in fields
        assert "semantic_index_id" in fields

    def test_auto_detect_base_class(self):
        """Should auto-detect BaseVersionedData if base_cls not provided."""
        # Without explicit base_cls
        fields1 = get_subclass_fields(SemanticIndex.Metadata)

        # With explicit base_cls
        fields2 = get_subclass_fields(SemanticIndex.Metadata, BaseVersionedData)

        # Should be identical
        assert fields1 == fields2

    def test_no_base_class_returns_all_fields(self):
        """Should return all fields if no base class in MRO."""

        class StandaloneModel(BaseModel):
            field1: str
            field2: int

        fields = get_subclass_fields(StandaloneModel)

        assert "field1" in fields
        assert "field2" in fields
        assert len(fields) == 2


class TestExtractMetadataParams:
    """Tests for extract_metadata_params function."""

    def test_semantic_index_extraction(self):
        """Should separate semantic index typed fields from generic metadata."""
        metadata = {
            "corpus_id": "123abc",
            "model_name": "bge-m3",
            "vocabulary_hash": "hash123",
            "embedding_dimension": 1024,
            "index_type": "IVFPQ",
            # Extra fields (not in Metadata)
            "num_embeddings": 50000,
            "custom_field": "value",
        }

        typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)

        # Typed fields
        assert typed == {
            "corpus_id": "123abc",
            "model_name": "bge-m3",
            "vocabulary_hash": "hash123",
            "embedding_dimension": 1024,
            "index_type": "IVFPQ",
        }

        # Generic metadata
        assert generic == {
            "num_embeddings": 50000,
            "custom_field": "value",
        }

    def test_corpus_extraction(self):
        """Should separate corpus typed fields from generic metadata."""
        metadata = {
            "corpus_name": "test-corpus",
            "corpus_type": "lexicon",
            "language": "english",
            "parent_corpus_id": None,
            "child_corpus_ids": [],
            "is_master": True,
            "vocabulary_size": 10000,  # This IS in Corpus.Metadata
            "vocabulary_hash": "hash123",  # This IS in Corpus.Metadata
            # Extra fields (not in Metadata)
            "build_time": 1.5,
            "custom_tag": "value",
        }

        typed, generic = extract_metadata_params(metadata, Corpus.Metadata)

        # Typed fields (all fields defined in Corpus.Metadata)
        assert "corpus_name" in typed
        assert "corpus_type" in typed
        assert "language" in typed
        assert "is_master" in typed
        assert "vocabulary_size" in typed  # Defined in Corpus.Metadata
        assert "vocabulary_hash" in typed  # Defined in Corpus.Metadata

        # Generic metadata (extra fields not in Corpus.Metadata)
        assert "build_time" in generic
        assert "custom_tag" in generic
        assert "vocabulary_size" not in generic  # Should be in typed, not generic

    def test_trie_index_extraction(self):
        """Should extract trie index fields."""
        metadata = {
            "corpus_id": "abc123",
            "vocabulary_hash": "hash456",
            "extra_field": "extra_value",
        }

        typed, generic = extract_metadata_params(metadata, TrieIndex.Metadata)

        assert typed == {
            "corpus_id": "abc123",
            "vocabulary_hash": "hash456",
        }
        assert generic == {"extra_field": "extra_value"}

    def test_search_index_extraction(self):
        """Should extract search index fields."""
        metadata = {
            "corpus_id": "abc",
            "vocabulary_hash": "hash",
            "has_trie": True,
            "has_fuzzy": True,
            "has_semantic": False,
            "trie_index_id": "trie123",
            "semantic_index_id": None,
            "custom_metric": 0.95,
        }

        typed, generic = extract_metadata_params(metadata, SearchIndex.Metadata)

        assert typed["has_trie"] is True
        assert typed["has_semantic"] is False
        assert "custom_metric" in generic

    def test_empty_metadata(self):
        """Should handle empty metadata dict."""
        metadata = {}

        typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)

        assert typed == {}
        assert generic == {}

    def test_only_generic_metadata(self):
        """Should handle metadata with no typed fields."""
        metadata = {
            "custom1": "value1",
            "custom2": "value2",
        }

        typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)

        assert typed == {}
        assert generic == metadata

    def test_only_typed_fields(self):
        """Should handle metadata with only typed fields."""
        metadata = {
            "corpus_id": "123",
            "model_name": "model",
        }

        typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)

        assert "corpus_id" in typed
        assert "model_name" in typed
        assert generic == {}

    def test_preserves_values(self):
        """Should preserve exact values (no modification)."""
        metadata = {
            "corpus_id": None,  # None value
            "model_name": "",  # Empty string
            "embedding_dimension": 0,  # Zero value
        }

        typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)

        assert typed["corpus_id"] is None
        assert typed["model_name"] == ""
        assert typed["embedding_dimension"] == 0

"""Test model registration and versioning functionality."""

import pytest

from floridify.caching.models import ResourceType
from floridify.models.registry import initialize_model_registry
from floridify.models.registry import get_model_class
from floridify.caching.models import ResourceType


class TestModelRegistration:
    """Test model registration system."""

    def test_all_models_registered(self):
        """Test that all expected models are registered."""
        # Ensure initialization
        initialize_model_registry()

        # Check all resource types have registered models
        expected_types = [
            ResourceType.CORPUS,
            ResourceType.DICTIONARY,
            ResourceType.LANGUAGE,
            ResourceType.LITERATURE,
            ResourceType.SEARCH,
            ResourceType.TRIE,
            ResourceType.SEMANTIC,
        ]

        for resource_type in expected_types:
            assert resource_type in MODEL_REGISTRY, f"Missing registration for {resource_type}"

            # Also verify through get_model_class
            model_class = get_model_class(resource_type)
            assert model_class is not None
            # Check model fields (not instance attributes)
            assert "resource_id" in model_class.model_fields
            assert "resource_type" in model_class.model_fields

    def test_model_class_retrieval(self):
        """Test retrieving model classes by resource type."""
        from floridify.corpus.core import Corpus
        from floridify.providers.dictionary.models import DictionaryProviderEntry
        from floridify.providers.language.models import LanguageEntry
        from floridify.providers.literature.models import LiteratureEntry
        from floridify.search.models import SearchIndex, TrieIndex
        from floridify.search.semantic.models import SemanticIndex

        # Test each mapping
        mappings = {
            ResourceType.CORPUS: Corpus.Metadata,
            ResourceType.DICTIONARY: DictionaryProviderEntry.Metadata,
            ResourceType.LANGUAGE: LanguageEntry.Metadata,
            ResourceType.LITERATURE: LiteratureEntry.Metadata,
            ResourceType.SEARCH: SearchIndex.Metadata,
            ResourceType.TRIE: TrieIndex.Metadata,
            ResourceType.SEMANTIC: SemanticIndex.Metadata,
        }

        for resource_type, expected_class in mappings.items():
            actual_class = get_model_class(resource_type)
            assert actual_class == expected_class, f"Wrong class for {resource_type}"

    def test_unregistered_model_error(self):
        """Test that unregistered resource types raise appropriate errors."""
        # Create a fake resource type that's not registered
        # This would require modifying the ResourceType enum, so we'll test differently

        # Clear a registration temporarily
        original = MODEL_REGISTRY.get(ResourceType.CORPUS)
        try:
            if ResourceType.CORPUS in MODEL_REGISTRY:
                del MODEL_REGISTRY[ResourceType.CORPUS]

            with pytest.raises(ValueError) as exc_info:
                get_model_class(ResourceType.CORPUS)

            assert "No model registered" in str(exc_info.value)
        finally:
            # Restore registration
            if original:
                MODEL_REGISTRY[ResourceType.CORPUS] = original

    def test_model_inheritance(self):
        """Test that all registered models inherit from BaseVersionedData."""
        from floridify.caching.models import BaseVersionedData

        for resource_type, model_class in MODEL_REGISTRY.items():
            assert issubclass(model_class, BaseVersionedData), (
                f"Model for {resource_type} doesn't inherit from BaseVersionedData"
            )

    def test_model_fields(self):
        """Test that all registered models have required fields."""
        required_fields = [
            "resource_id",
            "resource_type",
            "version_info",
            "content_location",
        ]

        for resource_type, model_class in MODEL_REGISTRY.items():
            # Get model fields
            fields = model_class.model_fields

            for field_name in required_fields:
                assert field_name in fields, (
                    f"Model for {resource_type} missing field: {field_name}"
                )

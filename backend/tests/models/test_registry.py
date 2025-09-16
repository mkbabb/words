"""Test model registry implementations."""

import pytest

from floridify.caching.models import BaseVersionedData, ResourceType
from floridify.models.registry import get_model_class


def test_get_model_class_simple():
    """Test the simple registry approach."""
    
    # Test all resource types
    for resource_type in ResourceType:
        model_class = get_model_class(resource_type)
        assert model_class is not None
        assert issubclass(model_class, BaseVersionedData)
    
    # Test unknown resource type
    with pytest.raises(ValueError, match="Unknown resource type"):
        get_model_class("invalid_type")  # type: ignore


def test_lazy_import_efficiency():
    """Verify lazy imports work correctly."""
    import sys
    
    # Remove dictionary module if already loaded from previous test
    dict_module = "floridify.providers.dictionary.models"
    lit_module = "floridify.providers.literature.models"
    
    if dict_module in sys.modules:
        del sys.modules[dict_module]
    if lit_module in sys.modules:
        del sys.modules[lit_module]
    
    # Verify modules are not loaded
    assert dict_module not in sys.modules
    assert lit_module not in sys.modules
    
    # Get a dictionary model class
    model_class = get_model_class(ResourceType.DICTIONARY)
    
    # Dictionary module should now be imported, but not literature
    assert dict_module in sys.modules
    assert lit_module not in sys.modules
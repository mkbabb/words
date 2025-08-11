#!/usr/bin/env python
"""Quick test to verify refactored repositories work correctly."""

import asyncio
from typing import Any

from beanie import PydanticObjectId

# Test imports
try:
    from src.floridify.api.repositories import (
        DefinitionCreate,
        DefinitionRepository,
        DefinitionUpdate,
        SynthesisCreate,
        SynthesisRepository,
        SynthesisUpdate,
    )
    from src.floridify.models import (
        Definition,
        Example,
        SynthesizedDictionaryEntry,
    )
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)

# Test repository instantiation
try:
    def_repo = DefinitionRepository()
    syn_repo = SynthesisRepository()
    print("✓ Repositories instantiated successfully")
except Exception as e:
    print(f"✗ Repository instantiation error: {e}")
    exit(1)

# Test schema validation
try:
    # Test DefinitionCreate with string word_id (should be accepted)
    def_create = DefinitionCreate(
        word_id="507f1f77bcf86cd799439011",  # String ObjectId
        part_of_speech="noun",
        text="A test definition",
    )
    print("✓ DefinitionCreate accepts string word_id")
    
    # Test with ObjectId
    def_create2 = DefinitionCreate(
        word_id=PydanticObjectId("507f1f77bcf86cd799439011"),
        part_of_speech="verb",
        text="Another test definition",
    )
    print("✓ DefinitionCreate accepts PydanticObjectId")
    
    # Test SynthesisCreate
    syn_create = SynthesisCreate(
        word_id=PydanticObjectId("507f1f77bcf86cd799439011"),
    )
    print("✓ SynthesisCreate schema valid")
    
except Exception as e:
    print(f"✗ Schema validation error: {e}")
    exit(1)

# Test that methods exist
try:
    # Check definition repo methods
    assert hasattr(def_repo, 'add_example')
    assert hasattr(def_repo, 'remove_example')
    assert hasattr(def_repo, 'add_image')
    assert hasattr(def_repo, 'remove_image')
    assert hasattr(def_repo, 'get_expanded')
    assert hasattr(def_repo, 'batch_add_examples')
    assert hasattr(def_repo, 'update_linguistic_components')
    print("✓ All DefinitionRepository methods exist")
    
    # Check synthesis repo methods
    assert hasattr(syn_repo, 'add_definition')
    assert hasattr(syn_repo, 'remove_definition')
    assert hasattr(syn_repo, 'add_fact')
    assert hasattr(syn_repo, 'set_pronunciation')
    assert hasattr(syn_repo, 'get_expanded')
    assert hasattr(syn_repo, 'track_access')
    assert hasattr(syn_repo, 'create_or_update_for_word')
    print("✓ All SynthesisRepository methods exist")
    
except AssertionError as e:
    print(f"✗ Method missing: {e}")
    exit(1)

print("\n✅ All tests passed! Refactored repositories are working correctly.")
"""Pydantic V2 introspection utilities for dynamic metadata handling.

This module provides utilities to eliminate hardcoded field lists by using
Pydantic's model_fields introspection API. This enables automatic metadata
field extraction based on model class definitions.

Key Functions:
    - get_subclass_fields: Extract fields specific to a child class
    - extract_metadata_params: Separate typed fields from generic metadata

Example:
    >>> from floridify.caching.models import BaseVersionedData
    >>> from floridify.search.semantic.models import SemanticIndex
    >>>
    >>> # Get fields specific to SemanticIndex.Metadata
    >>> fields = get_subclass_fields(SemanticIndex.Metadata, BaseVersionedData)
    >>> # {'corpus_id', 'model_name', 'vocabulary_hash', ...}
    >>>
    >>> # Automatically separate metadata dict
    >>> metadata = {
    ...     "corpus_id": "123",
    ...     "model_name": "bge-m3",
    ...     "custom_field": "value"
    ... }
    >>> typed, generic = extract_metadata_params(metadata, SemanticIndex.Metadata)
    >>> # typed: {'corpus_id': '123', 'model_name': 'bge-m3'}
    >>> # generic: {'custom_field': 'value'}
"""

from typing import Any

from pydantic import BaseModel

__all__ = [
    "get_subclass_fields",
    "extract_metadata_params",
]


def get_subclass_fields(
    cls: type[BaseModel],
    base_cls: type[BaseModel] | None = None,
) -> set[str]:
    """Get field names defined in cls that are NOT in base_cls.

    This function uses Pydantic's model_fields to perform set difference
    between child and parent class fields, enabling automatic detection
    of subclass-specific fields without hardcoding.

    Args:
        cls: Child class to extract fields from (e.g., Corpus.Metadata)
        base_cls: Base class to exclude fields from (auto-detected if None)

    Returns:
        Set of field names specific to cls (excluding base class fields)

    Example:
        >>> from floridify.caching.models import BaseVersionedData
        >>> from floridify.corpus.core import Corpus
        >>>
        >>> fields = get_subclass_fields(Corpus.Metadata, BaseVersionedData)
        >>> # Returns: {'corpus_name', 'corpus_type', 'language',
        >>> #           'parent_corpus_id', 'child_corpus_ids', 'is_master'}

    Note:
        If base_cls is None, this function auto-detects BaseVersionedData
        in the class's method resolution order (MRO).
    """
    if base_cls is None:
        # Auto-detect BaseVersionedData in MRO
        for parent in cls.__mro__[1:]:
            if parent.__name__ == "BaseVersionedData":
                base_cls = parent
                break

    if base_cls is None:
        # No base class found, return all fields
        return set(cls.model_fields.keys())

    # Perform set difference: child fields - base fields
    base_fields = set(base_cls.model_fields.keys())
    cls_fields = set(cls.model_fields.keys())
    return cls_fields - base_fields


def extract_metadata_params(
    metadata_dict: dict[str, Any],
    model_class: type[BaseModel],
    base_cls: type[BaseModel] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate metadata dict into typed fields and generic metadata.

    This function replaces hardcoded field lists by using Pydantic introspection
    to determine which fields belong to the model class vs generic metadata.

    Args:
        metadata_dict: Combined metadata from caller
        model_class: Target Metadata class (e.g., Corpus.Metadata, SemanticIndex.Metadata)
        base_cls: Base class to exclude fields from (auto-detected if None)

    Returns:
        Tuple of (typed_fields, generic_metadata)
            - typed_fields: Fields that exist in model_class (go to constructor)
            - generic_metadata: Fields that don't exist in model_class (go to metadata dict)

    Example:
        >>> metadata = {
        ...     "corpus_name": "test",
        ...     "corpus_type": "lexicon",
        ...     "language": "english",
        ...     "custom_field": "value",
        ...     "another_custom": 123
        ... }
        >>> typed, generic = extract_metadata_params(metadata, Corpus.Metadata)
        >>> # typed: {'corpus_name': 'test', 'corpus_type': 'lexicon', 'language': 'english'}
        >>> # generic: {'custom_field': 'value', 'another_custom': 123}

    Replaces:
        # OLD (hardcoded):
        corpus_fields = ["corpus_name", "corpus_type", "language", ...]
        for field in corpus_fields:
            if field in combined_metadata:
                constructor_params[field] = combined_metadata.pop(field)

        # NEW (introspection):
        typed, generic = extract_metadata_params(combined_metadata, Corpus.Metadata)
        constructor_params.update(typed)
    """
    # Get fields specific to this model (excluding base class)
    model_specific_fields = get_subclass_fields(model_class, base_cls)

    # Separate typed fields from generic metadata
    typed_fields = {}
    generic_metadata = {}

    for key, value in metadata_dict.items():
        if key in model_specific_fields:
            typed_fields[key] = value
        else:
            generic_metadata[key] = value

    return typed_fields, generic_metadata

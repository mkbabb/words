"""Versioned model infrastructure.

This module acts as a bridge between the models and caching systems,
providing a registry pattern to avoid circular imports.
"""

from __future__ import annotations

from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    CompressionType,
    QuantizationType,
    ResourceType,
    VersionConfig,
    VersionInfo,
)

# Registry for model classes to avoid circular imports
_MODEL_REGISTRY: dict[ResourceType, type[BaseVersionedData]] = {}


def register_model(resource_type: ResourceType):
    """Decorator to register a model class with its resource type."""

    def decorator(cls: type[BaseVersionedData]):
        _MODEL_REGISTRY[resource_type] = cls
        return cls

    return decorator


def get_model_class(resource_type: ResourceType) -> type[BaseVersionedData]:
    """Get the model class for a given resource type.

    All model classes should be registered using the @register_model decorator.
    """
    if resource_type not in _MODEL_REGISTRY:
        raise ValueError(
            f"No model registered for resource type: {resource_type}. "
            f"Ensure the model class uses @register_model decorator."
        )
    return _MODEL_REGISTRY[resource_type]

"""Ultra-simple model registry - KISS approach.

Maps ResourceType directly to model classes without decorators or auto-discovery.
This is the simplest, most maintainable approach.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..caching.models import ResourceType
from ..corpus.core import Corpus
from ..providers.dictionary.models import DictionaryProviderEntry
from ..providers.language.models import LanguageEntry
from ..providers.literature.models import LiteratureEntry
from ..search.models import SearchIndex, TrieIndex
from ..search.semantic.models import SemanticIndex

if TYPE_CHECKING:
    from ..caching.models import BaseVersionedData

# Pre-built registry mapping - all imports at module level
_MODEL_CLASS_REGISTRY: dict[ResourceType, type[BaseVersionedData]] = {
    ResourceType.CORPUS: Corpus.Metadata,
    ResourceType.DICTIONARY: DictionaryProviderEntry.Metadata,
    ResourceType.LANGUAGE: LanguageEntry.Metadata,
    ResourceType.LITERATURE: LiteratureEntry.Metadata,
    ResourceType.SEARCH: SearchIndex.Metadata,
    ResourceType.TRIE: TrieIndex.Metadata,
    ResourceType.SEMANTIC: SemanticIndex.Metadata,
}


def get_model_class(resource_type: ResourceType) -> type[BaseVersionedData]:
    """Get model class for a resource type.

    This approach:
    1. Uses explicit mapping dictionary with all imports at module level
    2. Eliminates decorators and auto-discovery complexity
    3. Makes the mapping explicit and easy to understand
    4. Follows KISS - just a simple dictionary lookup
    """
    if resource_type not in _MODEL_CLASS_REGISTRY:
        raise ValueError(f"Unknown resource type: {resource_type}")

    return _MODEL_CLASS_REGISTRY[resource_type]

"""Ultra-simple model registry - KISS approach.

Maps ResourceType directly to model classes without decorators or auto-discovery.
This is the simplest, most maintainable approach.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..caching.models import ResourceType

if TYPE_CHECKING:
    from ..caching.models import BaseVersionedData


def get_model_class(resource_type: ResourceType) -> type[BaseVersionedData]:
    """Get model class for a resource type using lazy imports.

    This approach:
    1. Avoids circular imports by importing only when needed
    2. Eliminates decorators and auto-discovery complexity
    3. Makes the mapping explicit and easy to understand
    4. Follows KISS - just a simple switch statement
    """
    # Lazy imports to avoid circular dependencies
    if resource_type == ResourceType.CORPUS:
        from ..corpus.core import Corpus

        return Corpus.Metadata

    if resource_type == ResourceType.DICTIONARY:
        from ..providers.dictionary.models import DictionaryProviderEntry

        return DictionaryProviderEntry.Metadata

    if resource_type == ResourceType.LANGUAGE:
        from ..providers.language.models import LanguageEntry

        return LanguageEntry.Metadata

    if resource_type == ResourceType.LITERATURE:
        from ..providers.literature.models import LiteratureEntry

        return LiteratureEntry.Metadata

    if resource_type == ResourceType.SEARCH:
        from ..search.models import SearchIndex

        return SearchIndex.Metadata

    if resource_type == ResourceType.TRIE:
        from ..search.models import TrieIndex

        return TrieIndex.Metadata

    if resource_type == ResourceType.SEMANTIC:
        from ..search.semantic.models import SemanticIndex

        return SemanticIndex.Metadata

    raise ValueError(f"Unknown resource type: {resource_type}")

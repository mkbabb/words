"""Literature metadata models for versioned storage.

This module contains metadata models for literature that integrate with the
versioned data system for proper storage and retrieval.
"""


class LiteratureEntryMetadata(BaseVersionedData):
    """Literature work metadata with external content storage."""

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.LITERATURE)
        data.setdefault("namespace", CacheNamespace.LITERATURE)
        super().__init__(**data)

"""Language corpus models."""

from __future__ import annotations

from beanie import Document, PydanticObjectId
from pydantic import Field

from ...caching.models import BaseVersionedData, ResourceType
from ...models.base import Language
from ...models.versioned import register_model
from ...providers.language import LanguageProvider
from ..models import CorpusType


@register_model(ResourceType.CORPUS)
class LanguageCorpusMetadata(BaseVersionedData, Document):
    """MongoDB metadata for language corpus with versioning."""
    
    corpus_name: str
    corpus_type: CorpusType = CorpusType.LANGUAGE
    language: Language
    providers: list[LanguageProvider] = Field(default_factory=list)
    
    # Tree structure
    parent_id: PydanticObjectId | None = None
    child_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False
    
    # Statistics
    total_entries: int = 0
    unique_entries: int = 0
    provider_counts: dict[str, int] = Field(default_factory=dict)
    
    class Settings:
        """Beanie document settings."""
        
        name = "language_corpora"
        indexes = [
            "corpus_name",
            "language",
            "providers",
            "is_latest",
        ]
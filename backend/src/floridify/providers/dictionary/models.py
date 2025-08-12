"""Dictionary-specific models."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel

from ...models.definition import Definition, Etymology, Language, Pronunciation
from ...models.provider import DictionaryProvider
from ..models import VersionedData


class DictionaryProviderData(BaseModel):
    """Clean dictionary provider data model."""
    
    provider: DictionaryProvider
    definitions: list[Definition] = []
    pronunciation: Pronunciation | None = None
    etymology: Etymology | None = None
    language: Language = Language.ENGLISH
    
    # No raw_data - only clean, processed data
    # No definition_ids - embed directly for simplicity
    
    @property
    def has_content(self) -> bool:
        """Check if data has meaningful content."""
        return bool(self.definitions)


class VersionedDictionaryData(VersionedData):
    """Versioned dictionary data with word reference."""
    
    word_id: PydanticObjectId
    word_text: str
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "word")
        data.setdefault("provider_type", "dictionary")
        super().__init__(**data)
        
    class Settings:
        name = "versioned_dictionary_data"
        indexes = [
            "word_id",
            "word_text",
            [("word_id", 1), ("provider_name", 1), ("is_latest", -1)],
        ]
"""Repository for Definition model operations."""

from typing import Any

from beanie import PydanticObjectId
from beanie.operators import In
from pydantic import BaseModel, Field

from ...models import (
    Collocation,
    Definition,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
)
from ..core.base import BaseRepository


class DefinitionCreate(BaseModel):
    """Schema for creating a definition."""

    word_id: str
    part_of_speech: str
    text: str = Field(..., min_length=1)
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None
    word_forms: list[WordForm] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    language_register: str | None = None
    domain: str | None = None
    region: str | None = None
    transitivity: str | None = None
    cefr_level: str | None = None
    frequency_band: int | None = Field(None, ge=1, le=5)


class DefinitionUpdate(BaseModel):
    """Schema for updating a definition."""

    part_of_speech: str | None = None
    text: str | None = Field(None, min_length=1)
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None
    word_forms: list[WordForm] | None = None
    synonyms: list[str] | None = None
    antonyms: list[str] | None = None
    language_register: str | None = None
    domain: str | None = None
    region: str | None = None
    transitivity: str | None = None
    cefr_level: str | None = None
    frequency_band: int | None = Field(None, ge=1, le=5)
    usage_notes: list[UsageNote] | None = None
    grammar_patterns: list[GrammarPattern] | None = None
    collocations: list[Collocation] | None = None
    add_image_id: str | None = Field(None, description="Image ID to add to the definition")
    remove_image_id: str | None = Field(None, description="Image ID to remove from the definition")


class DefinitionFilter(BaseModel):
    """Filter parameters for definition queries."""

    word_id: str | None = None
    part_of_speech: str | None = None
    language_register: str | None = None
    domain: str | None = None
    cefr_level: str | None = None
    frequency_band: int | None = None
    has_examples: bool | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.word_id:
            query["word_id"] = self.word_id

        if self.part_of_speech:
            query["part_of_speech"] = self.part_of_speech

        if self.language_register:
            query["language_register"] = self.language_register

        if self.domain:
            query["domain"] = self.domain

        if self.cefr_level:
            query["cefr_level"] = self.cefr_level

        if self.frequency_band is not None:
            query["frequency_band"] = self.frequency_band

        if self.has_examples is not None:
            if self.has_examples:
                query["example_ids"] = {"$ne": []}
            else:
                query["example_ids"] = []

        return query


class DefinitionRepository(BaseRepository[Definition, DefinitionCreate, DefinitionUpdate]):
    """Repository for Definition CRUD operations."""

    def __init__(self) -> None:
        super().__init__(Definition)

    async def find_by_word(
        self, word_id: str, part_of_speech: str | None = None
    ) -> list[Definition]:
        """Find definitions for a word."""
        query = {"word_id": word_id}
        if part_of_speech:
            query["part_of_speech"] = part_of_speech

        return await Definition.find(query).to_list()

    async def find_by_meaning_cluster(self, cluster_id: str) -> list[Definition]:
        """Find definitions in the same meaning cluster."""
        return await Definition.find({"meaning_cluster.cluster_id": cluster_id}).to_list()

    async def update_components(
        self, id: PydanticObjectId, components: dict[str, Any]
    ) -> Definition:
        """Update specific components of a definition."""
        definition = await self.get(id, raise_on_missing=True)
        assert definition is not None

        # Update individual components
        if "word_forms" in components:
            definition.word_forms = [WordForm(**wf) for wf in components["word_forms"]]

        if "grammar_patterns" in components:
            definition.grammar_patterns = [
                GrammarPattern(**gp) for gp in components["grammar_patterns"]
            ]

        if "collocations" in components:
            definition.collocations = [Collocation(**col) for col in components["collocations"]]

        if "usage_notes" in components:
            definition.usage_notes = [UsageNote(**un) for un in components["usage_notes"]]

        # Update scalar fields
        for field in [
            "synonyms",
            "antonyms",
            "cefr_level",
            "frequency_band",
            "language_register",
            "domain",
            "region",
        ]:
            if field in components:
                setattr(definition, field, components[field])

        definition.version += 1
        await definition.save()
        return definition

    async def update(
        self, id: PydanticObjectId, data: DefinitionUpdate, version: int | None = None
    ) -> Definition:
        """Update a definition with support for image operations."""
        # Get the definition
        definition = await self.get(id, raise_on_missing=True)
        assert definition is not None
        
        # Check version for optimistic locking
        if version is not None and hasattr(definition, "version"):
            if definition.version != version:
                from ...core.exceptions import VersionConflictException
                raise VersionConflictException(
                    expected=version,
                    actual=definition.version,
                    resource="Definition",
                )
        
        # Handle special image operations
        update_data = data.model_dump(exclude_unset=True)
        
        # Add image
        if "add_image_id" in update_data:
            image_id = update_data.pop("add_image_id")
            if image_id and image_id not in definition.image_ids:
                definition.image_ids.append(image_id)
        
        # Remove image
        if "remove_image_id" in update_data:
            image_id = update_data.pop("remove_image_id")
            if image_id and image_id in definition.image_ids:
                definition.image_ids.remove(image_id)
        
        # Update other fields
        for field, value in update_data.items():
            setattr(definition, field, value)
        
        # Increment version
        if hasattr(definition, "version"):
            definition.version += 1
        
        await definition.save()
        return definition

    async def _cascade_delete(self, definition: Definition) -> None:
        """Delete related documents when deleting a definition."""
        from ...models import Example

        # Delete all examples for this definition
        if definition.example_ids:
            await Example.find(In(Example.id, definition.example_ids)).delete()

    async def get_with_examples(self, id: PydanticObjectId) -> dict[str, Any]:
        """Get definition with expanded examples."""
        from ...models import Example

        definition = await self.get(id, raise_on_missing=True)
        assert definition is not None
        definition_dict = definition.model_dump()

        # Fetch and include examples
        if definition.example_ids:
            examples = await Example.find(In(Example.id, definition.example_ids)).to_list()
            definition_dict["examples"] = [ex.model_dump() for ex in examples]
        else:
            definition_dict["examples"] = []

        return definition_dict

    async def get_many_with_examples(self, definitions: list[Definition]) -> list[dict[str, Any]]:
        """Get multiple definitions with expanded examples efficiently."""
        from ...models import Example

        # Collect all example IDs
        all_example_ids = []
        for definition in definitions:
            if definition.example_ids:
                all_example_ids.extend(definition.example_ids)

        # Fetch all examples in one query
        examples_map = {}
        if all_example_ids:
            examples = await Example.find(In(Example.id, all_example_ids)).to_list()
            examples_map = {str(ex.id): ex for ex in examples}

        # Build results with examples
        results = []
        for definition in definitions:
            def_dict = definition.model_dump()
            if definition.example_ids:
                def_dict["examples"] = [
                    examples_map[str(ex_id)].model_dump()
                    for ex_id in definition.example_ids
                    if str(ex_id) in examples_map
                ]
            else:
                def_dict["examples"] = []
            results.append(def_dict)

        return results

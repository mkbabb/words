"""Repository for Definition model operations - isomorphic to the Definition model."""

from typing import Any, Literal

from beanie import PydanticObjectId
from beanie.operators import In
from pydantic import BaseModel, Field

from ...models import (
    Collocation,
    Definition,
    Example,
    GrammarPattern,
    ImageMedia,
    MeaningCluster,
    UsageNote,
    WordForm,
)
from ..core.base import BaseRepository


class DefinitionCreate(BaseModel):
    """Schema for creating a definition - mirrors the Definition model."""

    word_id: PydanticObjectId | str  # Accept both ObjectId and string
    part_of_speech: str
    text: str = Field(..., min_length=1)
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None
    word_forms: list[WordForm] = Field(default_factory=list)

    # Examples and relationships
    example_ids: list[PydanticObjectId] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)

    # Usage and context
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None = None
    domain: str | None = None
    region: str | None = None
    usage_notes: list[UsageNote] = Field(default_factory=list)

    # Grammar and patterns
    grammar_patterns: list[GrammarPattern] = Field(default_factory=list)
    collocations: list[Collocation] = Field(default_factory=list)
    transitivity: Literal["transitive", "intransitive", "both"] | None = None

    # Educational metadata
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    frequency_band: int | None = Field(None, ge=1, le=5)

    # Media and provenance
    image_ids: list[PydanticObjectId] = Field(default_factory=list)
    provider_data_id: PydanticObjectId | None = None


class DefinitionUpdate(BaseModel):
    """Schema for updating a definition - partial updates allowed."""

    part_of_speech: str | None = None
    text: str | None = Field(None, min_length=1)
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None
    word_forms: list[WordForm] | None = None

    # Examples and relationships
    example_ids: list[PydanticObjectId] | None = None
    synonyms: list[str] | None = None
    antonyms: list[str] | None = None

    # Usage and context
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None = None
    domain: str | None = None
    region: str | None = None
    usage_notes: list[UsageNote] | None = None

    # Grammar and patterns
    grammar_patterns: list[GrammarPattern] | None = None
    collocations: list[Collocation] | None = None
    transitivity: Literal["transitive", "intransitive", "both"] | None = None

    # Educational metadata
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    frequency_band: int | None = Field(None, ge=1, le=5)

    # Media and provenance
    image_ids: list[PydanticObjectId] | None = None
    provider_data_id: PydanticObjectId | None = None


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
    """Repository for Definition CRUD operations - isomorphic to Definition model."""

    def __init__(self) -> None:
        super().__init__(Definition)

    # Core queries matching Definition model relationships
    async def find_by_word(
        self,
        word_id: PydanticObjectId | str,
        part_of_speech: str | None = None,
    ) -> list[Definition]:
        """Find definitions for a word."""
        word_oid = PydanticObjectId(word_id) if isinstance(word_id, str) else word_id
        query = {"word_id": word_oid}
        if part_of_speech:
            query["part_of_speech"] = part_of_speech
        return await Definition.find(query).to_list()

    async def find_by_meaning_cluster(self, cluster_id: str) -> list[Definition]:
        """Find definitions in the same meaning cluster."""
        return await Definition.find({"meaning_cluster.cluster_id": cluster_id}).to_list()

    async def find_by_provider(self, provider_data_id: PydanticObjectId | str) -> list[Definition]:
        """Find definitions from a specific provider."""
        provider_oid = (
            PydanticObjectId(provider_data_id)
            if isinstance(provider_data_id, str)
            else provider_data_id
        )
        return await Definition.find({"provider_data_id": provider_oid}).to_list()

    # Generic CRUD for related entities
    async def add_example(
        self,
        definition_id: PydanticObjectId,
        example_text: str,
        example_type: Literal["generated", "literature"] = "generated",
        **kwargs: Any,
    ) -> Example:
        """Add an example to a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        example = Example(
            definition_id=definition_id,
            text=example_text,
            type=example_type,
            **kwargs,
        )
        await example.save()

        if example.id and example.id not in definition.example_ids:
            definition.example_ids.append(example.id)
            definition.version += 1
            await definition.save()

        return example

    async def remove_example(
        self,
        definition_id: PydanticObjectId,
        example_id: PydanticObjectId,
    ) -> bool:
        """Remove an example from a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        if example_id in definition.example_ids:
            definition.example_ids.remove(example_id)
            definition.version += 1
            await definition.save()

            # Delete the example
            example = await Example.get(example_id)
            if example:
                await example.delete()
            return True
        return False

    async def add_image(
        self,
        definition_id: PydanticObjectId,
        image_id: PydanticObjectId,
    ) -> Definition:
        """Add an image to a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        if image_id not in definition.image_ids:
            definition.image_ids.append(image_id)
            definition.version += 1
            await definition.save()

        return definition

    async def remove_image(
        self,
        definition_id: PydanticObjectId,
        image_id: PydanticObjectId,
    ) -> Definition:
        """Remove an image from a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        if image_id in definition.image_ids:
            definition.image_ids.remove(image_id)
            definition.version += 1
            await definition.save()

        return definition

    # Unified expansion method
    async def get_expanded(
        self,
        definition_id: PydanticObjectId | None = None,
        definitions: list[Definition] | None = None,
        expand: set[str] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Get definition(s) with expanded related entities.

        Args:
            definition_id: Single definition to expand
            definitions: Multiple definitions to expand
            expand: Set of fields to expand ('examples', 'images')

        Returns:
            Expanded definition(s) as dict(s)

        """
        if definition_id:
            definition = await self.get(definition_id, raise_on_missing=True)
            assert definition is not None
            definitions = [definition]
        elif not definitions:
            raise ValueError("Either definition_id or definitions must be provided")

        # Collect all IDs for batch fetching
        all_example_ids = set()
        all_image_ids = set()

        for definition in definitions:
            if expand and "examples" in expand:
                all_example_ids.update(definition.example_ids)
            if expand and "images" in expand:
                all_image_ids.update(definition.image_ids)

        # Batch fetch related entities
        examples_map = {}
        images_map = {}

        if all_example_ids:
            examples = await Example.find(In(Example.id, list(all_example_ids))).to_list()
            examples_map = {str(ex.id): ex.model_dump() for ex in examples}

        if all_image_ids:
            images = await ImageMedia.find(In(ImageMedia.id, list(all_image_ids))).to_list()
            images_map = {str(img.id): img.model_dump() for img in images}

        # Build results
        results = []
        for definition in definitions:
            def_dict = definition.model_dump()

            if expand:
                if "examples" in expand:
                    def_dict["examples"] = [
                        examples_map[str(ex_id)]
                        for ex_id in definition.example_ids
                        if str(ex_id) in examples_map
                    ]

                if "images" in expand:
                    def_dict["images"] = [
                        images_map[str(img_id)]
                        for img_id in definition.image_ids
                        if str(img_id) in images_map
                    ]

            results.append(def_dict)

        return results[0] if definition_id else results

    async def _cascade_delete(self, definition: Definition) -> None:
        """Delete related documents when deleting a definition."""
        # Delete all examples for this definition
        if definition.example_ids:
            await Example.find(In(Example.id, definition.example_ids)).delete()

        # Note: Images are not deleted as they may be shared across definitions

    # Batch operations for efficiency
    async def batch_add_examples(
        self,
        definition_id: PydanticObjectId,
        example_texts: list[str],
        example_type: Literal["generated", "literature"] = "generated",
    ) -> list[Example]:
        """Add multiple examples to a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        examples = [
            Example(
                definition_id=definition_id,
                text=text,
                type=example_type,
            )
            for text in example_texts
        ]

        await Example.insert_many(examples)

        new_example_ids = [ex.id for ex in examples if ex.id]
        definition.example_ids.extend(new_example_ids)
        definition.version += 1
        await definition.save()

        return examples

    async def update_linguistic_components(
        self,
        definition_id: PydanticObjectId,
        word_forms: list[WordForm] | None = None,
        grammar_patterns: list[GrammarPattern] | None = None,
        collocations: list[Collocation] | None = None,
        usage_notes: list[UsageNote] | None = None,
    ) -> Definition:
        """Update linguistic components of a definition."""
        definition = await self.get(definition_id, raise_on_missing=True)
        assert definition is not None

        if word_forms is not None:
            definition.word_forms = word_forms
        if grammar_patterns is not None:
            definition.grammar_patterns = grammar_patterns
        if collocations is not None:
            definition.collocations = collocations
        if usage_notes is not None:
            definition.usage_notes = usage_notes

        definition.version += 1
        await definition.save()
        return definition

"""Repository for DictionaryEntry - collection of definitions."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from beanie.operators import In
from pydantic import BaseModel, Field

from ...models.base import Etymology, ImageMedia, ModelInfo
from ...models.dictionary import (
    Definition,
    DictionaryEntry,
    Fact,
    Pronunciation,
)
from ..core.base import BaseRepository


class SynthesisCreate(BaseModel):
    """Schema for creating a synthesized entry - mirrors DictionaryEntry model."""

    word_id: PydanticObjectId
    pronunciation_id: PydanticObjectId | None = None
    definition_ids: list[PydanticObjectId] = Field(default_factory=list)
    etymology: Etymology | None = None
    fact_ids: list[PydanticObjectId] = Field(default_factory=list)
    image_ids: list[PydanticObjectId] = Field(default_factory=list)
    model_info: ModelInfo | None = None


class SynthesisUpdate(BaseModel):
    """Schema for updating a synthesized entry - partial updates allowed."""

    pronunciation_id: PydanticObjectId | None = None
    definition_ids: list[PydanticObjectId] | None = None
    etymology: Etymology | None = None
    fact_ids: list[PydanticObjectId] | None = None
    image_ids: list[PydanticObjectId] | None = None
    model_info: ModelInfo | None = None


class SynthesisFilter(BaseModel):
    """Filter parameters for synthesis queries."""

    word_id: str | None = None
    has_pronunciation: bool | None = None
    has_etymology: bool | None = None
    has_facts: bool | None = None
    accessed_after: datetime | None = None
    min_access_count: int | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.word_id:
            query["word_id"] = self.word_id

        if self.has_pronunciation is not None:
            if self.has_pronunciation:
                query["pronunciation_id"] = {"$ne": None}
            else:
                query["pronunciation_id"] = None

        if self.has_etymology is not None:
            if self.has_etymology:
                query["etymology"] = {"$ne": None}
            else:
                query["etymology"] = None

        if self.has_facts is not None:
            if self.has_facts:
                query["fact_ids"] = {"$ne": []}
            else:
                query["fact_ids"] = []

        if self.accessed_after:
            query["accessed_at"] = {"$gte": self.accessed_after}

        if self.min_access_count is not None:
            query["access_count"] = {"$gte": self.min_access_count}

        return query


class ComponentStatus(BaseModel):
    """Status of synthesized entry components."""

    word_id: str
    has_pronunciation: bool
    has_etymology: bool
    has_facts: bool
    definition_count: int
    fact_count: int
    completeness_score: float
    last_updated: datetime | None
    model_version: str | None


class SynthesisRepository(
    BaseRepository[DictionaryEntry, SynthesisCreate, SynthesisUpdate],
):
    """Repository for DictionaryEntry synthesis - simplified CRUD for definition collections."""

    def __init__(self) -> None:
        super().__init__(DictionaryEntry)

    # Core queries matching model relationships
    async def find_by_word(
        self, word_id: PydanticObjectId | str
    ) -> DictionaryEntry | None:
        """Find synthesized entry for a word."""
        word_oid = PydanticObjectId(word_id) if isinstance(word_id, str) else word_id
        return await DictionaryEntry.find_one({
            "word_id": word_oid,
            "provider": "synthesis"
        })

    async def find_by_model(self, model_name: str) -> list[DictionaryEntry]:
        """Find entries synthesized by a specific model."""
        return await DictionaryEntry.find({
            "model_info.name": model_name,
            "provider": "synthesis"
        }).to_list()

    # CRUD for related definitions
    async def add_definition(
        self, entry_id: PydanticObjectId, definition_id: PydanticObjectId
    ) -> DictionaryEntry:
        """Add a definition to the synthesis."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        if definition_id not in entry.definition_ids:
            entry.definition_ids.append(definition_id)
            entry.version += 1
            await entry.save()

        return entry

    async def remove_definition(
        self, entry_id: PydanticObjectId, definition_id: PydanticObjectId
    ) -> DictionaryEntry:
        """Remove a definition from the synthesis."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        if definition_id in entry.definition_ids:
            entry.definition_ids.remove(definition_id)
            entry.version += 1
            await entry.save()

        return entry

    async def add_fact(
        self, entry_id: PydanticObjectId, fact_id: PydanticObjectId
    ) -> DictionaryEntry:
        """Add a fact to the synthesis."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        if fact_id not in entry.fact_ids:
            entry.fact_ids.append(fact_id)
            entry.version += 1
            await entry.save()

        return entry

    async def set_pronunciation(
        self, entry_id: PydanticObjectId, pronunciation_id: PydanticObjectId
    ) -> DictionaryEntry:
        """Set the pronunciation for the synthesis."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        entry.pronunciation_id = pronunciation_id
        entry.version += 1
        await entry.save()

        return entry

    # Completeness and status tracking
    async def get_completeness_score(self, entry: DictionaryEntry) -> float:
        """Calculate completeness score for an entry."""
        components = [
            entry.pronunciation_id is not None,
            entry.etymology is not None,
            bool(entry.fact_ids),
            bool(entry.definition_ids),
            bool(entry.image_ids),
        ]
        return sum(components) / len(components)

    async def find_incomplete(self, limit: int = 100) -> list[DictionaryEntry]:
        """Find entries missing components."""
        return (
            await DictionaryEntry.find(
                {
                    "$or": [
                        {"pronunciation_id": None},
                        {"etymology": None},
                        {"fact_ids": []},
                        {"definition_ids": []},
                    ],
                },
            )
            .limit(limit)
            .to_list()
        )

    async def track_access(self, entry_id: PydanticObjectId) -> DictionaryEntry:
        """Track access to an entry."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        entry.accessed_at = datetime.now(UTC)
        entry.access_count += 1
        await entry.save()

        return entry

    async def _cascade_delete(self, entry: DictionaryEntry) -> None:
        """Delete is handled at word level, definitions are preserved."""
        # Definitions, pronunciations, facts, and images are independent entities
        # They should not be deleted when a synthesis is deleted

    # Unified expansion method
    async def get_expanded(
        self,
        entry_id: PydanticObjectId | None = None,
        entries: list[DictionaryEntry] | None = None,
        expand: set[str] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Get entry(ies) with expanded related entities.

        Args:
            entry_id: Single entry to expand
            entries: Multiple entries to expand
            expand: Set of fields to expand ('definitions', 'pronunciation', 'facts', 'images')

        Returns:
            Expanded entry(ies) as dict(s)

        """
        if entry_id:
            entry = await self.get(entry_id, raise_on_missing=True)
            assert entry is not None
            entries = [entry]
        elif not entries:
            raise ValueError("Either entry_id or entries must be provided")

        # Collect all IDs for batch fetching
        all_definition_ids = set()
        all_pronunciation_ids = set()
        all_fact_ids = set()
        all_image_ids = set()

        for entry in entries:
            if expand:
                if "definitions" in expand:
                    all_definition_ids.update(entry.definition_ids)
                if "pronunciation" in expand and entry.pronunciation_id:
                    all_pronunciation_ids.add(entry.pronunciation_id)
                if "facts" in expand:
                    all_fact_ids.update(entry.fact_ids)
                if "images" in expand:
                    all_image_ids.update(entry.image_ids)

        # Batch fetch related entities
        definitions_map = {}
        pronunciations_map = {}
        facts_map = {}
        images_map = {}

        if all_definition_ids:
            definitions = await Definition.find(
                In(Definition.id, list(all_definition_ids))
            ).to_list()
            definitions_map = {str(d.id): d.model_dump() for d in definitions}

        if all_pronunciation_ids:
            pronunciations = await Pronunciation.find(
                In(Pronunciation.id, list(all_pronunciation_ids))
            ).to_list()
            pronunciations_map = {str(p.id): p.model_dump() for p in pronunciations}

        if all_fact_ids:
            facts = await Fact.find(In(Fact.id, list(all_fact_ids))).to_list()
            facts_map = {str(f.id): f.model_dump() for f in facts}

        if all_image_ids:
            images = await ImageMedia.find(In(ImageMedia.id, list(all_image_ids))).to_list()
            images_map = {str(img.id): img.model_dump(exclude={"data"}) for img in images}

        # Build results
        results = []
        for entry in entries:
            entry_dict = entry.model_dump()

            if expand:
                if "definitions" in expand:
                    entry_dict["definitions"] = [
                        definitions_map[str(def_id)]
                        for def_id in entry.definition_ids
                        if str(def_id) in definitions_map
                    ]

                if "pronunciation" in expand and entry.pronunciation_id:
                    entry_dict["pronunciation"] = pronunciations_map.get(
                        str(entry.pronunciation_id)
                    )

                if "facts" in expand:
                    entry_dict["facts"] = [
                        facts_map[str(fact_id)]
                        for fact_id in entry.fact_ids
                        if str(fact_id) in facts_map
                    ]

                if "images" in expand:
                    entry_dict["images"] = [
                        images_map[str(img_id)]
                        for img_id in entry.image_ids
                        if str(img_id) in images_map
                    ]

            results.append(entry_dict)

        return results[0] if entry_id else results

    # Batch operations
    async def batch_add_definitions(
        self,
        entry_id: PydanticObjectId,
        definition_ids: list[PydanticObjectId],
    ) -> DictionaryEntry:
        """Add multiple definitions to the synthesis."""
        entry = await self.get(entry_id, raise_on_missing=True)
        assert entry is not None

        new_ids = [d_id for d_id in definition_ids if d_id not in entry.definition_ids]
        if new_ids:
            entry.definition_ids.extend(new_ids)
            entry.version += 1
            await entry.save()

        return entry

    async def create_or_update_for_word(
        self,
        word_id: PydanticObjectId,
        data: SynthesisCreate | SynthesisUpdate,
    ) -> DictionaryEntry:
        """Create or update synthesis for a word."""
        existing = await self.find_by_word(word_id)

        if existing:
            # Update existing
            if isinstance(data, SynthesisCreate):
                # Convert create to update
                update_data = SynthesisUpdate(**data.model_dump(exclude={"word_id"}))
            else:
                update_data = data

            assert existing.id is not None  # Entry from database always has ID
            return await self.update(existing.id, update_data)
        # Create new
        if isinstance(data, SynthesisUpdate):
            # Convert update to create
            create_data = SynthesisCreate(
                word_id=word_id,
                **data.model_dump(exclude_unset=True),
            )
        else:
            create_data = data

        return await self.create(create_data)

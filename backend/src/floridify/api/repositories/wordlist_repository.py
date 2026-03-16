"""Repository for WordList model operations."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from beanie.odm.enums import SortDirection
from beanie.operators import RegEx
from pydantic import BaseModel, Field

from ...corpus.core import Corpus
from ...corpus.manager import TreeCorpusManager, get_tree_corpus_manager
from ...corpus.models import CorpusType
from ...models import Word
from ...models.base import Language
from ...text import normalize
from ...utils.logging import get_logger
from ...wordlist.constants import MasteryLevel
from ...wordlist.models import WordList, WordListItemDoc
from ...wordlist.stats import LearningStats
from ...wordlist.utils import generate_wordlist_hash
from ..core.base import BaseRepository
from ..core.exceptions import VersionConflictException
from .corpus_repository import CorpusRepository, CorpusSearchParams

logger = get_logger(__name__)


class WordListCreate(BaseModel):
    """Schema for creating a word list."""

    name: str = Field(..., min_length=1, max_length=200, description="List name")
    description: str = Field(default="", max_length=1000, description="List description")
    words: list[str] = Field(default_factory=list, description="Initial words")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    is_public: bool = Field(default=False, description="Public visibility")
    owner_id: str | None = Field(default=None, description="Owner user ID")


class WordListUpdate(BaseModel):
    """Schema for updating a word list."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    tags: list[str] | None = None
    is_public: bool | None = None


class WordListFilter(BaseModel):
    """Filter parameters for word list queries."""

    name: str | None = None
    name_pattern: str | None = None
    owner_id: str | None = None
    is_public: bool | None = None
    has_tag: str | None = None
    mastery_level: MasteryLevel | None = None
    min_words: int | None = Field(None, ge=0)
    max_words: int | None = Field(None, ge=0)
    created_after: datetime | None = None
    created_before: datetime | None = None
    accessed_after: datetime | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.name:
            query["name"] = self.name
        elif self.name_pattern:
            query["name"] = RegEx(self.name_pattern, "i")

        if self.owner_id:
            query["owner_id"] = self.owner_id

        if self.is_public is not None:
            query["is_public"] = self.is_public

        if self.has_tag:
            query["tags"] = {"$in": [self.has_tag]}

        if self.min_words is not None or self.max_words is not None:
            word_count_query: dict[str, int] = {}
            if self.min_words is not None:
                word_count_query["$gte"] = self.min_words
            if self.max_words is not None:
                word_count_query["$lte"] = self.max_words
            query["unique_words"] = word_count_query

        if self.created_after or self.created_before:
            created_query: dict[str, datetime] = {}
            if self.created_after:
                created_query["$gte"] = self.created_after
            if self.created_before:
                created_query["$lte"] = self.created_before
            query["created_at"] = created_query

        if self.accessed_after:
            query["last_accessed"] = {"$gte": self.accessed_after}

        return query


class WordAddRequest(BaseModel):
    """Request to add words to a list."""

    words: list[str] = Field(..., min_length=1, description="Words to add")
    version: int | None = Field(
        default=None,
        description="Expected wordlist version for optimistic locking. "
        "If provided, the operation will fail with 409 if the wordlist has been modified.",
    )


class WordReviewRequest(BaseModel):
    """Request to review a word."""

    word: str = Field(..., min_length=1, description="Word to review")
    quality: int = Field(..., ge=0, le=5, description="Review quality (0-5)")


class StudySessionRequest(BaseModel):
    """Request to record a study session."""

    duration_minutes: int = Field(..., ge=1, description="Session duration in minutes")
    words_studied: int = Field(default=0, ge=0, description="Number of words studied")
    words_mastered: int = Field(default=0, ge=0, description="Number of words mastered")


class WordListRepository(BaseRepository[WordList, WordListCreate, WordListUpdate]):
    """Repository for WordList CRUD operations."""

    def __init__(self) -> None:
        super().__init__(WordList)
        self.corpus_repo = CorpusRepository()
        self._corpus_manager: TreeCorpusManager | None = None

    async def _get_tree_corpus_manager(self) -> TreeCorpusManager:
        """Get or create corpus manager instance."""
        if self._corpus_manager is None:
            self._corpus_manager = get_tree_corpus_manager()
        return self._corpus_manager

    async def find_by_name(self, name: str, owner_id: str | None = None) -> WordList | None:
        """Find word list by name and optional owner."""
        query = {"name": name}
        if owner_id:
            query["owner_id"] = owner_id
        return await WordList.find_one(query)

    async def find_by_hash(self, hash_id: str) -> WordList | None:
        """Find word list by content hash."""
        return await WordList.find_one({"hash_id": hash_id})

    async def find_by_owner(self, owner_id: str, limit: int = 20) -> list[WordList]:
        """Find word lists by owner."""
        return await WordList.find({"owner_id": owner_id}).limit(limit).to_list()

    async def find_public(self, limit: int = 20) -> list[WordList]:
        """Find public word lists."""
        return await WordList.find({"is_public": True}).limit(limit).to_list()

    async def search_by_name(self, query: str, limit: int = 10) -> list[WordList]:
        """Search word lists by name pattern."""
        return await WordList.find({"name": RegEx(query, "i")}).limit(limit).to_list()

    async def get_popular(self, limit: int = 10) -> list[WordList]:
        """Get most accessed word lists."""
        return (
            await WordList.find({"is_public": True})
            .sort([("last_accessed", SortDirection.DESCENDING)])
            .limit(limit)
            .to_list()
        )

    async def create(self, data: WordListCreate) -> tuple[WordList, bool]:
        """Create a new word list. Returns (wordlist, created) tuple.

        If a wordlist with the same content hash already exists, returns (existing, False).
        """
        # Generate hash from words
        hash_id = generate_wordlist_hash(data.words)

        # Check for existing list with same hash
        existing = await self.find_by_hash(hash_id)
        if existing:
            return existing, False

        # Create new word list (without embedded words)
        wordlist = WordList(
            name=data.name,
            description=data.description,
            hash_id=hash_id,
            tags=data.tags,
            is_public=data.is_public,
            owner_id=data.owner_id,
        )
        await wordlist.create()

        # Add words as separate documents if provided
        if data.words:
            word_ids = await self.batch_get_or_create_words(data.words)
            items = [WordListItemDoc(wordlist_id=wordlist.id, word_id=wid) for wid in word_ids]
            await WordListItemDoc.insert_many(items)
            await self.recompute_stats(wordlist.id)
            # Re-fetch to get updated stats
            wordlist = await self.get(wordlist.id, raise_on_missing=True)

        await self._invalidate_names_corpus()

        # Create corpus for this wordlist's words immediately
        if data.words:
            await self._create_wordlist_corpus(wordlist)

        return wordlist, True

    async def batch_get_or_create_words(self, word_texts: list[str]) -> list[PydanticObjectId]:
        """Batch get or create Word documents, returning their IDs.

        This method optimizes performance by:
        1. Normalizing all words at once
        2. Performing a single bulk lookup
        3. Bulk creating missing words
        4. Returning word IDs in the same order as input
        """
        # Normalize all words using the standard normalize_comprehensive function
        # This ensures consistent normalization for search
        normalized_map = {}
        normalized_list = []
        for text in word_texts:
            # Keep original text for display, normalize for lookup
            original = text.strip()
            normalized = normalize(original)
            normalized_map[normalized] = original
            normalized_list.append(normalized)

        # Remove duplicates while preserving order
        seen = set()
        unique_normalized = []
        for norm in normalized_list:
            if norm not in seen:
                seen.add(norm)
                unique_normalized.append(norm)

        # Bulk lookup existing words
        existing_words = await Word.find(
            {"normalized": {"$in": unique_normalized}, "languages": Language.ENGLISH.value},
        ).to_list()

        # Create a map of normalized text to word ObjectId
        existing_map = {word.normalized: word.id for word in existing_words}

        # Identify missing words
        missing_normalized = [norm for norm in unique_normalized if norm not in existing_map]

        # Bulk create missing words if any
        if missing_normalized:
            new_words = [
                Word(text=normalized_map[norm], languages=[Language.ENGLISH])
                for norm in missing_normalized
            ]

            # Bulk insert - insert_many returns InsertManyResult with inserted_ids
            result = await Word.insert_many(new_words)

            # Add new words to existing map using the returned IDs
            # Key by the comprehensive-normalized form (matching the lookup key),
            # NOT word.normalized which uses normalize_basic and may differ.
            for i, norm in enumerate(missing_normalized):
                word_id = result.inserted_ids[i]
                existing_map[norm] = word_id

        # Return word IDs in the same order as input
        word_ids: list[PydanticObjectId] = []
        for text in word_texts:
            # Use the same normalization as above
            original = text.strip()
            normalized = normalize(original)
            word_id = existing_map.get(normalized)
            if word_id is None:
                raise ValueError(f"Word ID not found for '{text}' after processing")
            word_ids.append(word_id)

        return word_ids

    async def _create_wordlist_corpus(self, wordlist: WordList) -> None:
        """Create corpus for wordlist words immediately upon creation."""
        word_texts = await self._get_word_texts_for_wordlist(wordlist.id)
        if not word_texts:
            return

        corpus_manager = await self._get_tree_corpus_manager()
        corpus_name = f"wordlist_{wordlist.id}"
        corpus = await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=word_texts,
        )
        corpus.corpus_type = CorpusType.WORDLIST
        corpus = await corpus_manager.save_corpus(corpus=corpus)
        if not corpus:
            raise ValueError(f"Failed to save corpus '{corpus_name}'")
        logger.debug(
            f"Created unified corpus {corpus.vocabulary_hash[:8]} for wordlist {wordlist.id} with {len(word_texts)} vocabulary items",
        )

    async def add_word(self, wordlist_id: PydanticObjectId, request: WordAddRequest) -> WordList:
        """Add words to an existing word list.

        Supports optimistic locking: if request.version is provided, the operation
        will fail with 409 Conflict if the wordlist has been modified since the
        client last read it.
        """
        await self._get_wordlist_with_version_check(wordlist_id, request.version)

        word_ids = await self.batch_get_or_create_words(request.words)

        for word_id in word_ids:
            existing_item = await WordListItemDoc.find_one(
                {"wordlist_id": wordlist_id, "word_id": word_id}
            )
            if existing_item:
                existing_item.increment()
                await existing_item.save()
            else:
                new_item = WordListItemDoc(wordlist_id=wordlist_id, word_id=word_id)
                await new_item.create()

        return await self._finalize_word_change(wordlist_id)

    async def remove_word(
        self,
        wordlist_id: PydanticObjectId,
        word_id: PydanticObjectId,
        version: int | None = None,
    ) -> WordList:
        """Remove a word from a word list by word ID.

        Supports optimistic locking: if version is provided, the operation
        will fail with 409 Conflict if the wordlist has been modified since the
        client last read it.
        """
        await self._get_wordlist_with_version_check(wordlist_id, version)

        await WordListItemDoc.find(
            {"wordlist_id": wordlist_id, "word_id": word_id}
        ).delete()

        return await self._finalize_word_change(wordlist_id)

    async def update(
        self,
        id: PydanticObjectId,
        data: WordListUpdate,
        version: int | None = None,
    ) -> WordList:
        """Update a wordlist and invalidate name corpus cache if name changed."""
        # Get the original wordlist to check if name changed
        original_wordlist = await self.get(id, raise_on_missing=True)
        original_name = original_wordlist.name

        # Use parent's update method
        updated_wordlist = await super().update(id, data, version)

        # Invalidate name corpus cache if name changed
        if data.name and data.name != original_name:
            corpus_manager = await self._get_tree_corpus_manager()
            await corpus_manager.invalidate_corpus("wordlist_names_global")

        return updated_wordlist

    async def delete(self, id: PydanticObjectId, cascade: bool = False) -> bool:
        """Delete a wordlist, its items, and invalidate corpus caches."""
        # Delete all items for this wordlist (always, regardless of cascade flag)
        await WordListItemDoc.find({"wordlist_id": id}).delete()

        # Call parent's delete method
        result = await super().delete(id, cascade)

        # Invalidate both corpus caches using unified manager
        corpus_manager = await self._get_tree_corpus_manager()
        corpus_name = f"wordlist_{id}"
        await corpus_manager.invalidate_corpus(corpus_name)
        await corpus_manager.invalidate_corpus("wordlist_names_global")

        return result

    async def review_word(
        self,
        wordlist_id: PydanticObjectId,
        request: WordReviewRequest,
    ) -> WordList:
        """Process a word review session."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find the word document by text
        word_doc = await Word.find_one({"text": request.word})
        if not word_doc or word_doc.id is None:
            return wordlist

        # Find the item in the items collection
        item = await WordListItemDoc.find_one(
            {"wordlist_id": wordlist_id, "word_id": word_doc.id}
        )
        if item:
            item.review(request.quality)
            await item.save()
            await self.recompute_stats(wordlist_id)

        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        wordlist.mark_accessed()
        await wordlist.save()

        return wordlist

    async def mark_word_visited(self, wordlist_id: PydanticObjectId, word: str) -> WordList:
        """Mark a word as visited/viewed."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find the word document by text
        word_doc = await Word.find_one({"text": word})
        if word_doc and word_doc.id is not None:
            item = await WordListItemDoc.find_one(
                {"wordlist_id": wordlist_id, "word_id": word_doc.id}
            )
            if item:
                item.mark_visited()
                await item.save()

        wordlist.mark_accessed()
        await wordlist.save()

        return wordlist

    async def record_study_session(
        self,
        wordlist_id: PydanticObjectId,
        request: StudySessionRequest,
    ) -> WordList:
        """Record a study session."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        wordlist.record_study_session(request.duration_minutes)
        await wordlist.save()
        return wordlist

    async def get_due_words(
        self,
        wordlist_id: PydanticObjectId,
        limit: int | None = None,
    ) -> list[WordListItemDoc]:
        """Get words due for review from a word list."""
        query = WordListItemDoc.find(
            {
                "wordlist_id": wordlist_id,
                "review_data.next_review_date": {"$lte": datetime.now(UTC)},
            }
        ).sort([("review_data.next_review_date", 1)])

        if limit:
            query = query.limit(limit)

        return await query.to_list()

    async def get_by_mastery(
        self,
        wordlist_id: PydanticObjectId,
        level: MasteryLevel,
    ) -> list[WordListItemDoc]:
        """Get words at a specific mastery level."""
        return await WordListItemDoc.find(
            {"wordlist_id": wordlist_id, "mastery_level": level}
        ).to_list()

    async def get_statistics(self, wordlist_id: PydanticObjectId) -> dict[str, Any]:
        """Get detailed statistics for a word list using aggregation pipelines."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            return {}

        now = datetime.now(UTC)
        collection = WordListItemDoc.get_pymongo_collection()

        # Single aggregation using $facet for mastery distribution + summary counts
        stats_pipeline: list[dict[str, Any]] = [
            {"$match": {"wordlist_id": wordlist_id}},
            {
                "$facet": {
                    "mastery": [
                        {"$group": {"_id": "$mastery_level", "count": {"$sum": 1}}},
                    ],
                    "summary": [
                        {
                            "$group": {
                                "_id": None,
                                "hot_count": {
                                    "$sum": {"$cond": [{"$eq": ["$temperature", "hot"]}, 1, 0]}
                                },
                                "cold_count": {
                                    "$sum": {"$cond": [{"$eq": ["$temperature", "cold"]}, 1, 0]}
                                },
                                "due_count": {
                                    "$sum": {
                                        "$cond": [
                                            {"$lte": ["$review_data.next_review_date", now]},
                                            1,
                                            0,
                                        ]
                                    }
                                },
                            }
                        },
                    ],
                }
            },
        ]

        mastery_counts: dict[str, int] = dict.fromkeys([m.value for m in MasteryLevel], 0)
        temperature_counts = {"hot": 0, "cold": 0}
        due_count = 0

        async for doc in collection.aggregate(stats_pipeline):
            for entry in doc.get("mastery", []):
                level_val = entry["_id"]
                if level_val in mastery_counts:
                    mastery_counts[level_val] = entry["count"]
            summary_list = doc.get("summary", [])
            if summary_list:
                summary = summary_list[0]
                temperature_counts["hot"] = summary.get("hot_count", 0)
                temperature_counts["cold"] = summary.get("cold_count", 0)
                due_count = summary.get("due_count", 0)

        # Top 5 most frequent (uses index, returns only 5 docs)
        top_freq = await WordListItemDoc.find(
            {"wordlist_id": wordlist_id}
        ).sort([("frequency", -1)]).limit(5).to_list()
        most_frequent = [w.model_dump(mode="json") for w in top_freq]

        # Top 5 hot words (uses index, returns only hot docs)
        hot = await WordListItemDoc.find(
            {"wordlist_id": wordlist_id, "temperature": "hot"}
        ).sort([("last_visited", -1)]).limit(5).to_list()
        hot_words = [w.model_dump(mode="json") for w in hot]

        return {
            "basic_stats": wordlist.learning_stats.model_dump(mode="json"),
            "word_counts": {
                "total": wordlist.total_words,
                "unique": wordlist.unique_words,
                "due_for_review": due_count,
            },
            "mastery_distribution": mastery_counts,
            "temperature_distribution": temperature_counts,
            "most_frequent": most_frequent,
            "hot_words": hot_words,
        }

    async def create_corpus(self, wordlist_id: PydanticObjectId, ttl_hours: float = 2.0) -> str:
        """Create a corpus from wordlist for search operations."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        corpus_name = f"wordlist_{wordlist_id}"
        existing_corpus = await self.corpus_repo.get(corpus_name)
        if existing_corpus:
            return corpus_name

        word_texts = await self._get_word_texts_for_wordlist(wordlist_id)

        return await self.corpus_repo.create_from_wordlist(
            vocabulary=word_texts,
            name=corpus_name,
        )

    async def search_wordlist_corpus(
        self,
        wordlist_id: PydanticObjectId,
        query: str,
        max_results: int = 20,
        min_score: float = 0.6,
    ) -> dict[str, Any]:
        """Search within a wordlist using corpus functionality."""
        corpus_id = await self.create_corpus(wordlist_id, ttl_hours=1.0)

        params = CorpusSearchParams(
            query=query,
            max_results=max_results,
            min_score=min_score,
        )

        return await self.corpus_repo.search(corpus_id, params)

    async def _cascade_delete(self, wordlist: WordList) -> None:
        """Handle cascade deletion - delete all items for this wordlist."""
        await WordListItemDoc.find({"wordlist_id": wordlist.id}).delete()

    # ── Private helpers ────────────────────────────────────────────

    async def _get_wordlist_with_version_check(
        self,
        wordlist_id: PydanticObjectId,
        version: int | None,
    ) -> WordList:
        """Fetch a wordlist and verify optimistic locking version if provided."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        if version is not None and wordlist.version != version:
            raise VersionConflictException(
                expected=version,
                actual=wordlist.version,
                resource="WordList",
            )
        return wordlist

    async def _finalize_word_change(self, wordlist_id: PydanticObjectId) -> WordList:
        """Recompute stats, mark accessed, and invalidate corpus after a word change."""
        await self.recompute_stats(wordlist_id)

        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        wordlist.mark_accessed()
        await wordlist.save()

        corpus_manager = await self._get_tree_corpus_manager()
        await corpus_manager.invalidate_corpus(f"wordlist_{wordlist_id}")

        return wordlist

    async def _invalidate_names_corpus(self) -> None:
        """Invalidate the global wordlist names corpus."""
        corpus_manager = await self._get_tree_corpus_manager()
        await corpus_manager.invalidate_corpus("wordlist_names_global")

    async def _get_word_ids_for_wordlist(
        self, wordlist_id: PydanticObjectId
    ) -> list[PydanticObjectId]:
        """Get word_id values for a wordlist using a projection (avoids loading full documents)."""
        collection = WordListItemDoc.get_pymongo_collection()
        cursor = collection.find({"wordlist_id": wordlist_id}, {"word_id": 1, "_id": 0})
        return [doc["word_id"] async for doc in cursor if doc.get("word_id")]

    async def _get_word_texts_for_wordlist(self, wordlist_id: PydanticObjectId) -> list[str]:
        """Get word texts for all items in a wordlist via projected lookup."""
        word_ids = await self._get_word_ids_for_wordlist(wordlist_id)
        if not word_ids:
            return []
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()
        return [word.text for word in words if word.text]

    async def recompute_stats(self, wordlist_id: PydanticObjectId) -> None:
        """Recompute denormalized stats on WordList via aggregation pipeline."""
        pipeline = [
            {"$match": {"wordlist_id": wordlist_id}},
            {
                "$group": {
                    "_id": None,
                    "unique_words": {"$sum": 1},
                    "total_words": {"$sum": "$frequency"},
                    "words_mastered": {
                        "$sum": {"$cond": [{"$eq": ["$mastery_level", "gold"]}, 1, 0]}
                    },
                    "avg_ease": {"$avg": "$review_data.ease_factor"},
                    "total_reps": {"$sum": "$review_data.repetitions"},
                    "total_lapses": {"$sum": "$review_data.lapse_count"},
                }
            },
        ]

        stats = LearningStats()
        unique_words = 0
        total_words = 0

        collection = WordListItemDoc.get_pymongo_collection()
        async for doc in collection.aggregate(pipeline):
            unique_words = doc.get("unique_words", 0)
            total_words = doc.get("total_words", 0)
            stats.words_mastered = doc.get("words_mastered", 0)
            avg_ease = doc.get("avg_ease")
            if avg_ease is not None:
                stats.average_ease_factor = avg_ease
            total_reps = doc.get("total_reps", 0)
            total_lapses = doc.get("total_lapses", 0)
            if total_reps > 0:
                stats.retention_rate = 1 - (total_lapses / (total_reps + total_lapses))

        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        wordlist.set_stats(unique_words, total_words, stats)
        await wordlist.save()

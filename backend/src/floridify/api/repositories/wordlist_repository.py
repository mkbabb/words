"""Repository for WordList model operations."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from beanie.odm.enums import SortDirection
from beanie.operators import RegEx
from pydantic import BaseModel, Field

from ...constants import Language
from ...models.models import Word
from ...wordlist.constants import MasteryLevel, Temperature
from ...wordlist.models import WordList, WordListItem
from ...wordlist.utils import generate_wordlist_hash
from ...search.corpus import invalidate_wordlist_names_corpus, invalidate_wordlist_corpus
from ...utils.logging import get_logger
from ..core.base import BaseRepository
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

    async def create(self, data: WordListCreate) -> WordList:
        """Create a new word list."""
        # Generate hash from words
        hash_id = generate_wordlist_hash(data.words)

        # Check for existing list with same hash
        # Temporarily disabled to avoid loading old data format
        # existing = await self.find_by_hash(hash_id)
        # if existing:
        #     return existing

        # Create new word list
        wordlist = WordList(
            name=data.name,
            description=data.description,
            hash_id=hash_id,
            tags=data.tags,
            is_public=data.is_public,
            owner_id=data.owner_id,
        )

        # Add words if provided
        if data.words:
            # Batch process words for better performance
            word_ids = await self._batch_get_or_create_words(data.words)
            wordlist.add_words(word_ids)

        await wordlist.create()
        
        # Only invalidate corpus cache if there were existing wordlists
        # If this is the first wordlist, there's no corpus to invalidate
        existing_count = await WordList.count()
        if existing_count > 1:  # More than just the one we just created
            logger.debug(f"Invalidating wordlist names corpus (total wordlists: {existing_count})")
            await invalidate_wordlist_names_corpus()
        else:
            logger.debug("Skipping corpus invalidation - this is the first wordlist")
        
        # Create corpus for this wordlist's words immediately
        if data.words:
            await self._create_wordlist_corpus(wordlist)
        
        return wordlist

    async def _batch_get_or_create_words(self, word_texts: list[str]) -> list[PydanticObjectId]:
        """Batch get or create Word documents, returning their IDs.

        This method optimizes performance by:
        1. Normalizing all words at once
        2. Performing a single bulk lookup
        3. Bulk creating missing words
        4. Returning word IDs in the same order as input
        """
        # Normalize all words
        normalized_map = {}
        normalized_list = []
        for text in word_texts:
            normalized = text.lower().strip()
            normalized_map[normalized] = text.strip()
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
            {"normalized": {"$in": unique_normalized}, "language": Language.ENGLISH}
        ).to_list()

        # Create a map of normalized text to word ObjectId
        existing_map = {word.normalized: word.id for word in existing_words}

        # Identify missing words
        missing_normalized = [norm for norm in unique_normalized if norm not in existing_map]

        # Bulk create missing words if any
        if missing_normalized:
            new_words = [
                Word(text=normalized_map[norm], normalized=norm, language=Language.ENGLISH)
                for norm in missing_normalized
            ]

            # Bulk insert
            await Word.insert_many(new_words)

            # Add new words to existing map - use new_words which now have IDs populated after insert
            for word in new_words:
                assert word.id is not None  # After insert_many, id should be populated
                existing_map[word.normalized] = word.id

        # Return word IDs in the same order as input
        word_ids: list[PydanticObjectId] = []
        for text in word_texts:
            normalized = text.lower().strip()
            word_id = existing_map.get(normalized)
            if word_id is None:
                raise ValueError(f"Word ID not found for '{text}' after processing")
            word_ids.append(word_id)

        return word_ids

    async def _create_wordlist_corpus(self, wordlist: WordList) -> None:
        """Create corpus for wordlist words immediately upon creation."""
        from ...search.corpus import get_corpus_cache
        
        # Get Word documents for this wordlist
        word_ids = [w.word_id for w in wordlist.words if w.word_id]
        if not word_ids:
            return
            
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()
        word_texts = [word.text for word in words if word.text]
        
        if not word_texts:
            return
            
        # Create corpus with no TTL (ttl_hours=None means no expiration)
        cache = await get_corpus_cache()
        corpus_id = cache.create_corpus(
            words=word_texts,
            name=wordlist.get_words_corpus_name(),
            ttl_hours=None,  # No expiration
        )
        logger.debug(f"Created corpus {corpus_id[:8]} for wordlist {wordlist.id} with {len(word_texts)} words")

    async def add_word(self, wordlist_id: PydanticObjectId, request: WordAddRequest) -> WordList:
        """Add words to an existing word list."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Use batch processing for better performance
        word_ids = await self._batch_get_or_create_words(request.words)

        wordlist.add_words(word_ids)
        wordlist.mark_accessed()
        await wordlist.save()
        
        # Invalidate corpus cache for this wordlist since words changed
        await invalidate_wordlist_corpus(str(wordlist_id))
        
        return wordlist

    async def remove_word(
        self, wordlist_id: PydanticObjectId, word_id: PydanticObjectId
    ) -> WordList:
        """Remove a word from a word list by word ID."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find and remove the word by ID
        wordlist.words = [w for w in wordlist.words if w.word_id != word_id]
        wordlist.update_stats()
        wordlist.mark_accessed()
        await wordlist.save()
        
        # Invalidate corpus cache for this wordlist since words changed
        await invalidate_wordlist_corpus(str(wordlist_id))
        
        return wordlist

    async def update(self, id: PydanticObjectId, data: WordListUpdate) -> WordList:
        """Update a wordlist and invalidate name corpus cache if name changed."""
        # Get the original wordlist to check if name changed
        original_wordlist = await self.get(id, raise_on_missing=True)
        assert original_wordlist is not None
        original_name = original_wordlist.name
        
        # Use parent's update method
        updated_wordlist = await super().update(id, data)
        
        # Invalidate name corpus cache if name changed
        if data.name and data.name != original_name:
            from ..routers.wordlists.utils import invalidate_wordlist_names_corpus
            await invalidate_wordlist_names_corpus()
        
        return updated_wordlist

    async def delete(self, id: PydanticObjectId, cascade: bool = False) -> bool:
        """Delete a wordlist and invalidate corpus caches."""
        # Call parent's delete method
        result = await super().delete(id, cascade)
        
        # Invalidate both corpus caches
        await invalidate_wordlist_corpus(str(id))
        await invalidate_wordlist_names_corpus()
        
        return result

    async def review_word(
        self, wordlist_id: PydanticObjectId, request: WordReviewRequest
    ) -> WordList:
        """Process a word review session."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find the word and process review
        word_item = await wordlist.get_word_item(request.word)
        if word_item:
            word_item.review(request.quality)
            wordlist.update_stats()
            wordlist.mark_accessed()
            await wordlist.save()

        return wordlist

    async def mark_word_visited(self, wordlist_id: PydanticObjectId, word: str) -> WordList:
        """Mark a word as visited/viewed."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        word_item = await wordlist.get_word_item(word)
        if word_item:
            word_item.mark_visited()
            wordlist.mark_accessed()
            await wordlist.save()

        return wordlist

    async def record_study_session(
        self, wordlist_id: PydanticObjectId, request: StudySessionRequest
    ) -> WordList:
        """Record a study session."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        wordlist.record_study_session(request.duration_minutes)
        await wordlist.save()
        return wordlist

    async def get_due_words(
        self, wordlist_id: PydanticObjectId, limit: int | None = None
    ) -> list[WordListItem]:
        """Get words due for review from a word list."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            return []

        return wordlist.get_due_for_review(limit)

    async def get_by_mastery(
        self, wordlist_id: PydanticObjectId, level: MasteryLevel
    ) -> list[WordListItem]:
        """Get words at a specific mastery level."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            return []

        return wordlist.get_by_mastery(level)

    async def get_statistics(self, wordlist_id: PydanticObjectId) -> dict[str, Any]:
        """Get detailed statistics for a word list."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            return {}

        # Calculate additional statistics
        mastery_distribution = wordlist.get_mastery_distribution()
        mastery_counts = {level.value: count for level, count in mastery_distribution.items()}

        temperature_counts = {
            "hot": len([w for w in wordlist.words if w.temperature == Temperature.HOT]),
            "cold": len([w for w in wordlist.words if w.temperature == Temperature.COLD]),
        }

        due_count = len(wordlist.get_due_for_review())

        return {
            "basic_stats": wordlist.learning_stats.model_dump(),
            "word_counts": {
                "total": wordlist.total_words,
                "unique": wordlist.unique_words,
                "due_for_review": due_count,
            },
            "mastery_distribution": mastery_counts,
            "temperature_distribution": temperature_counts,
            "most_frequent": [w.model_dump() for w in wordlist.get_most_frequent(5)],
            "hot_words": [w.model_dump() for w in wordlist.get_hot_words(5)],
        }

    async def create_corpus(self, wordlist_id: PydanticObjectId, ttl_hours: float = 2.0) -> str:
        """Create a corpus from wordlist for search operations."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Check if corpus already exists for this wordlist
        corpus_name = f"wordlist-{str(wordlist_id)}"
        existing_corpus = await self.corpus_repo.get_by_name(corpus_name)
        if existing_corpus:
            return existing_corpus

        # Fetch Word documents to get text (word_ids are now ObjectIds)
        word_ids = [item.word_id for item in wordlist.words if item.word_id]

        words = await Word.find({"_id": {"$in": word_ids}}).to_list()

        # Extract word text
        word_texts = [word.text for word in words]

        return await self.corpus_repo.create_from_wordlist(
            words=word_texts,
            name=corpus_name,
            ttl_hours=ttl_hours,
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
        """Handle cascade deletion - WordList is self-contained."""
        # WordList contains all data internally, no cascade needed
        pass

    async def populate_words(self, wordlist: WordList) -> dict[str, Any]:
        """Populate wordlist with actual word text instead of just IDs.

        Returns a dictionary representation with word text included.
        """
        # Get word IDs from wordlist items (they are now ObjectIds)
        word_ids = [item.word_id for item in wordlist.words if item.word_id]

        if not word_ids:
            # No words to fetch, return empty wordlist
            wordlist_dict = wordlist.model_dump(mode="json")
            for word_item in wordlist_dict["words"]:
                word_item.pop("word_id", None)
                word_item["word"] = ""
            return wordlist_dict

        # Fetch Word documents directly with ObjectIds (no conversion needed!)
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()

        # Create word text map using string IDs
        word_text_map = {str(word.id): word.text for word in words}

        # Convert wordlist to dict and update word items
        wordlist_dict = wordlist.model_dump(mode="json")

        # Update each word item with actual word text
        for word_item in wordlist_dict["words"]:
            word_id = word_item.pop("word_id", "")
            word_item["word"] = word_text_map.get(word_id, "")

        return wordlist_dict

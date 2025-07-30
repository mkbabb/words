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
from ..core.base import BaseRepository
from .corpus_repository import CorpusRepository, CorpusSearchParams


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
            # Get or create Word documents inline
            word_ids = []
            for text in data.words:
                normalized = text.lower().strip()

                # Try to find existing word
                existing_word = await Word.find_one(
                    {"normalized": normalized, "language": Language.ENGLISH}
                )

                if existing_word:
                    word_ids.append(str(existing_word.id))
                else:
                    # Create new word
                    word = Word(text=text.strip(), normalized=normalized, language=Language.ENGLISH)
                    await word.create()
                    word_ids.append(str(word.id))

            wordlist.add_words(word_ids)

        await wordlist.create()
        return wordlist

    async def add_word(self, wordlist_id: PydanticObjectId, request: WordAddRequest) -> WordList:
        """Add words to an existing word list."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Get or create Word documents inline
        word_ids = []
        for text in request.words:
            normalized = text.lower().strip()

            # Try to find existing word
            existing_word = await Word.find_one(
                {"normalized": normalized, "language": Language.ENGLISH}
            )

            if existing_word:
                word_ids.append(str(existing_word.id))
            else:
                # Create new word
                word = Word(text=text.strip(), normalized=normalized, language=Language.ENGLISH)
                await word.create()
                word_ids.append(str(word.id))

        wordlist.add_words(word_ids)
        wordlist.mark_accessed()
        await wordlist.save()
        return wordlist

    async def remove_word(self, wordlist_id: PydanticObjectId, word_id: str) -> WordList:
        """Remove a word from a word list by word ID."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find and remove the word by ID
        wordlist.words = [w for w in wordlist.words if w.word_id != word_id]
        wordlist.update_stats()
        wordlist.mark_accessed()
        await wordlist.save()
        return wordlist

    async def review_word(
        self, wordlist_id: PydanticObjectId, request: WordReviewRequest
    ) -> WordList:
        """Process a word review session."""
        wordlist = await self.get(wordlist_id, raise_on_missing=True)
        if wordlist is None:
            raise ValueError(f"WordList with id {wordlist_id} not found")

        # Find the word and process review
        word_item = wordlist.get_word_item(request.word)
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

        word_item = wordlist.get_word_item(word)
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

        # Fetch Word documents to get text
        from ...models import Word

        word_ids = [item.word_id for item in wordlist.words]
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
        # Get word IDs
        word_ids = [item.word_id for item in wordlist.words]
        
        # Fetch Word documents
        from ...models import Word
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()
        
        # Create word text map
        word_text_map = {str(word.id): word.text for word in words}
        
        # Convert wordlist to dict and update word items
        wordlist_dict = wordlist.model_dump(mode="json")
        
        # Update each word item with actual word text and remove word_id
        for word_item in wordlist_dict["words"]:
            word_id = word_item.pop("word_id", "")
            word_item["word"] = word_text_map.get(word_id, "")
        
        return wordlist_dict

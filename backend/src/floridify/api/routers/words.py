"""Word management endpoints with field selection."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...constants import Language
from ...models import Definition, Fact, Pronunciation, ProviderData, Word, WordForm
from ...utils.logging import get_logger
from ..middleware.field_selection import FieldSelector

logger = get_logger(__name__)
router = APIRouter()


class WordCreate(BaseModel):
    """Create a new word."""
    
    text: str = Field(..., min_length=1, max_length=100)
    normalized: str | None = None
    language: str = "en"
    word_forms: list[dict[str, Any]] = []
    offensive_flag: bool = False


class WordUpdate(BaseModel):
    """Update an existing word."""
    
    normalized: str | None = None
    word_forms: list[dict[str, Any]] | None = None
    offensive_flag: bool | None = None


@router.get("/{word_id}")
async def get_word(
    word_id: str,
    include: str | None = Query(None, description="Comma-separated fields to include"),
    exclude: str | None = Query(None, description="Comma-separated fields to exclude"),
    expand: str | None = Query(None, description="Comma-separated related fields to expand"),
) -> dict[str, Any]:
    """Get a word by ID with field selection."""
    
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word {word_id} not found"
        )
    
    # Apply field selection
    selector = FieldSelector(include=include, exclude=exclude)
    result = selector.select(word)
    
    # Handle field expansion
    if expand:
        expand_fields = {f.strip() for f in expand.split(",") if f.strip()}
        
        if "definitions" in expand_fields:
            definitions = await Definition.find(Definition.word_id == word_id).to_list()
            result["definitions"] = [selector.select(d) for d in definitions]
        
        if "pronunciation" in expand_fields:
            pronunciation = await Pronunciation.find_one(Pronunciation.word_id == word_id)
            if pronunciation:
                result["pronunciation"] = selector.select(pronunciation)
        
        if "facts" in expand_fields:
            facts = await Fact.find(Fact.word_id == word_id).to_list()
            result["facts"] = [selector.select(f) for f in facts]
    
    return result


@router.post("", response_model=dict)
async def create_word(word_data: WordCreate) -> dict[str, Any]:
    """Create a new word."""
    
    # Check if word exists
    existing = await Word.find_one(Word.text == word_data.text)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Word '{word_data.text}' already exists"
        )
    
    # Create word
    word = Word(
        text=word_data.text,
        normalized=word_data.normalized or word_data.text.lower(),
        language=Language(word_data.language),
        word_forms=[WordForm(**wf) for wf in word_data.word_forms],
        offensive_flag=word_data.offensive_flag,
    )
    await word.save()
    
    return {"id": str(word.id), "text": word.text}


@router.patch("/{word_id}")
async def update_word(
    word_id: str,
    updates: WordUpdate,
    expected_version: int = Query(..., description="Expected version for optimistic locking"),
) -> dict[str, Any]:
    """Update a word with version checking."""
    
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word {word_id} not found"
        )
    
    # Check version
    if word.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch: expected {expected_version}, got {word.version}"
        )
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(word, field, value)
    
    word.version += 1
    await word.save()
    
    return {"id": str(word.id), "version": word.version}


@router.delete("/{word_id}")
async def delete_word(word_id: str) -> dict[str, Any]:
    """Delete a word and all related data."""
    
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word {word_id} not found"
        )
    
    # Delete related data
    await Definition.find(Definition.word_id == word_id).delete()
    await Pronunciation.find(Pronunciation.word_id == word_id).delete()
    await Fact.find(Fact.word_id == word_id).delete()
    await ProviderData.find(ProviderData.word_id == word_id).delete()
    
    # Delete word
    await word.delete()
    
    return {"id": word_id, "deleted": True}


@router.get("")
async def list_words(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    language: str | None = Query(None),
    search: str | None = Query(None, description="Search words by text"),
    include: str | None = Query(None, description="Comma-separated fields to include"),
    exclude: str | None = Query(None, description="Comma-separated fields to exclude"),
) -> dict[str, Any]:
    """List words with pagination and field selection."""
    
    # Build query
    query: dict[str, Any] = {}
    if language:
        query["language"] = language
    if search:
        query["$or"] = [
            {"text": {"$regex": search, "$options": "i"}},
            {"normalized": {"$regex": search, "$options": "i"}},
        ]
    
    # Get total count
    total = await Word.find(query).count()
    
    # Get words with pagination
    words = await Word.find(query).skip(skip).limit(limit).to_list()
    
    # Apply field selection
    selector = FieldSelector(include=include, exclude=exclude)
    items = [selector.select(word) for word in words]
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
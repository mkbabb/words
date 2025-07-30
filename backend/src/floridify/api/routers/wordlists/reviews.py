"""WordList review and study endpoints."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ....models import Word
from ....wordlist.constants import MasteryLevel
from ...core import ListResponse, ResourceResponse
from ...repositories import StudySessionRequest, WordListRepository, WordReviewRequest

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


class ReviewSessionParams(BaseModel):
    """Parameters for getting a review session."""

    limit: int = Field(20, ge=1, le=50, description="Maximum words to review")
    mastery_threshold: MasteryLevel = Field(
        MasteryLevel.SILVER, description="Maximum mastery level to include"
    )


class BulkReviewRequest(BaseModel):
    """Request for bulk review submission."""

    reviews: list[WordReviewRequest] = Field(..., description="List of word reviews")


@router.get("/{wordlist_id}/review/due", response_model=ListResponse[dict[str, Any]])
async def get_due_words(
    wordlist_id: PydanticObjectId,
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Get words due for review based on spaced repetition.

    Query Parameters:
        - limit: Maximum number of due words

    Returns:
        List of words that need review.
    """
    due_words = await repo.get_due_words(wordlist_id, limit)

    # Fetch Word documents to get text
    word_ids = [w.word_id for w in due_words]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    items = []
    for word_item in due_words:
        items.append(
            {
                "word": word_text_map.get(word_item.word_id, ""),
                "mastery_level": word_item.mastery_level,
                "last_reviewed": word_item.review_data.last_review_date.isoformat()
                if word_item.review_data.last_review_date
                else None,
                "review_count": word_item.review_data.repetitions,
                "due_priority": word_item.get_overdue_days(),
            }
        )

    return ListResponse(
        items=items,
        total=len(items),
        offset=0,
        limit=limit,
    )


@router.get("/{wordlist_id}/review/session", response_model=ResourceResponse)
async def get_review_session(
    wordlist_id: PydanticObjectId,
    params: ReviewSessionParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get a new review session with words to study.

    Query Parameters:
        - limit: Maximum words in session
        - mastery_threshold: Include words up to this mastery level

    Returns:
        Review session with selected words.
    """
    # Get wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Select words for review
    review_words = []
    now = datetime.utcnow()

    for word in wordlist.words:
        # Skip if above mastery threshold
        if word.mastery_level.value > params.mastery_threshold.value:
            continue

        # Include if due for review
        if word.is_due_for_review():
            review_words.append(word)

        if len(review_words) >= params.limit:
            break

    # Fetch Word documents to get text for review words
    word_ids = [w.word_id for w in review_words]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    # Convert to response
    session_words = []
    for word_item in review_words:
        session_words.append(
            {
                "word": word_text_map.get(word_item.word_id, ""),
                "mastery_level": word_item.mastery_level,
                "last_reviewed": word_item.review_data.last_review_date.isoformat()
                if word_item.review_data.last_review_date
                else None,
                "notes": word_item.notes,
            }
        )

    return ResourceResponse(
        data={
            "session_id": str(wordlist.id) + "_" + str(int(now.timestamp())),
            "wordlist_id": str(wordlist.id),
            "words": session_words,
            "total_words": len(session_words),
            "created_at": now.isoformat(),
        },
        metadata={
            "wordlist_name": wordlist.name,
            "total_list_words": len(wordlist.words),
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "submit": f"/wordlists/{wordlist_id}/review",
        },
    )


@router.post("/{wordlist_id}/review", response_model=ResourceResponse)
async def submit_review(
    wordlist_id: PydanticObjectId,
    request: WordReviewRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Submit a single word review result.

    Body:
        - word: Word that was reviewed
        - mastery_level: New mastery level
        - quality_score: Review quality (0-1)

    Returns:
        Updated word metadata.
    """
    updated_list = await repo.review_word(wordlist_id, request)

    # Find the updated word by fetching Word documents
    word_ids = [w.word_id for w in updated_list.words]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    updated_word = None
    for word_item in updated_list.words:
        if word_text_map.get(word_item.word_id, "") == request.word:
            updated_word = word_item
            break

    return ResourceResponse(
        data={
            "word": request.word,
            "mastery_level": updated_word.mastery_level if updated_word else None,
            "last_reviewed": updated_word.review_data.last_review_date.isoformat()
            if updated_word and updated_word.review_data.last_review_date
            else None,
        },
        metadata={
            "wordlist_version": updated_list.version,
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "next_due": f"/wordlists/{wordlist_id}/review/due",
        },
    )


@router.post("/{wordlist_id}/review/bulk", response_model=ResourceResponse)
async def submit_bulk_reviews(
    wordlist_id: PydanticObjectId,
    request: BulkReviewRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Submit multiple word reviews at once.

    Body:
        - reviews: List of review results

    Returns:
        Summary of review results.
    """
    # Process each review
    success_count = 0
    failed_words = []

    for review in request.reviews:
        try:
            await repo.review_word(wordlist_id, review)
            success_count += 1
        except Exception:
            failed_words.append(review.word)

    return ResourceResponse(
        data={
            "total_reviewed": len(request.reviews),
            "successful": success_count,
            "failed": len(failed_words),
            "failed_words": failed_words,
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "statistics": f"/wordlists/{wordlist_id}/stats",
        },
    )


@router.post("/{wordlist_id}/review/study-session", response_model=ResourceResponse)
async def record_study_session(
    wordlist_id: PydanticObjectId,
    request: StudySessionRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Record a study session.

    Body:
        - duration_minutes: Session duration
        - words_studied: Number of words studied
        - words_mastered: Number of words mastered

    Returns:
        Updated statistics.
    """
    updated_list = await repo.record_study_session(wordlist_id, request)

    return ResourceResponse(
        data={
            "total_study_time": updated_list.learning_stats.study_time_minutes,
            "study_session_count": updated_list.learning_stats.total_reviews,
            "last_studied": updated_list.learning_stats.last_study_date.isoformat()
            if updated_list.learning_stats.last_study_date
            else None,
        },
        metadata={
            "session": {
                "duration_minutes": request.duration_minutes,
                "words_studied": request.words_studied,
                "words_mastered": request.words_mastered,
            }
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "statistics": f"/wordlists/{wordlist_id}/stats",
        },
    )

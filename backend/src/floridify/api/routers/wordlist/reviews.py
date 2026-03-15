"""WordList review and study endpoints."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ....models import Word
from ....wordlist.constants import MasteryLevel
from ...core import CurrentUserDep, ListResponse, ResourceResponse
from ...repositories import StudySessionRequest, WordListRepository, WordReviewRequest

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


class ReviewSessionParams(BaseModel):
    """Parameters for getting a review session."""

    limit: int = Field(20, ge=1, le=50, description="Maximum words to review")
    mastery_threshold: MasteryLevel = Field(
        MasteryLevel.SILVER,
        description="Maximum mastery level to include",
    )


class BulkReviewRequest(BaseModel):
    """Request for bulk review submission."""

    reviews: list[WordReviewRequest] = Field(..., description="List of word reviews")


@router.get("/{wordlist_id}/review/due", response_model=ListResponse[dict[str, Any]])
async def get_due_words(
    wordlist_id: PydanticObjectId,
    user_id: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Get words due for review based on spaced repetition."""
    due_words = await repo.get_due_words(wordlist_id, limit)

    # Fetch Word documents to get text
    word_ids = [w.word_id for w in due_words if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    items = []
    for word_item in due_words:
        # Get predicted intervals for frontend button labels
        predicted_intervals = word_item.review_data.get_predicted_intervals()

        items.append(
            {
                "word": word_text_map.get(str(word_item.word_id), ""),
                "mastery_level": word_item.mastery_level,
                "card_state": word_item.review_data.card_state,
                "ease_factor": word_item.review_data.ease_factor,
                "interval_days": word_item.review_data.interval,
                "last_reviewed": word_item.review_data.last_review_date.isoformat()
                if word_item.review_data.last_review_date
                else None,
                "review_count": word_item.review_data.repetitions,
                "lapse_count": word_item.review_data.lapse_count,
                "is_leech": word_item.review_data.is_leech,
                "due_priority": word_item.get_overdue_days(),
                "predicted_intervals": predicted_intervals,
                "notes": word_item.notes,
            },
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
    user_id: CurrentUserDep,
    params: ReviewSessionParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get a new review session with words to study."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Select words for review
    review_words = []
    now = datetime.now(UTC)

    for word in wordlist.words:
        # Skip if above mastery threshold (uses correct ordering now)
        if word.mastery_level > params.mastery_threshold:
            continue

        # Include if due for review
        if word.is_due_for_review():
            review_words.append(word)

        if len(review_words) >= params.limit:
            break

    # Sort by urgency (most overdue first)
    review_words.sort(key=lambda w: w.get_overdue_days(), reverse=True)

    # Fetch Word documents to get text
    word_ids = [w.word_id for w in review_words if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    # Convert to response with full review state
    session_words = []
    for word_item in review_words:
        predicted_intervals = word_item.review_data.get_predicted_intervals()
        session_words.append(
            {
                "word": word_text_map.get(str(word_item.word_id), ""),
                "mastery_level": word_item.mastery_level,
                "card_state": word_item.review_data.card_state,
                "ease_factor": word_item.review_data.ease_factor,
                "interval_days": word_item.review_data.interval,
                "repetitions": word_item.review_data.repetitions,
                "lapse_count": word_item.review_data.lapse_count,
                "is_leech": word_item.review_data.is_leech,
                "last_reviewed": word_item.review_data.last_review_date.isoformat()
                if word_item.review_data.last_review_date
                else None,
                "notes": word_item.notes,
                "predicted_intervals": predicted_intervals,
            },
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
    user_id: CurrentUserDep,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Submit a single word review result.

    Returns full computed review state so frontend can display
    without recomputing SM-2 logic.
    """
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Find the word item and capture previous mastery
    word_item = await wordlist.get_word_item(request.word)
    if not word_item:
        from fastapi import HTTPException

        raise HTTPException(404, f"Word '{request.word}' not in wordlist")

    previous_mastery = word_item.mastery_level

    # Process review (updates SM-2 state, card state, mastery)
    word_item.review(request.quality)
    wordlist.update_stats()
    wordlist.mark_accessed()
    await wordlist.save()

    # Get predicted intervals for next review
    predicted_intervals = word_item.review_data.get_predicted_intervals()

    return ResourceResponse(
        data={
            "word": request.word,
            "card_state": word_item.review_data.card_state,
            "mastery_level": word_item.mastery_level,
            "ease_factor": word_item.review_data.ease_factor,
            "interval_days": word_item.review_data.interval,
            "next_review_date": word_item.review_data.next_review_date.isoformat(),
            "repetitions": word_item.review_data.repetitions,
            "lapse_count": word_item.review_data.lapse_count,
            "is_leech": word_item.review_data.is_leech,
            "mastery_changed": previous_mastery != word_item.mastery_level,
            "previous_mastery": previous_mastery,
            "predicted_intervals": predicted_intervals,
        },
        metadata={
            "wordlist_version": wordlist.version,
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
    user_id: CurrentUserDep,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Submit multiple word reviews at once.

    Loads wordlist once, applies all reviews in memory, saves once.
    """
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    success_count = 0
    failed_words = []
    results = []

    for review in request.reviews:
        word_item = await wordlist.get_word_item(review.word)
        if word_item:
            previous_mastery = word_item.mastery_level
            word_item.review(review.quality)
            success_count += 1
            results.append(
                {
                    "word": review.word,
                    "card_state": word_item.review_data.card_state,
                    "mastery_level": word_item.mastery_level,
                    "mastery_changed": previous_mastery != word_item.mastery_level,
                    "interval_days": word_item.review_data.interval,
                    "is_leech": word_item.review_data.is_leech,
                }
            )
        else:
            failed_words.append(review.word)

    # Single save for all reviews
    if success_count > 0:
        wordlist.update_stats()
        wordlist.mark_accessed()
        await wordlist.save()

    return ResourceResponse(
        data={
            "total_reviewed": len(request.reviews),
            "successful": success_count,
            "failed": len(failed_words),
            "failed_words": failed_words,
            "results": results,
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
    user_id: CurrentUserDep,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Record a study session."""
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
            },
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "statistics": f"/wordlists/{wordlist_id}/stats",
        },
    )

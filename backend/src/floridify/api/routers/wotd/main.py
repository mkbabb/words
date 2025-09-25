"""Word of the Day API - Daily vocabulary learning with notifications."""

from datetime import datetime, timedelta
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from ....ai.connector import OpenAIConnector, get_openai_connector
from ....wordlist.word_of_the_day.models import (
    NotificationFrequency,
    WordOfTheDayBatch,
    WordOfTheDayConfig,
    WordOfTheDayEntry,
)
from ...core import (
    ListResponse,
    ResourceResponse,
)

router = APIRouter()


async def get_ai_connector() -> OpenAIConnector:
    """Get OpenAI connector dependency."""
    return get_openai_connector()


@router.get("/current", response_model=ResourceResponse)
async def get_current_word_of_the_day(
    generate_if_empty: bool = Query(True, description="Generate new batch if empty"),
    ai: OpenAIConnector = Depends(get_ai_connector),
) -> ResourceResponse:
    """Get the current Word of the Day.

    This endpoint is used by the notification server and frontend.
    Returns the next scheduled word or generates a new batch if needed.

    Query Parameters:
        - generate_if_empty: Automatically generate new batch if no words available

    Returns:
        Current Word of the Day with all educational content.

    Errors:
        404: No word available and generation disabled
        500: Word generation failed

    """
    # Get or create active batch
    batch = await WordOfTheDayBatch.find_one({"active": True})
    if not batch:
        batch = WordOfTheDayBatch(
            context="",
            frequency=NotificationFrequency.DAILY,
            active=True,
        )
        await batch.create()
        await batch.initialize_first_batch()

    # Check if we need to generate new words
    if batch.needs_new_batch() and generate_if_empty:
        try:
            await _generate_new_batch(batch, ai)
        except Exception as e:
            if not batch.current_batch:  # Only fail if we have no words at all
                raise HTTPException(500, f"Failed to generate words: {e}")

    # Get next word
    next_word = batch.get_next_word()
    if not next_word:
        raise HTTPException(404, "No Word of the Day available")

    return ResourceResponse(
        data=next_word.model_dump(),
        metadata={
            "batch_id": str(batch.id),
            "words_remaining": len(batch.current_batch),
            "total_sent": batch.total_words_sent,
            "is_due": batch.is_due_for_sending(),
            "next_send_time": batch.next_send_time,
        },
        links={
            "batch": f"/wotd/batches/{batch.id}",
            "config": "/wotd/config",
            "history": "/wotd/history",
        },
    )


@router.post("/send", response_model=ResourceResponse)
async def send_current_word(
    ai: OpenAIConnector = Depends(get_ai_connector),
) -> ResourceResponse:
    """Mark the current word as sent and advance to next.

    Used by the notification server to track sent words.

    Returns:
        The word that was sent with updated statistics.

    Errors:
        404: No word available to send
        409: Word not due for sending yet

    """
    # Get active batch
    batch = await WordOfTheDayBatch.find_one({"active": True})
    if not batch:
        raise HTTPException(404, "No active Word of the Day batch")

    # Get current word
    current_word = batch.get_next_word()
    if not current_word:
        # Try to generate new batch
        try:
            await _generate_new_batch(batch, ai)
            current_word = batch.get_next_word()
            if not current_word:
                raise HTTPException(404, "No words available")
        except Exception as e:
            raise HTTPException(500, f"Failed to generate words: {e}")

    # Check if due for sending (can be overridden)
    if not batch.is_due_for_sending():
        if batch.next_send_time:
            time_until_due = batch.next_send_time - datetime.now()
            raise HTTPException(
                409,
                f"Word not due for sending yet. Next word in {time_until_due.total_seconds():.0f} seconds",
            )
        raise HTTPException(409, "Word not due for sending yet")

    # Mark as sent
    word_text = current_word.word
    batch.mark_word_sent(current_word.word)
    await batch.save()

    return ResourceResponse(
        data=current_word.model_dump(),
        metadata={
            "word_sent": word_text,
            "sent_at": datetime.now(),
            "next_send_time": batch.next_send_time,
            "words_remaining": len(batch.current_batch),
            "total_sent": batch.total_words_sent,
        },
    )


@router.get("/batches", response_model=ListResponse[dict[str, Any]])
async def list_word_batches(
    active_only: bool = Query(False, description="Show only active batches"),
    limit: int = Query(10, ge=1, le=50),
) -> ListResponse[dict[str, Any]]:
    """List Word of the Day batches.

    Query Parameters:
        - active_only: Show only active batches
        - limit: Maximum batches to return

    Returns:
        List of batches with metadata and statistics.

    """
    query = {"active": True} if active_only else {}
    batches = await WordOfTheDayBatch.find(query).limit(limit).to_list()

    return ListResponse(
        items=[batch.model_dump() for batch in batches],
        total=len(batches),
        offset=0,
        limit=limit,
    )


@router.get("/batches/{batch_id}", response_model=ResourceResponse)
async def get_word_batch(
    batch_id: PydanticObjectId,
) -> ResourceResponse:
    """Get detailed information about a Word of the Day batch.

    Path Parameters:
        - batch_id: MongoDB ObjectId of the batch

    Returns:
        Batch details with current words and statistics.

    Errors:
        404: Batch not found

    """
    batch = await WordOfTheDayBatch.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    batch_data = batch.model_dump()

    # Add computed statistics
    batch_data["statistics"] = {
        "words_remaining": len(batch.current_batch),
        "words_sent": len(batch.sent_words),
        "batch_progress": len(batch.sent_words)
        / max(1, batch.total_words_sent + len(batch.current_batch)),
        "days_active": (datetime.now() - batch.created_at).days,
        "average_words_per_day": batch.total_words_sent
        / max(1, (datetime.now() - batch.created_at).days)
        if batch.created_at
        else 0,
    }

    return ResourceResponse(
        data=batch_data,
        metadata={
            "is_active": batch.active,
            "needs_generation": batch.needs_new_batch(),
            "is_due": batch.is_due_for_sending(),
        },
    )


@router.put("/batches/{batch_id}/config", response_model=ResourceResponse)
async def update_batch_config(
    batch_id: PydanticObjectId,
    context: str = Query(None, description="New context for word generation"),
    frequency: NotificationFrequency = Query(None, description="New notification frequency"),
    max_seen_words: int = Query(None, ge=100, le=2000, description="Maximum seen words to track"),
    active: bool = Query(None, description="Batch active status"),
) -> ResourceResponse:
    """Update Word of the Day batch configuration.

    Path Parameters:
        - batch_id: MongoDB ObjectId of the batch

    Query Parameters:
        - context: Context for AI word generation
        - frequency: Notification frequency
        - max_seen_words: Maximum seen words to track
        - active: Whether batch is active

    Returns:
        Updated batch configuration.

    Errors:
        404: Batch not found

    """
    batch = await WordOfTheDayBatch.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    # Update provided fields
    updated = False
    if context is not None:
        batch.context = context
        updated = True
    if frequency is not None:
        batch.frequency = frequency
        updated = True
    if max_seen_words is not None:
        batch.max_seen_words = max_seen_words
        # Trim seen words if necessary
        if len(batch.sent_words) > max_seen_words:
            batch.sent_words = batch.sent_words[-max_seen_words:]
        updated = True
    if active is not None:
        batch.active = active
        updated = True

    if updated:
        batch.updated_at = datetime.now()
        await batch.save()

    return ResourceResponse(
        data=batch.model_dump(),
        metadata={
            "updated_at": batch.updated_at,
            "changes_applied": updated,
        },
    )


@router.post("/batches/{batch_id}/generate", response_model=ResourceResponse)
async def generate_new_batch_words(
    batch_id: PydanticObjectId,
    count: int = Query(20, ge=5, le=50, description="Number of words to generate"),
    ai: OpenAIConnector = Depends(get_ai_connector),
) -> ResourceResponse:
    """Generate new words for a batch.

    Path Parameters:
        - batch_id: MongoDB ObjectId of the batch

    Query Parameters:
        - count: Number of words to generate

    Returns:
        Updated batch with new words added.

    Errors:
        404: Batch not found
        500: Word generation failed

    """
    batch = await WordOfTheDayBatch.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    try:
        await _generate_new_batch(batch, ai, count)
        return ResourceResponse(
            data=batch.model_dump(),
            metadata={
                "words_generated": count,
                "total_words": len(batch.current_batch),
                "generated_at": batch.last_generation,
            },
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to generate words: {e}")


@router.get("/history", response_model=ListResponse[dict[str, Any]])
async def get_word_history(
    batch_id: PydanticObjectId = Query(None, description="Filter by batch ID"),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to retrieve"),
    limit: int = Query(50, ge=1, le=200),
) -> ListResponse[dict[str, Any]]:
    """Get history of sent words.

    Query Parameters:
        - batch_id: Optional batch ID filter
        - days_back: Number of days to look back
        - limit: Maximum words to return

    Returns:
        List of recently sent words with metadata.

    """
    query: dict[str, Any] = {}
    if batch_id:
        query["_id"] = batch_id

    # Get batches and extract sent word history
    batches = await WordOfTheDayBatch.find(query).to_list()

    # Collect sent words from all batches
    sent_history = []
    cutoff_date = datetime.now() - timedelta(days=days_back)

    for batch in batches:
        # Note: In a production system, you'd want to store full word history
        # For now, we just return the sent_words list with estimated dates
        for i, word in enumerate(batch.sent_words[-limit:]):
            # Estimate sent date based on frequency and position
            estimated_date = (
                batch.last_sent
                - timedelta(minutes=batch.frequency.minutes * (len(batch.sent_words) - i - 1))
                if batch.last_sent
                else batch.created_at or datetime.now()
            )

            if estimated_date >= cutoff_date:
                sent_history.append(
                    {
                        "word": word,
                        "estimated_sent_date": estimated_date,
                        "batch_id": str(batch.id),
                        "batch_context": batch.context,
                    },
                )

    # Sort by date and limit
    sent_history.sort(key=lambda x: x["estimated_sent_date"], reverse=True)  # type: ignore[arg-type,return-value]
    sent_history = sent_history[:limit]

    return ListResponse(
        items=sent_history,
        total=len(sent_history),
        offset=0,
        limit=limit,
    )


@router.get("/config", response_model=ResourceResponse)
async def get_word_of_the_day_config() -> ResourceResponse:
    """Get global Word of the Day configuration.

    Returns:
        Global configuration settings.

    """
    config = await WordOfTheDayConfig.get_default()
    return ResourceResponse(
        data=config.model_dump(),
        metadata={
            "last_updated": config.updated_at,
        },
    )


@router.put("/config", response_model=ResourceResponse)
async def update_word_of_the_day_config(
    default_batch_size: int = Query(None, ge=5, le=100),
    min_batch_threshold: int = Query(None, ge=1, le=20),
    max_previous_words: int = Query(None, ge=10, le=1000),
    generation_enabled: bool = Query(None),
) -> ResourceResponse:
    """Update global Word of the Day configuration.

    Query Parameters:
        - default_batch_size: Default number of words to generate
        - min_batch_threshold: Generate new batch when below this threshold
        - max_previous_words: Maximum previous words to consider
        - generation_enabled: Whether automatic generation is enabled

    Returns:
        Updated configuration.

    """
    config = await WordOfTheDayConfig.get_default()

    updated = False
    if default_batch_size is not None:
        config.default_batch_size = default_batch_size
        updated = True
    if min_batch_threshold is not None:
        config.min_batch_threshold = min_batch_threshold
        updated = True
    if max_previous_words is not None:
        config.max_previous_words = max_previous_words
        updated = True
    if generation_enabled is not None:
        config.generation_enabled = generation_enabled
        updated = True

    if updated:
        config.updated_at = datetime.now()
        await config.save()

    return ResourceResponse(
        data=config.model_dump(),
        metadata={
            "updated_at": config.updated_at,
            "changes_applied": updated,
        },
    )


# Helper function for batch generation
async def _generate_new_batch(
    batch: WordOfTheDayBatch,
    ai: OpenAIConnector,
    count: int | None = None,
) -> None:
    """Generate new words for a batch."""
    config = await WordOfTheDayConfig.get_default()

    if not config.generation_enabled:
        raise Exception("Word generation is disabled")

    generation_count = count or config.default_batch_size
    context_params = batch.get_context_for_generation()

    # Generate words one by one to ensure variety
    new_words: list[WordOfTheDayEntry] = []
    for _ in range(generation_count):
        try:
            # Update previous words to include newly generated ones
            if new_words:
                existing_previous = context_params.get("previous_words", []) or []
                context_params["previous_words"] = existing_previous + [w.word for w in new_words]

            response = await ai.generate_word_of_the_day(
                context=context_params.get("context"),
                previous_words=context_params.get("previous_words"),
            )

            new_entry = WordOfTheDayEntry(
                word=response.word,
                definition=response.definition,
                etymology=response.etymology,
                example_usage=response.example_usage,
                fascinating_fact=response.fascinating_fact,
                difficulty_level=response.difficulty_level,
                memorable_aspect=response.memorable_aspect,
                confidence=response.confidence,
            )
            new_words.append(new_entry)

        except Exception as e:
            # Log error but continue with other words
            print(f"Failed to generate word {len(new_words) + 1}: {e}")
            continue

    if not new_words:
        raise Exception("Failed to generate any words")

    batch.add_words_to_batch(new_words)
    await batch.save()

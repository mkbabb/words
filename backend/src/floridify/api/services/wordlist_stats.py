"""Wordlist statistics computation service.

Pure aggregation logic extracted from WordListRepository — computes
denormalized stats (mastery distribution, retention rate, temperature)
via MongoDB pipelines and writes back to the WordList document.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId

from ...utils.logging import get_logger
from ...wordlist.constants import MasteryLevel
from ...wordlist.models import WordList, WordListItemDoc
from ...wordlist.stats import LearningStats

logger = get_logger(__name__)


async def recompute_stats(wordlist_id: PydanticObjectId) -> None:
    """Recompute denormalized stats on a WordList via aggregation pipeline.

    Aggregates WordListItemDoc rows to produce:
      - unique_words / total_words counts
      - words_mastered (gold-level count)
      - average_ease_factor, retention_rate

    Then persists the result on the WordList document for fast reads.
    """
    pipeline: list[dict[str, Any]] = [
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

    wordlist = await WordList.get(wordlist_id)
    if wordlist is None:
        logger.warning(f"recompute_stats: WordList {wordlist_id} not found")
        return
    wordlist.set_stats(unique_words, total_words, stats)
    await wordlist.save()


async def get_statistics(wordlist_id: PydanticObjectId) -> dict[str, Any]:
    """Get detailed statistics for a wordlist using aggregation pipelines.

    Returns mastery distribution, temperature distribution, due-for-review
    count, top-5 frequent words, and top-5 hot words.
    """
    wordlist = await WordList.get(wordlist_id)
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
    top_freq = (
        await WordListItemDoc.find({"wordlist_id": wordlist_id})
        .sort([("frequency", -1)])
        .limit(5)
        .to_list()
    )
    most_frequent = [w.model_dump(mode="json") for w in top_freq]

    # Top 5 hot words (uses index, returns only hot docs)
    hot = (
        await WordListItemDoc.find({"wordlist_id": wordlist_id, "temperature": "hot"})
        .sort([("last_visited", -1)])
        .limit(5)
        .to_list()
    )
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

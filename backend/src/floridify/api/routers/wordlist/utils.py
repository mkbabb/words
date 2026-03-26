"""Utility functions for wordlist searching using generalized SearchEngine."""

from typing import Any

from beanie import PydanticObjectId

from ....api.repositories import WordListRepository
from ....corpus.core import Corpus
from ....corpus.manager import get_tree_corpus_manager
from ....models import Word
from ....models.base import Language
from ....models.responses import SearchResponse
from ....search import Search, SearchMethod
from ....search.result import SearchResult
from ....wordlist.models import WordList, WordListItemDoc

# Map mode strings to SearchMethod enum values
_MODE_TO_METHOD: dict[str, SearchMethod] = {
    "exact": SearchMethod.EXACT,
    "fuzzy": SearchMethod.FUZZY,
    "semantic": SearchMethod.SEMANTIC,
}


async def enrich_search_results_with_wordlist_data(
    results: list[SearchResult],
    wordlist_id: PydanticObjectId,
) -> list[dict[str, Any]]:
    """Merge search results with WordListItemDoc data (mastery, temperature, etc.).

    Pattern mirrors list_words() in words.py — batch-fetch Word docs + items, then merge.
    """
    if not results:
        return []

    # 1. Batch-fetch Word docs by text
    word_texts = [r.word for r in results]
    word_docs = await Word.find({"text": {"$in": word_texts}}).to_list()
    text_to_word_id = {w.text: w.id for w in word_docs}

    # 2. Batch-fetch WordListItemDocs for this wordlist
    word_ids = [wid for wid in text_to_word_id.values() if wid]
    items = await WordListItemDoc.find(
        {"wordlist_id": wordlist_id, "word_id": {"$in": word_ids}}
    ).to_list()
    word_id_to_item = {str(item.word_id): item for item in items}

    # 3. Merge search result with item data
    enriched: list[dict[str, Any]] = []
    # Fields to strip from item dump (internal FKs)
    _strip_keys = {"id", "word_id", "wordlist_id", "revision_id"}

    for result in results:
        entry = result.model_dump(mode="json")
        word_id = text_to_word_id.get(result.word)
        if word_id:
            item = word_id_to_item.get(str(word_id))
            if item:
                # Apply lazy temperature cooling
                item.update_temperature()
                item_data = item.model_dump(mode="json")
                for k in _strip_keys:
                    item_data.pop(k, None)
                entry.update(item_data)
        enriched.append(entry)

    return enriched


async def search_wordlist_names(
    query: str,
    owner_id: str | None = None,
    max_results: int = 20,
    # TODO[MEDIUM]: Remove compatibility-only `min_score` parameter once callers migrate.
    min_score: float = 0.6,  # noqa: ARG001 - retained for signature compatibility
    _repo: WordListRepository | None = None,
) -> list[dict[str, Any]]:
    """Basic case-insensitive search across wordlist names."""
    normalized_query = query.strip().lower()
    if not normalized_query:
        return []

    matches: list[dict[str, Any]] = []
    cursor = WordList.find({"name": {"$regex": normalized_query, "$options": "i"}})
    for wordlist in await cursor.limit(max_results).to_list():
        matches.append(
            {
                "wordlist": wordlist.model_dump(mode="json"),
                "score": 1.0,
            },
        )

    return matches


async def search_words_in_wordlist(
    wordlist_id: PydanticObjectId,
    query: str,
    max_results: int = 20,
    min_score: float = 0.6,
    mode: str | None = None,
    repo: WordListRepository | None = None,
    collect_all_matches: bool = False,
) -> SearchResponse:
    """Search words in a wordlist using generalized SearchEngine.

    Args:
        wordlist_id: ID of the wordlist to search within.
        query: Search query string.
        max_results: Maximum number of results to return.
        min_score: Minimum similarity score threshold.
        mode: Search mode — "smart", "exact", "fuzzy", "semantic".
            None or "smart" triggers the full cascade.
        repo: Optional repository instance for dependency injection.
    """
    repository = repo or WordListRepository()

    wordlist = await repository.get(wordlist_id, raise_on_missing=True)
    if not wordlist:
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            languages=[Language.ENGLISH],
            mode="smart",
            metadata={},
        )

    items = await WordListItemDoc.find({"wordlist_id": wordlist_id}).to_list()
    if not items:
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            languages=[Language.ENGLISH],
            mode=mode or "smart",
            metadata={},
        )

    word_ids = [item.word_id for item in items if item.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_texts = [word.text for word in words]

    if not word_texts:
        language = _resolve_wordlist_language(wordlist)
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            languages=[language],
            mode=mode or "smart",
            metadata={},
        )

    # Always enable semantic so embeddings build in background
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_tree_corpus_manager()
    existing_corpus = await corpus_manager.get_corpus(corpus_name=corpus_name)
    if existing_corpus is None:
        corpus = await Corpus.create(
            corpus_name=corpus_name,
            vocabulary=word_texts,
        )
        saved = await corpus_manager.save_corpus(corpus=corpus)
        if not saved:
            raise ValueError(f"Failed to save corpus '{corpus_name}'")

    search_engine = await Search.get_or_create(
        corpus_name=corpus_name,
        min_score=min_score,
        semantic=True,
    )

    # Map mode string to SearchMethod; None/"smart" → None (smart cascade)
    method = _MODE_TO_METHOD.get(mode) if mode else None

    results = await search_engine.search(
        query=query,
        max_results=max_results,
        min_score=min_score,
        method=method,
        collect_all_matches=collect_all_matches,
    )

    language = _resolve_wordlist_language(wordlist)
    search_mode = mode or "smart"
    return SearchResponse(
        query=query,
        results=results,
        total_found=len(results),
        languages=[language],
        mode=search_mode,
        metadata={"corpus_name": corpus_name, "mode": search_mode},
    )


async def post_filter_search_results(
    results: list[dict[str, Any]],
    wordlist_id: PydanticObjectId,
    mastery_levels: list[str] | None = None,
    hot_only: bool | None = None,
    due_only: bool | None = None,
) -> list[dict[str, Any]]:
    """Post-filter search results by mastery, temperature, and due status.

    Fast path: if results are already enriched (have mastery_level key), filter directly.
    Slow path: batch-fetch WordListItemDoc from DB (legacy callers).
    """

    if not results or not any([mastery_levels, hot_only, due_only]):
        return results

    # Fast path: enriched dicts already contain item fields
    if results and "mastery_level" in results[0]:
        filtered = []
        for result in results:
            if mastery_levels and result.get("mastery_level") not in mastery_levels:
                continue
            if hot_only and result.get("temperature") != "hot":
                continue
            if due_only:
                # Check review_data.next_review_date
                review_data = result.get("review_data", {})
                next_review = review_data.get("next_review_date") if review_data else None
                if not next_review:
                    continue
                from datetime import UTC, datetime
                try:
                    if datetime.fromisoformat(next_review) > datetime.now(UTC):
                        continue
                except (ValueError, TypeError):
                    continue
            filtered.append(result)
        return filtered

    # Slow path: fetch from DB (legacy)
    word_texts = [r.get("word", "") for r in results if r.get("word")]
    if not word_texts:
        return results

    word_docs = await Word.find({"text": {"$in": word_texts}}).to_list()
    word_text_to_id = {w.text: w.id for w in word_docs}

    word_ids = [wid for wid in word_text_to_id.values() if wid]
    items = await WordListItemDoc.find(
        {"wordlist_id": wordlist_id, "word_id": {"$in": word_ids}}
    ).to_list()
    word_id_to_item = {str(item.word_id): item for item in items}

    filtered = []
    for result in results:
        word_text = result.get("word", "")
        word_id = word_text_to_id.get(word_text)
        if not word_id:
            continue

        item = word_id_to_item.get(str(word_id))
        if not item:
            continue

        item.update_temperature()

        if mastery_levels and item.mastery_level not in mastery_levels:
            continue
        if hot_only and item.temperature != "hot":
            continue
        if due_only and not item.is_due_for_review():
            continue

        filtered.append(result)

    return filtered


def _resolve_wordlist_language(wordlist: WordList) -> Language:
    """Best-effort extraction of a Language value from wordlist metadata."""
    raw = wordlist.metadata.get("language")
    if isinstance(raw, Language):
        return raw
    if isinstance(raw, str):
        try:
            return Language(raw)
        except ValueError:
            return Language.ENGLISH
    return Language.ENGLISH

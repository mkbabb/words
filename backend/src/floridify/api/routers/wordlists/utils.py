"""Utility functions for wordlist searching using generalized SearchEngine."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ....search import SearchEngine
from ....search.corpus.manager import get_corpus_manager


class SearchResultItem(BaseModel):
    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: str = Field(..., description="Search method used")
    is_phrase: bool = Field(False, description="Whether this is a phrase")


def get_adaptive_min_score(query: str, base_score: float = 0.4) -> float:
    """Get adaptive minimum score - stubbed."""
    return base_score


async def search_wordlist_names(
    query: str,
    owner_id: str | None = None,
    max_results: int = 20,
    min_score: float = 0.6,
    repo: Any | None = None,
) -> list[dict[str, Any]]:
    """Search wordlist names using generalized SearchEngine."""
    from ....wordlist.models import WordList

    # Get all wordlist names
    if owner_id:
        wordlists = await WordList.find({"user_id": owner_id}).to_list()
    else:
        wordlists = await WordList.find().to_list()

    if not wordlists:
        return []

    # Extract names and create vocabulary
    vocabulary = [wl.name for wl in wordlists if wl.name]

    if not vocabulary:
        return []

    # Create/get corpus for wordlist names
    corpus_name = f"wordlist_names_{owner_id}" if owner_id else "wordlist_names_all"
    corpus_manager = get_corpus_manager()
    await corpus_manager.get_or_create_corpus(
        corpus_name=corpus_name, vocabulary=vocabulary, force_rebuild=False
    )

    # Create search engine and perform search
    search_engine = SearchEngine(
        corpus_name=corpus_name,
        min_score=min_score,
        semantic=False,  # Disable semantic for name search
    )
    await search_engine.initialize()

    results = await search_engine.search(query=query, max_results=max_results, min_score=min_score)

    # Map results back to wordlist objects with expected format
    name_to_wordlist = {wl.name: wl for wl in wordlists}
    search_results = []

    for result in results:
        if result.word in name_to_wordlist:
            wordlist = name_to_wordlist[result.word]
            search_results.append(
                {
                    "wordlist": {  # Return full wordlist object as expected by endpoint
                        "id": str(wordlist.id),
                        "name": wordlist.name,
                        "word_count": len(wordlist.words),
                        "description": wordlist.description,
                        "created_at": wordlist.created_at.isoformat()
                        if wordlist.created_at
                        else None,
                        "updated_at": wordlist.updated_at.isoformat()
                        if wordlist.updated_at
                        else None,
                    },
                    "score": result.score,
                }
            )

    return search_results


async def search_words_in_wordlist(
    wordlist_id: PydanticObjectId,
    query: str,
    max_results: int = 20,
    min_score: float = 0.6,
    repo: Any | None = None,
) -> list[dict[str, Any]]:
    """Search words in a wordlist using generalized SearchEngine."""
    from ....api.repositories import WordListRepository
    from ....models import Word

    # Get repository if not provided
    if repo is None:
        repo = WordListRepository()

    # Get wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    if not wordlist or not wordlist.words:
        return []

    # Get word texts for the wordlist - batch query
    word_ids = [w.word_id for w in wordlist.words if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_texts = [word.text for word in words]

    if not word_texts:
        return []

    # Create/get corpus for this wordlist
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_corpus_manager()
    await corpus_manager.get_or_create_corpus(
        corpus_name=corpus_name, vocabulary=word_texts, force_rebuild=False
    )

    # Create search engine and perform search
    search_engine = SearchEngine(
        corpus_name=corpus_name,
        min_score=min_score,
        semantic=False,  # Disable semantic for wordlist search
    )
    await search_engine.initialize()

    results = await search_engine.search(query=query, max_results=max_results, min_score=min_score)

    # Convert results to expected format
    return [
        {
            "word": result.word,
            "score": result.score,
            "method": result.method.value if result.method else "fuzzy",
        }
        for result in results
    ]


async def invalidate_wordlist_corpus(wordlist_id: PydanticObjectId) -> None:
    """Invalidate wordlist corpus when wordlist is modified."""
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_corpus_manager()
    await corpus_manager.invalidate_corpus(corpus_name)


async def invalidate_wordlist_names_corpus() -> None:
    """Invalidate wordlist names corpus when wordlists are added/removed/renamed."""
    corpus_manager = get_corpus_manager()
    # Invalidate all wordlist name corpora
    await corpus_manager.invalidate_corpus("wordlist_names_all")


async def get_corpus_stats() -> dict[str, Any]:
    """Get corpus statistics for monitoring."""
    corpus_manager = get_corpus_manager()
    return await corpus_manager.get_stats()

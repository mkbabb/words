"""Utility functions for wordlist searching using generalized SearchEngine."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ....api.repositories import WordListRepository
from ....corpus.manager import get_corpus_manager
from ....models import Word
from ....search import SearchEngine
from ..search import SearchResponse


async def search_wordlist_names(
    query: str,
    owner_id: str | None = None,
    max_results: int = 20,
    min_score: float = 0.6,
) -> None:
    """Search wordlist names using generalized SearchEngine."""
    raise NotImplementedError("search_wordlist_names is not implemented")


async def search_words_in_wordlist(
    wordlist_id: PydanticObjectId,
    query: str,
    max_results: int = 20,
    min_score: float = 0.6,
    repo: Any | None = None,
) -> SearchResponse:
    """Search words in a wordlist using generalized SearchEngine."""
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
        corpus_name=corpus_name,
        vocabulary=word_texts,
        force_rebuild=False,
    )

    # Create search engine and perform search
    search_engine = SearchEngine(
        corpus_name=corpus_name,
        min_score=min_score,
        semantic=False,  # Disable semantic for wordlist search
    )
    await search_engine.initialize()

    results = await search_engine.search(
        query=query,
        max_results=max_results,
        min_score=min_score,
    )

    # Convert results to expected format
    return SearchResponse(
        query=query,
        results=results,
        total_found=len(results),
        language=None,
    )

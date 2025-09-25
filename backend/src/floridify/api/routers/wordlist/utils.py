"""Utility functions for wordlist searching using generalized SearchEngine."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ....api.repositories import WordListRepository
from ....corpus.manager import get_corpus_manager
from ....models import Word
from ....models.base import Language
from ....search import Search
from ....wordlist.models import WordList
from ..search import SearchResponse


async def search_wordlist_names(
    query: str,
    owner_id: str | None = None,
    max_results: int = 20,
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
    repo: WordListRepository | None = None,
) -> SearchResponse:
    """Search words in a wordlist using generalized SearchEngine."""
    # Get repository if not provided
    repository = repo or WordListRepository()

    # Get wordlist
    wordlist = await repository.get(wordlist_id, raise_on_missing=True)
    if not wordlist or not wordlist.words:
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            language=Language.ENGLISH,
            metadata={},
        )

    # Get word texts for the wordlist - batch query
    word_ids = [w.word_id for w in wordlist.words if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_texts = [word.text for word in words]

    if not word_texts:
        language = _resolve_wordlist_language(wordlist)
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            language=language,
            metadata={},
        )

    # Create/get corpus for this wordlist
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_corpus_manager()
    existing_corpus = await corpus_manager.get_corpus(corpus_name=corpus_name)
    if existing_corpus is None:
        await corpus_manager.create_corpus(
            corpus_name=corpus_name,
            vocabulary=word_texts,
        )

    # Create search engine and perform search
    search_engine = await Search.from_corpus(
        corpus_name=corpus_name,
        min_score=min_score,
        semantic=False,  # Disable semantic for wordlist search
        config=None,
    )

    results = await search_engine.search(
        query=query,
        max_results=max_results,
        min_score=min_score,
    )

    # Convert results to expected format
    language = _resolve_wordlist_language(wordlist)
    return SearchResponse(
        query=query,
        results=results,
        total_found=len(results),
        language=language,
        metadata={"corpus_name": corpus_name},
    )


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

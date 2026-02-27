"""Shared fixtures for API integration tests.

These fixtures mock the heavy infrastructure (search indices, real providers, AI)
that the lookup pipeline needs, while keeping the REST layer and MongoDB real.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from floridify.caching.core import get_global_cache
from floridify.models.base import Language, ModelInfo
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Pronunciation,
    Word,
)
from floridify.models.parameters import SearchParams
from floridify.models.responses import SearchResponse
from floridify.search.models import SearchResult


@pytest_asyncio.fixture
async def mock_search_pipeline(test_db):
    """Mock _cached_search to bypass LanguageSearch/corpus index infrastructure.

    Queries the MongoDB Word collection directly using simple string matching,
    simulating exact and fuzzy search behavior for API-level tests.
    """
    from rapidfuzz import fuzz

    from floridify.search.constants import SearchMethod

    async def _mock_cached_search(query: str, params: SearchParams) -> SearchResponse:
        """Search Word documents in the test DB directly."""
        query_lower = query.strip().lower()

        if not query_lower:
            # Simulate validation — the router checks this before calling
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Empty query")

        if len(query_lower) > 200:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Query too long")

        # Find all words in the test DB
        all_words = await Word.find_all().to_list()

        results: list[SearchResult] = []
        for word_doc in all_words:
            word_text = word_doc.text.lower()

            # Exact match
            if word_text == query_lower:
                results.append(
                    SearchResult(
                        word=word_doc.text,
                        score=1.0,
                        method=SearchMethod.EXACT,
                        language=word_doc.language,
                    )
                )
            else:
                # Fuzzy match using rapidfuzz
                ratio = fuzz.WRatio(query_lower, word_text) / 100.0
                if ratio >= params.min_score:
                    results.append(
                        SearchResult(
                            word=word_doc.text,
                            score=ratio,
                            method=SearchMethod.FUZZY,
                            language=word_doc.language,
                        )
                    )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[: params.max_results]

        return SearchResponse(
            query=query,
            results=results,
            total_found=len(results),
            languages=params.languages,
            mode=params.mode,
            metadata={},
        )

    with patch(
        "floridify.api.routers.search._cached_search",
        side_effect=_mock_cached_search,
    ):
        yield _mock_cached_search


async def _clear_api_cache() -> None:
    """Clear the global L1+L2 cache to prevent stale results across tests.

    The @cached_api_call_with_dedup decorator persists to L2 diskcache on disk,
    which can return stale data from previous test runs (different test DBs).
    """
    cache = await get_global_cache()
    await cache.clear()


async def _build_synthesis_entry_for_word(word_text: str) -> DictionaryEntry | None:
    """Build a DictionaryEntry (synthesis) for a word, using existing DB data or creating new.

    If Word + Definitions already exist in the test DB, wraps them.
    Otherwise, creates a Word, a default Definition, and a Pronunciation.
    Returns a SYNTHESIS DictionaryEntry referencing the real documents.
    """
    # Try to find existing word
    word_obj = await Word.find_one(Word.text == word_text)

    if word_obj:
        # Use existing definitions
        definitions = await Definition.find(Definition.word_id == word_obj.id).to_list()
        definition_ids = [d.id for d in definitions if d.id]

        # Find existing pronunciation
        pronunciation = await Pronunciation.find_one(Pronunciation.word_id == word_obj.id)
        pronunciation_id = pronunciation.id if pronunciation else None
    else:
        # Create new word
        word_obj = Word(text=word_text, language=Language.ENGLISH)
        await word_obj.save()

        # Create a default definition
        definition = Definition(
            word_id=word_obj.id,
            part_of_speech="noun",
            text=f"A test definition for {word_text}",
            providers=[DictionaryProvider.WIKTIONARY],
        )
        await definition.save()
        definition_ids = [definition.id]

        # Create pronunciation
        pronunciation = Pronunciation(
            word_id=word_obj.id,
            phonetic=f"/{word_text}/",
        )
        await pronunciation.save()
        pronunciation_id = pronunciation.id

    # Create synthesis entry
    synth = DictionaryEntry(
        word_id=word_obj.id,
        definition_ids=definition_ids,
        pronunciation_id=pronunciation_id,
        provider=DictionaryProvider.SYNTHESIS,
        language=Language.ENGLISH,
    )
    await synth.save()
    return synth


@pytest_asyncio.fixture
async def mock_lookup_pipeline(test_db):
    """Mock lookup_word_pipeline to bypass search indices and real providers.

    The mock creates real MongoDB documents (Word, Definition, DictionaryEntry)
    in the test database, so the DictionaryEntryLoader can resolve them normally.
    This ensures the full API response serialization path is tested.

    For words already created via word_factory/definition_factory, the mock
    wraps the existing documents into a synthesis entry.
    """
    # Clear L1+L2 cache to prevent stale hits from previous test runs
    await _clear_api_cache()

    async def _mock_pipeline(
        word,
        providers=None,
        languages=None,
        semantic=True,
        no_ai=False,
        force_refresh=False,
        state_tracker=None,
    ):
        return await _build_synthesis_entry_for_word(word)

    with patch(
        "floridify.api.routers.lookup.lookup_word_pipeline",
        side_effect=_mock_pipeline,
    ):
        yield _mock_pipeline


@pytest_asyncio.fixture
async def mock_lookup_pipeline_with_ai(test_db):
    """Same as mock_lookup_pipeline but also sets model_info on the synthesis entry.

    Use this for tests that assert on AI model metadata.
    """
    await _clear_api_cache()

    async def _mock_pipeline(
        word,
        providers=None,
        languages=None,
        semantic=True,
        no_ai=False,
        force_refresh=False,
        state_tracker=None,
    ):
        entry = await _build_synthesis_entry_for_word(word)
        if entry and not no_ai:
            entry.model_info = ModelInfo(
                name="gpt-4",
                confidence=0.95,
                temperature=0.7,
            )
            await entry.save()
        return entry

    with patch(
        "floridify.api.routers.lookup.lookup_word_pipeline",
        side_effect=_mock_pipeline,
    ):
        yield _mock_pipeline


@pytest_asyncio.fixture
async def mock_streaming_lookup(test_db):
    """Mock dependencies for the streaming endpoint.

    The streaming endpoint uses _lookup_with_tracking which has its own
    cache check logic before calling lookup_word_pipeline. We need to
    mock both the cache check and the pipeline.
    """
    await _clear_api_cache()

    async def _mock_get_synthesized_entry(word_text):
        """Return None to skip the DB cache in streaming path."""
        return None

    async def _mock_pipeline(
        word,
        providers=None,
        languages=None,
        semantic=True,
        no_ai=False,
        force_refresh=False,
        state_tracker=None,
    ):
        entry = await _build_synthesis_entry_for_word(word)

        # If state_tracker provided, simulate progress updates
        if state_tracker:
            from floridify.core.state_tracker import Stages

            await state_tracker.update_stage(Stages.SEARCH_START)
            await state_tracker.update_stage(Stages.SEARCH_COMPLETE)
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)
            await state_tracker.update_stage(Stages.COMPLETE)

        return entry

    with (
        patch(
            "floridify.api.routers.lookup.lookup_word_pipeline",
            side_effect=_mock_pipeline,
        ),
        patch(
            "floridify.api.routers.lookup.get_synthesized_entry",
            side_effect=_mock_get_synthesized_entry,
        ),
    ):
        yield _mock_pipeline

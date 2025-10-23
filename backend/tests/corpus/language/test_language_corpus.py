"""LanguageCorpus tree operations using stubbed providers."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.providers.language.models import LanguageEntry, LanguageSource, ParserType
from floridify.providers.language.scraper.url import URLLanguageConnector


class StubConnector(URLLanguageConnector):
    """Connector backed by MockTransport for deterministic behaviours."""

    def __init__(self) -> None:
        super().__init__()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/primary"):
                return httpx.Response(200, text="alpha\nbeta\nalpha beta")
            if request.url.path.endswith("/secondary"):
                payload = {"vocabulary": ["gamma"], "phrases": ["gamma ray"]}
                return httpx.Response(200, text=json.dumps(payload))
            return httpx.Response(404, text="")

        self._scraper_session = httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest_asyncio.fixture
async def connector() -> StubConnector:
    stub = StubConnector()
    try:
        yield stub
    finally:
        await stub.close()


@pytest.mark.asyncio
async def test_add_language_source_builds_child(connector: StubConnector, test_db) -> None:
    corpus = LanguageCorpus(
        corpus_name="language_parent",
        language=Language.ENGLISH,
        vocabulary=[],
        corpus_type=CorpusType.LANGUAGE,
        is_master=True,
    )
    await corpus.save()

    source = LanguageSource(
        name="primary",
        url="https://example.com/primary",
        parser=ParserType.TEXT_LINES,
        language=Language.ENGLISH,
    )

    child_id = await corpus.add_language_source(source, connector=connector)
    assert child_id is not None

    # Use corpus_name (stable across versions) instead of corpus_id (changes with each version)
    refreshed = await TreeTreeCorpusManager().get_corpus(corpus_name=corpus.corpus_name)
    assert refreshed is not None
    assert len(refreshed.child_uuids) == 1
    assert sorted(refreshed.vocabulary) == ["alpha", "alpha beta", "beta"]


@pytest.mark.asyncio
async def test_remove_language_source(connector: StubConnector, test_db) -> None:
    corpus = LanguageCorpus(
        corpus_name="language_parent_remove",
        language=Language.ENGLISH,
        vocabulary=[],
        corpus_type=CorpusType.LANGUAGE,
        is_master=True,
    )
    await corpus.save()

    source = LanguageSource(
        name="secondary",
        url="https://example.com/secondary",
        parser=ParserType.JSON_VOCABULARY,
        language=Language.ENGLISH,
    )
    child_id = await corpus.add_language_source(source, connector=connector)
    assert child_id is not None
    # Get the child to check its UUID is in parent's child_uuids
    child = await TreeTreeCorpusManager().get_corpus(corpus_id=child_id)
    assert child is not None
    assert child.corpus_uuid in corpus.child_uuids

    await corpus.remove_source("secondary")

    # Force fresh read from database, bypassing cache
    from floridify.caching.models import VersionConfig

    # Use corpus_name (stable across versions) instead of corpus_id (changes with each version)
    updated = await TreeTreeCorpusManager().get_corpus(
        corpus_name=corpus.corpus_name,
        config=VersionConfig(use_cache=False),
    )
    assert updated is not None
    assert updated.child_uuids == []
    assert updated.vocabulary == []


@pytest.mark.asyncio
async def test_create_from_language_uses_all_sources(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    class FixedConnector(URLLanguageConnector):
        async def fetch_source(
            self,
            source: LanguageSource,
            config=None,
            state_tracker=None,
        ) -> LanguageEntry | None:
            return LanguageEntry(
                provider=self.provider,
                source=source,
                vocabulary=[f"{source.name}_word"],
                phrases=[],
                idioms=[],
                metadata={},
            )

    monkeypatch.setattr("floridify.corpus.language.core.URLLanguageConnector", FixedConnector)

    from floridify.providers.language.sources import LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE

    # Get all sources for English - this is what create_from_language actually uses
    sources = LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE[Language.ENGLISH]

    corpus = await LanguageCorpus.create_from_language(
        corpus_name="composed",
        language=Language.ENGLISH,
    )

    assert corpus.is_master is True
    assert len(corpus.child_uuids) == len(sources)
    assert all(source.name in "".join(corpus.vocabulary) for source in sources)

"""GutenbergConnector tests without network access."""

from __future__ import annotations

import pytest

from floridify.models.base import Language
from floridify.models.literature import AuthorInfo, Genre, Period
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.models import LiteratureEntry

SAMPLE_HEADER_TEXT = """
*** START OF THIS PROJECT GUTENBERG EBOOK TEST ***
This is the core content.
*** END OF THIS PROJECT GUTENBERG EBOOK TEST ***
"""

SAMPLE_SEARCH_HTML = """
<ul>
  <li class="booklink">
    <a class="link" href="/ebooks/123">
      <span class="title">Sample Work</span>
      <span class="subtitle">Sample Author</span>
      <span>456 downloads</span>
    </a>
  </li>
</ul>
"""


@pytest.mark.asyncio
async def test_download_work_cleans_headers(monkeypatch: pytest.MonkeyPatch, test_db) -> None:
    connector = GutenbergConnector()

    async def fake_fetch_content(source_id: str, metadata: dict[str, str]) -> str:
        return SAMPLE_HEADER_TEXT

    monkeypatch.setattr(connector, "_fetch_work_content", fake_fetch_content)

    work = LiteratureEntry(
        title="Test Work",
        author=AuthorInfo(name="Tester", period=Period.CONTEMPORARY, primary_genre=Genre.NOVEL),
        gutenberg_id="999",
        language=Language.ENGLISH,
    )

    cleaned = await connector.download_work(work)
    assert cleaned.strip() == "This is the core content."


@pytest.mark.asyncio
async def test_search_works_parses_catalog(monkeypatch: pytest.MonkeyPatch, test_db) -> None:
    connector = GutenbergConnector()

    class StubClient:
        async def get(self, url: str, params: dict[str, str] | None = None) -> object:  # noqa: ARG002
            return type("Resp", (), {"text": SAMPLE_SEARCH_HTML})()

    class StubScraper:
        async def __aenter__(self) -> StubClient:
            return StubClient()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(
        "floridify.providers.literature.api.gutenberg.respectful_scraper",
        lambda name, config: StubScraper(),
    )

    results = await connector.search_works(author_name="Sample", limit=1)
    assert len(results) == 1
    entry = results[0]
    assert entry["source_id"] == "123"
    assert entry["title"] == "Sample Work"
    assert entry["download_count"] == 456


@pytest.mark.asyncio
async def test_fetch_from_provider_returns_text(monkeypatch: pytest.MonkeyPatch, test_db) -> None:
    connector = GutenbergConnector()

    async def fake_fetch_content(source_id: str, metadata: dict[str, str]) -> str:
        return SAMPLE_HEADER_TEXT

    async def fake_fetch_metadata(
        source_id: str,
        title: str | None,
        author_name: str | None,
    ) -> dict[str, str]:
        return {
            "title": title or "Test",
            "author": author_name or "Tester",
            "source_url": "https://example.com",
        }

    monkeypatch.setattr(connector, "_fetch_work_content", fake_fetch_content)
    monkeypatch.setattr(connector, "_fetch_work_metadata", fake_fetch_metadata)

    entry = await connector._fetch_from_provider("123")
    assert isinstance(entry, str)
    assert entry.strip() == "This is the core content."

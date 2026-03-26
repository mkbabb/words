"""Tests for the wordlist reconcile-preview API helper."""

from types import SimpleNamespace

import pytest

from floridify.models.base import Language
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.result import SearchResult
from floridify.api.repositories.wordlist_repository import WordListEntryInput
from floridify.wordlist.reconcile import build_reconcile_preview


class _FakeQuery:
    def __init__(self, docs: list[SimpleNamespace]) -> None:
        self._docs = docs

    async def to_list(self) -> list[SimpleNamespace]:
        return self._docs


class _FakeLanguageSearch:
    async def search_with_mode(
        self,
        query: str,
        mode: SearchMode,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        if query == "teh":
            return [
                SearchResult(word="the", score=0.93, method=SearchMethod.FUZZY),
                SearchResult(word="ten", score=0.71, method=SearchMethod.FUZZY),
            ][:max_results]
        return []


@pytest.mark.asyncio
async def test_reconcile_preview_classifies_exact_and_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    from floridify.wordlist import reconcile as reconcile_module

    exact_doc = SimpleNamespace(id="word-1", text="apple", normalized="apple")
    fuzzy_doc = SimpleNamespace(id="word-2", text="the", normalized="the")
    alt_doc = SimpleNamespace(id="word-3", text="ten", normalized="ten")

    async def fake_get_language_search(languages: list[Language], semantic: bool = False):
        assert languages == [Language.ENGLISH]
        assert semantic is False
        return _FakeLanguageSearch()

    def fake_word_find(query: dict[str, object]) -> _FakeQuery:
        if "normalized" in query:
            values = query["normalized"]
            assert isinstance(values, dict)
            wanted = set(values.get("$in", []))
            docs = [exact_doc] if "apple" in wanted else []
            return _FakeQuery(docs)
        if "text" in query:
            values = query["text"]
            assert isinstance(values, dict)
            wanted = set(values.get("$in", []))
            docs = [doc for doc in [fuzzy_doc, alt_doc] if doc.text in wanted]
            return _FakeQuery(docs)
        return _FakeQuery([])

    monkeypatch.setattr(reconcile_module, "get_language_search", fake_get_language_search)
    monkeypatch.setattr(reconcile_module.Word, "find", fake_word_find)

    response = await build_reconcile_preview(
        [
            "apple",
            WordListEntryInput(source_text="teh", frequency=2, notes="check spelling"),
        ],
        limit=3,
        min_score=0.55,
    )

    assert response.summary.total_entries == 2
    assert response.summary.exact_entries == 1
    assert response.summary.ambiguous_entries == 1
    assert response.summary.unresolved_entries == 0

    assert response.exact[0].resolved_text == "apple"
    assert response.ambiguous[0].resolved_text == "the"
    assert response.ambiguous[0].candidates[0].word == "the"

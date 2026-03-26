"""Wordlist reconciliation helpers.

Used by upload/add-word flows to preview likely misspellings before commit.
"""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ..models import Word
from ..models.base import Language
from ..search.constants import SearchMode
from ..search.language import get_language_search
from ..text import normalize
from ..utils.logging import get_logger
from ..api.repositories.wordlist_repository import WordListEntryInput, WordListRepository
from .models import WordListItemDoc

logger = get_logger(__name__)


class ReconcilePreviewRequest(BaseModel):
    """Request body for word reconciliation previews."""

    entries: list[str | WordListEntryInput] = Field(
        ...,
        min_length=1,
        description="Words or structured entries to preview",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Candidate limit per entry")
    min_score: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for reconciliation candidates",
    )


class ReconcileCandidate(BaseModel):
    """A single reconciliation candidate."""

    word: str = Field(..., description="Suggested canonical word")
    word_id: str | None = Field(default=None, description="Matched word document id")
    score: float = Field(..., ge=0.0, le=1.0, description="Candidate score")
    method: str = Field(..., description="Search method that produced the suggestion")
    lemmatized_word: str | None = Field(default=None, description="Underlying lemma if known")
    already_in_wordlist: bool = Field(
        default=False,
        description="Whether the candidate is already present in the target wordlist",
    )


class ReconcilePreviewItem(BaseModel):
    """Preview data for a single input entry."""

    source_text: str = Field(..., description="Original input text")
    resolved_text: str | None = Field(default=None, description="Suggested canonical text")
    frequency: int = Field(default=1, ge=1, description="Occurrence count")
    notes: str | None = Field(default=None, description="Original notes")
    tags: list[str] = Field(default_factory=list, description="Original tags")
    status: str = Field(..., description="exact, ambiguous, or unresolved")
    exact_match: bool = Field(default=False, description="Whether the entry matched exactly")
    candidates: list[ReconcileCandidate] = Field(
        default_factory=list,
        description="Ranked reconciliation candidates",
    )


class ReconcilePreviewSummary(BaseModel):
    """Aggregated summary for reconciliation preview results."""

    total_entries: int
    total_frequency: int
    exact_entries: int
    ambiguous_entries: int
    unresolved_entries: int
    exact_frequency: int
    ambiguous_frequency: int
    unresolved_frequency: int


class ReconcilePreviewResponse(BaseModel):
    """Response payload for reconciliation preview."""

    exact: list[ReconcilePreviewItem] = Field(default_factory=list)
    ambiguous: list[ReconcilePreviewItem] = Field(default_factory=list)
    unresolved: list[ReconcilePreviewItem] = Field(default_factory=list)
    summary: ReconcilePreviewSummary
    metadata: dict[str, Any] = Field(default_factory=dict)


def _entry_text(entry: str | WordListEntryInput) -> str:
    if isinstance(entry, WordListEntryInput):
        return (entry.resolved_text or entry.source_text).strip()
    return str(entry).strip()


async def build_reconcile_preview(
    entries: list[str | WordListEntryInput],
    *,
    limit: int = 5,
    min_score: float = 0.55,
    wordlist_id: PydanticObjectId | None = None,
) -> ReconcilePreviewResponse:
    """Build a reconciliation preview from structured or raw entries."""
    collapsed = WordListRepository._collapse_entries(entries)
    if not collapsed:
        return ReconcilePreviewResponse(
            summary=ReconcilePreviewSummary(
                total_entries=0,
                total_frequency=0,
                exact_entries=0,
                ambiguous_entries=0,
                unresolved_entries=0,
                exact_frequency=0,
                ambiguous_frequency=0,
                unresolved_frequency=0,
            ),
            metadata={"wordlist_id": str(wordlist_id) if wordlist_id else None},
        )

    # Batch exact lookups up front.
    normalized_texts = [normalize(_entry_text(entry)) for entry in collapsed]
    exact_docs = await Word.find(
        {
            "normalized": {"$in": normalized_texts},
            "languages": Language.ENGLISH.value,
        }
    ).to_list()
    normalized_to_exact_docs: dict[str, list[Word]] = {}
    for doc in exact_docs:
        normalized_to_exact_docs.setdefault(doc.normalized, []).append(doc)

    # Optional target wordlist membership lookup for duplicate/reconcile hints.
    target_word_ids: set[str] = set()
    if wordlist_id is not None:
        items = await WordListItemDoc.find({"wordlist_id": wordlist_id}).to_list()
        target_word_ids = {str(item.word_id) for item in items if item.word_id}

    search_engine = await get_language_search([Language.ENGLISH], semantic=False)

    exact_items: list[ReconcilePreviewItem] = []
    ambiguous_items: list[ReconcilePreviewItem] = []
    unresolved_items: list[ReconcilePreviewItem] = []

    total_frequency = 0
    exact_frequency = 0
    ambiguous_frequency = 0
    unresolved_frequency = 0

    for entry in collapsed:
        text = _entry_text(entry)
        normalized = normalize(text)
        total_frequency += entry.frequency

        exact_candidates = normalized_to_exact_docs.get(normalized, [])
        if exact_candidates:
            chosen = exact_candidates[0]
            candidate = ReconcileCandidate(
                word=chosen.text,
                word_id=str(chosen.id) if chosen.id else None,
                score=1.0,
                method="exact",
                lemmatized_word=None,
                already_in_wordlist=bool(chosen.id and str(chosen.id) in target_word_ids),
            )
            item = ReconcilePreviewItem(
                source_text=entry.source_text,
                resolved_text=chosen.text,
                frequency=entry.frequency,
                notes=entry.notes,
                tags=list(entry.tags),
                status="exact" if len(exact_candidates) == 1 else "ambiguous",
                exact_match=True,
                candidates=[candidate],
            )
            exact_items.append(item)
            exact_frequency += entry.frequency
            continue

        try:
            results = await search_engine.search_with_mode(
                query=text,
                mode=SearchMode.SMART,
                max_results=limit,
                min_score=min_score,
            )
        except Exception as exc:
            logger.warning(f"Reconcile preview search failed for '{text}': {exc}")
            results = []

        candidate_texts = [result.word for result in results]
        candidate_docs = await Word.find({"text": {"$in": candidate_texts}}).to_list()
        text_to_doc = {doc.text: doc for doc in candidate_docs}

        candidates = [
            ReconcileCandidate(
                word=result.word,
                word_id=str(text_to_doc[result.word].id) if result.word in text_to_doc and text_to_doc[result.word].id else None,
                score=result.score,
                method=result.method.value,
                lemmatized_word=result.lemmatized_word,
                already_in_wordlist=bool(
                    result.word in text_to_doc
                    and text_to_doc[result.word].id
                    and str(text_to_doc[result.word].id) in target_word_ids
                ),
            )
            for result in results
        ]

        if candidates:
            item = ReconcilePreviewItem(
                source_text=entry.source_text,
                resolved_text=candidates[0].word,
                frequency=entry.frequency,
                notes=entry.notes,
                tags=list(entry.tags),
                status="ambiguous",
                exact_match=False,
                candidates=candidates,
            )
            ambiguous_items.append(item)
            ambiguous_frequency += entry.frequency
        else:
            item = ReconcilePreviewItem(
                source_text=entry.source_text,
                resolved_text=None,
                frequency=entry.frequency,
                notes=entry.notes,
                tags=list(entry.tags),
                status="unresolved",
                exact_match=False,
                candidates=[],
            )
            unresolved_items.append(item)
            unresolved_frequency += entry.frequency

    summary = ReconcilePreviewSummary(
        total_entries=len(collapsed),
        total_frequency=total_frequency,
        exact_entries=len(exact_items),
        ambiguous_entries=len(ambiguous_items),
        unresolved_entries=len(unresolved_items),
        exact_frequency=exact_frequency,
        ambiguous_frequency=ambiguous_frequency,
        unresolved_frequency=unresolved_frequency,
    )

    return ReconcilePreviewResponse(
        exact=exact_items,
        ambiguous=ambiguous_items,
        unresolved=unresolved_items,
        summary=summary,
        metadata={
            "wordlist_id": str(wordlist_id) if wordlist_id else None,
            "limit": limit,
            "min_score": min_score,
            "search_mode": "smart",
            "semantic_enabled": False,
        },
    )

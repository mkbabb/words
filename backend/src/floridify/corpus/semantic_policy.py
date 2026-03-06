"""Semantic enablement policy helpers for corpus trees."""

from __future__ import annotations

from typing import Any

from ..caching.models import VersionConfig
from .core import Corpus


def compute_effective_semantic_state(
    explicit: bool | None,
    child_states: list[bool],
) -> bool:
    """Compute child-to-parent OR semantic policy."""
    return bool(explicit is True or any(child_states))


async def _persist_effective_state(
    *,
    corpus: Corpus,
    effective: bool,
    save_corpus_fn: Any,
    config: VersionConfig | None = None,
) -> None:
    """Persist effective semantic state if it changed."""
    if corpus.semantic_enabled_effective == effective:
        return
    if not corpus.corpus_id:
        return

    corpus.semantic_enabled_effective = effective
    await save_corpus_fn(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        content=corpus.model_dump(mode="json"),
        corpus_type=corpus.corpus_type,
        language=corpus.language,
        parent_uuid=corpus.parent_uuid,
        child_uuids=corpus.child_uuids,
        is_master=corpus.is_master,
        semantic_enabled_explicit=corpus.semantic_enabled_explicit,
        semantic_enabled_effective=effective,
        semantic_model=corpus.semantic_model,
        config=config,
    )


async def recompute_semantic_effective_upward(
    *,
    start_corpus_uuid: str | None,
    get_corpus_fn: Any,
    get_corpora_by_uuids_fn: Any | None,
    save_corpus_fn: Any,
    config: VersionConfig | None = None,
) -> None:
    """Recompute effective semantic flags from a node up to root."""
    current_uuid = start_corpus_uuid
    visited: set[str] = set()

    while current_uuid and current_uuid not in visited:
        visited.add(current_uuid)
        current = await get_corpus_fn(corpus_uuid=current_uuid, config=config)
        if not current:
            return

        child_uuids = current.child_uuids or []
        child_states: list[bool] = []
        if child_uuids:
            if get_corpora_by_uuids_fn:
                children = await get_corpora_by_uuids_fn(child_uuids, config=config)
                child_states = [child.semantic_enabled_effective for child in children]
            else:
                for child_uuid in child_uuids:
                    child = await get_corpus_fn(corpus_uuid=child_uuid, config=config)
                    if child:
                        child_states.append(child.semantic_enabled_effective)

        effective = compute_effective_semantic_state(
            current.semantic_enabled_explicit, child_states
        )
        await _persist_effective_state(
            corpus=current,
            effective=effective,
            save_corpus_fn=save_corpus_fn,
            config=config,
        )

        current_uuid = current.parent_uuid


async def recompute_semantic_effective_subtree(
    *,
    root_corpus_uuid: str | None,
    get_corpus_fn: Any,
    save_corpus_fn: Any,
    config: VersionConfig | None = None,
) -> bool:
    """Recompute effective semantic flags bottom-up for a subtree."""
    if not root_corpus_uuid:
        return False

    root = await get_corpus_fn(corpus_uuid=root_corpus_uuid, config=config)
    if not root:
        return False

    child_states: list[bool] = []
    for child_uuid in root.child_uuids or []:
        child_states.append(
            await recompute_semantic_effective_subtree(
                root_corpus_uuid=child_uuid,
                get_corpus_fn=get_corpus_fn,
                save_corpus_fn=save_corpus_fn,
                config=config,
            )
        )

    effective = compute_effective_semantic_state(root.semantic_enabled_explicit, child_states)
    await _persist_effective_state(
        corpus=root,
        effective=effective,
        save_corpus_fn=save_corpus_fn,
        config=config,
    )
    return effective

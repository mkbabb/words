"""API tests for per-corpus semantic policy propagation and search gating."""

from __future__ import annotations

import pytest

from floridify.caching.models import VersionConfig
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
async def test_patch_semantic_policy_propagates_to_ancestor(async_client, test_db) -> None:
    manager = TreeCorpusManager()

    parent = await manager.save_corpus(
        corpus_name="policy_parent",
        content={"vocabulary": ["parent_word"]},
        corpus_type=CorpusType.CUSTOM,
        language=Language.ENGLISH,
        is_master=True,
        config=VersionConfig(use_cache=False),
    )
    assert parent and parent.corpus_id and parent.corpus_uuid

    child = await manager.save_corpus(
        corpus_name="policy_child",
        content={"vocabulary": ["child_word"]},
        corpus_type=CorpusType.CUSTOM,
        language=Language.ENGLISH,
        parent_uuid=parent.corpus_uuid,
        config=VersionConfig(use_cache=False),
    )
    assert child and child.corpus_id

    enable_resp = await async_client.patch(
        f"/api/v1/corpus/{child.corpus_id}/semantic",
        json={"enabled": True, "model_name": "all-MiniLM-L6-v2"},
    )
    assert enable_resp.status_code == 200
    enable_data = enable_resp.json()
    assert enable_data["semantic_enabled_explicit"] is True
    assert enable_data["semantic_enabled_effective"] is True
    assert enable_data["semantic_model"] == "all-MiniLM-L6-v2"

    parent_resp = await async_client.get(f"/api/v1/corpus/{parent.corpus_id}")
    assert parent_resp.status_code == 200
    parent_stats = parent_resp.json()["statistics"]
    assert parent_stats["semantic_enabled_effective"] is True

    disable_resp = await async_client.patch(
        f"/api/v1/corpus/{child.corpus_id}/semantic",
        json={"enabled": False},
    )
    assert disable_resp.status_code == 200
    disable_data = disable_resp.json()
    assert disable_data["semantic_enabled_explicit"] is False

    parent_after_disable = await async_client.get(f"/api/v1/corpus/{parent.corpus_id}")
    assert parent_after_disable.status_code == 200
    parent_after_stats = parent_after_disable.json()["statistics"]
    assert parent_after_stats["semantic_enabled_effective"] is False


@pytest.mark.asyncio
async def test_semantic_mode_rejected_when_corpus_policy_disabled(async_client, test_db) -> None:
    manager = TreeCorpusManager()
    corpus = await manager.save_corpus(
        corpus_name="policy_disabled_search",
        content={"vocabulary": ["perspicacious", "perceptive"]},
        corpus_type=CorpusType.CUSTOM,
        language=Language.ENGLISH,
        semantic_enabled_explicit=False,
        semantic_enabled_effective=False,
        config=VersionConfig(use_cache=False),
    )
    assert corpus and corpus.corpus_id

    semantic_resp = await async_client.get(
        "/api/v1/search/perspicacious",
        params={"corpus_id": str(corpus.corpus_id), "mode": "semantic"},
    )
    assert semantic_resp.status_code == 409
    assert "disabled by corpus policy" in semantic_resp.json()["detail"]

    smart_resp = await async_client.get(
        "/api/v1/search/perspicacious",
        params={"corpus_id": str(corpus.corpus_id), "mode": "smart"},
    )
    assert smart_resp.status_code == 200
    smart_data = smart_resp.json()
    assert smart_data["metadata"]["semantic_enabled_effective"] is False
    assert smart_data["metadata"]["semantic_disabled_reason"] == "corpus_policy"

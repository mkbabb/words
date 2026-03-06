"""Slimmed TreeCorpusManager: singleton, version manager init, delegation.

The manager class delegates all operations to standalone functions in:
  - corpus.crud: save, get, batch retrieval, stats
  - corpus.aggregation: aggregate vocabularies across tree hierarchy
  - corpus.tree: create tree, update parent, add/remove child, delete, invalidate
"""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ..caching.manager import VersionedDataManager, get_version_manager
from ..caching.models import VersionConfig
from ..models.base import Language
from ..utils.logging import get_logger

# Import helper modules
from . import aggregation as _agg, crud as _crud, tree as _tree
from .core import Corpus
from .models import CorpusType
from .semantic_policy import recompute_semantic_effective_upward

logger = get_logger(__name__)


class TreeCorpusManager:
    """Manager for hierarchical corpus structures with vocabulary aggregation."""

    def __init__(self, vm: VersionedDataManager | None = None) -> None:
        """Initialize with optional version manager.

        Args:
            vm: Version manager instance or None to use default

        """
        if vm is not None:
            self.vm = vm
        else:
            self.vm = get_version_manager()

    # ── Static helpers ──────────────────────────────────────────────

    @staticmethod
    def _remove_self_references(
        child_uuids: list[str] | None,
        corpus_uuid: str | None = None,
    ) -> list[str]:
        """Remove self-references from child_uuids list.

        Delegates to crud.remove_self_references.
        """
        return _crud.remove_self_references(child_uuids, corpus_uuid=corpus_uuid)

    # ── CRUD operations (delegated to corpus.crud) ──────────────────

    async def save_corpus_simple(
        self,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Simplified save that focuses on tree structure."""
        return await _crud.save_corpus_simple(vm=self.vm, corpus=corpus, config=config)

    async def save_metadata(self, metadata: Corpus.Metadata) -> Corpus.Metadata:
        """Save a Corpus.Metadata object directly to MongoDB."""
        return await _crud.save_metadata(metadata)

    async def save_corpus(
        self,
        corpus: Corpus | None = None,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        content: dict[str, Any] | None = None,
        corpus_type: CorpusType = CorpusType.LEXICON,
        language: Language = Language.ENGLISH,
        parent_uuid: str | None = None,
        child_uuids: list[str] | None = None,
        is_master: bool | None = None,
        semantic_enabled_explicit: bool | None = None,
        semantic_enabled_effective: bool | None = None,
        semantic_model: str | None = None,
        config: VersionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Corpus | None:
        """Save a corpus - ONLY saves data, does NOT manage relationships."""
        return await _crud.save_corpus(
            vm=self.vm,
            corpus=corpus,
            corpus_id=corpus_id,
            corpus_name=corpus_name,
            content=content,
            corpus_type=corpus_type,
            language=language,
            parent_uuid=parent_uuid,
            child_uuids=child_uuids,
            is_master=is_master,
            semantic_enabled_explicit=semantic_enabled_explicit,
            semantic_enabled_effective=semantic_enabled_effective,
            semantic_model=semantic_model,
            config=config,
            metadata=metadata,
            get_corpus_fn=self.get_corpus,
        )

    async def get_corpus_metadata(self, corpus_name: str) -> Corpus.Metadata | None:
        """Retrieve corpus metadata by resource id."""
        return await _crud.get_corpus_metadata(corpus_name)

    async def get_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Simple corpus retrieval by ID, uuid, or name - always returns latest version."""
        return await _crud.get_corpus(
            vm=self.vm,
            corpus_id=corpus_id,
            corpus_uuid=corpus_uuid,
            corpus_name=corpus_name,
            config=config,
        )

    async def get_corpora_by_ids(
        self,
        corpus_ids: list[PydanticObjectId],
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get multiple corpora by their IDs in batch."""
        return await _crud.get_corpora_by_ids(vm=self.vm, corpus_ids=corpus_ids, config=config)

    async def get_corpora_by_uuids(
        self,
        corpus_uuids: list[str],
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get multiple corpora by their UUIDs in batch (CRITICAL N+1 FIX)."""
        return await _crud.get_corpora_by_uuids(
            vm=self.vm, corpus_uuids=corpus_uuids, config=config
        )

    # ── Aggregation operations (delegated to corpus.aggregation) ────

    async def aggregate_vocabularies(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        config: VersionConfig | None = None,
        update_parent: bool = True,
    ) -> list[str]:
        """Aggregate vocabularies from a corpus and its children."""
        return await _agg.aggregate_vocabularies(
            vm=self.vm,
            corpus_id=corpus_id,
            corpus_uuid=corpus_uuid,
            config=config,
            update_parent=update_parent,
            get_corpus_fn=self.get_corpus,
            save_corpus_fn=self.save_corpus,
            recompute_semantic_fn=self._recompute_semantic_policy,
        )

    async def get_vocabulary(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        aggregate: bool = False,
        config: VersionConfig | None = None,
    ) -> list[str] | None:
        """Get vocabulary from a corpus."""
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name, config=config)
        if not corpus:
            return None

        if aggregate and corpus.corpus_id:
            return await self.aggregate_vocabularies(corpus.corpus_id, config)

        return corpus.vocabulary if corpus else []

    async def aggregate_vocabulary(
        self,
        corpus_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> bool:
        """Aggregate vocabulary from children and update parent."""
        return await _agg.aggregate_vocabulary(
            vm=self.vm,
            corpus_id=corpus_id,
            config=config,
            get_corpus_fn=self.get_corpus,
            save_corpus_fn=self.save_corpus,
        )

    async def aggregate_from_children(
        self,
        parent_corpus_id: PydanticObjectId | None = None,
        parent_corpus_uuid: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Aggregate vocabularies from parent and all children into a new corpus."""
        return await _agg.aggregate_from_children(
            vm=self.vm,
            parent_corpus_id=parent_corpus_id,
            parent_corpus_uuid=parent_corpus_uuid,
            config=config,
            get_corpus_fn=self.get_corpus,
            save_corpus_fn=self.save_corpus,
        )

    # ── Tree operations (delegated to corpus.tree) ──────────────────

    async def create_tree(
        self,
        master_id: PydanticObjectId | None = None,
        master_name: str | None = None,
        children: list[dict[str, Any]] | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Create a hierarchical corpus tree."""
        return await _tree.create_tree(
            vm=self.vm,
            master_id=master_id,
            master_name=master_name,
            children=children,
            config=config,
            save_corpus_fn=self.save_corpus,
        )

    async def get_tree(
        self,
        corpus_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get the tree structure of a corpus and its descendants."""
        return await _tree.get_tree(
            vm=self.vm,
            corpus_id=corpus_id,
            config=config,
            get_corpus_fn=self.get_corpus,
        )

    async def update_parent(
        self,
        parent_id: PydanticObjectId | Any,
        child_id: PydanticObjectId | Any,
        config: VersionConfig | None = None,
    ) -> bool | None:
        """Simple tree operation: add child to parent."""
        return await _tree.update_parent(
            vm=self.vm,
            parent_id=parent_id,
            child_id=child_id,
            config=config,
            get_corpus_fn=self.get_corpus,
            save_corpus_fn=self.save_corpus,
            would_create_cycle_fn=self._would_create_cycle,
            recompute_semantic_fn=self._recompute_semantic_policy,
        )

    async def update_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        content: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Update an existing corpus."""
        corpus = await self.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name, config=config)
        if not corpus:
            return None

        # Merge content into the corpus object
        existing_content = corpus.model_dump()
        if content:
            logger.info(f"update_corpus: updating content with {list(content.keys())}")
            existing_content.update(content)

        # Extract corpus-specific fields from content for metadata
        existing_metadata = {}
        corpus_specific_fields: dict[str, Any] = {}

        if metadata:
            # Extract corpus-specific fields from metadata
            for field in [
                "parent_uuid",
                "child_uuids",
                "is_master",
                "corpus_type",
                "language",
                "semantic_enabled_explicit",
                "semantic_enabled_effective",
                "semantic_model",
            ]:
                if field in metadata:
                    corpus_specific_fields[field] = metadata.pop(field)

            # Update remaining generic metadata
            existing_metadata.update(metadata)

        # Preserve existing child_uuids if not explicitly provided
        if "child_uuids" not in corpus_specific_fields:
            corpus_specific_fields["child_uuids"] = corpus.child_uuids

        # Preserve existing is_master if not explicitly provided
        if "is_master" not in corpus_specific_fields:
            corpus_specific_fields["is_master"] = corpus.is_master
        if "semantic_enabled_explicit" not in corpus_specific_fields:
            corpus_specific_fields["semantic_enabled_explicit"] = corpus.semantic_enabled_explicit
        if "semantic_enabled_effective" not in corpus_specific_fields:
            corpus_specific_fields["semantic_enabled_effective"] = corpus.semantic_enabled_effective
        if "semantic_model" not in corpus_specific_fields:
            corpus_specific_fields["semantic_model"] = corpus.semantic_model

        # Save updated corpus with corpus-specific fields
        logger.info(
            f"update_corpus: saving corpus {corpus.corpus_id} with vocabulary size {len(existing_content.get('vocabulary', []))}, is_master={corpus_specific_fields.get('is_master')}"
        )
        result = await self.save_corpus(
            corpus_id=corpus.corpus_id,
            corpus_name=corpus.corpus_name,
            content=existing_content,
            metadata=existing_metadata,
            **corpus_specific_fields,  # Pass corpus-specific fields directly
            config=config or VersionConfig(increment_version=True, use_cache=False),
        )
        logger.info(
            f"update_corpus: save result {result.corpus_id if result else None}, vocabulary size {len(result.vocabulary) if result else 'None'}, is_master={result.is_master if result else None}"
        )
        return result

    async def delete_corpus(
        self,
        corpus_id: PydanticObjectId | None = None,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        cascade: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Delete a corpus and optionally its children."""
        return await _tree.delete_corpus(
            vm=self.vm,
            corpus_id=corpus_id,
            corpus_uuid=corpus_uuid,
            corpus_name=corpus_name,
            cascade=cascade,
            config=config,
            get_corpus_fn=self.get_corpus,
            remove_child_fn=self.remove_child,
        )

    async def invalidate_corpus(self, corpus_name: str) -> bool:
        """Invalidate a specific corpus and all related caches."""
        return await _tree.invalidate_corpus(vm=self.vm, corpus_name=corpus_name)

    async def invalidate_all_corpora(self) -> int:
        """Invalidate all corpora and related caches."""
        return await _tree.invalidate_all_corpora(vm=self.vm)

    async def add_child(
        self,
        parent: Corpus,
        child: Corpus,
        config: VersionConfig | None = None,
    ) -> bool:
        """Add a child to a parent corpus."""
        return await _tree.add_child(
            vm=self.vm,
            parent=parent,
            child=child,
            config=config,
            update_parent_fn=self.update_parent,
        )

    async def get_children(
        self,
        parent_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get all child corpora of a parent (N+1 QUERY FIX)."""
        return await _tree.get_children(
            vm=self.vm,
            parent_id=parent_id,
            config=config,
            get_corpus_fn=self.get_corpus,
            get_corpora_by_uuids_fn=self.get_corpora_by_uuids,
        )

    async def remove_child(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        delete_child: bool = False,
        config: VersionConfig | None = None,
    ) -> bool:
        """Simple tree operation: remove child from parent."""
        return await _tree.remove_child(
            vm=self.vm,
            parent_id=parent_id,
            child_id=child_id,
            delete_child=delete_child,
            config=config,
            get_corpus_fn=self.get_corpus,
            save_corpus_fn=self.save_corpus,
            delete_corpus_fn=self.delete_corpus,
            recompute_semantic_fn=self._recompute_semantic_policy,
        )

    async def _recompute_semantic_policy(
        self,
        start_corpus_uuid: str | None,
        config: VersionConfig | None = None,
    ) -> None:
        """Recompute effective semantic flags from a node to root."""
        await recompute_semantic_effective_upward(
            start_corpus_uuid=start_corpus_uuid,
            get_corpus_fn=self.get_corpus,
            get_corpora_by_uuids_fn=self.get_corpora_by_uuids,
            save_corpus_fn=self.save_corpus,
            config=config,
        )

    async def recompute_semantic_policy(
        self,
        start_corpus_uuid: str | None,
        config: VersionConfig | None = None,
    ) -> None:
        """Public wrapper for semantic policy recomputation."""
        await self._recompute_semantic_policy(start_corpus_uuid=start_corpus_uuid, config=config)

    async def _would_create_cycle(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId,
        config: VersionConfig | None = None,
    ) -> bool:
        """Simple cycle detection: walk up from parent to see if we hit child."""
        return await _tree.would_create_cycle(
            vm=self.vm,
            parent_id=parent_id,
            child_id=child_id,
            config=config,
            get_corpus_fn=self.get_corpus,
        )


# Global tree corpus manager instance
_tree_corpus_manager: TreeCorpusManager | None = None


def get_tree_corpus_manager() -> TreeCorpusManager:
    """Get the global tree corpus manager instance.

    Returns:
        TreeCorpusManager singleton

    """
    global _tree_corpus_manager
    if _tree_corpus_manager is None:
        _tree_corpus_manager = TreeCorpusManager()
    return _tree_corpus_manager

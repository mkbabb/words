"""Corpus vocabulary aggregation operations.

Standalone async functions for aggregating vocabularies across hierarchical
corpus trees. Receives needed parameters from the TreeCorpusManager caller.
"""

from __future__ import annotations

import asyncio
from typing import Any

from beanie import PydanticObjectId

from ..caching.manager import VersionedDataManager
from ..caching.models import VersionConfig
from ..utils.logging import get_logger
from .core import Corpus

logger = get_logger(__name__)


async def aggregate_vocabularies(
    vm: VersionedDataManager,
    corpus_id: PydanticObjectId | None = None,
    corpus_uuid: str | None = None,
    config: VersionConfig | None = None,
    update_parent: bool = True,
    get_corpus_fn: Any = None,
    save_corpus_fn: Any = None,
) -> list[str]:
    """Aggregate vocabularies from a corpus and its children.

    Args:
        vm: Version manager instance
        corpus_id: Corpus MongoDB ID to aggregate from (deprecated, use corpus_uuid)
        corpus_uuid: Corpus stable UUID to aggregate from (preferred)
        config: Version configuration
        update_parent: Whether to update the parent corpus with aggregated vocabulary
        get_corpus_fn: Callable to get a corpus by id/uuid/name
        save_corpus_fn: Callable to save a corpus

    Returns:
        Aggregated vocabulary list

    """
    logger.info(
        f"aggregate_vocabularies: ENTER with corpus_id={corpus_id}, corpus_uuid={corpus_uuid}"
    )
    corpus = await get_corpus_fn(corpus_id=corpus_id, corpus_uuid=corpus_uuid, config=config)
    logger.info(
        f"aggregate_vocabularies: get_corpus returned corpus: {corpus is not None}, uuid={corpus.corpus_uuid if corpus else None}"
    )
    if not corpus:
        logger.warning("aggregate_vocabularies: corpus is None, returning empty list")
        return []

    # For master corpora, only aggregate children's vocabularies
    # Don't include the parent's own vocabulary since it's just an aggregate container
    vocabulary: set[str] = set()

    # Get child vocabularies recursively in parallel
    child_ids = corpus.child_uuids or []
    if child_ids:
        # Fetch all child vocabularies concurrently
        child_vocabs = await asyncio.gather(
            *[
                aggregate_vocabularies(
                    vm=vm,
                    corpus_uuid=cid,
                    config=config,
                    update_parent=False,
                    get_corpus_fn=get_corpus_fn,
                    save_corpus_fn=save_corpus_fn,
                )
                for cid in child_ids
            ],
            return_exceptions=True,
        )
        # Merge successful vocabularies
        for i, child_vocab in enumerate(child_vocabs):
            if isinstance(child_vocab, Exception):
                logger.error(
                    f"Failed to aggregate vocabulary for child {child_ids[i]}: {child_vocab}"
                )
            elif child_vocab:  # Ensure we have a valid vocabulary list
                vocabulary.update(child_vocab)

    # Determine whether to include the corpus's own vocabulary
    if corpus.is_master:
        # Master corpora never include their own vocabulary, only children's
        logger.info(f"Master corpus {corpus_id} - using only children's vocabulary")
    # Non-master corpora always include their own vocabulary
    elif corpus.vocabulary:
        vocabulary.update(corpus.vocabulary)

    aggregated = sorted(vocabulary)
    logger.info(
        f"aggregate_vocabularies: corpus_uuid={corpus.corpus_uuid}, is_master={corpus.is_master}, child_ids={child_ids}, aggregated={aggregated}, update_parent={update_parent}"
    )

    # Update the parent corpus with aggregated vocabulary if requested
    if update_parent and aggregated != corpus.vocabulary:
        corpus.vocabulary = aggregated
        corpus.unique_word_count = len(aggregated)
        corpus.total_word_count = len(aggregated)

        # Update vocabulary stats and indices
        corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(aggregated)}
        corpus.vocabulary_stats["unique_words"] = len(aggregated)
        corpus.vocabulary_stats["total_words"] = len(aggregated)

        # Rebuild unified indices (lemmatization, etc.) for the aggregated vocabulary
        logger.info(f"Rebuilding indices for aggregated corpus {corpus_id}")
        await corpus._create_unified_indices()
        corpus._build_signature_index()

        # Save the entire corpus with all rebuilt indices
        # This ensures lemmatization, signatures, etc. are persisted
        logger.info(f"Saving aggregated corpus {corpus_id} with all indices")
        await save_corpus_fn(
            corpus=corpus,
            config=config,
        )
        logger.info(f"Saved corpus {corpus_id} with vocabulary of size {len(aggregated)}")

    return aggregated


async def aggregate_vocabulary(
    vm: VersionedDataManager,
    corpus_id: PydanticObjectId,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    save_corpus_fn: Any = None,
) -> bool:
    """Aggregate vocabulary from children and update parent.

    Args:
        vm: Version manager instance
        corpus_id: Corpus ID
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        save_corpus_fn: Callable to save a corpus

    Returns:
        True if aggregation succeeded

    """
    aggregated = await aggregate_vocabularies(
        vm=vm,
        corpus_id=corpus_id,
        config=config,
        get_corpus_fn=get_corpus_fn,
        save_corpus_fn=save_corpus_fn,
    )
    return len(aggregated) > 0


async def aggregate_from_children(
    vm: VersionedDataManager,
    parent_corpus_id: PydanticObjectId | None = None,
    parent_corpus_uuid: str | None = None,
    config: VersionConfig | None = None,
    get_corpus_fn: Any = None,
    save_corpus_fn: Any = None,
) -> Corpus | None:
    """Aggregate vocabularies from parent and all children into a new corpus.

    Args:
        vm: Version manager instance
        parent_corpus_id: Parent corpus ID to aggregate from (deprecated, use parent_corpus_uuid)
        parent_corpus_uuid: Parent corpus UUID to aggregate from (preferred)
        config: Version configuration
        get_corpus_fn: Callable to get a corpus
        save_corpus_fn: Callable to save a corpus

    Returns:
        Corpus object with aggregated vocabulary from parent and children

    """
    # Get the parent corpus
    parent = await get_corpus_fn(
        corpus_id=parent_corpus_id, corpus_uuid=parent_corpus_uuid, config=config
    )
    if not parent:
        return None

    # Collect vocabularies from parent and children
    vocabulary = set()

    # Add parent's vocabulary if it exists
    if parent.vocabulary:
        vocabulary.update(parent.vocabulary)

    # Get child vocabularies recursively using existing aggregate_vocabularies method
    child_ids = parent.child_uuids or []
    for child_id in child_ids:
        child_vocab = await aggregate_vocabularies(
            vm=vm,
            corpus_uuid=child_id,
            config=config,
            update_parent=False,
            get_corpus_fn=get_corpus_fn,
            save_corpus_fn=save_corpus_fn,
        )
        vocabulary.update(child_vocab)

    # Create a new corpus with the aggregated vocabulary
    aggregated_vocab = sorted(vocabulary)

    # Create a copy of the parent corpus with the aggregated vocabulary
    aggregated_corpus_data = parent.model_dump()
    aggregated_corpus_data["vocabulary"] = aggregated_vocab
    aggregated_corpus_data["unique_word_count"] = len(aggregated_vocab)
    aggregated_corpus_data["total_word_count"] = len(aggregated_vocab)

    # Rebuild vocabulary index
    aggregated_corpus_data["vocabulary_to_index"] = {
        word: idx for idx, word in enumerate(aggregated_vocab)
    }

    # Update vocabulary stats
    if "vocabulary_stats" not in aggregated_corpus_data:
        aggregated_corpus_data["vocabulary_stats"] = {}
    aggregated_corpus_data["vocabulary_stats"]["unique_words"] = len(aggregated_vocab)
    aggregated_corpus_data["vocabulary_stats"]["total_words"] = len(aggregated_vocab)

    return Corpus.model_validate(aggregated_corpus_data)


__all__ = [
    "aggregate_from_children",
    "aggregate_vocabularies",
    "aggregate_vocabulary",
]

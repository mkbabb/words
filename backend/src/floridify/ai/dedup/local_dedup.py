"""Local 3-tier definition deduplication pipeline.

Replaces the AI deduplicate_definitions() call with a local pipeline that
uses canonicalized exact matching, fuzzy token matching, and semantic
embedding similarity. Returns the same DeduplicationResponse model for
drop-in compatibility.

Adapted from gaggle/content/generate/pipeline/ngram_dedup.py.
"""

from __future__ import annotations

import numpy as np
from rapidfuzz import fuzz

from ...models.base import DedupMergeRecord
from ...models.dictionary import Definition
from ...utils.logging import get_logger
from ..prompts.synthesize.models import (
    DeduplicatedDefinition,
    DeduplicationResponse,
)
from .canonicalize import canonicalize, extract_content_words

logger = get_logger(__name__)


def _tier1_exact(
    definitions: list[Definition],
) -> tuple[list[list[int]], list[DedupMergeRecord]]:
    """Tier 1: Group definitions with identical canonicalized text + POS.

    Returns:
        groups: list of index groups (each group shares the same canonical text)
        records: DedupMergeRecord for each merge decision
    """
    # Group by (POS, canonical_text)
    canonical_map: dict[tuple[str, str], list[int]] = {}
    for idx, defn in enumerate(definitions):
        key = (defn.part_of_speech, canonicalize(defn.text))
        canonical_map.setdefault(key, []).append(idx)

    groups: list[list[int]] = []
    records: list[DedupMergeRecord] = []

    for _key, indices in canonical_map.items():
        groups.append(indices)
        if len(indices) > 1:
            records.append(
                DedupMergeRecord(
                    kept_index=indices[0],
                    merged_indices=indices[1:],
                    reasoning="Identical after canonicalization",
                    similarity_score=1.0,
                    tier="exact",
                )
            )

    return groups, records


def _tier2_fuzzy(
    definitions: list[Definition],
    groups: list[list[int]],
    threshold: float = 85.0,
) -> tuple[list[list[int]], list[DedupMergeRecord]]:
    """Tier 2: Merge groups whose representative definitions are fuzzy-similar.

    Uses rapidfuzz token_sort_ratio on canonical text. Only compares
    definitions within the same POS and sharing at least one content word.
    """
    # Build representative text for each group
    group_reps: list[tuple[int, str, str, set[str]]] = []  # (group_idx, pos, canonical, content_words)
    for g_idx, indices in enumerate(groups):
        primary = definitions[indices[0]]
        canonical = canonicalize(primary.text)
        content = extract_content_words(primary.text)
        group_reps.append((g_idx, primary.part_of_speech, canonical, content))

    merged_groups: list[list[int]] = []
    consumed: set[int] = set()
    records: list[DedupMergeRecord] = []

    for i, (g_idx_i, pos_i, canon_i, content_i) in enumerate(group_reps):
        if g_idx_i in consumed:
            continue

        current_group = list(groups[g_idx_i])

        for j in range(i + 1, len(group_reps)):
            g_idx_j, pos_j, canon_j, content_j = group_reps[j]
            if g_idx_j in consumed:
                continue

            # Pre-filter: same POS and shared content words
            if pos_i != pos_j:
                continue
            if not (content_i & content_j):
                continue

            score = fuzz.token_sort_ratio(canon_i, canon_j)
            if score >= threshold:
                consumed.add(g_idx_j)
                merged_indices = groups[g_idx_j]
                current_group.extend(merged_indices)
                records.append(
                    DedupMergeRecord(
                        kept_index=groups[g_idx_i][0],
                        merged_indices=[groups[g_idx_j][0]],
                        reasoning=f"Fuzzy match (score={score:.0f})",
                        similarity_score=score / 100.0,
                        tier="fuzzy",
                    )
                )

        merged_groups.append(current_group)

    return merged_groups, records


async def _tier3_semantic(
    definitions: list[Definition],
    groups: list[list[int]],
    threshold: float = 0.88,
) -> tuple[list[list[int]], list[DedupMergeRecord]]:
    """Tier 3: Merge groups whose definitions are semantically equivalent.

    Uses the already-loaded Qwen3-0.6B SemanticEncoder for embeddings.
    Falls back gracefully if the encoder is unavailable.
    """
    if len(groups) <= 1:
        return groups, []

    from ..embedding_utils import encode_texts

    # Get representative text for each group
    texts = [definitions[g[0]].text for g in groups]
    pos_list = [definitions[g[0]].part_of_speech for g in groups]

    embeddings = await encode_texts(texts)
    if embeddings is None or len(embeddings) == 0:
        return groups, []

    # Compute pairwise cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
    normalized = embeddings / norms
    similarity_matrix = normalized @ normalized.T

    # Merge groups above threshold (same POS only)
    consumed: set[int] = set()
    merged_groups: list[list[int]] = []
    records: list[DedupMergeRecord] = []

    for i in range(len(groups)):
        if i in consumed:
            continue

        current_group = list(groups[i])

        for j in range(i + 1, len(groups)):
            if j in consumed:
                continue
            if pos_list[i] != pos_list[j]:
                continue

            sim = float(similarity_matrix[i, j])
            if sim >= threshold:
                consumed.add(j)
                current_group.extend(groups[j])
                records.append(
                    DedupMergeRecord(
                        kept_index=groups[i][0],
                        merged_indices=[groups[j][0]],
                        reasoning=f"Semantic match (cosine={sim:.3f})",
                        similarity_score=sim,
                        tier="semantic",
                    )
                )

        merged_groups.append(current_group)

    return merged_groups, records


def _select_best_definition(
    definitions: list[Definition],
    indices: list[int],
) -> int:
    """Select the best definition from a group of duplicates.

    Prefers the definition with the most metadata (synonyms, examples, etc.)
    and longest text.
    """
    if len(indices) == 1:
        return indices[0]

    def richness(idx: int) -> int:
        d = definitions[idx]
        return (
            len(d.synonyms)
            + len(d.antonyms)
            + len(d.example_ids)
            + len(d.collocations)
            + len(d.usage_notes)
            + len(d.text)  # Longer definitions are often more detailed
        )

    return max(indices, key=richness)


async def local_deduplicate_definitions(
    word: str,
    definitions: list[Definition],
    fuzzy_threshold: float = 85.0,
    semantic_threshold: float = 0.88,
    enable_semantic: bool = True,
) -> DeduplicationResponse:
    """Three-tier local deduplication pipeline.

    Drop-in replacement for ai.deduplicate_definitions(). Returns the same
    DeduplicationResponse model with the same contract.

    Args:
        word: The word being deduplicated.
        definitions: Raw definitions from all providers.
        fuzzy_threshold: rapidfuzz token_sort_ratio threshold (0-100).
        semantic_threshold: Cosine similarity threshold (0-1).
        enable_semantic: Whether to run Tier 3 (requires SemanticEncoder).

    Returns:
        DeduplicationResponse compatible with the AI version.
    """
    if len(definitions) <= 1:
        return DeduplicationResponse(
            deduplicated_definitions=[
                DeduplicatedDefinition(
                    part_of_speech=definitions[0].part_of_speech if definitions else "unknown",
                    definition=definitions[0].text if definitions else "",
                    source_indices=[0] if definitions else [],
                    quality_score=1.0,
                    reasoning="Single definition",
                )
            ]
            if definitions
            else [],
            removed_count=0,
            confidence=1.0,
        )

    all_merge_records: list[DedupMergeRecord] = []
    original_count = len(definitions)

    # Tier 1: Exact canonicalized match
    groups, records = _tier1_exact(definitions)
    all_merge_records.extend(records)
    tier1_removed = original_count - len(groups)
    if tier1_removed > 0:
        logger.info(f"Tier 1 (exact): {original_count} → {len(groups)} groups ({tier1_removed} merged)")

    # Tier 2: Fuzzy token match
    groups, records = _tier2_fuzzy(definitions, groups, threshold=fuzzy_threshold)
    all_merge_records.extend(records)
    tier2_count = len(groups)
    tier2_removed = (original_count - tier1_removed) - tier2_count
    if tier2_removed > 0:
        logger.info(f"Tier 2 (fuzzy): → {tier2_count} groups ({tier2_removed} merged)")

    # Tier 3: Semantic embedding match
    if enable_semantic:
        groups, records = await _tier3_semantic(definitions, groups, threshold=semantic_threshold)
        all_merge_records.extend(records)
        tier3_count = len(groups)
        tier3_removed = tier2_count - tier3_count
        if tier3_removed > 0:
            logger.info(f"Tier 3 (semantic): → {tier3_count} groups ({tier3_removed} merged)")

    # Build DeduplicatedDefinition for each group
    deduped: list[DeduplicatedDefinition] = []
    for group_indices in groups:
        best_idx = _select_best_definition(definitions, group_indices)
        best_def = definitions[best_idx]

        deduped.append(
            DeduplicatedDefinition(
                part_of_speech=best_def.part_of_speech,
                definition=best_def.text,
                source_indices=group_indices,
                quality_score=1.0,
                reasoning="Local 3-tier dedup" if len(group_indices) > 1 else "Unique",
            )
        )

    removed_count = original_count - len(deduped)
    logger.success(
        f"Local dedup for '{word}': {original_count} → {len(deduped)} "
        f"(removed {removed_count} duplicates)"
    )

    return DeduplicationResponse(
        deduplicated_definitions=deduped,
        removed_count=removed_count,
        confidence=0.95,  # High confidence for local dedup
    )

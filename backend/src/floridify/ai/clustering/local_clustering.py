"""Local definition clustering using sentence embeddings + agglomerative clustering.

Pre-groups definitions into sense clusters. When cluster quality is high
(silhouette score ≥ threshold), the result can be used directly without
AI refinement. When ambiguous, the result provides hints for the AI.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...models.dictionary import Definition
from ...utils.logging import get_logger

logger = get_logger(__name__)

# Silhouette score threshold for using local clusters directly (skipping AI)
SILHOUETTE_THRESHOLD = 0.4

# Cosine distance threshold for agglomerative clustering
_DEFAULT_DISTANCE_THRESHOLD = 0.55


def _wordnet_sense_count(word: str, pos: str | None = None) -> int | None:
    """Get number of WordNet synsets as a prior for cluster count."""
    try:
        from nltk.corpus import wordnet as wn
    except ImportError:
        return None

    pos_map = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
    wn_pos = pos_map.get(pos) if pos else None
    synsets = wn.synsets(word, pos=wn_pos)
    return len(synsets) if synsets else None


def _compute_cluster_quality(
    embeddings: np.ndarray,
    labels: list[int] | np.ndarray,
) -> float:
    """Compute silhouette score as a measure of cluster separation.

    Returns -1.0 if fewer than 2 clusters or all items in one cluster.
    """
    from sklearn.metrics import silhouette_score

    unique_labels = set(labels) if isinstance(labels, list) else set(labels.tolist())
    if len(unique_labels) < 2 or len(unique_labels) >= len(labels):
        return -1.0

    return float(silhouette_score(embeddings, labels, metric="cosine"))


def _cluster_embeddings(
    embeddings: np.ndarray,
    pos_list: list[str],
    distance_threshold: float = _DEFAULT_DISTANCE_THRESHOLD,
    word: str = "",
) -> tuple[list[list[int]], float]:
    """Cluster embeddings into sense groups using agglomerative clustering.

    Returns:
        (clusters, silhouette_score) — clusters is a list of index groups,
        silhouette is the quality metric (-1.0 if not computable).
    """
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_distances

    n = len(embeddings)
    if n <= 1:
        return [[i] for i in range(n)], -1.0

    # Group indices by POS
    pos_groups: dict[str, list[int]] = {}
    for i, pos in enumerate(pos_list):
        pos_groups.setdefault(pos, []).append(i)

    all_clusters: list[list[int]] = []
    all_labels = np.full(n, -1, dtype=int)
    label_offset = 0

    for pos, indices in pos_groups.items():
        if len(indices) <= 1:
            all_clusters.append(indices)
            all_labels[indices[0]] = label_offset
            label_offset += 1
            continue

        sub_embeddings = embeddings[indices]
        threshold = distance_threshold

        # Tighten threshold for words with many WordNet senses
        wn_count = _wordnet_sense_count(word, pos) if word else None
        if wn_count and wn_count >= 5 and len(indices) >= 5:
            threshold = min(threshold, 0.45)

        dist_matrix = cosine_distances(sub_embeddings)

        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=threshold,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(dist_matrix)

        cluster_map: dict[int, list[int]] = {}
        for sub_idx, label in enumerate(labels):
            cluster_map.setdefault(int(label), []).append(indices[sub_idx])
            all_labels[indices[sub_idx]] = int(label) + label_offset

        label_offset += max(labels) + 1
        all_clusters.extend(cluster_map.values())

    # Compute overall silhouette score
    silhouette = _compute_cluster_quality(embeddings, all_labels.tolist())

    return all_clusters, silhouette


@dataclass
class LocalClusterResult:
    """Result of local clustering with quality metrics."""

    clusters: list[list[int]]
    silhouette: float
    high_confidence: bool = False

    def __post_init__(self) -> None:
        self.high_confidence = self.silhouette >= SILHOUETTE_THRESHOLD


async def local_cluster_definitions(
    definitions: list[Definition],
    word: str = "",
) -> LocalClusterResult | None:
    """Pre-cluster definitions into sense groups with quality assessment.

    Args:
        definitions: Definitions to cluster.
        word: Word text (used for WordNet synset count prior).

    Returns:
        LocalClusterResult with clusters and quality metrics, or None if
        clustering is unavailable.
    """
    if len(definitions) <= 2:
        return None

    from ..embedding_utils import encode_texts

    texts = [d.text for d in definitions]
    pos_list = [d.part_of_speech for d in definitions]

    embeddings = await encode_texts(texts)
    if embeddings is None or len(embeddings) == 0:
        return None

    clusters, silhouette = _cluster_embeddings(embeddings, pos_list, word=word)

    result = LocalClusterResult(clusters=clusters, silhouette=silhouette)

    logger.info(
        f"Local clustering: {len(definitions)} defs → {len(clusters)} sense clusters "
        f"(silhouette={silhouette:.3f}, {'HIGH' if result.high_confidence else 'LOW'} confidence)"
    )

    return result


def format_cluster_hints(
    definitions: list[Definition],
    clusters: list[list[int]],
) -> str:
    """Format local clusters as hint text for AI refinement."""
    lines = [f"Pre-analysis suggests {len(clusters)} distinct senses:"]
    for i, indices in enumerate(clusters):
        texts = [definitions[idx].text[:80] for idx in indices]
        pos = definitions[indices[0]].part_of_speech
        lines.append(f"  Sense {i + 1} ({pos}, {len(indices)} defs): {'; '.join(texts)}")
    return "\n".join(lines)

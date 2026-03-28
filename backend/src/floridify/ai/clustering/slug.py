"""Deterministic slug and name generation for meaning clusters.

Produces consistent, readable slugs from definition content using TF-IDF
to identify the most salient word(s) per cluster. Format: {word}_{pos}_{salient}.
Deterministic: same input → same slug, no randomness, no AI.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ...models.dictionary import Definition
from ...text.constants import ENGLISH_STOPWORDS
from ...utils.logging import get_logger

logger = get_logger(__name__)


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alpha, filter stopwords and short tokens."""
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in ENGLISH_STOPWORDS and len(w) > 2]


def _tfidf_salient_word(
    cluster_texts: list[str],
    all_cluster_texts: list[list[str]],
) -> str:
    """Find the most salient word in this cluster via TF-IDF.

    TF = frequency in this cluster / total words in this cluster
    IDF = log(total_clusters / clusters_containing_word)
    """
    # Tokenize this cluster
    cluster_tokens = []
    for text in cluster_texts:
        cluster_tokens.extend(_tokenize(text))

    if not cluster_tokens:
        return "unknown"

    # TF for this cluster
    tf_counts = Counter(cluster_tokens)
    total_tokens = len(cluster_tokens)

    # Document frequency across all clusters
    n_clusters = len(all_cluster_texts)
    df: Counter[str] = Counter()
    for other_texts in all_cluster_texts:
        other_tokens = set()
        for text in other_texts:
            other_tokens.update(_tokenize(text))
        for token in other_tokens:
            df[token] += 1

    # TF-IDF scores
    scores: dict[str, float] = {}
    for token, count in tf_counts.items():
        tf = count / total_tokens
        idf = math.log((n_clusters + 1) / (df.get(token, 0) + 1))
        scores[token] = tf * idf

    # Return the highest-scoring word
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best


def generate_cluster_slug(
    word: str,
    pos: str,
    definitions: list[Definition],
    cluster_indices: list[int],
    all_clusters: list[list[int]],
) -> str:
    """Generate a deterministic, readable slug for a meaning cluster.

    Format: {word}_{pos}_{salient} — e.g., bank_noun_financial, bank_verb_tilt.
    Collision handling: appends numeric suffix if two clusters share a salient word.

    Args:
        word: The word being clustered.
        pos: Part of speech for this cluster.
        definitions: All definitions (indices reference into this list).
        cluster_indices: Indices of definitions in this cluster.
        all_clusters: All cluster index groups (for TF-IDF contrast).
    """
    # Normalize POS for slug
    pos_slug = pos.split()[0].lower()  # "verb (transitive)" → "verb"

    # Collect texts for this cluster and all clusters
    cluster_texts = [definitions[i].text for i in cluster_indices]
    all_cluster_texts = [
        [definitions[i].text for i in c]
        for c in all_clusters
    ]

    salient = _tfidf_salient_word(cluster_texts, all_cluster_texts)
    slug = f"{word}_{pos_slug}_{salient}"

    # Sanitize: only lowercase alphanumeric + underscore
    slug = re.sub(r"[^a-z0-9_]", "", slug)

    return slug


def deduplicate_slugs(slugs: list[str]) -> list[str]:
    """Ensure all slugs are unique by appending numeric suffixes to duplicates."""
    seen: dict[str, int] = {}
    result: list[str] = []

    for slug in slugs:
        if slug in seen:
            seen[slug] += 1
            result.append(f"{slug}_{seen[slug]}")
        else:
            seen[slug] = 0
            result.append(slug)

    return result


def generate_cluster_name(
    definitions: list[Definition],
    cluster_indices: list[int],
) -> str:
    """Generate a short, human-readable name for a meaning cluster.

    Extracts the most representative 2-4 word phrase from the cluster's
    definitions. Picks the shortest definition's key noun phrase.
    """
    if not cluster_indices:
        return "Unknown"

    # Pick the shortest definition as most concise
    texts = [(len(definitions[i].text), definitions[i].text) for i in cluster_indices]
    texts.sort()
    shortest = texts[0][1]

    # Extract first meaningful noun phrase (rough heuristic: first 2-4 content words)
    tokens = _tokenize(shortest)[:4]
    if not tokens:
        return "General"

    name = " ".join(tokens).title()
    # Cap at 30 chars
    if len(name) > 30:
        name = name[:27] + "..."

    return name

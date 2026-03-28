"""Tests for local sense clustering with silhouette quality gating."""

from __future__ import annotations

import numpy as np
import pytest

from floridify.ai.clustering.local_clustering import (
    LocalClusterResult,
    _cluster_embeddings,
    _compute_cluster_quality,
    _wordnet_sense_count,
    format_cluster_hints,
)


class TestWordNetSenseCount:
    def test_polysemous_word_has_many_senses(self) -> None:
        count = _wordnet_sense_count("bank")
        assert count is not None
        assert count >= 10

    def test_filters_by_pos(self) -> None:
        noun_count = _wordnet_sense_count("bank", "noun")
        verb_count = _wordnet_sense_count("bank", "verb")
        assert noun_count is not None and verb_count is not None
        assert noun_count > verb_count


class TestClusterQuality:
    def test_returns_negative_for_single_cluster(self) -> None:
        embeddings = np.array([[1.0, 0.0], [0.9, 0.1]])
        assert _compute_cluster_quality(embeddings, [0, 0]) == -1.0

    def test_positive_for_well_separated(self) -> None:
        embeddings = np.array([
            [1.0, 0.0], [0.95, 0.05],
            [0.0, 1.0], [0.05, 0.95],
        ])
        score = _compute_cluster_quality(embeddings, [0, 0, 1, 1])
        assert score > 0.3


class TestClusterEmbeddings:
    def test_single_item(self) -> None:
        embeddings = np.array([[1.0, 0.0, 0.0]])
        clusters, silhouette = _cluster_embeddings(embeddings, ["noun"])
        assert len(clusters) == 1
        assert silhouette == -1.0

    def test_clearly_separable(self) -> None:
        embeddings = np.array([
            [1.0, 0.0, 0.0],   # A
            [0.95, 0.05, 0.0],  # A
            [0.0, 1.0, 0.0],   # B
            [0.05, 0.95, 0.0],  # B
            [0.0, 0.0, 1.0],   # C
            [0.0, 0.05, 0.95],  # C
        ])
        clusters, silhouette = _cluster_embeddings(embeddings, ["noun"] * 6)
        assert len(clusters) == 3
        assert silhouette > 0.3

    def test_respects_pos_boundary(self) -> None:
        embeddings = np.array([[1.0, 0.0], [0.99, 0.01]])
        clusters, _ = _cluster_embeddings(embeddings, ["noun", "verb"])
        assert len(clusters) == 2

    def test_preserves_all_indices(self) -> None:
        n = 8
        rng = np.random.RandomState(42)
        embeddings = rng.randn(n, 10).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        clusters, _ = _cluster_embeddings(embeddings, ["noun"] * n)
        all_indices = sorted(idx for c in clusters for idx in c)
        assert all_indices == list(range(n))

    def test_returns_silhouette(self) -> None:
        embeddings = np.array([
            [1.0, 0.0], [0.95, 0.05],
            [0.0, 1.0], [0.05, 0.95],
        ])
        _, silhouette = _cluster_embeddings(embeddings, ["noun"] * 4)
        assert isinstance(silhouette, float)


class TestLocalClusterResult:
    def test_high_confidence_threshold(self) -> None:
        result = LocalClusterResult(clusters=[[0], [1]], silhouette=0.5)
        assert result.high_confidence

    def test_low_confidence(self) -> None:
        result = LocalClusterResult(clusters=[[0, 1]], silhouette=0.2)
        assert not result.high_confidence


class TestFormatClusterHints:
    def test_produces_readable_output(self) -> None:
        from unittest.mock import MagicMock

        defs = []
        for text, pos in [
            ("A financial institution.", "noun"),
            ("Sloping land beside a river.", "noun"),
        ]:
            d = MagicMock()
            d.text = text
            d.part_of_speech = pos
            defs.append(d)

        clusters = [[0], [1]]
        result = format_cluster_hints(defs, clusters)
        assert "2 distinct senses" in result

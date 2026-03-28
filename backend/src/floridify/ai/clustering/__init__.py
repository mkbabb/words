"""Local clustering for definition grouping by meaning.

Uses sentence-transformer embeddings + sklearn clustering to pre-group
definitions before AI refinement.
"""

from .local_clustering import local_cluster_definitions

__all__ = ["local_cluster_definitions"]

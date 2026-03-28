"""Local 3-tier definition deduplication pipeline.

Adapted from gaggle's ngram_dedup for dictionary definitions:
  Tier 1: Canonicalized exact text match (free, instant)
  Tier 2: Fuzzy token match via rapidfuzz (free, sub-second)
  Tier 3: Semantic match via sentence-transformers (essentially free, model already loaded)
"""

from .local_dedup import local_deduplicate_definitions

__all__ = ["local_deduplicate_definitions"]

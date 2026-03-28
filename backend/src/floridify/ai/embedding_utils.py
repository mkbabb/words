"""Shared embedding utilities for local dedup, clustering, and synset matching.

Wraps SemanticEncoder with proper initialization and caching. Provides:
  - encode_texts(): batch text → embedding conversion
  - best_synset_by_embedding(): match a definition to its WordNet synset
    using semantic similarity (replaces brittle word-overlap matching)
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..utils.logging import get_logger

logger = get_logger(__name__)

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None  # type: ignore[assignment]


# ── Encoder singleton ─────────────────────────────────────────────────

_encoder_instance = None
_encoder_initialized = False


async def encode_texts(texts: list[str]) -> np.ndarray | None:
    """Encode a list of texts into embeddings using the shared SemanticEncoder.

    Handles initialization, model loading, and error recovery.
    Returns None if the encoder is unavailable.
    """
    global _encoder_instance, _encoder_initialized

    if not texts:
        return np.array([])

    try:
        from ..search.semantic.constants import DEFAULT_BATCH_SIZE, DEFAULT_SENTENCE_MODEL
        from ..search.semantic.encoder import SemanticEncoder

        # DEFAULT_SENTENCE_MODEL may be a string or an object with .name
        model_name = DEFAULT_SENTENCE_MODEL if isinstance(DEFAULT_SENTENCE_MODEL, str) else DEFAULT_SENTENCE_MODEL.name

        if _encoder_instance is None:
            _encoder_instance = SemanticEncoder()

        if not _encoder_initialized:
            await _encoder_instance.initialize_model(model_name)
            _encoder_initialized = True

        embeddings = _encoder_instance.encode(
            texts,
            model_name=model_name,
            batch_size=min(DEFAULT_BATCH_SIZE, len(texts)),
            use_multiprocessing=False,
        )

        return embeddings

    except Exception as e:
        logger.debug(f"Embedding encoding failed: {e}")
        return None


# ── Synset matching ───────────────────────────────────────────────────


def _get_synsets(word: str, pos: str) -> list[Any]:
    """Get WordNet synsets for a word+POS. Returns [] if WordNet unavailable."""
    if wn is None:
        return []

    pos_map = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
    wn_pos = pos_map.get(pos)
    return wn.synsets(word, pos=wn_pos)


def best_synset_word_overlap(
    word: str,
    pos: str,
    definition_text: str,
) -> Any | None:
    """Match a definition to a WordNet synset using word overlap.

    Synchronous fallback when the embedding encoder is unavailable.
    Less accurate for polysemous words because synthesized definitions
    use different phrasing than WordNet's terse glosses.
    """
    synsets = _get_synsets(word, pos)
    if not synsets:
        return None

    def_words = set(definition_text.lower().split())
    best = None
    best_overlap = 0

    for synset in synsets:
        syn_words = set(synset.definition().lower().split())
        overlap = len(def_words & syn_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best = synset

    return best


async def best_synset_by_embedding(
    word: str,
    pos: str,
    definition_text: str,
    similarity_threshold: float = 0.3,
) -> Any | None:
    """Match a definition to its closest WordNet synset using embedding similarity.

    Encodes the definition text and all WordNet synset glosses in one batch,
    then picks the synset with the highest cosine similarity. This is far more
    robust than word overlap for polysemous words where synthesized definitions
    use very different phrasing from WordNet's terse glosses.

    Falls back to word-overlap matching when the encoder is unavailable.

    Args:
        word: The word being defined.
        pos: Part of speech (noun, verb, adjective, adverb).
        definition_text: The synthesized definition text to match.
        similarity_threshold: Minimum cosine similarity to accept a match.

    Returns:
        The best-matching WordNet Synset, or None.
    """
    synsets = _get_synsets(word, pos)
    if not synsets:
        return None

    # Build batch: [definition_text, synset1_gloss, synset2_gloss, ...]
    texts = [definition_text] + [s.definition() for s in synsets]

    embeddings = await encode_texts(texts)
    if embeddings is None or len(embeddings) < 2:
        # Fallback to word overlap
        logger.debug("Embedding unavailable, falling back to word overlap for synset matching")
        return best_synset_word_overlap(word, pos, definition_text)

    # Cosine similarity between definition (index 0) and each synset
    def_embedding = embeddings[0]
    synset_embeddings = embeddings[1:]

    # Normalize
    def_norm = np.linalg.norm(def_embedding)
    if def_norm == 0:
        return best_synset_word_overlap(word, pos, definition_text)

    def_unit = def_embedding / def_norm
    norms = np.linalg.norm(synset_embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    synset_units = synset_embeddings / norms

    similarities = synset_units @ def_unit

    best_idx = int(np.argmax(similarities))
    best_sim = float(similarities[best_idx])

    if best_sim < similarity_threshold:
        return None

    matched = synsets[best_idx]
    logger.debug(
        f"Synset match for '{word}' ({pos}): {matched.name()} "
        f"(sim={best_sim:.3f}, def='{matched.definition()[:50]}')"
    )
    return matched

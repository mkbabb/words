"""Phonetic encoder: ICU normalization + jellyfish Metaphone.

Applies CLDR-backed transliteration for script/diacritics normalization,
then cross-linguistic phonetic rules (compiled ICU automaton), then
jellyfish Metaphone (Rust-backed) for the final encoding.

All ICU transliterators are compiled once at module load time.
Per-query cost is two C++ string passes + one Rust Metaphone call.
"""

from __future__ import annotations

import re

import jellyfish

from .constants import FULL_PHONETIC_CHAIN, PHONETIC_NORMALIZER

# Strip non-alpha characters, keeping spaces for word splitting
_NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")


class PhoneticEncoder:
    """ICU-normalized jellyfish Metaphone encoder.

    Thread-safe: ICU Transliterator instances are compiled at module level
    and transliterate() is a pure function (no mutable state).
    """

    def normalize(self, text: str) -> str:
        """Apply full phonetic normalization pipeline.

        Stage 1: Any-Latin; Latin-ASCII; Lower (CLDR built-in)
        Stage 2: Cross-linguistic phonetic rules (compiled ICU automaton)

        Returns lowercase ASCII text with cross-linguistic sound
        equivalences collapsed.
        """
        # Stage 1: Script normalization + diacritics removal
        result = FULL_PHONETIC_CHAIN.transliterate(text)
        # Stage 2: Phonetic normalization (nasal vowels, digraphs, etc.)
        result = PHONETIC_NORMALIZER.transliterate(result)
        return result

    def encode(self, word: str) -> str:
        """Encode a single word to its Metaphone code.

        Applies ICU normalization before Metaphone encoding.
        """
        normalized = self.normalize(word)
        # Strip non-alpha for Metaphone
        cleaned = _NON_ALPHA_RE.sub("", normalized).strip()
        if len(cleaned) < 1:
            return ""
        return jellyfish.metaphone(cleaned)

    def encode_composite(self, phrase: str) -> str | None:
        """Encode a multi-word phrase to a composite Metaphone key.

        Each word is encoded independently, then joined with '|'.
        Returns None if no encodable words found.
        """
        normalized = self.normalize(phrase)
        words = [w for w in _NON_ALPHA_RE.sub("", normalized).split() if len(w) >= 2]
        if not words:
            return None

        codes = []
        for word in words:
            code = jellyfish.metaphone(word)
            if code:
                codes.append(code)

        return "|".join(codes) if codes else None


# Module-level singleton — zero construction cost per use
_default_encoder: PhoneticEncoder | None = None


def get_phonetic_encoder() -> PhoneticEncoder:
    """Get the module-level singleton PhoneticEncoder."""
    global _default_encoder
    if _default_encoder is None:
        _default_encoder = PhoneticEncoder()
    return _default_encoder


__all__ = ["PhoneticEncoder", "get_phonetic_encoder"]

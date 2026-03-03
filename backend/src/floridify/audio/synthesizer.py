"""Audio synthesis module with language-routed TTS backends.

- KittenTTS for English (15M params, fast, local)
- Kokoro-ONNX for non-English (82M params, 9 languages, local)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from loguru import logger

from ..utils.paths import get_project_root


@dataclass
class TTSResult:
    """Lightweight result from TTS synthesis (no MongoDB dependency)."""

    url: str
    format: str
    size_bytes: int
    duration_ms: int
    accent: str | None = None
    quality: str = "standard"


class AudioSynthesizer:
    """Public facade that routes to language-appropriate TTS backend.

    - English → KittenTTS (local, 15M params)
    - French, Spanish, Italian, Japanese, Mandarin, Hindi, Portuguese → Kokoro-ONNX
    - Unsupported languages (e.g. German) → None
    """

    def __init__(self) -> None:
        self._kitten: object | None = None
        self._kokoro: object | None = None

        # Ensure cache directory exists
        cache_dir = get_project_root() / "data" / "audio_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_kitten(self) -> object:
        """Lazy-init KittenTTS backend."""
        if self._kitten is None:
            from .kitten_synthesizer import KittenTTSSynthesizer

            self._kitten = KittenTTSSynthesizer()
            logger.info("Initialized KittenTTS backend for English")
        return self._kitten

    def _get_kokoro(self) -> object:
        """Lazy-init Kokoro backend."""
        if self._kokoro is None:
            from .kokoro_synthesizer import KokoroSynthesizer

            self._kokoro = KokoroSynthesizer()
            logger.info("Initialized Kokoro backend for non-English")
        return self._kokoro

    async def synthesize_word(
        self,
        word: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
        language: str = "en",
    ) -> TTSResult | None:
        """Synthesize audio for a word. Routes to appropriate backend by language."""
        if language == "en":
            backend = self._get_kitten()
            return await backend.synthesize_word(word, accent, voice_gender, language="en")  # type: ignore[union-attr]

        # Non-English: check Kokoro support
        from .kokoro_synthesizer import KokoroSynthesizer

        if KokoroSynthesizer.supports_language(language):
            backend = self._get_kokoro()
            return await backend.synthesize_word(word, language=language, voice_gender=voice_gender)  # type: ignore[union-attr]

        logger.debug(f"No TTS backend for language '{language}'")
        return None

    async def synthesize_pronunciation(
        self,
        pronunciation: object,
        word_text: str,
        language: str = "en",
    ) -> list[TTSResult]:
        """Generate audio files for a pronunciation entry."""
        if language == "en":
            backend = self._get_kitten()
            return await backend.synthesize_pronunciation(pronunciation, word_text, language="en")  # type: ignore[union-attr]

        from .kokoro_synthesizer import KokoroSynthesizer

        if KokoroSynthesizer.supports_language(language):
            backend = self._get_kokoro()
            return await backend.synthesize_pronunciation(pronunciation, word_text, language=language)  # type: ignore[union-attr]

        return []

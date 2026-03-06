"""Audio synthesis module with language-routed TTS backends.

- KittenTTS for English (15M params, fast, local)
- Kokoro-ONNX for non-English (82M params, 9 languages, local)
"""

from __future__ import annotations

from typing import Literal

from loguru import logger

from ..utils.paths import get_project_root
from .kitten_synthesizer import KittenTTSSynthesizer
from .kokoro_synthesizer import KokoroSynthesizer
from .types import TTSResult


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

    def initialize(self) -> None:
        """Eagerly load all TTS models. Call at startup for fast first-request."""
        logger.info("Initializing TTS backends...")
        try:
            self._get_kitten()
        except Exception as e:
            logger.error(f"Failed to initialize KittenTTS: {e}")
        try:
            self._get_kokoro()
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro: {e}")
        logger.info("TTS backend initialization complete")

    def _get_kitten(self) -> object:
        """Get KittenTTS backend (loads model on first call, cached after)."""
        if self._kitten is None:
            self._kitten = KittenTTSSynthesizer()
            self._kitten._ensure_model()  # type: ignore[union-attr]
            logger.info("Initialized KittenTTS backend for English")
        return self._kitten

    def _get_kokoro(self) -> object:
        """Get Kokoro backend (loads model on first call, cached after)."""
        if self._kokoro is None:
            self._kokoro = KokoroSynthesizer()
            self._kokoro._ensure_model()  # type: ignore[union-attr]
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
        if KokoroSynthesizer.supports_language(language):
            backend = self._get_kokoro()
            return await backend.synthesize_word(word, language=language, voice_gender=voice_gender)  # type: ignore[union-attr]

        logger.debug(f"No TTS backend for language '{language}'")
        # By design: unsupported language returns None for graceful "no audio available"
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

        if KokoroSynthesizer.supports_language(language):
            backend = self._get_kokoro()
            return await backend.synthesize_pronunciation(
                pronunciation, word_text, language=language
            )  # type: ignore[union-attr]

        # By design: unsupported language returns empty list for graceful degradation
        return []


_audio_synthesizer: AudioSynthesizer | None = None


def get_audio_synthesizer() -> AudioSynthesizer:
    """Get or create the singleton AudioSynthesizer instance."""
    global _audio_synthesizer
    if _audio_synthesizer is None:
        _audio_synthesizer = AudioSynthesizer()
    return _audio_synthesizer

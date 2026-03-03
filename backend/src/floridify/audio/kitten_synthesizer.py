"""KittenTTS local audio synthesis for pronunciation generation."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from ..utils.paths import get_project_root
from .synthesizer import TTSResult
from .utils import audio_to_mp3


# Voice mapping: (accent, gender) → KittenTTS voice name
# Available voices: expr-voice-{2,3,4,5}-{m,f}
VOICE_MAP: dict[tuple[str, str], str] = {
    ("american", "male"): "expr-voice-2-m",
    ("american", "female"): "expr-voice-2-f",
    ("british", "male"): "expr-voice-3-m",
    ("british", "female"): "expr-voice-3-f",
}

DEFAULT_VOICE = "expr-voice-2-m"


class KittenTTSConfig(BaseModel):
    """Configuration for KittenTTS local synthesis."""

    cache_dir: Path = Field(default_factory=lambda: get_project_root() / "data" / "audio_cache")
    sample_rate: int = 24000
    speaking_rate: float = 1.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class KittenTTSSynthesizer:
    """Local TTS synthesis using KittenTTS models."""

    _model: Any = None
    _lock = threading.Lock()

    def __init__(self, config: KittenTTSConfig | None = None):
        self.config = config or KittenTTSConfig()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_model(self) -> Any:
        """Lazy-load the KittenTTS model (thread-safe)."""
        if KittenTTSSynthesizer._model is not None:
            return KittenTTSSynthesizer._model

        with KittenTTSSynthesizer._lock:
            # Double-check after acquiring lock
            if KittenTTSSynthesizer._model is not None:
                return KittenTTSSynthesizer._model

            try:
                from kittentts import KittenTTS
            except ImportError as e:
                raise ImportError(
                    "kittentts is required for local TTS. Install with: uv sync --extra kitten-tts"
                ) from e

            logger.info("Loading KittenTTS model (auto-download from HuggingFace)...")
            KittenTTSSynthesizer._model = KittenTTS()
            logger.info("KittenTTS model loaded")
            return KittenTTSSynthesizer._model

    def _generate_cache_key(self, text: str, voice: str) -> str:
        """Generate MD5 cache key."""
        content = f"kitten:{text}:{voice}:{self.config.speaking_rate}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path with subdirectory bucketing."""
        subdir = cache_key[:2]
        return self.config.cache_dir / subdir / f"{cache_key}.mp3"

    def _resolve_voice(
        self,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> str:
        """Map (accent, gender) to a KittenTTS voice name."""
        return VOICE_MAP.get((accent, voice_gender), DEFAULT_VOICE)

    def _synthesize_sync(self, text: str, voice: str) -> tuple[bytes, int]:
        """Synchronous synthesis — runs in executor.

        Returns (mp3_bytes, duration_ms).
        """
        model = self._ensure_model()
        audio_array = model.generate(text=text, voice=voice, speed=self.config.speaking_rate)

        import numpy as np

        audio_array = np.asarray(audio_array).squeeze()
        sample_rate = self.config.sample_rate
        duration_ms = int(len(audio_array) / sample_rate * 1000)
        mp3_bytes = audio_to_mp3(audio_array, sample_rate)
        return mp3_bytes, duration_ms

    async def synthesize_word(
        self,
        word: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
        language: str = "en",
    ) -> TTSResult | None:
        """Synthesize audio for a word. Returns TTSResult or None on failure.

        Only supports English — returns None for other languages.
        """
        if language != "en":
            return None

        try:
            voice = self._resolve_voice(accent, voice_gender)
            cache_key = self._generate_cache_key(word, voice)
            cache_path = self._get_cache_path(cache_key)

            # Check cache
            if cache_path.exists():
                logger.debug(f"KittenTTS cache hit: {word}")
                file_size = cache_path.stat().st_size
                duration_ms = max(len(word) * 150, 200)
                return TTSResult(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=file_size,
                    duration_ms=duration_ms,
                    accent=accent,
                    quality="standard",
                )

            # Synthesize in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            mp3_bytes, duration_ms = await loop.run_in_executor(
                None, self._synthesize_sync, word, voice
            )

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(mp3_bytes)

            logger.info(f"KittenTTS synthesized: {word} ({duration_ms}ms) → {cache_path}")

            return TTSResult(
                url=str(cache_path),
                format="mp3",
                size_bytes=len(mp3_bytes),
                duration_ms=duration_ms,
                accent=accent,
                quality="standard",
            )

        except Exception as e:
            logger.error(f"KittenTTS failed for '{word}': {e}")
            return None

    async def synthesize_ipa(
        self,
        ipa_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> TTSResult | None:
        """Synthesize from IPA text. Falls back to speaking the IPA as-is."""
        return await self.synthesize_word(ipa_text, accent, voice_gender)

    async def synthesize_phonetic(
        self,
        word: str,
        phonetic_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> TTSResult | None:
        """Synthesize from phonetic spelling. Uses the word text for natural speech."""
        return await self.synthesize_word(word, accent, voice_gender)

    async def synthesize_pronunciation(
        self,
        pronunciation: object,
        word_text: str,
        language: str = "en",
    ) -> list[TTSResult]:
        """Generate audio files for a pronunciation entry."""
        if language != "en":
            return []

        results: list[TTSResult] = []

        ipa = getattr(pronunciation, "ipa", "")
        phonetic = getattr(pronunciation, "phonetic", "")

        if ipa:
            result = await self.synthesize_word(word_text, accent="american")
            if result:
                results.append(result)

        if not results and phonetic:
            result = await self.synthesize_word(word_text, accent="american")
            if result:
                results.append(result)

        return results

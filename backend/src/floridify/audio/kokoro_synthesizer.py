"""Kokoro-ONNX TTS synthesizer for non-English languages."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from ..utils.paths import get_project_root
from .types import TTSResult
from .utils import audio_to_mp3

# Language → (kokoro_lang_code, female_voice, male_voice)
KOKORO_LANG_MAP: dict[str, tuple[str, str, str]] = {
    "fr": ("fr-fr", "ff_siwis", "ff_siwis"),  # Only 1 French voice
    "es": ("es", "ef_dora", "em_alex"),
    "de": ("de", "bf_emma", "bm_daniel"),  # No dedicated German voices; British voices + espeak-ng phonemization
    "it": ("it", "if_sara", "im_nicola"),
    "ja": ("ja", "jf_alpha", "jm_kumo"),
    "zh": ("zh", "zf_xiaobei", "zm_yunjian"),
    "hi": ("hi", "hf_alpha", "hm_omega"),
    "pt": ("pt-br", "pf_dora", "pm_alex"),
}

KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


class KokoroTTSConfig(BaseModel):
    """Configuration for Kokoro-ONNX synthesis."""

    cache_dir: Path = Field(default_factory=lambda: get_project_root() / "data" / "audio_cache")
    sample_rate: int = 24000
    speaking_rate: float = 1.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class KokoroSynthesizer:
    """Non-English TTS synthesis using Kokoro-ONNX (82M params, 9 languages)."""

    _model: Any = None
    _lock = threading.Lock()
    _voices: dict[str, Any] = {}

    def __init__(self, config: KokoroTTSConfig | None = None):
        self.config = config or KokoroTTSConfig()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def supports_language(cls, language: str) -> bool:
        """Check if a language is supported by Kokoro."""
        return language in KOKORO_LANG_MAP

    @staticmethod
    def _download_file(url: str, dest: Path) -> Path:
        """Download a file if it doesn't already exist."""
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading {url} → {dest}")
        # TODO[HIGH]: Hoist nested import to module scope unless this is an intentional lazy-init boundary (e.g., CLI or heavyweight model init); document rationale when kept nested.
        import urllib.request
        urllib.request.urlretrieve(url, str(dest))
        return dest

    def _ensure_model(self) -> Any:
        """Lazy-load the Kokoro-ONNX model (thread-safe)."""
        if KokoroSynthesizer._model is not None:
            return KokoroSynthesizer._model

        with KokoroSynthesizer._lock:
            if KokoroSynthesizer._model is not None:
                return KokoroSynthesizer._model

            try:
                from kokoro_onnx import Kokoro
            except ImportError as e:
                raise ImportError(
                    "kokoro-onnx is required for non-English TTS. "
                    "Install with: uv sync --extra kokoro-tts"
                ) from e

            # Patch phonemizer-fork compat: set_data_path was removed in 3.3.2,
            # replaced by a property setter. Kokoro 0.5.0 still calls the old method.
            try:
                # TODO[CRITICAL]: Remove runtime monkeypatch (`hasattr`/`setattr`) compatibility shim.
                from phonemizer.backend.espeak.wrapper import EspeakWrapper

                if not hasattr(EspeakWrapper, "set_data_path"):
                    EspeakWrapper.set_data_path = classmethod(  # type: ignore[attr-defined]
                        lambda cls, path: setattr(cls, "data_path", path)
                    )
            except ImportError:
                # TODO[HIGH]: Fail explicitly when phonemizer integration is unavailable.
                pass

            # Prefer system espeak-ng over bundled espeakng-loader (the bundled lib
            # has hardcoded CI paths that fail on ARM/Docker). Setting the env var
            # before Kokoro init makes it use the system library.
            # TODO[HIGH]: Hoist nested import to module scope unless this is an intentional lazy-init boundary (e.g., CLI or heavyweight model init); document rationale when kept nested.
            import ctypes.util
            import os

            if not os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
                sys_lib = ctypes.util.find_library("espeak-ng")
                if sys_lib:
                    os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = sys_lib
                    logger.debug(f"Using system espeak-ng: {sys_lib}")

            # Download model files to project data dir (cached after first download)
            models_dir = get_project_root() / "data" / "kokoro_models"
            model_path = self._download_file(KOKORO_MODEL_URL, models_dir / "kokoro-v1.0.onnx")
            voices_path = self._download_file(KOKORO_VOICES_URL, models_dir / "voices-v1.0.bin")

            logger.info("Loading Kokoro-ONNX model...")
            KokoroSynthesizer._model = Kokoro(str(model_path), str(voices_path))
            logger.info("Kokoro-ONNX model loaded")
            return KokoroSynthesizer._model

    def _generate_cache_key(self, text: str, voice: str, lang_code: str) -> str:
        """Generate MD5 cache key."""
        content = f"kokoro:{text}:{voice}:{lang_code}:{self.config.speaking_rate}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path with subdirectory bucketing."""
        subdir = cache_key[:2]
        return self.config.cache_dir / subdir / f"{cache_key}.mp3"

    def _resolve_voice(
        self,
        language: str,
        voice_gender: Literal["male", "female"] = "female",
    ) -> tuple[str, str] | None:
        """Map (language, gender) to (lang_code, voice_name). Returns None if unsupported."""
        lang_info = KOKORO_LANG_MAP.get(language)
        if not lang_info:
            return None
        lang_code, female_voice, male_voice = lang_info
        voice = female_voice if voice_gender == "female" else male_voice
        return lang_code, voice

    def _synthesize_sync(self, text: str, voice: str, lang_code: str) -> tuple[bytes, int]:
        """Synchronous synthesis — runs in executor.

        Returns (mp3_bytes, duration_ms).
        """
        # TODO[HIGH]: Hoist nested import to module scope unless this is an intentional lazy-init boundary (e.g., CLI or heavyweight model init); document rationale when kept nested.
        import numpy as np

        model = self._ensure_model()
        samples, sample_rate = model.create(
            text, voice=voice, speed=self.config.speaking_rate, lang=lang_code
        )

        audio_array = np.asarray(samples).squeeze()
        duration_ms = int(len(audio_array) / sample_rate * 1000)
        mp3_bytes = audio_to_mp3(audio_array, sample_rate)
        return mp3_bytes, duration_ms

    async def synthesize_word(
        self,
        word: str,
        language: str = "fr",
        voice_gender: Literal["male", "female"] = "female",
    ) -> TTSResult | None:
        """Synthesize audio for a word in a non-English language.

        Returns TTSResult or None if the language is unsupported.
        """
        resolved = self._resolve_voice(language, voice_gender)
        if not resolved:
            # TODO[MEDIUM]: Decide whether unsupported-language should be explicit failure instead of None.
            logger.debug(f"Kokoro: language '{language}' not supported")
            return None

        lang_code, voice = resolved

        try:
            cache_key = self._generate_cache_key(word, voice, lang_code)
            cache_path = self._get_cache_path(cache_key)

            # Check cache
            if cache_path.exists():
                logger.debug(f"Kokoro cache hit: {word} ({language})")
                file_size = cache_path.stat().st_size
                duration_ms = max(len(word) * 150, 200)
                return TTSResult(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=file_size,
                    duration_ms=duration_ms,
                    accent=language,
                    quality="standard",
                )

            # Synthesize in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            mp3_bytes, duration_ms = await loop.run_in_executor(
                None, self._synthesize_sync, word, voice, lang_code
            )

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(mp3_bytes)

            logger.info(f"Kokoro synthesized: {word} ({language}) ({duration_ms}ms) → {cache_path}")

            return TTSResult(
                url=str(cache_path),
                format="mp3",
                size_bytes=len(mp3_bytes),
                duration_ms=duration_ms,
                accent=language,
                quality="standard",
            )

        except Exception as e:
            logger.error(f"Kokoro failed for '{word}' ({language}): {e}")
            # TODO[HIGH]: Stop collapsing synthesis failures to None; raise typed audio-generation errors.
            return None

    async def synthesize_pronunciation(
        self,
        pronunciation: object,
        word_text: str,
        language: str = "fr",
    ) -> list[TTSResult]:
        """Generate audio files for a pronunciation entry."""
        if not self.supports_language(language):
            return []

        result = await self.synthesize_word(word_text, language=language)
        if result:
            return [result]
        return []

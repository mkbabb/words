"""Audio synthesis module with pluggable TTS backends.

Supports:
- KittenTTS (local, default) — fast, no API key needed
- Google Cloud TTS — high-quality WaveNet voices

Set TTS_BACKEND env var to: "auto" (default), "kitten", or "google".
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from ..models.base import AudioMedia
from ..models.dictionary import Pronunciation
from ..utils.config import Config
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


class AudioSynthesisConfig(BaseModel):
    """Configuration for Google Cloud Text-to-Speech."""

    credentials_path: Path | None = None
    project_id: str | None = None
    cache_dir: Path = Field(default_factory=lambda: get_project_root() / "data" / "audio_cache")

    # Voice configuration
    american_voice: str = "en-US-Wavenet-D"  # Male voice
    british_voice: str = "en-GB-Wavenet-B"  # Male voice
    american_voice_female: str = "en-US-Wavenet-F"
    british_voice_female: str = "en-GB-Wavenet-A"

    # Audio configuration - default to MP3 encoding (3)
    audio_encoding: int = 3  # texttospeech.AudioEncoding.MP3
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0

    # Quality settings
    sample_rate_hertz: int = 24000  # 24kHz for high quality

    model_config = ConfigDict(arbitrary_types_allowed=True)


class _GoogleCloudTTSSynthesizer:
    """Google Cloud Text-to-Speech backend."""

    def __init__(self, config: AudioSynthesisConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        """Get or create the TTS client."""
        if self._client is None:
            try:
                from google.cloud import texttospeech_v1 as texttospeech
                from google.oauth2 import service_account
            except ImportError as e:
                raise ImportError(
                    "google-cloud-texttospeech is required for Google TTS. "
                    "Install with: pip install google-cloud-texttospeech"
                ) from e

            if self.config.credentials_path and self.config.credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.config.credentials_path),
                )
                self._client = texttospeech.TextToSpeechClient(credentials=credentials)
            else:
                self._client = texttospeech.TextToSpeechClient()
        return self._client

    def _generate_cache_key(self, text: str, voice_name: str, is_ssml: bool = False) -> str:
        """Generate a cache key for the audio file."""
        content = f"{text}:{voice_name}:{is_ssml}:{self.config.audio_encoding}:{self.config.speaking_rate}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a given key."""
        subdir = cache_key[:2]
        return self.config.cache_dir / subdir / f"{cache_key}.mp3"

    def _select_voice(
        self,
        accent: Literal["american", "british"],
        voice_gender: Literal["male", "female"],
    ) -> tuple[str, str]:
        """Select voice name and language code."""
        if accent == "american":
            voice_name = (
                self.config.american_voice
                if voice_gender == "male"
                else self.config.american_voice_female
            )
            language_code = "en-US"
        else:
            voice_name = (
                self.config.british_voice
                if voice_gender == "male"
                else self.config.british_voice_female
            )
            language_code = "en-GB"
        return voice_name, language_code

    def _estimate_duration(self, text: str) -> int:
        """Estimate audio duration in milliseconds."""
        return len(text) * 150

    async def synthesize_ipa(
        self,
        ipa_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> AudioMedia | None:
        """Synthesize audio from IPA pronunciation."""
        try:
            voice_name, language_code = self._select_voice(accent, voice_gender)
            ssml_text = f'<speak><phoneme alphabet="ipa" ph="{ipa_text}"/></speak>'

            cache_key = self._generate_cache_key(ssml_text, voice_name, is_ssml=True)
            cache_path = self._get_cache_path(cache_key)

            if cache_path.exists():
                logger.info(f"Using cached audio for IPA: {ipa_text}")
                return AudioMedia(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=cache_path.stat().st_size,
                    duration_ms=self._estimate_duration(ipa_text),
                    accent=accent,
                    quality="high",
                )

            from google.cloud import texttospeech_v1 as texttospeech

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.config.audio_encoding,
                speaking_rate=self.config.speaking_rate,
                pitch=self.config.pitch,
                volume_gain_db=self.config.volume_gain_db,
                sample_rate_hertz=self.config.sample_rate_hertz,
            )

            response = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                ),
            )

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.audio_content)

            logger.info(f"Synthesized audio for IPA: {ipa_text} -> {cache_path}")

            return AudioMedia(
                url=str(cache_path),
                format="mp3",
                size_bytes=len(response.audio_content),
                duration_ms=self._estimate_duration(ipa_text),
                accent=accent,
                quality="high",
            )

        except Exception as e:
            logger.error(f"Failed to synthesize audio for IPA '{ipa_text}': {e}")
            return None

    async def synthesize_phonetic(
        self,
        word: str,
        phonetic_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> AudioMedia | None:
        """Synthesize audio from phonetic spelling."""
        try:
            voice_name, language_code = self._select_voice(accent, voice_gender)
            synthesis_text = word

            cache_key = self._generate_cache_key(synthesis_text, voice_name, is_ssml=False)
            cache_path = self._get_cache_path(cache_key)

            if cache_path.exists():
                logger.info(f"Using cached audio for word: {word}")
                return AudioMedia(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=cache_path.stat().st_size,
                    duration_ms=self._estimate_duration(word),
                    accent=accent,
                    quality="high",
                )

            from google.cloud import texttospeech_v1 as texttospeech

            synthesis_input = texttospeech.SynthesisInput(text=synthesis_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.config.audio_encoding,
                speaking_rate=self.config.speaking_rate,
                pitch=self.config.pitch,
                volume_gain_db=self.config.volume_gain_db,
                sample_rate_hertz=self.config.sample_rate_hertz,
            )

            response = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                ),
            )

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.audio_content)

            logger.info(f"Synthesized audio for word: {word} -> {cache_path}")

            return AudioMedia(
                url=str(cache_path),
                format="mp3",
                size_bytes=len(response.audio_content),
                duration_ms=self._estimate_duration(word),
                accent=accent,
                quality="high",
            )

        except Exception as e:
            logger.error(f"Failed to synthesize audio for word '{word}': {e}")
            return None

    async def synthesize_pronunciation(
        self,
        pronunciation: Pronunciation,
        word_text: str,
    ) -> list[AudioMedia]:
        """Generate audio files for a pronunciation entry."""
        audio_files: list[AudioMedia] = []

        if pronunciation.ipa:
            audio = await self.synthesize_ipa(pronunciation.ipa, accent="american")
            if audio:
                await audio.save()
                audio_files.append(audio)

        if not audio_files and pronunciation.phonetic:
            audio = await self.synthesize_phonetic(
                word_text, pronunciation.phonetic, accent="american"
            )
            if audio:
                await audio.save()
                audio_files.append(audio)

        return audio_files


def _load_google_config() -> AudioSynthesisConfig:
    """Load Google Cloud TTS config from config file."""
    main_config = Config.from_file()

    if main_config.google_cloud:
        gc_config = main_config.google_cloud
        credentials_path = Path(gc_config.credentials_path) if gc_config.credentials_path else None

        if not credentials_path:
            auth_dir = get_project_root() / "auth"
            for filename in [
                "google-cloud-credentials.json",
                "gcp-credentials.json",
                "tts-credentials.json",
            ]:
                path = auth_dir / filename
                if path.exists():
                    credentials_path = path
                    break

        return AudioSynthesisConfig(
            credentials_path=credentials_path,
            project_id=gc_config.project_id or os.getenv("GOOGLE_CLOUD_PROJECT"),
            american_voice=gc_config.tts_american_voice,
            british_voice=gc_config.tts_british_voice,
            american_voice_female=gc_config.tts_american_voice_female,
            british_voice_female=gc_config.tts_british_voice_female,
        )

    auth_dir = get_project_root() / "auth"
    credentials_path = None
    for filename in [
        "google-cloud-credentials.json",
        "gcp-credentials.json",
        "tts-credentials.json",
    ]:
        path = auth_dir / filename
        if path.exists():
            credentials_path = path
            break

    return AudioSynthesisConfig(
        credentials_path=credentials_path,
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
    )


class AudioSynthesizer:
    """Public facade that dispatches to the configured TTS backend.

    Backend selection via TTS_BACKEND env var:
    - "auto" (default): tries kitten, falls back to google
    - "kitten": KittenTTS only
    - "google": Google Cloud TTS only
    """

    def __init__(self, config: AudioSynthesisConfig | None = None):
        self._backend_name = os.getenv("TTS_BACKEND", "auto").lower()
        self._google_config = config
        self._backend = self._create_backend()

        # Ensure cache directory exists
        cache_dir = (
            self._google_config.cache_dir
            if self._google_config
            else get_project_root() / "data" / "audio_cache"
        )
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _create_backend(self) -> _GoogleCloudTTSSynthesizer | object:
        """Create the appropriate TTS backend."""
        if self._backend_name == "google":
            google_config = self._google_config or _load_google_config()
            return _GoogleCloudTTSSynthesizer(google_config)

        if self._backend_name in ("kitten", "auto"):
            try:
                from .kitten_synthesizer import KittenTTSSynthesizer

                logger.info("Using KittenTTS backend")
                return KittenTTSSynthesizer()
            except ImportError:
                if self._backend_name == "kitten":
                    raise
                logger.info("KittenTTS not available, falling back to Google Cloud TTS")
                google_config = self._google_config or _load_google_config()
                return _GoogleCloudTTSSynthesizer(google_config)

        # Default fallback
        google_config = self._google_config or _load_google_config()
        return _GoogleCloudTTSSynthesizer(google_config)

    async def synthesize_ipa(
        self,
        ipa_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> AudioMedia | None:
        """Synthesize audio from IPA pronunciation."""
        return await self._backend.synthesize_ipa(ipa_text, accent, voice_gender)

    async def synthesize_phonetic(
        self,
        word: str,
        phonetic_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> AudioMedia | None:
        """Synthesize audio from phonetic spelling."""
        return await self._backend.synthesize_phonetic(word, phonetic_text, accent, voice_gender)

    async def synthesize_pronunciation(
        self,
        pronunciation: Pronunciation,
        word_text: str,
    ) -> list[AudioMedia]:
        """Generate audio files for a pronunciation entry."""
        return await self._backend.synthesize_pronunciation(pronunciation, word_text)

    async def synthesize_word(
        self,
        word: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> TTSResult | None:
        """Synthesize audio for a word. Returns lightweight TTSResult (no MongoDB).

        Delegates to synthesize_word for Kitten or synthesize_phonetic for Google.
        """
        if hasattr(self._backend, "synthesize_word"):
            return await self._backend.synthesize_word(word, accent, voice_gender)
        # Google backend returns AudioMedia; wrap in TTSResult
        result = await self._backend.synthesize_phonetic(word, word, accent, voice_gender)
        if result is None:
            return None
        return TTSResult(
            url=result.url,
            format=result.format,
            size_bytes=result.size_bytes,
            duration_ms=result.duration_ms,
            accent=result.accent,
            quality=result.quality,
        )

"""Audio synthesis module for generating pronunciation audio using Google Cloud Text-to-Speech."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Literal

from google.cloud import texttospeech_v1 as texttospeech
from google.oauth2 import service_account
from loguru import logger
from pydantic import BaseModel, Field

from ..models.base import AudioMedia
from ..models.dictionary import Pronunciation
from ..utils.config import Config
from ..utils.paths import get_project_root


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

    # Audio configuration
    audio_encoding: int = texttospeech.AudioEncoding.MP3
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0

    # Quality settings
    sample_rate_hertz: int = 24000  # 24kHz for high quality

    class Config:
        arbitrary_types_allowed = True


class AudioSynthesizer:
    """Synthesizes audio pronunciations using Google Cloud Text-to-Speech."""

    def __init__(self, config: AudioSynthesisConfig | None = None):
        """Initialize the audio synthesizer.

        Args:
            config: Audio synthesis configuration. If None, will load from main config.

        """
        self.config = config or self._load_config()
        self._client: texttospeech.TextToSpeechClient | None = None

        # Ensure cache directory exists
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> AudioSynthesisConfig:
        """Load configuration from main config file."""
        main_config = Config.from_file()

        # Use Google Cloud config if available
        if main_config.google_cloud:
            gc_config = main_config.google_cloud
            credentials_path = (
                Path(gc_config.credentials_path) if gc_config.credentials_path else None
            )

            # If no path specified, look in auth directory
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
        # Fallback to environment-based config
        auth_dir = get_project_root() / "auth"
        credentials_path = None

        # Check for common credential file names
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

    @property
    def client(self) -> texttospeech.TextToSpeechClient:
        """Get or create the TTS client."""
        if self._client is None:
            if self.config.credentials_path and self.config.credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.config.credentials_path),
                )
                self._client = texttospeech.TextToSpeechClient(credentials=credentials)
            else:
                # Try default credentials (from environment)
                self._client = texttospeech.TextToSpeechClient()
        return self._client

    def _generate_cache_key(self, text: str, voice_name: str, is_ssml: bool = False) -> str:
        """Generate a cache key for the audio file."""
        content = f"{text}:{voice_name}:{is_ssml}:{self.config.audio_encoding}:{self.config.speaking_rate}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a given key."""
        # Use subdirectories to avoid too many files in one directory
        subdir = cache_key[:2]
        return self.config.cache_dir / subdir / f"{cache_key}.mp3"

    async def synthesize_ipa(
        self,
        ipa_text: str,
        accent: Literal["american", "british"] = "american",
        voice_gender: Literal["male", "female"] = "male",
    ) -> AudioMedia | None:
        """Synthesize audio from IPA pronunciation.

        Args:
            ipa_text: IPA pronunciation text
            accent: American or British accent
            voice_gender: Male or female voice

        Returns:
            AudioMedia object with file information, or None if synthesis fails

        """
        try:
            # Select appropriate voice
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

            # Convert IPA to SSML with phoneme tag
            ssml_text = f'<speak><phoneme alphabet="ipa" ph="{ipa_text}"/></speak>'

            # Check cache
            cache_key = self._generate_cache_key(ssml_text, voice_name, is_ssml=True)
            cache_path = self._get_cache_path(cache_key)

            if cache_path.exists():
                logger.info(f"Using cached audio for IPA: {ipa_text}")
                file_size = cache_path.stat().st_size

                # Estimate duration (rough approximation)
                duration_ms = self._estimate_duration(ipa_text)

                return AudioMedia(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=file_size,
                    duration_ms=duration_ms,
                    accent=accent,
                    quality="high",
                )

            # Synthesize new audio
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.config.audio_encoding,
                speaking_rate=self.config.speaking_rate,
                pitch=self.config.pitch,
                volume_gain_db=self.config.volume_gain_db,
                sample_rate_hertz=self.config.sample_rate_hertz,
            )

            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                ),
            )

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.audio_content)

            file_size = len(response.audio_content)
            duration_ms = self._estimate_duration(ipa_text)

            logger.info(f"Synthesized audio for IPA: {ipa_text} -> {cache_path}")

            return AudioMedia(
                url=str(cache_path),
                format="mp3",
                size_bytes=file_size,
                duration_ms=duration_ms,
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
        """Synthesize audio from phonetic spelling.

        Args:
            word: The actual word (for context)
            phonetic_text: Phonetic spelling (e.g., "on koo-LEES")
            accent: American or British accent
            voice_gender: Male or female voice

        Returns:
            AudioMedia object with file information, or None if synthesis fails

        """
        try:
            # Select appropriate voice
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

            # For phonetic spelling, we'll use the word itself for synthesis
            # as Google TTS handles pronunciation well for most English words
            synthesis_text = word

            # Check cache
            cache_key = self._generate_cache_key(synthesis_text, voice_name, is_ssml=False)
            cache_path = self._get_cache_path(cache_key)

            if cache_path.exists():
                logger.info(f"Using cached audio for word: {word}")
                file_size = cache_path.stat().st_size
                duration_ms = self._estimate_duration(word)

                return AudioMedia(
                    url=str(cache_path),
                    format="mp3",
                    size_bytes=file_size,
                    duration_ms=duration_ms,
                    accent=accent,
                    quality="high",
                )

            # Synthesize new audio
            synthesis_input = texttospeech.SynthesisInput(text=synthesis_text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.config.audio_encoding,
                speaking_rate=self.config.speaking_rate,
                pitch=self.config.pitch,
                volume_gain_db=self.config.volume_gain_db,
                sample_rate_hertz=self.config.sample_rate_hertz,
            )

            # Make the request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                ),
            )

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.audio_content)

            file_size = len(response.audio_content)
            duration_ms = self._estimate_duration(word)

            logger.info(f"Synthesized audio for word: {word} -> {cache_path}")

            return AudioMedia(
                url=str(cache_path),
                format="mp3",
                size_bytes=file_size,
                duration_ms=duration_ms,
                accent=accent,
                quality="high",
            )

        except Exception as e:
            logger.error(f"Failed to synthesize audio for word '{word}': {e}")
            return None

    def _estimate_duration(self, text: str) -> int:
        """Estimate audio duration in milliseconds based on text length."""
        # Rough estimation: ~150ms per phoneme/character for speech
        return len(text) * 150

    async def synthesize_pronunciation(
        self,
        pronunciation: Pronunciation,
        word_text: str,
    ) -> list[AudioMedia]:
        """Generate audio files for a pronunciation entry.

        Args:
            pronunciation: Pronunciation object with IPA and phonetic data
            word_text: The actual word text

        Returns:
            List of AudioMedia objects for generated audio files

        """
        audio_files: list[AudioMedia] = []

        # Generate American pronunciation if available
        if pronunciation.ipa:
            audio = await self.synthesize_ipa(pronunciation.ipa, accent="american")
            if audio:
                await audio.save()
                audio_files.append(audio)

        # If no IPA but we have phonetic spelling, generate from word
        if not audio_files and pronunciation.phonetic:
            # Try American accent
            audio = await self.synthesize_phonetic(
                word_text,
                pronunciation.phonetic,
                accent="american",
            )
            if audio:
                await audio.save()
                audio_files.append(audio)

        return audio_files

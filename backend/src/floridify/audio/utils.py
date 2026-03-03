"""Shared audio utilities for TTS synthesizers."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


def audio_to_mp3(audio_array: np.ndarray, sample_rate: int) -> bytes:
    """Convert numpy audio array to MP3 bytes via WAV → ffmpeg."""
    import numpy as np
    import soundfile as sf

    # Normalize to [-1, 1] float32
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    peak = np.abs(audio_array).max()
    if peak > 0:
        audio_array = audio_array / peak

    # Write WAV to temp file, convert with ffmpeg
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
        sf.write(wav_f.name, audio_array, sample_rate)
        wav_path = wav_f.name

    mp3_path = wav_path.replace(".wav", ".mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", "-f", "mp3", mp3_path],
            capture_output=True,
            check=True,
        )
        with open(mp3_path, "rb") as f:
            return f.read()
    finally:
        for p in (wav_path, mp3_path):
            try:
                os.unlink(p)
            except OSError:
                pass

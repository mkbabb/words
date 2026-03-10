# audio/

Multi-language TTS with language-based routing. All local, no cloud dependencies.

```
audio/
├── __init__.py
├── kitten_synthesizer.py   # KittenTTS (English, 15M params)
├── kokoro_synthesizer.py   # Kokoro-ONNX (non-English, 82M params, 8 languages)
├── synthesizer.py          # AudioSynthesizer facade—routes by language
├── types.py                # TTSResult dataclass
└── utils.py                # audio_to_mp3() WAV->MP3 conversion
```

- **English** -> KittenTTS (local, ~15M params)
- **French, Spanish, German, Italian, Japanese, Mandarin, Hindi, Portuguese** -> Kokoro-ONNX (82M params)
- Unsupported languages -> `None` (graceful "no audio available")
- MP3 format, MD5-based file caching with subdirectory bucketing
- Lazy model loading with thread-safe double-check locking
- Kokoro models auto-downloaded from GitHub releases (`kokoro-v1.0.onnx` + `voices-v1.0.bin`)

# audio/

Google Cloud TTS integration for pronunciation audio.

```
audio/
└── synthesizer.py          # AudioSynthesizer
```

- `synthesize_audio()` — generate from IPA/phonetic text
- Accents: US, UK, Australian
- Formats: MP3, WAV. Quality: Standard, Premium (WaveNet)
- Storage: MongoDB GridFS. Cached via GlobalCacheManager
- Lazy loading: Google Cloud SDK imported only when needed

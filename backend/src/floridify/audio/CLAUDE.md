# Audio Module - Speech Synthesis

Google Cloud Text-to-Speech integration for pronunciation audio.

## Key Components

**AudioSynthesizer** (`synthesizer.py`):
- `synthesize_audio()` - Generate audio from IPA/phonetic
- Accents: US, UK, Australian
- Format: MP3, WAV
- Quality levels: Standard, Premium (WaveNet)

**Storage**:
- MongoDB GridFS for audio files
- AudioMedia model with metadata
- Automatic caching via GlobalCacheManager

**Lazy Loading**: Google Cloud SDK imported only when needed

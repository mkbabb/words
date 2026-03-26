# Audio / TTS Pipeline

A local multi-language text-to-speech pipeline that routes between two engines by language, caches to the filesystem, and serves MP3.

## Table of Contents

1. [Architecture](#1-architecture)
2. [Language Routing](#2-language-routing)
3. [TTS Engines](#3-tts-engines)
4. [Voice Selection](#4-voice-selection)
5. [Phonemization](#5-phonemization)
6. [Audio Post-Processing](#6-audio-post-processing)
7. [Caching](#7-caching)
8. [Data Flow](#8-data-flow)
9. [System Dependencies](#9-system-dependencies)
10. [Key Files](#10-key-files)

## 1. Architecture

`AudioSynthesizer` is a facade that routes synthesis requests to the appropriate TTS backend based on language. Both engines produce raw float32 audio, which passes through shared post-processing ([`audio/utils.py`](../backend/src/floridify/audio/utils.py)) before reaching the filesystem cache.

```
                    ┌─────────────────────────┐
                    │   AudioSynthesizer      │
                    │   (facade, singleton)    │
                    └────────┬────────────────┘
                             │ routes by language
                 ┌───────────┴───────────┐
                 │                       │
    ┌────────────▼──────────┐  ┌─────────▼──────────────┐
    │  KokoroSynthesizer    │  │  KittenTTSSynthesizer   │
    │  82M params, ONNX     │  │  15M params             │
    │  10 language variants  │  │  English fallback       │
    └────────────┬──────────┘  └─────────┬──────────────┘
                 │                       │
                 └───────────┬───────────┘
                             │ float32 audio
                    ┌────────▼────────────┐
                    │  Post-Processing    │
                    │  fade → pad → norm  │
                    │  → WAV → ffmpeg MP3 │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │  Filesystem Cache   │
                    │  MD5-keyed, bucketed│
                    └─────────────────────┘
```

The singleton is accessed via `get_audio_synthesizer()`. On first call, it instantiates `AudioSynthesizer` and creates the cache directory at `data/audio_cache/`. Model loading is deferred until the first synthesis request (or eagerly via `initialize()` at API startup).

**Why two engines instead of one?** KittenTTS (15M parameters) loads faster and produces better English prosody than Kokoro at that model size. Kokoro (82M parameters) handles 9 languages. The architecture optimizes for the common case—English—while supporting multilingual synthesis through a single routing decision.

**Why local over cloud?** Google Cloud TTS was the original backend but was removed entirely. Network latency added 200–500ms per request, per-character billing accumulated quickly for a dictionary app, and the hard external dependency complicated offline development and deployment. Local models synthesize in under 500ms, cost nothing per request, and work offline.

## 2. Language Routing

The facade's `synthesize_word()` method resolves the target engine in two steps:

1. Map English accent variants: `language="en"` + `accent="british"` becomes `kokoro_lang="en-gb"`
2. Check `KokoroSynthesizer.supports_language(kokoro_lang)` against the `KOKORO_LANG_MAP` table

If Kokoro supports the language, it handles synthesis. If not, the method returns `None`—a graceful signal that no audio is available, propagated to the frontend as an absent playback button.

KittenTTS is retained as an optional fallback for English but isn't invoked by the current routing logic. The facade routes all supported languages (including English) through Kokoro. KittenTTS remains available for direct instantiation or future A/B testing.

## 3. TTS Engines

### KittenTTS (English, 15M params)

[`audio/kitten_synthesizer.py`](../backend/src/floridify/audio/kitten_synthesizer.py)

- **Model**: Auto-downloaded from HuggingFace on first load
- **Output**: 24kHz float32 mono audio
- **Loading**: Thread-safe double-checked locking on a class-level `_model` attribute. The lock is acquired only when `_model is None`; subsequent calls skip it entirely
- **Synthesis**: Synchronous `model.generate()` dispatched to a thread executor via `asyncio.get_running_loop().run_in_executor()`
- **Language**: English only. Returns `None` for any other language code

### Kokoro-ONNX (82M params, 10 language variants)

[`audio/kokoro_synthesizer.py`](../backend/src/floridify/audio/kokoro_synthesizer.py)

- **Runtime**: ONNX Runtime (CPU inference)
- **Model files**: Downloaded from GitHub releases on first load—`kokoro-v1.0.onnx` (model weights) and `voices-v1.0.bin` (voice embeddings), cached at `data/kokoro_models/`. The HuggingFace `voices.bin` URL 404s; only the GitHub releases host works
- **Output**: 24kHz float32 mono audio via `model.create(text, voice, speed, lang)`
- **Loading**: Same double-checked locking pattern as KittenTTS, plus a `phonemizer-fork` compatibility shim (see [Phonemization](#5-phonemization))
- **Languages**: en, en-gb, fr, es, de, it, ja, zh, hi, pt

## 4. Voice Selection

### Kokoro Voice Map

Each language maps to a Kokoro language code, a female voice, and a male voice:

| Language | Code | Kokoro Lang | Female Voice | Male Voice |
|----------|------|-------------|--------------|------------|
| English (American) | `en` | `en-us` | `af_heart` | `am_michael` |
| English (British) | `en-gb` | `en-gb` | `bf_emma` | `bm_daniel` |
| French | `fr` | `fr-fr` | `ff_siwis` | `ff_siwis` |
| Spanish | `es` | `es` | `ef_dora` | `em_alex` |
| German | `de` | `de` | `bf_emma` | `bm_daniel` |
| Italian | `it` | `it` | `if_sara` | `im_nicola` |
| Japanese | `ja` | `ja` | `jf_alpha` | `jm_kumo` |
| Chinese | `zh` | `zh` | `zf_xiaobei` | `zm_yunjian` |
| Hindi | `hi` | `hi` | `hf_alpha` | `hm_omega` |
| Portuguese | `pt` | `pt-br` | `pf_dora` | `pm_alex` |

French has a single voice (`ff_siwis`) used for both genders—Kokoro ships only one French voice.

**The German workaround**: Kokoro has no native German voices. The `de` entry uses British voices (`bf_emma`, `bm_daniel`) paired with German phonemes produced by espeak-ng. This works because the British voice set handles Germanic phoneme inventories adequately—the result is intelligible, if accented, German. Better than silence.

### KittenTTS Voice Map

| Accent | Gender | Voice |
|--------|--------|-------|
| American | Male | `expr-voice-2-m` |
| American | Female | `expr-voice-2-f` |
| British | Male | `expr-voice-3-m` |
| British | Female | `expr-voice-3-f` |

The default is `expr-voice-2-m` (American male).

## 5. Phonemization

Kokoro uses espeak-ng for text-to-phoneme conversion via the `phonemizer-fork` Python package.

**The phonemizer conflict**: KittenTTS depends on `phonemizer` (the original package). Kokoro depends on `phonemizer-fork` (a maintained fork). Both packages occupy the same import namespace (`import phonemizer`). The project pins to `phonemizer-fork` since Kokoro handles more languages; KittenTTS works with either package.

**Compat shim**: Kokoro 0.5.0 calls `EspeakWrapper.set_data_path()`, a method that was removed in `phonemizer-fork` 3.3.2 and replaced with a property setter. The Kokoro synthesizer patches this at model-load time:

```python
if not hasattr(EspeakWrapper, "set_data_path"):
    EspeakWrapper.set_data_path = classmethod(
        lambda cls, path: setattr(cls, "data_path", path)
    )
```

**System espeak-ng preference**: The initializer checks for a system-installed `espeak-ng` library via `ctypes.util.find_library()` and sets `PHONEMIZER_ESPEAK_LIBRARY` to prefer it over the bundled `espeakng-loader`. The bundled library has hardcoded CI paths that fail on ARM and Docker.

## 6. Audio Post-Processing

Both engines apply identical post-processing before caching. The steps execute in the synchronous `_synthesize_sync()` method (running in a thread executor):

1. **Normalize to float32**: `np.asarray(audio, dtype=np.float32).squeeze()`
2. **Fade-out** (50ms): Linear ramp from 1.0→0.0 over the final 1,200 samples (at 24kHz). Prevents click/pop artifacts at the end of the waveform
3. **Trailing silence pad** (250ms): 6,000 zero samples appended. Prevents the MP3 encoder from truncating the last frame—a common LAME/ffmpeg edge case where the final few milliseconds of audio get clipped
4. **Peak normalization**: Divide by `max(|samples|)` to scale to [-1, 1]. Applied inside `audio_to_mp3()`
5. **WAV→MP3 conversion**: `soundfile` writes a temporary WAV; `ffmpeg` converts to MP3 at 128kbps. Temp files are cleaned up best-effort

The conversion pipeline ([`audio/utils.py`](../backend/src/floridify/audio/utils.py)):

```
float32 array → soundfile.write(WAV) → ffmpeg -b:a 128k → MP3 bytes
```

The sample rate is 24kHz throughout, so no resampling occurs.

## 7. Caching

### L1: Filesystem (MD5-keyed)

Each synthesizer generates an MD5 cache key from its parameters:

- **KittenTTS**: `kitten:v{VERSION}:{text}:{voice}:{speed}`
- **Kokoro**: `kokoro:v{VERSION}:{text}:{voice}:{lang_code}:{speed}`

The key's first two hex characters form a subdirectory for bucketing—distributing files across 256 directories to avoid filesystem performance degradation from too many files in a single directory:

```
data/audio_cache/
├── 3a/
│   └── 3a7f2b...e4.mp3
├── b1/
│   └── b1c9d0...f2.mp3
└── ...
```

`_CACHE_VERSION` (currently `2` for both engines) is embedded in the cache key. Bumping it invalidates all cached audio—used when post-processing parameters change (e.g., after adding the fade-out and silence padding).

Cache hits return a `TTSResult` directly from file metadata without re-synthesis. Duration is estimated heuristically on cache hit (`max(len(word) * 150, 200)` ms) since reading the MP3 to extract actual duration would negate the caching benefit.

### L2: MongoDB (AudioMedia documents)

The API layer ([`api/routers/media/audio.py`](../backend/src/floridify/api/routers/media/audio.py)) maintains `AudioMedia` documents in MongoDB, indexed on `(word, language)`. The TTS generation endpoint checks MongoDB before invoking the synthesizer:

1. Query `AudioMedia` for matching word + language
2. If found, verify the filesystem path still exists
3. If the file is missing (stale entry), delete the document and regenerate
4. If not found, synthesize, save the MP3 to disk, and create an `AudioMedia` document

This two-tier scheme means MongoDB acts as a durable registry of generated audio, surviving container restarts where the filesystem cache might be on an ephemeral volume.

## 8. Data Flow

Audio enters the system through three integration points:

### Background synthesis during lookup

When the lookup pipeline returns a cached entry, it fires `_ensure_primary_audio()` as a background task via `asyncio.ensure_future()`. This checks whether the entry's pronunciation has audio files attached. If not, it calls `_generate_audio_files()` from [`ai/synthesis/word_level.py`](../backend/src/floridify/ai/synthesis/word_level.py), which:

1. Gets the `AudioSynthesizer` singleton
2. Calls `synthesize_pronunciation()`, which synthesizes the word text
3. Creates `AudioMedia` documents for each `TTSResult`
4. Attaches the audio IDs to `pronunciation.audio_file_ids`

Errors are logged but never propagated—audio is optional and must not block the lookup response.

### On-demand TTS API

`POST /api/v1/audio/tts/generate` accepts a word, accent, gender, and language. It checks MongoDB first, falls back to synthesis, persists the result, and returns a `content_url` pointing to the cached file endpoint.

`GET /api/v1/audio/cache/{subdir}/{filename}` serves cached MP3 files with path traversal protection: the resolved path must start with the cache directory after `Path.resolve()`.

### Frontend playback

The [`useAudioPlayback`](../frontend/src/components/custom/definition/composables/useAudioPlayback.ts) composable manages the full lifecycle:

1. Check for existing `AudioFile` entries attached to the word (language-matched)
2. If found, construct a URL via `audioApi.getAudioContentUrl()`
3. If not found (or playback fails), call `audioApi.generateAudio()` to trigger backend TTS
4. Play via `HTMLAudioElement` with states: `idle → loading → playing → idle`
5. On error, retry once through the TTS generation path (handles stale file URLs)
6. Reset cached URL when word or language changes

## 9. System Dependencies

### System packages

| Package | Purpose | Required by |
|---------|---------|-------------|
| `ffmpeg` | WAV→MP3 conversion (128kbps) | `audio/utils.py` |
| `espeak-ng` | Text-to-phoneme conversion | Kokoro-ONNX (via phonemizer-fork) |
| `libicu-dev` | ICU C++ library | PyICU (phonetic search, not TTS—but installed in same Docker layer) |

### Python packages

| Package | Purpose |
|---------|---------|
| `kittentts>=0.1.0` | English TTS engine |
| `kokoro-onnx>=0.5.0` | Multi-language TTS engine (ONNX runtime) |
| `soundfile>=0.12.1` | WAV file I/O |
| `numpy` | Audio array manipulation |
| `phonemizer-fork` | espeak-ng Python bindings (transitive dep of kokoro-onnx) |

The `phonemizer-fork` vs `phonemizer` conflict is the key packaging concern. Both packages install as `phonemizer` in the Python namespace. The project uses `phonemizer-fork` because Kokoro requires it; KittenTTS is compatible with either. If both are installed, import resolution is undefined—pin to one.

## 10. Key Files

```
backend/src/floridify/
├── audio/
│   ├── synthesizer.py           # AudioSynthesizer facade, get_audio_synthesizer() singleton
│   ├── kitten_synthesizer.py    # KittenTTS engine (English, 15M params)
│   ├── kokoro_synthesizer.py    # Kokoro-ONNX engine (82M params, 10 language variants)
│   ├── types.py                 # TTSResult model
│   └── utils.py                 # audio_to_mp3() WAV→MP3 via ffmpeg
├── ai/synthesis/
│   └── word_level.py            # _generate_audio_files()—pronunciation audio attachment
├── core/
│   └── lookup_pipeline.py       # _ensure_primary_audio()—background audio generation
├── api/routers/media/
│   └── audio.py                 # TTS generation endpoint, cached file serving, CRUD
└── models/
    └── base.py                  # AudioMedia document model

frontend/src/
├── api/
│   └── audio.ts                 # generateAudio(), getAudioContentUrl()
└── components/custom/definition/
    └── composables/
        └── useAudioPlayback.ts  # Playback state machine, fallback-to-TTS logic
```

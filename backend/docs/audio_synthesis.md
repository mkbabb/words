# Audio Synthesis for Pronunciations

This document describes the audio synthesis feature that generates pronunciation audio files using Google Cloud Text-to-Speech API.

## Overview

The audio synthesis module (`floridify.audio`) provides automatic generation of pronunciation audio files from IPA (International Phonetic Alphabet) transcriptions and phonetic spellings. Audio files are generated when pronunciations are created or enhanced through the AI synthesis pipeline.

## Features

- **IPA-based synthesis**: Uses SSML phoneme tags to accurately pronounce IPA transcriptions
- **Multi-accent support**: Generates both American and British English pronunciations
- **Voice options**: Male and female voices available for each accent
- **Automatic caching**: Audio files are cached to avoid regenerating identical pronunciations
- **Integrated with synthesis pipeline**: Audio generation happens automatically during pronunciation synthesis

## Setup

### 1. Google Cloud Configuration

1. Create a Google Cloud project and enable the Text-to-Speech API
2. Create a service account and download the credentials JSON file
3. Place the credentials file in the `auth/` directory (e.g., `auth/google-cloud-credentials.json`)

### 2. Configuration File

Add the following to your `auth/config.toml`:

```toml
[google_cloud]
# Path to service account credentials JSON file
credentials_path = "auth/google-cloud-credentials.json"

# Optional: Google Cloud project ID
project_id = "your-project-id"

# Voice settings (optional - these are the defaults)
tts_american_voice = "en-US-Wavenet-D"        # Male voice
tts_british_voice = "en-GB-Wavenet-B"         # Male voice
tts_american_voice_female = "en-US-Wavenet-F" # Female voice
tts_british_voice_female = "en-GB-Wavenet-A"  # Female voice
```

### 3. Install Dependencies

The Google Cloud Text-to-Speech library is included in the project dependencies:

```bash
cd backend
uv sync
```

## Usage

### Automatic Generation

Audio files are automatically generated when:

1. A new pronunciation is synthesized through the AI pipeline
2. An existing pronunciation is enhanced (and has no audio files)

### Manual Generation

To manually generate audio for a pronunciation:

```python
from floridify.audio import AudioSynthesizer
from floridify.models import Pronunciation

# Assume you have a pronunciation object
pronunciation = await Pronunciation.get(pronunciation_id)

# Create synthesizer
synthesizer = AudioSynthesizer()

# Generate audio files
audio_files = await synthesizer.synthesize_pronunciation(
    pronunciation, 
    word_text="example"
)

# Update pronunciation with audio file IDs
if audio_files:
    pronunciation.audio_file_ids = [str(audio.id) for audio in audio_files]
    await pronunciation.save()
```

## Audio File Storage

Audio files are stored in:
- **Cache directory**: `data/audio_cache/` (organized by first 2 characters of hash)
- **Database**: `AudioMedia` documents store metadata and file paths
- **Format**: MP3 at 24kHz sample rate for high quality

## Voice Options

The module uses Google Cloud's WaveNet voices for natural-sounding speech:

- **American English**: 
  - Male: en-US-Wavenet-D
  - Female: en-US-Wavenet-F
  
- **British English**:
  - Male: en-GB-Wavenet-B
  - Female: en-GB-Wavenet-A

You can customize these in the configuration file.

## API Endpoint Integration

The audio files are accessible through the existing pronunciation endpoints:

```python
# GET /words/{word}/pronunciations
{
    "pronunciations": [
        {
            "id": "...",
            "phonetic": "ig-ZAM-pul",
            "ipa_american": "/ɪɡˈzæmpəl/",
            "ipa_british": "/ɪɡˈzɑːmpəl/",
            "audio_files": [
                {
                    "id": "...",
                    "url": "/audio/cache/ab/abcdef123456.mp3",
                    "accent": "american",
                    "format": "mp3",
                    "duration_ms": 850
                },
                {
                    "id": "...",
                    "url": "/audio/cache/cd/cdef567890.mp3",
                    "accent": "british",
                    "format": "mp3",
                    "duration_ms": 900
                }
            ]
        }
    ]
}
```

## Testing

Run the test script to verify your setup:

```bash
cd backend
python test_audio_synthesis.py
```

This will:
1. Create a test word "example"
2. Generate pronunciations with IPA
3. Synthesize audio files
4. Display the results
5. Clean up test data

## Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Verify the credentials file exists at the specified path
2. Check that the service account has Text-to-Speech API permissions
3. Ensure the API is enabled in your Google Cloud project

### No Audio Generated

If no audio files are generated:
1. Check the logs for warnings about audio synthesis
2. Verify IPA transcriptions are valid
3. Ensure the cache directory is writable

### Performance

- Audio generation is done asynchronously to avoid blocking
- Files are cached to prevent regenerating identical audio
- Consider rate limits when processing many words

## Cost Considerations

Google Cloud Text-to-Speech pricing (as of 2024):
- WaveNet voices: $16.00 per 1 million characters
- Standard voices: $4.00 per 1 million characters

The module uses WaveNet voices by default for higher quality. Monitor usage in the Google Cloud Console.
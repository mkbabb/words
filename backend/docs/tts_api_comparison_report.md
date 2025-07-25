# Text-to-Speech API Comparison for Pronunciation Audio Generation

## Executive Summary

This report evaluates various Text-to-Speech (TTS) APIs for generating pronunciation audio files for the Floridify dictionary application. The evaluation focuses on each service's support for IPA (International Phonetic Alphabet) input, voice quality, API availability, and integration complexity.

## Key Requirements

Based on the Floridify application's Pronunciation model (`backend/src/floridify/models/models.py`):
- Support for British and American English pronunciations
- Ability to handle IPA notation (stored as `ipa_british` and `ipa_american`)
- Audio file generation in common formats (mp3, wav, ogg)
- High-quality, natural-sounding voice output
- API-based integration for automated generation

## Comparison Matrix

| Service | IPA Support | SSML Support | Voice Quality | Pricing | Key Features | Limitations |
|---------|------------|--------------|---------------|---------|--------------|-------------|
| **OpenAI TTS** | ❌ No | ❌ No | ⭐⭐⭐⭐⭐ Excellent | $15/1M chars | Low latency, natural voices, style control | No phonetic control, no SSML |
| **Google Cloud TTS** | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ Excellent | $4-16/1M chars | Full IPA/X-SAMPA support via SSML | Chirp HD voices don't support SSML |
| **Amazon Polly** | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐ Very Good | $4/1M chars | IPA/X-SAMPA, lexicon files, neural voices | Standard pricing model |
| **Azure Speech** | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ Excellent | $16/1M chars | IPA/SAPI support, custom lexicons | SAPI format for some locales |
| **ElevenLabs** | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ Excellent | $330/mo (1M chars) | IPA/CMU support, pronunciation dictionaries | Limited to specific models |
| **eSpeak-ng** | ✅ Yes | ❌ No | ⭐⭐ Basic | Free | Direct IPA input, 100+ languages | Robotic voice quality |
| **Festival** | ✅ Yes | ✅ Yes | ⭐⭐⭐ Good | Free | Customizable, research-grade | Complex setup, dated voices |
| **Piper TTS** | ✅ Yes* | ❌ No | ⭐⭐⭐⭐ Very Good | Free | Fast, low resource usage, AI-based | Uses eSpeak-ng for phonemes |

*Indirect support through eSpeak-ng dependency

## Detailed Analysis

### 1. **Google Cloud Text-to-Speech** ⭐ RECOMMENDED

**Pros:**
- Full IPA support through SSML `<phoneme>` tag
- Example: `<phoneme alphabet="ipa" ph="ˌmænɪˈtoʊbə">manitoba</phoneme>`
- Excellent voice quality with multiple accent options
- Well-documented API with client libraries
- Supports both IPA and X-SAMPA alphabets
- Studio voices support most SSML tags

**Cons:**
- Newer Chirp HD voices don't support SSML
- Costs $4-16 per 1M characters depending on voice type

**Integration Example:**
```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

# For IPA pronunciation
ssml_text = f'<speak><phoneme alphabet="ipa" ph="{ipa_notation}">{word}</phoneme></speak>'

synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Studio-O"  # Or en-GB for British
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

response = client.synthesize_speech(
    input=synthesis_input, 
    voice=voice, 
    audio_config=audio_config
)
```

### 2. **Amazon Polly** ⭐ Alternative Option

**Pros:**
- Supports both IPA and X-SAMPA through SSML
- X-SAMPA is easier to type with standard keyboards
- Lexicon files for managing pronunciations at scale
- Neural voices available
- Good documentation and AWS integration

**Cons:**
- Slightly lower voice quality than Google/Azure
- AWS ecosystem lock-in

**Integration Example:**
```python
import boto3

polly = boto3.client('polly')

# For IPA pronunciation
ssml_text = f'<speak><phoneme alphabet="ipa" ph="{ipa_notation}">{word}</phoneme></speak>'

response = polly.synthesize_speech(
    Text=ssml_text,
    TextType='ssml',
    OutputFormat='mp3',
    VoiceId='Matthew'  # Or 'Amy' for British
)
```

### 3. **Azure Speech Service**

**Pros:**
- Excellent voice quality
- IPA support through SSML
- SAPI format for specific locales
- Strong language support

**Cons:**
- More expensive ($16/1M chars)
- Microsoft ecosystem requirements
- SAPI format complexity for some languages

### 4. **ElevenLabs**

**Pros:**
- State-of-the-art voice quality
- IPA support (though CMU recommended)
- Pronunciation dictionary feature
- Modern API design

**Cons:**
- Most expensive option ($330/month)
- IPA support limited to specific models
- Subscription-based pricing

### 5. **Open Source Options**

**eSpeak-ng:**
- Direct IPA input support
- Free and lightweight (2MB)
- Poor voice quality (robotic)
- Best for testing/development

**Piper TTS:**
- Good voice quality for open source
- Fast and efficient
- Uses eSpeak-ng for phoneme conversion
- Requires local deployment

## Recommendations

### Primary Recommendation: **Google Cloud Text-to-Speech**

**Reasoning:**
1. **Native IPA Support**: Direct support for IPA notation through SSML phoneme tags
2. **Voice Quality**: Excellent, natural-sounding voices with multiple accents
3. **Cost-Effective**: Reasonable pricing at $4-16 per 1M characters
4. **API Maturity**: Well-established service with comprehensive documentation
5. **Language Support**: Separate British and American English voices
6. **Format Flexibility**: Supports MP3, WAV, and OGG output formats

### Implementation Strategy

1. **Development Phase**: Use eSpeak-ng for testing IPA accuracy
2. **Production Phase**: Implement Google Cloud TTS with fallback to regular text
3. **Caching Strategy**: Store generated audio files to minimize API calls
4. **Error Handling**: Fallback to phonetic text representation if IPA fails

### Integration Architecture

```python
class PronunciationAudioGenerator:
    def __init__(self):
        self.tts_client = texttospeech.TextToSpeechClient()
        
    def generate_pronunciation_audio(
        self, 
        word: str, 
        ipa: str, 
        accent: Literal["british", "american"]
    ) -> AudioMedia:
        """Generate pronunciation audio from IPA notation."""
        
        # Build SSML with IPA
        ssml = f'<speak><phoneme alphabet="ipa" ph="{ipa}">{word}</phoneme></speak>'
        
        # Select voice based on accent
        voice_name = "en-GB-Studio-B" if accent == "british" else "en-US-Studio-O"
        
        # Generate audio
        response = self._synthesize_speech(ssml, voice_name)
        
        # Store and return AudioMedia object
        return self._create_audio_media(response, accent)
```

### Cost Analysis

For a dictionary with 100,000 words:
- Average word length: 10 characters
- With IPA notation: ~50 characters per synthesis
- Total characters: 5M
- **Google Cloud TTS**: $20-80 (one-time generation)
- **OpenAI TTS**: $75 (but no IPA support)
- **ElevenLabs**: $330/month (ongoing)

## Conclusion

Google Cloud Text-to-Speech offers the best balance of IPA support, voice quality, and cost-effectiveness for the Floridify application. Its native SSML phoneme tag support allows direct use of the stored IPA notations, while providing high-quality voices for both British and American English pronunciations.

For development and testing, eSpeak-ng can serve as a free alternative to validate IPA notations before committing to paid API calls. The generated audio files should be cached to minimize ongoing costs.
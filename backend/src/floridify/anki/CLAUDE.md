# Anki Module - Flashcard Export

Direct Anki flashcard generation from wordlists.

## Features

**Card Types**:
- Fill-in-the-blank (cloze deletion)
- Multiple choice (best describes)
- Definition → word
- Word → definition

**Export** (`exporter.py`):
- `export_wordlist_to_anki()` - Generate .apkg file
- Deck configuration (daily limits, learning steps)
- Card styling (CSS)
- Media embedding (audio, images)

**Integration**: Uses AI synthesis for card content generation

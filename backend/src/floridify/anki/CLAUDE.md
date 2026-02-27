# anki/

Flashcard export to .apkg format.

```
anki/
├── generator.py (717)      # AnkiDeckGenerator: .apkg creation
├── templates.py (527)      # Card HTML/CSS templates
├── ankiconnect.py (441)    # AnkiConnect API client (optional)
└── constants.py (21)
```

Card types: fill-in-the-blank (cloze), multiple choice, definition→word, word→definition.

`export_wordlist_to_anki()` generates .apkg with deck config, card styling, and media embedding. Uses AI synthesis for card content generation.

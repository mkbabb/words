# anki/

Flashcard export to .apkg format.

```
anki/
├── __init__.py
├── ankiconnect.py      # AnkiConnectInterface, AnkiDirectIntegration
├── constants.py        # Card type constants
├── generator.py        # AnkiCardGenerator, extract_definitions(), render_template()
└── templates.py        # Card HTML/CSS templates
```

Card types: fill-in-the-blank (cloze), multiple choice, definition->word, word->definition.

`AnkiCardGenerator` builds .apkg files with deck config, card styling, and media embedding. Uses AI synthesis for card content. `AnkiConnectInterface` talks to a running Anki instance via AnkiConnect's HTTP API.

# Synonyms: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}
{% if existing_synonyms %}Existing: {{ existing_synonyms | join(', ') }}{% endif %}

Generate {{ count }}{% if existing_synonyms %} NEW{% endif %} synonyms:
- 40% common
- 30% expressive/literary
- 20% foreign (if precise)
- 10% technical

Per synonym: word, language, relevance (0-1), efflorescence (0-1), explanation (1 sentence).
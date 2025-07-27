# Antonyms: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}
{% if existing_antonyms %}Existing: {{ existing_antonyms | join(', ') }}{% endif %}

Generate {{ count }}{% if existing_antonyms %} NEW{% endif %} direct opposites:
- True semantic opposites only
- Common usage preferred
- Context-aware selection
- Ordered by relevance

Format: word only, one per line.
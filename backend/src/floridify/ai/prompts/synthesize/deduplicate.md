# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions

{% for idx, def in enumerate(definitions) %}
{{ idx }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task

**Aggressively deduplicate across the definition/part of speech pair**. Select highest quality. Never merge definitions with different parts of speech. Brief reasoning (max 10 words).

Example: "A light, four-wheeled carriage" vs "A light four-wheeled carriage" → Keep clearer punctuation.
Example: "An instance or occurrence that is used to clarify or demonstrate a rule or principle.", "An instance or case that illustrates a rule or concept, often used for learning or demonstration purposes." → Keep the first.

Output indices merged, quality score (0-1).

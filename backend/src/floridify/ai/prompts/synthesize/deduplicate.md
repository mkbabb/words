# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions
{% for idx, def in enumerate(definitions) %}
{{ idx }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task
Merge near-duplicates. Select highest quality. Brief reasoning (max 10 words).

Example: "A light, four-wheeled carriage" vs "A light four-wheeled carriage" → Keep clearer punctuation.

Output indices merged, quality score (0-1).
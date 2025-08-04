# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions

{% for idx, def in enumerate(definitions) %}
{{ idx }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task

**Aggressively** deduplicate definitions herein across the definition/part of speech pairs. Select the highest quality **ONLY**. Never merge definitions with different parts of speech. Brief reasoning (max 10 words). **Output indices merged, quality score (0-1).**

## Examples

#### `phaeton`

"A light, four-wheeled carriage", "A light four-wheeled carriage", "A light four-wheeled carriage drawn by horses", "A light, four-wheeled carriage drawn by horses"

Keep clearer punctuation and pithier phrasing: "A light, four-wheeled carriage".

#### `example`

"An instance or occurrence that is used to clarify or demonstrate a rule or principle."
"An instance or case that illustrates a rule or concept, often used for learning or demonstration purposes."

Keep the first: "An instance or occurrence that is used to clarify or demonstrate a rule or principle."

#### `en coulisse`

"Behind the scenes", "In the background", "In the background, away from public view"

Keep the first: "Behind the scenes".

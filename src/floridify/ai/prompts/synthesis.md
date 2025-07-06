# Synthesize Definitions for "{{ word }}"

{% if meaning_cluster %}

## Meaning Cluster (disambiguation of the word): {{ meaning_cluster }}

{% endif %}

## Provider Sources (`provider`, `word_type`, `definition`)

{% for provider, word_type, definition in provider_definitions %}
**{{ provider }}** ({{ word_type }}): {{ definition }}
{% endfor %}

For each word type, synthesize a clear, concise definition that:

-   Combines the best elements from all sources
-   Maintains academic dictionary tone
-   Preserves key terminology, phrasing, and structure
-   Removes redundancy

Return only the synthesized definitions - be concise!

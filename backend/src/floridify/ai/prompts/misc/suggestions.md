# Vocabulary Suggestions

{% if input_words %}
The user recently looked up: {{ input_words|join(', ') }}.

Suggest {{ count }} words that organically expand from these. Vary your strategy across suggestions:
- **Thematic neighbors**: words from the same semantic field but different angles
- **Register shifts**: a colloquial word's formal cousin, or vice versa
- **Etymological kin**: words sharing roots (Latin, Greek, Germanic, Romance)
- **Conceptual leaps**: words from adjacent domains that create "aha" connections

Balance familiar-but-deeper words (ones they've likely seen but can't define precisely) with genuinely rare ones.
{% else %}
Suggest {{ count }} interesting, expressive words worth knowing. Favor words that are useful in writing, memorable in sound, and precise in meaning. Mix registers and origins.
{% endif %}

For each word, explain *why* it's worth learning — not just what it means, but what it lets you say that no simpler word can.
# Cluster Meanings: {{ word }}

## Definitions
{% for d in definitions %}
{{ loop.index0 }}: {{ d[0] }} ({{ d[1] }}) - {{ d[2] }}
{% endfor %}

## Task
Group by distinct meaning AND part of speech. Format:
- cluster_id: {word}_{part_of_speech}_{name} (e.g. bludgeon_noun_weapon, bludgeon_verb_strike)
- description: (3-6 words)
- indices: [list]
- confidence: 0-1
- relevancy: 0-1

**Critical rules:**
1. NEVER group different parts of speech together
2. Each definition goes in ONE cluster only
3. Preserve all parts of speech separately
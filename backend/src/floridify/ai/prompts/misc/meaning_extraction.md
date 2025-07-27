# Cluster Meanings: {{ word }}

## Definitions
{% for d in definitions %}
{{ loop.index0 }}: {{ d[0] }} ({{ d[1] }}) - {{ d[2] }}
{% endfor %}

## Task
Group by distinct meaning. Format:
- cluster_id: {word}_{name} (1-2 words)
- description: (3-6 words)
- indices: [list]
- confidence: 0-1
- relevancy: 0-1

Avoid duplicates. Each ID in one cluster only.
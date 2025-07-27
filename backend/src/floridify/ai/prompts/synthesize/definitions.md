# Synthesize: {{ word }}{% if meaning_cluster %} ({{ meaning_cluster }}){% endif %}

## Sources
{% for d in definitions %}
{{ d.part_of_speech }}: {{ d.text }}{% if d.synonyms %} [{{ d.synonyms[:3] | join(', ') }}{% if d.synonyms|length > 3 %}...{% endif %}]{% endif %}
{% endfor %}

## Task
Synthesize clear, unique definitions by word type. Include relevancy score (0-1).
Output supreme normalized definitions without redundancy.
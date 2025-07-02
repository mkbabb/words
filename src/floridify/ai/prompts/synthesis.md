# Synthesize Definition for "{{ word }}" ({{ word_type }})

## Provider Sources
{% for provider, definition in provider_definitions %}
**{{ provider }}**: {{ definition }}
{% endfor %}

Create a concise, clear definition (1-2 sentences max) that:
- Combines the best elements from all sources
- Maintains academic dictionary tone  
- Preserves key terminology
- Removes redundancy

Return only the synthesized definition - be concise!
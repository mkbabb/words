# Etymology: {{ word }}

{% for provider in provider_data %}
**{{ provider.name }}**: {{ provider.etymology_text }}
{% endfor %}

Synthesize a pithy scholarly etymology with:
- Origin language
- Root words/morphemes
- First known use
- Concise historical development

Format: Text, Origin Language, Root Words, First Known Use
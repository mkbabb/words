# Etymology Extraction

Extract and synthesize etymology information for the word "{{ word }}" from the following provider data:

{% for provider in provider_data %}
**{{ provider.name }}**:
{{ provider.etymology_text }}
{% endfor %}

## Requirements:
1. Synthesize a coherent etymology narrative from all sources
2. Identify the origin language with confidence
3. Extract root words or morphemes
4. Include first known use date if available
5. Resolve any conflicts between sources intelligently
6. Keep the text concise but informative

## Expected Format:
- **Text**: A flowing narrative explaining the word's origin and development
- **Origin Language**: The primary language of origin (e.g., Latin, Greek, French)
- **Root Words**: List of root words or morphemes
- **First Known Use**: Date or period (e.g., "14th century", "1850s")

Generate a comprehensive etymology for "{{ word }}".
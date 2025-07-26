# Suggestions

{% if input_words %}
Suggest {{ count }} sophisticated words based on: {{ input_words|join(', ') }}.
{% else %}
Suggest {{ count }} sophisticated words, florid, and contextually relevant vocabulary.
{% endif %}

Analyze their semantic themes and complexity, then provide florid vocabulary that builds contextually on their demonstrated interests.

Return structured JSON with exactly {{ count }} suggestions. All word suggestions must be in lowercase.
{% if input_words %}
Suggest {{ count }} sophisticated words based on: {{ input_words|join(', ') }}.
{% else %}
Suggest {{ count }} sophisticated, florid words.
{% endif %}

Return JSON: {{ count }} lowercase suggestions matching semantic themes.
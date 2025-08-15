# Lexical Suggestions

{% if input_words %}
Suggest {{ count }} sophisticated words related to: {{ input_words|join(', ') }}.
{% else %}
Suggest {{ count }} sophisticated, interesting words.
{% endif %}

## Examples
Input: `beautiful` → `pulchritudinous, resplendent, ravissant`
Input: `dark` → `tenebrous, crepuscular, stygian`
Input: `think` → `ruminate, cogitate, cerebrate`

Output: {{ count }} lowercase suggestions, semantically related.
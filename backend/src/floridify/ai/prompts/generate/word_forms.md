# Forms: {{ word }} ({{ part_of_speech }})

Generate inflections:
{% if part_of_speech == 'noun' %}plural, possessive, plural_possessive{% elif part_of_speech == 'verb' %}present_participle, past, past_participle, third_person_singular{% elif part_of_speech == 'adjective' %}comparative, superlative{% elif part_of_speech == 'adverb' %}comparative, superlative (if applicable){% endif %}

Output format: type: form
# Word Forms: {{ word }} ({{ part_of_speech }})

Generate inflections:
{% if part_of_speech == 'noun' %}plural, possessive, plural_possessive{% elif part_of_speech == 'verb' %}present_participle, past, past_participle, third_person_singular{% elif part_of_speech == 'adjective' %}comparative, superlative{% elif part_of_speech == 'adverb' %}comparative, superlative (if applicable){% endif %}

## Examples

### Nouns
`phaeton`: plural: phaetons | possessive: phaeton's | plural_possessive: phaetons'
`analysis`: plural: analyses | possessive: analysis's | plural_possessive: analyses'

### Verbs
`run`: present_participle: running | past: ran | past_participle: run | third_person_singular: runs
`synthesize`: present_participle: synthesizing | past: synthesized | past_participle: synthesized | third_person_singular: synthesizes

### Adjectives
`beautiful`: comparative: more beautiful | superlative: most beautiful
`efflorescent`: comparative: more efflorescent | superlative: most efflorescent

Output: type: form
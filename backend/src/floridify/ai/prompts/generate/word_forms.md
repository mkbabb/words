# Word Forms: {{ word }} ({{ part_of_speech }})

Generate all standard inflections plus common derived forms.

{% if part_of_speech == 'noun' %}
Inflections: plural, possessive, plural_possessive
Derived (if they exist): adjective form, verb form (e.g., glory → glorious, glorify)
{% elif part_of_speech == 'verb' %}
Inflections: present_participle, past, past_participle, third_person_singular
Derived (if they exist): agent noun, action noun, adjective (e.g., observe → observer, observation, observable)
{% elif part_of_speech == 'adjective' %}
Inflections: comparative, superlative (use "more/most" for 3+ syllables)
Derived (if they exist): adverb, noun form (e.g., curious → curiously, curiosity)
{% elif part_of_speech == 'adverb' %}
Inflections: comparative, superlative (if applicable)
Derived (if they exist): adjective form
{% endif %}

Flag irregular forms explicitly. For multi-word entries (e.g., phrasal verbs), inflect the head word only.

## Examples

### Nouns
`analysis`: plural: analyses | possessive: analysis's | plural_possessive: analyses' | adjective: analytical
`child`: plural: children [irregular] | possessive: child's | plural_possessive: children's [irregular]

### Verbs
`run`: present_participle: running | past: ran [irregular] | past_participle: run [irregular] | third_person_singular: runs | agent_noun: runner | action_noun: running
`synthesize`: present_participle: synthesizing | past: synthesized | past_participle: synthesized | third_person_singular: synthesizes | agent_noun: synthesizer | action_noun: synthesis | adjective: synthetic

### Adjectives
`beautiful`: comparative: more beautiful | superlative: most beautiful | adverb: beautifully | noun: beauty
`good`: comparative: better [irregular] | superlative: best [irregular] | adverb: well [irregular]

Output: type: form
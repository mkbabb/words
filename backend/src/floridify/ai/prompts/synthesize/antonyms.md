# Antonyms: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}
{% if existing_antonyms %}Existing: {{ existing_antonyms | join(', ') }}{% endif %}

Generate {{ count }}{% if existing_antonyms %} NEW{% endif %} varied antonyms:
- 40% common: everyday opposites
- 30% expressive: literary/sophisticated
- 20% foreign: when English lacks precision
- 10% technical: domain-specific

Per antonym: word | language | relevance (0-1) | efflorescence (0-1) | brief explanation
Efflorescence: 0=plain, 1=ornate

## Examples

### `beautiful` (adjective)
ugly | English | 0.95 | 0.2 | Direct everyday opposite
grotesque | English | 0.85 | 0.8 | Distorted, repulsive beauty
mostruoso | Italian | 0.75 | 0.7 | Monstrous, horrifying appearance

### `increase` (verb)
decrease | English | 0.95 | 0.3 | Standard opposite
attenuate | English | 0.8 | 0.8 | Gradually weaken or reduce
abate | English | 0.85 | 0.7 | Diminish in intensity or amount
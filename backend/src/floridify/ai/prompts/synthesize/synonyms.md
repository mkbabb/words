# Synonyms: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}
{% if existing_synonyms %}Existing: {{ existing_synonyms | join(', ') }}{% endif %}

Generate {{ count }}{% if existing_synonyms %} NEW{% endif %} varied synonyms:
- 40% common: everyday alternatives
- 30% expressive: literary/sophisticated
- 20% foreign: when English lacks precision
- 10% technical: domain-specific

Per synonym: word | language | relevance (0-1) | efflorescence (0-1) | brief explanation
Efflorescence: 0=plain, 1=ornate

## Examples

### `beautiful` (adjective)
gorgeous | English | 0.9 | 0.4 | Striking, impressive beauty
pulchritudinous | English | 0.75 | 1.0 | Ostentatiously literary for physical beauty
ravissant | French | 0.8 | 0.8 | Enchantingly beautiful

### `obscure` (adjective)  
unclear | English | 0.95 | 0.2 | Simple, direct equivalent
abstruse | English | 0.85 | 0.9 | Difficult to understand, recondite
tenebrous | English | 0.7 | 0.95 | Dark, murky, shadowy
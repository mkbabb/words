# Synonyms: {{ word }} ({{ part_of_speech }})

**Definition**: {{ definition }}
{% if existing_synonyms %}**Existing**: {{ existing_synonyms | join(', ') }}{% endif %}

## Task

Generate {{ count }}{% if existing_synonyms %} NEW (not in Existing list){% endif %} synonyms for the specific sense defined above.

### Distribution
- ~40% common: everyday, widely understood alternatives
- ~30% literary: sophisticated or elevated register
- ~20% foreign: non-English terms where they capture a nuance English lacks
- ~10% technical: domain-specific vocabulary

### Quality Rules
- Every synonym must be substitutable in at least some contexts where the target word appears.
- Match the part of speech exactly (noun for noun, verb for verb, etc.).
- Foreign-language synonyms must be actual words in that language, not transliterations.
- Prefer synonyms that illuminate different facets of the meaning over near-exact duplicates.

### Output Per Synonym
- **word**: the synonym
- **language**: source language (e.g., English, French, Latin)
- **relevance** (0.0-1.0): semantic closeness to the target definition
- **efflorescence** (0.0-1.0): 0=plain/utilitarian, 1=ornate/literary
- **explanation**: 5-15 words on how this synonym relates to or differs from the target

## Examples

### `beautiful` (adjective)
gorgeous | English | 0.9 | 0.4 | Striking, impressive beauty with visual impact
pulchritudinous | English | 0.75 | 1.0 | Ostentatiously literary term for physical beauty
ravissant | French | 0.8 | 0.8 | Enchantingly beautiful, implies being captivated

### `obscure` (adjective)
unclear | English | 0.95 | 0.2 | Simple, direct equivalent for lack of clarity
abstruse | English | 0.85 | 0.9 | Difficult to understand due to inherent complexity
tenebrous | English | 0.7 | 0.95 | Dark and murky, more physical than intellectual
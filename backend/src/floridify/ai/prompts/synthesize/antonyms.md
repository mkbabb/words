# Antonyms: {{ word }} ({{ part_of_speech }})

**Definition**: {{ definition }}
**Language**: {{ language | default('English') }}
{% if existing_antonyms %}**Existing**: {{ existing_antonyms | join(', ') }}{% endif %}

## Task

Generate up to {{ count }}{% if existing_antonyms %} NEW (not in Existing list){% endif %} antonyms for the specific sense defined above. Not all words have antonyms. If no genuine antonym exists, return an empty list. Return fewer rather than padding with weak alternatives.

### Distribution
- ~80% {{ language | default('English') }}: everyday, literary, and technical antonyms in the word's primary language
- ~20% cross-language: non-{{ language | default('English') }} terms that capture an opposing nuance the primary language lacks

### Quality Rules
- **NEVER include "{{ word }}" itself as an antonym.** A word cannot be its own antonym.
- Every antonym must express a genuinely opposing or contrary meaning to the target definition, not merely a different concept.
- Match the part of speech exactly.
- Distinguish between contradictory antonyms (hot/cold), complementary antonyms (alive/dead), and relational antonyms (buy/sell). Prefer contradictory when available.
- Foreign-language antonyms must be actual words in that language.

### Output Per Antonym
- **word**: the antonym
- **language**: source language (e.g., English, French, German)
- **relevance** (0.0-1.0): strength of the oppositional relationship
- **efflorescence** (0.0-1.0): 0=plain/utilitarian, 1=ornate/literary
- **explanation**: 5-15 words on how this antonym opposes the target

## Examples

### `beautiful` (adjective)
ugly | English | 0.95 | 0.2 | Direct everyday opposite of physical attractiveness
grotesque | English | 0.85 | 0.8 | Distorted or unnatural in a repulsive way
mostruoso | Italian | 0.75 | 0.7 | Monstrous, horrifying in appearance

### `increase` (verb)
decrease | English | 0.95 | 0.3 | Standard, direct opposite
attenuate | English | 0.8 | 0.8 | Gradually weaken, reduce, or thin out
abate | English | 0.85 | 0.7 | Diminish in intensity, force, or amount
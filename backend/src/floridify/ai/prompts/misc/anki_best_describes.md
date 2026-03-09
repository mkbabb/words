# Best Describes: {{ word }} ({{ part_of_speech }})

**Definition**: {{ definition }}
{% if examples %}**Examples**: {{ examples }}{% endif %}

Generate a "which best describes" multiple-choice question for "{{ word }}".

## Rules
- The correct choice is a **paraphrase** of the definition — same meaning, different words. Never copy the definition verbatim.
- The 3 distractors must be:
  - Plausible to someone with partial knowledge (related domain, similar register)
  - Clearly wrong to someone who knows the word
  - Not trick answers or near-synonyms of the correct choice
- NEVER include "{{ word }}" or morphological variants ({{ word }}ing, {{ word }}ed, etc.) in any choice.
- All 4 choices should be roughly equal length and grammatical style.
- Randomize the position of the correct answer across A-D.

## Distractor strategies
- Use definitions of words from the same semantic field (e.g., for "laconic": a definition of "terse" is too close; use one for "verbose", "eloquent", or "pedantic")
- Use a meaning the word *sounds like* it could have but doesn't
- Use a related but distinct concept from the same domain
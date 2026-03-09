# Fill-in-the-Blank: {{ word }} ({{ part_of_speech }})

**Definition**: {{ definition }}
{% if examples %}**Examples**: {{ examples }}{% endif %}

Generate a fill-in-the-blank question for "{{ word }}".

## Rules
- Write a sentence with _____ where "{{ word }}" belongs. The sentence must:
  - Provide enough context that only "{{ word }}" fits among the four choices
  - Sound natural — the kind of sentence you'd find in a novel, essay, or quality journalism
  - Not restate the dictionary definition (test *usage*, not recall)
- One choice must be "{{ word }}".
- The 3 distractors must be the same part of speech ({{ part_of_speech }}), plausible at first glance, but ruled out by the sentence's context.
- All 4 choices should be real words at a similar difficulty level.
- Randomize the position of "{{ word }}" across A-D.

## Good context clues (use 1-2)
- A scenario that evokes the word's specific connotation
- Collocations or phrases the word naturally appears in
- Cause-and-effect relationships that narrow the meaning
- A contrast or parallel that eliminates distractors
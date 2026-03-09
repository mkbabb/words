# Collocations: "{{ word }}" ({{ part_of_speech }})

{{ definition }}

Return up to {{ count }} collocations total across all types.

## Collocation Types
- **adjective**: modifying adjectives
- **verb**: verbal companions
- **noun**: noun associations
- **adverb**: adverbial modifiers
- **preposition**: prepositional bonds

## Strength Scale
- 1.0 = fixed/idiomatic (e.g., "make" + "decision", "strong" + "tea")
- 0.8–0.9 = highly conventional (e.g., "raise" + "concern")
- 0.6–0.7 = common pairing (e.g., "interesting" + "idea")
- <0.6 = do not include

## Rules
1. Only collocations a native speaker would produce unprompted. No forced or creative pairings.
2. Omit types with no strong collocations.
3. Strength reflects how conventionalized the pairing is, not just co-occurrence frequency.
4. Collocations must match the given sense/definition, not other senses of the word.
5. Prefer collocations that are distinctive to this word over generic ones (e.g., for "decision": "make" over "good").

## Anchors

### "decision" (noun)
- verb: make (0.95), reach (0.85), reverse (0.8)
- adjective: difficult (0.9), informed (0.85), final (0.8)

### "egregious" (adjective)
- noun: error (0.9), violation (0.9), breach (0.85)
- adverb: particularly (0.75), especially (0.7)

### "conduct" (verb)
- noun: research (0.9), investigation (0.9), experiment (0.85), survey (0.85)
- adverb: thoroughly (0.75)

Return collocations with strength scores (0.6–1.0).
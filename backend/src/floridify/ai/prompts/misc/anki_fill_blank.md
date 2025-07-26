# Create Fill-in-the-Blank Question for "{{ word }}" ({{ part_of_speech }})

## Word Information
**Word**: {{ word }}
**Definition**: {{ definition }}
**Part of Speech**: {{ part_of_speech }}
{% if examples %}**Examples**: {{ examples }}{% endif %}

Create a GRE-level fill-in-the-blank question that tests the student's ability to choose the correct word from four options.

## Task
Generate:
1. A sophisticated sentence with _____ where "{{ word }}" belongs
2. Four word choices (A, B, C, D) where exactly ONE will be the target word "{{ word }}"
3. Three distractor words that are plausible but incorrect

## Critical Requirements for Choices
- **Choice A, B, C, or D must be the target word "{{ word }}" itself**
- The other three choices must be different words (not variants of the target word)
- All four choices must be the same part of speech as "{{ word }}"
- Distractors should be semantically related but clearly incorrect in context
- Distractors should be words that could plausibly fit the sentence structure

## Guidelines
- Create a sentence where context clearly indicates the target word
- Use graduate-level vocabulary and sophisticated context
- Make distractors challenging but not impossible to eliminate
- Ensure the sentence is unambiguous when the correct word is chosen
- Test precise word meaning, not just grammatical fit

Generate the sentence and four word choices, then specify which letter (A, B, C, D) contains the target word "{{ word }}".
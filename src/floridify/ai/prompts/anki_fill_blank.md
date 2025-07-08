# Create Fill-in-the-Blank Question for "{{ word }}" ({{ word_type }})

## Word Information
**Word**: {{ word }}
**Definition**: {{ definition }}
**Part of Speech**: {{ word_type }}
{% if examples %}**Examples**: {{ examples }}{% endif %}

Create a GRE-level fill-in-the-blank question with multiple choice answers.

## Critical Requirements
- Create a sentence with _____ where "{{ word }}" belongs
- **NEVER include the target word "{{ word }}" in any of the four answer choices**
- **NEVER include any form, variant, or derivative of "{{ word }}" in the choices**
- One choice should be the correct answer (the target word itself, but this will be added separately)
- Three choices should be plausible but incorrect words that could fit the context

## Guidelines
- Create a sophisticated sentence where the word is essential to meaning
- Make the sentence challenging but not artificially obscure
- The blank should be unambiguous when context is understood
- Use vocabulary appropriate for graduate-level assessment
- Make distractors words that could plausibly fit the sentence context
- Ensure all choices are the same part of speech as the target word
- Test semantic understanding, not rote memorization

Generate a sentence with _____ and four word choices (A, B, C, D) where one will be replaced with the target word, and specify which letter is correct.
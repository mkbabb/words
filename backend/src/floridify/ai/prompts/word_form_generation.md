# Word Form Generation

Generate all standard word forms for "{{ word }}" ({{ word_type }}).

## Requirements:
1. Generate only grammatically correct forms
2. Include all standard inflections for the word type
3. Do not include compound forms or phrases
4. Each form should have a clear type label

## Expected Forms by Word Type:

### For Nouns:
- plural
- possessive
- plural possessive

### For Verbs:
- present_participle (ing form)
- past
- past_participle
- third_person_singular

### For Adjectives:
- comparative
- superlative

### For Adverbs:
- comparative (if applicable)
- superlative (if applicable)

## Example:
For "run" (verb):
- present_participle: running
- past: ran
- past_participle: run
- third_person_singular: runs

Generate appropriate word forms for "{{ word }}".
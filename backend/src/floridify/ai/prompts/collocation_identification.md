# Collocation Identification

Identify common collocations for "{{ word }}" ({{ word_type }}) based on:

**Definition**: {{ definition }}

## Collocation Types:
- **adjective**: Adjectives that commonly modify this word
- **verb**: Verbs that commonly take this word as object
- **noun**: Nouns commonly associated with this word
- **adverb**: Adverbs that commonly modify this word
- **preposition**: Prepositions that follow this word

## Requirements:
1. Include only strong, natural collocations
2. Provide frequency score (0.0-1.0)
3. Maximum 5 per type
4. Focus on this specific meaning/definition
5. Order by frequency within each type

## Example Format:
For "decision" (noun):
- adjective collocations:
  - "difficult" (0.9)
  - "important" (0.8)
- verb collocations:
  - "make" (0.95)
  - "reach" (0.7)

Identify natural collocations with frequency scores.
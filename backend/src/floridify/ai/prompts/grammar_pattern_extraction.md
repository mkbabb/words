# Grammar Pattern Extraction

Extract grammar patterns for the {{ part_of_speech }} based on this definition:

**Definition**: {{ definition }}

## Pattern Notation:
### For Verbs:
- [I] - Intransitive (no object)
- [T] - Transitive (requires object)
- [Tn] - Transitive + noun
- [Tn.pr] - Transitive + noun + preposition
- [Dn.n] - Ditransitive (two objects)
- [V-ing] - Followed by gerund
- [V to inf] - Followed by infinitive
- [V that] - Followed by that-clause

### For Nouns:
- [C] - Countable
- [U] - Uncountable
- [sing] - Singular only
- [pl] - Plural only

### For Adjectives:
- [attrib] - Attributive only
- [pred] - Predicative only
- [+ prep] - Requires specific preposition

## Requirements:
1. Use standard grammatical notation
2. Include human-readable descriptions
3. Extract patterns evident from the definition
4. Order by frequency of use

## Example:
For verb "give" (transfer possession):
- Pattern: [Dn.n]
- Description: "Ditransitive verb taking two objects"

Extract applicable patterns with descriptions.
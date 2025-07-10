# Synonym Generation with Balanced Expressiveness

Generate {{ count }} relevant synonyms for the given word, balancing semantic accuracy with linguistic beauty. Provide both common and expressive alternatives.

## Input Word
**Word:** {{ word }}
**Definition:** {{ definition }}
**Word Type:** {{ word_type }}

## Instructions

Generate exactly {{ count }} synonyms that capture the word's meaning. Create a balanced mix:

**Distribution (approximate):**
- 40% Common English synonyms (everyday usage)
- 30% Expressive English synonyms (literary, archaic, or vivid)
- 20% Foreign language terms (when they add precision or beauty)
- 10% Technical or specialized terms (when relevant)

## Scoring Criteria

**Relevance** (0.0-1.0): Semantic accuracy and contextual appropriateness
- 0.9-1.0: Direct synonyms, interchangeable in most contexts
- 0.7-0.9: Near-synonyms with slight contextual differences
- 0.5-0.7: Related concepts sharing core meaning

**Efflorescence** (0.0-1.0): Linguistic beauty and expressiveness
- 0.9-1.0: Irreplaceable precision, poetic resonance (e.g., "saudade", "schadenfreude")
- 0.7-0.9: Elegant expressions that enhance meaning (e.g., "au courant", "zeitgeist")
- 0.5-0.7: Vivid or memorable phrasing
- 0.3-0.5: Clear, functional synonyms

## Output Requirements

For each synonym provide:
- Word/phrase
- Language of origin
- Relevance score (how well it matches the meaning)
- Efflorescence score (beauty and expressiveness)
- Concise explanation (1-2 sentences max)

Order by relevance first, then efflorescence. Prioritize accuracy while including linguistically beautiful alternatives.
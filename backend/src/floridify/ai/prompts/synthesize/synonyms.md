# Synonym Synthesis with Balanced Expressiveness

{% if existing_synonyms and existing_synonyms|length > 0 %}
Synthesize {{ count }} total synonyms for the given word, enhancing the existing list by adding {{ count - existing_synonyms|length }} new relevant synonyms. Balance semantic accuracy with linguistic beauty.

## Input Word
**Word:** {{ word }}
**Definition:** {{ definition }}
**Part of Speech:** {{ part_of_speech }}

## Existing Synonyms
The following synonyms are already known for this word:
{% for synonym in existing_synonyms %}
- {{ synonym }}
{% endfor %}

## Instructions

Generate exactly {{ count - existing_synonyms|length }} NEW synonyms that:
1. Do NOT duplicate any existing synonyms
2. Complement the existing synonyms with different nuances
3. Capture the word's meaning with fresh perspectives
{% else %}
Generate {{ count }} relevant synonyms for the given word, balancing semantic accuracy with linguistic beauty. Provide both common and expressive alternatives.

## Input Word
**Word:** {{ word }}
**Definition:** {{ definition }}
**Part of Speech:** {{ part_of_speech }}

## Instructions

Generate exactly {{ count }} synonyms that capture the word's meaning.
{% endif %}

Create a balanced mix:

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
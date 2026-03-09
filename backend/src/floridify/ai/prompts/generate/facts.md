Generate {{ count }} or fewer facts about "{{ word }}" ({{ definition }}). Quality over quantity — omit a fact rather than include a banal one.

Each fact should teach something a well-read person might not know. 1-2 sentences each.

Spread across these categories (not all required — pick what's genuinely interesting):
- **Etymology**: surprising origin, semantic drift, borrowed-from language
- **Cultural**: how the word shaped or reflects culture, law, art, science
- **Usage**: counterintuitive grammar, common misuse, register shifts over time
- **Historical**: first attestation, famous usage, pivotal moments for the word
- **Linguistic**: cognates, false friends, phonological quirks, morphological oddities

Avoid: defining the word, stating the obvious ("X comes from Latin" without saying *why* that matters), or padding with filler.
{% if previous_words %}
If natural, connect to: {{ previous_words | join(', ') }}
{% endif %}
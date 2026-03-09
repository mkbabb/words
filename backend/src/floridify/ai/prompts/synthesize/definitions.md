# Synthesize Definitions: {{ word }}{% if meaning_cluster %} ({{ meaning_cluster }}){% endif %}

## Sources
{% for d in definitions %}
[{{ d.provider }}] {{ d.part_of_speech }}: {{ d.text }}
{% endfor %}

## Task

Synthesize the above provider definitions into unified, non-redundant definitions.

### Reconciliation Rules
- When providers agree on core meaning but differ in wording, synthesize the most precise and comprehensive version.
- When providers assign different parts of speech to the same sense, prefer the POS used by the majority. If tied, prefer the more grammatically standard label.
- When providers give conflicting information (e.g., different scope of meaning), produce a definition that captures the broadest defensible scope, noting restrictions only when well-attested.
- Preserve domain-specific senses (legal, medical, computing) as separate definitions even if only one provider includes them.

### Clustering Criteria
- MERGE definitions that describe the same core concept with different phrasing.
- KEEP SEPARATE definitions that differ in: part of speech, semantic domain, register (formal vs. informal), or connotation (positive vs. negative).
- For polysemous words, each distinct sense gets its own definition.

### Definition Quality Standards
- 20-35 words per definition.
- Structure: core meaning, then elaboration, then domain qualifier if relevant.
- Never define a word using itself or its direct morphological variants.
- Prefer active, concrete language over abstract paraphrase.
- Do not start with "Of or relating to" unless unavoidable.

### Output
- Part of speech for each definition.
- List of source providers that contributed to each synthesized definition.
- Relevancy score (0.0-1.0): how central this sense is to common usage.

## Examples

### `algorithm` (cluster: algorithm_noun_procedure)
Sources:
[Oxford] noun: finite sequence of well-defined instructions
[Wiktionary] noun: step-by-step procedure for calculations
[Merriam-Webster] noun: process or rules for problem-solving

**noun**: A finite sequence of well-defined instructions or rules, typically used to solve specific problems or perform computations systematically.
**Providers**: Oxford, Wiktionary, Merriam-Webster
**Relevancy**: 0.95

### `sanction` (cluster: sanction_noun)
Sources:
[Oxford] noun: official permission or approval for an action
[Merriam-Webster] noun: a coercive measure adopted by several nations to force compliance
[Wiktionary] noun: a penalty for disobeying a law or rule

**noun** (sense 1): Official permission, approval, or authoritative endorsement of an action or practice.
**Providers**: Oxford
**Relevancy**: 0.85

**noun** (sense 2): A punitive measure, especially one imposed by multiple states or an authority, to compel compliance with international law or norms.
**Providers**: Merriam-Webster, Wiktionary
**Relevancy**: 0.90
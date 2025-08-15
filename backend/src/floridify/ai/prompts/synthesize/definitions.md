# Synthesize: {{ word }}{% if meaning_cluster %} ({{ meaning_cluster }}){% endif %}

## Sources
{% for d in definitions %}
[{{ d.provider }}] {{ d.part_of_speech }}: {{ d.text }}
{% endfor %}

## Task
Create clear, precise definitions without redundancy.
Target: 20-35 words. Structure: core meaning → elaboration → domain if relevant.
Include source providers that contributed to each synthesized definition.
Output with relevancy score (0-1).

## Examples

### `algorithm` (cluster: algorithm_noun_procedure)
Sources: 
[Oxford] noun: finite sequence of well-defined instructions
[Wiktionary] noun: step-by-step procedure for calculations
[Merriam-Webster] noun: process or rules for problem-solving

**noun**: A finite sequence of well-defined instructions or rules, typically used to solve specific problems or perform computations systematically.
**Providers**: Oxford, Wiktionary, Merriam-Webster
**Relevancy**: 0.95

### `entropy` (cluster: entropy_noun_disorder)
Sources:
[Cambridge] noun: measure of disorder or randomness
[Physics Dictionary] noun: thermodynamic unavailability of energy
[Oxford] noun: gradual decline into disorder

**noun**: A measure of disorder or uncertainty in a system; in thermodynamics, unavailability of energy for work; broadly, tendency toward increasing disorder.
**Providers**: Cambridge, Physics Dictionary, Oxford
**Relevancy**: 0.92
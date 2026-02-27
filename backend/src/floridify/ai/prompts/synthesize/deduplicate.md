# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions

{% for def in definitions %}
{{ loop.index0 }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task

**AGGRESSIVELY** deduplicate definitions herein. Select supreme quality **ONLY**. Never merge different parts of speech. Merge if semantic similarity >80%. Brief reasoning (max 10 words). **Output indices merged, quality score (0-1).**

## Examples

#### `algorithm` (noun)
0: noun: A finite sequence of well-defined instructions
1: noun: Step-by-step procedure for calculations
2: noun: Process or rules for problem-solving operations
3: noun: Finite sequence of rigorous instructions for specific problems

**Merge**: [0,3] precision; [1,2] simplicity
**Keep**: 0 (comprehensive), 1 (accessible)
**Quality**: 0.9

#### `sanction` (noun)
0: noun: Official permission or approval
1: noun: Threatened penalty for disobeying
2: noun: Coercive measures by states
3: noun: Formal authorization

**Merge**: [0,3] approval; [1,2] penalty
**Keep**: 0 (clearer positive), 1 (clearer negative)
**Quality**: 0.95

#### `run` (verb)
0: verb: Move faster than walk
1: verb: Move rapidly with feet leaving ground
2: verb: Operate or function
3: verb: Be in charge of
4: verb: Make system work

**Merge**: [0,1] movement; [2,4] operation
**Keep**: 1 (precise), 2 (general), 3 (distinct management)
**Quality**: 0.85

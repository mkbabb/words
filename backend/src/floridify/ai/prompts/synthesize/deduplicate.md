# Deduplicate: {{ word }} {% if part_of_speech %}({{ part_of_speech }}){% endif %}

## Definitions

{% for def in definitions %}
{{ loop.index0 }}. {{ def.part_of_speech }}: {{ def.text }}
{% endfor %}

## Task

Identify and merge duplicate or near-duplicate definitions. Select the highest-quality representative from each group.

### Merge Criteria (merge when ANY apply)
- Same core meaning with different wording (semantic overlap >80%).
- One definition is a strict subset of another (e.g., "to walk" vs. "to walk or move on foot").
- Definitions differ only in example scope but describe the same action/state.

### Keep Separate (NEVER merge when ANY apply)
- Different parts of speech, even if semantically related.
- Same POS but different semantic domains (e.g., "run a race" vs. "run a company").
- Opposing connotations (e.g., "sanction" as approval vs. penalty).
- Literal vs. figurative senses.
- Different registers (slang vs. formal) when the distinction matters.

### Selection Preference
When choosing which definition to keep from a merged group:
1. Prefer the more precise and complete definition.
2. Prefer definitions that avoid circular phrasing.
3. Prefer definitions with clear scope boundaries.

### Output Format
- Group indices that should merge. State the shared meaning in max 10 words.
- Identify which index to keep from each group and why (max 10 words).
- Quality score (0.0-1.0): confidence in deduplication correctness.

## Examples

#### `algorithm` (noun)
0: noun: A finite sequence of well-defined instructions
1: noun: Step-by-step procedure for calculations
2: noun: Process or rules for problem-solving operations
3: noun: Finite sequence of rigorous instructions for specific problems

**Merge**: [0,3] same meaning, different phrasing; [1,2] simplified variants
**Keep**: 0 (most precise), 1 (most accessible)
**Quality**: 0.9

#### `sanction` (noun)
0: noun: Official permission or approval
1: noun: Threatened penalty for disobeying
2: noun: Coercive measures by states
3: noun: Formal authorization

**Merge**: [0,3] both mean approval; [1,2] both mean punishment
**Keep**: 0 (clearer for approval sense), 1 (clearer for penalty sense)
**Quality**: 0.95

#### `run` (verb)
0: verb: Move faster than walk
1: verb: Move rapidly with feet leaving ground
2: verb: Operate or function
3: verb: Be in charge of
4: verb: Make system work

**Merge**: [0,1] physical locomotion; [2,4] mechanical operation
**Keep**: 1 (precise physical), 2 (general operation), 3 (distinct: management)
**Quality**: 0.85
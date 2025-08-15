# Cluster Meanings: {{ word }}

## Definitions
{% for d in definitions %}
{{ loop.index0 }}: {{ d[0] }} ({{ d[1] }}) - {{ d[2] }}
{% endfor %}

## Task
Group by distinct meaning AND part of speech. Format:
- cluster_id: {word}_{part_of_speech}_{name} (e.g. bludgeon_noun_weapon, bludgeon_verb_strike)
- description: (3-6 words)
- indices: [list]
- confidence: 0-1
- relevancy: 0-1

**Critical rules:**
1. NEVER group different parts of speech together
2. Each definition goes in ONE cluster only
3. Preserve all parts of speech separately

**AGGRESSIVE MERGING IMPERATIVE:**
- Merge ALL definitions with >70% semantic overlap
- Wiktionary's multiple entries for ONE sense MUST coalesce
- Historical evolution (carriage→automobile) is NOT semantic divergence
- For 10+ definitions, forge 3-4 clusters maximum
- Ask: "Would a native speaker consider these the same sense?" If yes, MERGE

## Examples

### "phaeton" - Aggressive Vehicle Consolidation:
0: Wiktionary (noun) - light four-wheeled carriage drawn by horses
1: Oxford (noun) - light open carriage
2: Wiktionary (noun) - large touring motorcar with folding top
3: Webster (noun) - early automobile

- cluster_id: phaeton_noun_carriage
  description: open carriage, horse or motor
  indices: [0,1,2,3]
  confidence: 0.95
  relevancy: 1.0

### "sanction" - Preserving True Antonymy:
0: Oxford (noun) - official permission
1: Wiktionary (noun) - authoritative approval
2: Oxford (noun) - penalty for disobeying
3: Collins (noun) - coercive measure

- cluster_id: sanction_noun_approval
  description: official permission
  indices: [0,1]
  confidence: 0.95
  relevancy: 1.0

- cluster_id: sanction_noun_penalty
  description: punitive measure
  indices: [2,3]
  confidence: 0.95
  relevancy: 1.0
 
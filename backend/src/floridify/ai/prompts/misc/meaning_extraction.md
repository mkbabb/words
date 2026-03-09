# Cluster Definitions: {{ word }}

## Input
{% for d in definitions %}
{{ loop.index0 }}: {{ d[0] }} ({{ d[1] }}) - {{ d[2] }}
{% endfor %}

## Task
Group definitions into meaning clusters. Output fields per cluster:
- **cluster_id**: `{word}_{pos}_{sense}` (e.g. `bludgeon_noun_weapon`, `bludgeon_verb_strike`)
- **cluster_description**: 3-6 word summary
- **definition_indices**: [list of indices]
- **relevancy**: 0.0-1.0 (common usage frequency)

## Rules

### Part of Speech
- NEVER merge different parts of speech into one cluster.
- If providers disagree on POS for the same sense (e.g. one says "adjective", another says "noun" for the same meaning), create separate clusters per POS and note via cluster_id.

### When to MERGE
- Definitions with >70% semantic overlap, even if worded differently across providers.
- Historical evolution of the same referent (carriage→automobile) = same sense.
- Wiktionary's multiple sub-entries for one meaning MUST coalesce.
- Ask: "Would a native speaker consider these the same word sense?" If yes, merge.

### When to KEEP SEPARATE
- True antonymic senses (e.g. "sanction" = approval vs. penalty).
- Figurative vs. literal when meaning genuinely diverges (not just stylistic variation).
- Domain-specific senses distinct from general usage (e.g. "bug" in computing vs. entomology vs. espionage).

### Cluster Count
- Target 3-5 clusters for 10+ definitions. Fewer definitions = fewer clusters.
- Every definition index must appear in exactly one cluster.

## Examples

### Aggressive merge — "phaeton":
0: Wiktionary (noun) - light four-wheeled carriage drawn by horses
1: Oxford (noun) - light open carriage
2: Wiktionary (noun) - large touring motorcar with folding top
3: Webster (noun) - early automobile

→ cluster_id: phaeton_noun_carriage, indices: [0,1,2,3], relevancy: 1.0

### Preserving antonymy — "sanction":
0: Oxford (noun) - official permission
1: Wiktionary (noun) - authoritative approval
2: Oxford (noun) - penalty for disobeying
3: Collins (noun) - coercive measure

→ sanction_noun_approval: [0,1], relevancy: 0.8
→ sanction_noun_penalty: [2,3], relevancy: 1.0

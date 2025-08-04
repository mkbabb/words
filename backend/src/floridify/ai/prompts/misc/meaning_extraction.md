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

Be aggressive in grouping similar meanings, but do not force unrelated meanings together. Use the definitions to guide your grouping, though be extremely fastidious and meticulous.

## Examples

### "en coulisse":
- definitions: ["behind the scenes", "in the background"]
- clusters:
  - cluster_id: en_coulisse_preposition_backstage
    description: (behind the scenes)
    indices: [0]
    confidence: 0.9
    relevancy: 0.8
 
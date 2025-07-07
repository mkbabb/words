# Extract Distinct Meanings for "{{ word }}"

Analyze all definitions and create a numerical mapping of distinct meaning clusters to definition IDs.

## All Definitions

{% for definition in definitions %}
**ID {{ loop.index0 }}**: {{ definition[0] }} ({{ definition[1] }}) - {{ definition[2] }}
{% endfor %}

## Task

Create distinct meaning clusters where each cluster represents a fundamentally different sense/meaning of the word. Then map each cluster to the specific definition IDs (0-based indexing) that belong to that cluster.

## Examples

For "bank":
- cluster_id: "bank_financial", description: "Financial institutions and buildings", indices: [0, 3, 7]
- cluster_id: "bank_geographic", description: "Edge of water bodies", indices: [1, 4]
- cluster_id: "bank_arrangement", description: "Rows or arrangements of items", indices: [2, 5, 6]

For "run":
- cluster_id: "run_movement", description: "Moving quickly on foot", indices: [0, 2, 8]
- cluster_id: "run_operation", description: "Operating or managing something", indices: [1, 4, 9]
- cluster_id: "run_flow", description: "Flowing like a liquid", indices: [3, 6]

## Output Structure

Return a list of cluster mappings, where each mapping contains:
1. **cluster_id**: Unique identifier (e.g., "bank_financial", "bank_geographic")
2. **cluster_description**: Human-readable description of this cluster
3. **definition_indices**: List of definition indices (0-based) that belong to this cluster
4. **confidence**: Overall confidence in the clustering (0.0-1.0)

## Guidelines

- Only create separate clusters for truly distinct senses/meanings
- Don't separate for minor variations of the same concept
- Group related definitions together regardless of word type
- Ensure every definition ID appears in exactly one cluster
- Use descriptive cluster IDs (e.g., "word_context" format)
- Provide clear, concise cluster descriptions

**Example - Avoid Duplicates**: For "en coulisse" with definitions like "backstage" and "behind the scenes", these should be in ONE cluster since they describe the same core concept.

Return a structured response with the numerical mappings.

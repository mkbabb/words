# Synthesize Definitions for "{{ word }}"

{% if meaning_cluster %}

## Meaning Cluster (disambiguation of the word): {{ meaning_cluster }}

{% endif %}

## Source Definitions

{% for definition in definitions %}
**Word Type**: {{ definition.word_type }}  
**Definition**: {{ definition.definition }}  
{% if definition.synonyms %}**Synonyms**: {{ definition.synonyms | join(', ') }}{% endif %}  
{% if definition.examples and definition.examples.generated %}**Examples**:
{% for example in definition.examples.generated %}

-   {{ example.sentence }}
    {% endfor %}
    {% endif %}
    {% if definition.examples and definition.examples.literature %}**Literature Examples**:
    {% for lit_example in definition.examples.literature %}
-   "{{ lit_example.sentence }}" - {{ lit_example.source.title }}
    {% endfor %}
    {% endif %}
    {% if definition.raw_metadata %}**Metadata**: {{ definition.raw_metadata }}{% endif %}

---

{% endfor %}

## Task

For each word type represented in the source definitions, synthesize a clear, concise definition that:

-   Combines the best elements from all sources
-   Maintains academic dictionary tone
-   Preserves key terminology, phrasing, and structure
-   Removes redundancy
-   Leverages the full context from examples, synonyms, and metadata
-   Creates a supreme, normalized definition for this meaning cluster
-   Includes a relevancy score (0.0-1.0) indicating how commonly this definition is used compared to others in this cluster

Use all available information (synonyms, examples, metadata) to inform your synthesis.

**Output Requirements**: Each synthesized definition must include a relevancy score where 1.0 represents the most commonly encountered usage within this meaning cluster, and 0.0 represents highly specialized or rare usage.

Synthesize clear, unique definitions with distinct word types and meanings. Avoid duplicating semantically identical definitions.

For example, if "protean" has two meaning clusters, (variability and biochemical), but variability has two entries with the same definition, synthesize a single definition that captures both entries' essence without redundancy.

# Task: Synthesize Dictionary Definition

You are synthesizing a coherent definition from multiple dictionary providers.

## Input Data
Word: {{ word }}
Word Type: {{ word_type }}

## Provider Definitions
{% for provider, definition in provider_definitions %}
**{{ provider }}**: {{ definition }}
{% endfor %}

## Instructions
1. Select the most accurate and complete definition
2. Preserve original wording when possible
3. Discard incomplete or contradictory information
4. Maintain academic dictionary tone
5. Ensure grammatical correctness

## Output Format
Return a single, coherent definition that best represents the word's meaning.
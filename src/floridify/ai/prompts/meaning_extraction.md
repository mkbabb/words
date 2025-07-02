# Extract Distinct Meanings for "{{ word }}"

Analyze all provider definitions and identify distinct core meanings/senses of this word.

## All Provider Definitions
{% for provider, word_type, definition in all_provider_definitions %}
**{{ provider }}** ({{ word_type }}): {{ definition }}
{% endfor %}

## Task
Create distinct meaning clusters where each cluster represents a fundamentally different sense/meaning of the word. For example:

- "bank" meaning financial institution vs. river bank vs. arrangement of items
- "run" meaning to jog vs. to operate vs. to flee vs. to flow

## Output Structure
For each distinct meaning:
1. **meaning_id**: Short identifier (e.g., "bank_financial", "bank_geographic")  
2. **core_meaning**: Brief description of this meaning cluster
3. **word_types**: All grammatical types that apply to this meaning
4. **definitions_by_type**: List of definitions grouped by word type within this meaning
5. **confidence**: How confident you are this is a distinct meaning (0.0-1.0)

Each definitions_by_type entry should have:
- **word_type**: The grammatical type (noun, verb, etc.)
- **definitions**: List of provider definitions for this word type

## Guidelines
- Only create separate meanings for truly distinct senses
- Don't separate meanings for minor variations of the same concept
- Group related word types (noun/verb forms of same meaning) together
- Ensure every input definition is assigned to exactly one meaning cluster

**Example - Avoid Duplicates**: For "en coulisse" with definitions like "backstage" and "behind the scenes", these should be ONE meaning cluster (not two) since they describe the same core concept of "out of public view".

Return a structured response with all meaning clusters identified.
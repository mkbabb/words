# Antonym Synthesis

{% if existing_antonyms and existing_antonyms|length > 0 %}
Synthesize {{ count }} total antonyms for the word "{{ word }}" ({{ part_of_speech }}), enhancing the existing list by adding {{ count - existing_antonyms|length }} new antonyms.

**Definition**: {{ definition }}

## Existing Antonyms
The following antonyms are already known for this word:
{% for antonym in existing_antonyms %}
- {{ antonym }}
{% endfor %}

## Requirements:
1. Generate exactly {{ count - existing_antonyms|length }} NEW antonyms that represent the opposite meaning
2. Do NOT duplicate any existing antonyms
3. Complement the existing antonyms with different nuances of opposition
4. Avoid near-antonyms or contrasting words that aren't true opposites
5. Include only words that are commonly used and understood
6. Order by relevance to the specific definition provided
{% else %}
Generate {{ count }} antonyms for the word "{{ word }}" ({{ part_of_speech }}) based on the following definition:

**Definition**: {{ definition }}

## Requirements:
1. Generate exactly {{ count }} direct antonyms that represent the opposite meaning
2. Avoid near-antonyms or contrasting words that aren't true opposites
3. Include only words that are commonly used and understood
4. Order by relevance to the specific definition provided
5. Focus on the most common and recognizable opposites
{% endif %}

## Example:
For "happy" (adjective) meaning "feeling or showing pleasure":
- sad
- unhappy
- miserable
- depressed
- gloomy

Generate exactly {{ count }} antonyms for the given word and definition.
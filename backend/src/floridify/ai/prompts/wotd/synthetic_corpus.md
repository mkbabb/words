Generate {{ num_words }} real English words for semantic preference training data.

**Target Profile:**
- Style: {{ style }}
- Complexity: {{ complexity }}
- Era: {{ era }}

{% if theme %}
Theme: {{ theme }}
{% endif %}

{% if avoid_words %}
Exclude: {{ avoid_words | join(', ') }}
{% endif %}

**Hard constraints:**
1. Every word must be a real, attested English word — no coinages, no neologisms, no proper nouns.
2. Mix parts of speech: aim for roughly 40% nouns, 25% verbs, 25% adjectives, 10% adverbs.
3. Spread difficulty across beginner (10%), intermediate (40%), advanced (40%), expert (10%).
4. Each word must clearly exemplify the target style/complexity/era — if it doesn't obviously belong, pick a different word.

**Per-word output:**
- **word**: lowercase, no quotes
- **definition**: 1-2 sentences, precise
- **part_of_speech**: noun, verb, adjective, adverb, etc.
- **etymology**: origin language and key evolution (1-2 sentences)
- **example_sentence**: natural modern usage
- **semantic_justification**: why this word fits {{ style }}/{{ complexity }}/{{ era }} (1 sentence)
- **difficulty_level**: beginner, intermediate, advanced, or expert

Prioritize words that are genuinely distinctive of the target profile. A word that could belong to any category is a poor training example.
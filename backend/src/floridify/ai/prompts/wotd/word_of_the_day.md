Generate a compelling Word of the Day with educational value and memorable appeal.

{% if context %}
Context steering: {{ context }}
{% endif %}

{% if previous_words %}
Avoid these recently used words: {{ previous_words }}
{% endif %}

Requirements:
1. Select a word that is beautiful, useful, or intellectually stimulating
2. Choose words that expand vocabulary meaningfully (avoid overly common words)
3. Bias towards words with interesting etymology, cultural significance, or literary usage
4. Provide comprehensive educational context suitable for daily learning

Return:
- **word**: The selected word
- **definition**: Clear, concise definition (1-2 sentences)
- **etymology**: Brief origin and historical development
- **example_usage**: Natural sentence demonstrating proper usage
- **fascinating_fact**: Interesting linguistic, cultural, or historical insight
- **difficulty_level**: "intermediate" or "advanced" (avoid basic words)
- **memorable_aspect**: What makes this word particularly worth learning
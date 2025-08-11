Generate a high-quality corpus of words for semantic preference learning in a Word of the Day system.

**Target Characteristics:**
- **Style**: {{ style }} (classical: formal, timeless; modern: contemporary, current; romantic: emotive, aesthetic; neutral: balanced)
- **Complexity**: {{ complexity }} (beautiful: aesthetically pleasing, elegant; simple: accessible, clear; complex: sophisticated, nuanced; plain: straightforward)
- **Era**: {{ era }} (shakespearean: Elizabethan/Renaissance; victorian: 19th century; modernist: early-mid 20th; contemporary: current usage)
- **Count**: {{ num_words }} words

{% if theme %}
**Thematic Focus**: {{ theme }}
{% endif %}

{% if avoid_words %}
**Avoid These Words**: {{ avoid_words | join(', ') }}
{% endif %}

**Requirements:**
1. Select words that distinctly embody the target characteristics
2. Ensure variety in parts of speech (nouns, verbs, adjectives, adverbs)
3. Choose words with educational value and memorability
4. Include both common and less common words that fit the category
5. Provide etymological and contextual justification for each word
6. Ensure semantic coherence within the corpus

**Quality Standards:**
- Each word must clearly exemplify the requested style, complexity, and era
- Definitions should be precise and educational
- Examples should demonstrate natural, contemporary usage
- Etymology should be accurate and informative
- Avoid overly obscure or archaic words unless specifically requested

**Output Format:**
For each word, provide:
- **word**: The selected word (no quotes, just the word)
- **definition**: Clear, concise definition (1-2 sentences)
- **part_of_speech**: Grammatical category (noun, verb, adjective, etc.)
- **etymology**: Origin and historical development (2-3 sentences)
- **example_sentence**: Natural sentence demonstrating proper usage
- **semantic_justification**: Explain why this word fits {{ style }}/{{ complexity }}/{{ era }} (1-2 sentences)
- **difficulty_level**: Assessment - beginner, intermediate, advanced, or expert
- **confidence**: Your confidence in this classification (0.0 to 1.0)

Generate {{ num_words }} diverse words that form a semantically coherent corpus representing {{ style }}, {{ complexity }}, and {{ era }} characteristics.
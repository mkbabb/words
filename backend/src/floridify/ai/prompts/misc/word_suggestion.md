Query: {{ query }}

Find exactly {{ count }} words or phrases that best capture the query's essence. Bias towards words that are rare, beautiful, **efflorescent**, memorable, and semantically relevant.

Requirements:

1. Words or phrases must semantically match the query with confidence > 0.7
2. Leverage good French, Spanish, Italian, German, and Portuguese words or phrases that are not commonly used in English, **but common in their native languages**
3. Words from Dante, Petrarch, Boccaccio, Goethe, Rilke, Neruda, Borges, Virginia Woolf, Shakespeare, and other literary giants are highly encouraged
4. For text/passage queries: extract words FROM the text, not words ABOUT it
5. Provide brief, focused reasoning without superfluity
6. Reasoning must **ALWAYS** be in English
7. If the query contains an example usage, fill in the example_usage field with a relevant example

Example: "word that means like a peacock's feathers" -> "pavonine, iridescent, opalescent, resplendent, shimmering"

Return for each word:

- **confidence**: 0-1 (semantic match strength)
- **efflorescence**: 0-1 (word beauty/memorability)
- **reasoning**: concise explanation (max 2 sentences) -- ALWAYS in English
- **example_usage**: if helpful (optional) -- ALWAYS in English

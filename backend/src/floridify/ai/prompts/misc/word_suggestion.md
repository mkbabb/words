Query: {{ query }}

Find exactly {{ count }} words that best capture the query's essence. Bias towards words that are beautiful, efflorescent, memorable, and semantically relevant.

Requirements:
1. Words must semantically match the query with confidence > 0.7
2. For text/passage queries: extract words FROM the text, not words ABOUT it
3. Provide brief, focused reasoning without superfluity
4. Reasoning must **ALWAYS** be in English
5. If the query contains an example usage, fill in the example_usage field with a relevant example

Return for each word:
- **confidence**: 0-1 (semantic match strength)
- **efflorescence**: 0-1 (word beauty/memorability)
- **reasoning**: concise explanation (max 2 sentences) -- ALWAYS in English
- **example_usage**: if helpful (optional) -- ALWAYS in English

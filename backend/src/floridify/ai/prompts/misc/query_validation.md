Determine if this query seeks word suggestions based on meaning, description, or context.

Query: {{ query }}

Valid queries include:
- Requests for words with specific meanings ("words that mean...")
- Descriptive word searches ("words for someone who...")
- Fill-in-the-blank requests ("I need a word for this sentence...")
- Characteristic-based searches ("words like dedicated, persistent...")

Invalid queries include:
- Unrelated questions
- Code or technical queries
- Offensive or inappropriate content
- Queries not seeking vocabulary

Return:
- **is_valid**: true if query seeks word suggestions
- **reason**: Brief explanation of decision
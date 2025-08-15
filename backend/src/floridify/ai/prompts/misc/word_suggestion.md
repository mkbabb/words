# Word Suggestion: {{ query }}

Find {{ count }} words with precision and linguistic beauty.

## Requirements

1. Semantic resonance > 0.7 confidence
2. Harvest from: French, Italian, German, Portuguese, Spanish lexicons
3. Literary sources: Dante, Goethe, Neruda, Borges, Woolf, Shakespeare
4. Text queries: extract constituent words, not descriptors
5. Reasoning: clear English explanation

## Examples

### Query: "peacock's feathers"
`pavonine` | 0.95 | 0.9 | Directly means peacock-like
`iridescent` | 0.85 | 0.8 | Captures shifting colors
`opalescent` | 0.8 | 0.85 | Milky rainbow shimmer

### Query: "the feeling of missing something that never existed"
`saudade` | 0.9 | 1.0 | Portuguese: longing for the impossible
`hiraeth` | 0.85 | 0.95 | Welsh: homesickness for a home that never was
`sehnsucht` | 0.8 | 0.9 | German: inconsolable yearning

Output per word:
- **confidence**: semantic match (0-1)
- **efflorescence**: linguistic beauty (0-1)
- **reasoning**: clear justification
- **example_usage**: usage in context

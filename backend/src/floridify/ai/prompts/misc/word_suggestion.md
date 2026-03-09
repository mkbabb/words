# Word Suggestion: {{ query }}

Find {{ count }} words that answer this query. Favor precision, expressiveness, and linguistic beauty.

## Approach

1. Parse the query's intent: is it describing a feeling, a visual quality, a concept, a sound, a relationship?
2. Search across languages — English, French, Italian, German, Portuguese, Spanish, Welsh, Japanese, Arabic — for words that capture the idea with precision no paraphrase can match.
3. Rank by **confidence** (semantic fit) first, then **efflorescence** (beauty, memorability, mouth-feel).
4. For each word, provide a clear English reasoning and a usage example.

## Examples

**"peacock's feathers"**
- `pavonine` (0.95 / 0.9) — Directly means peacock-like; from Latin *pavo*
- `iridescent` (0.85 / 0.8) — Captures the shifting spectral colors
- `opalescent` (0.8 / 0.85) — The milky rainbow shimmer of nacre and feather

**"the feeling of missing something that never existed"**
- `saudade` (0.9 / 1.0) — Portuguese: longing for the absent or impossible
- `hiraeth` (0.85 / 0.95) — Welsh: homesickness for a home that may never have been
- `sehnsucht` (0.8 / 0.9) — German: inconsolable yearning for a far, nameless thing

**"words that feel like rain"**
- `petrichor` (0.95 / 0.95) — The scent of earth after rain
- `pluvial` (0.85 / 0.8) — Of or relating to rain; carries the weight of downpour
- `susurrus` (0.7 / 0.9) — A whispering, rustling sound — like rain on leaves

## Output per word
- **confidence**: semantic match (0-1)
- **efflorescence**: linguistic beauty and memorability (0-1)
- **reasoning**: why this word fits
- **example_usage**: the word used naturally in a sentence
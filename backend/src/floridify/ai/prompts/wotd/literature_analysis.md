Analyze vocabulary from a literary corpus and produce a 4D semantic fingerprint for preference vector training.

## Semantic Dimensions

**Style (0-7)**: 0=Formal/Academic, 1=Conversational, 2=Poetic/Literary, 3=Dramatic/Theatrical, 4=Archaic/Classical, 5=Regional/Dialectal, 6=Technical/Specialized, 7=Experimental/Avant-garde

**Complexity (0-7)**: 0=Elementary (Anglo-Saxon, short), 1=Basic, 2=Intermediate, 3=Advanced (multisyllabic), 4=Erudite (scholarly), 5=Ornate (baroque), 6=Dense (polysemous), 7=Esoteric (arcane)

**Era (0-7)**: 0=Ancient (<500 CE), 1=Medieval (500-1400), 2=Renaissance (1400-1600), 3=Early Modern (1600-1750), 4=Enlightenment (1750-1800), 5=Romantic/Victorian (1800-1900), 6=Modernist (1900-1950), 7=Contemporary (1950+)

**Variation (0-4)**: 0=Core/Central (most representative), 1=Common variant, 2=Uncommon variant, 3=Rare, 4=Experimental (author-specific)

## Calibration Examples

- Shakespeare ["tempest", "sovereign", "melancholy", "prithee"] → style=3, complexity=4, era=2, variation=0
- Woolf ["luminous", "consciousness", "wavering", "iridescent"] → style=2, complexity=5, era=6, variation=1
- Hemingway ["clean", "true", "good", "fish", "war"] → style=1, complexity=1, era=6, variation=0

## Task

1. **Classify** the corpus into the 4D space above. Weight toward the vocabulary's center of gravity, not outliers.
2. **Describe** each dimension choice in 1-2 sentences — explain *why*, not just *what*.
3. **Identify** 3-5 dominant themes and the most distinctive linguistic features.
4. **Assess** corpus quality (0.0-1.0): how well it represents the author's characteristic vocabulary vs. generic English.
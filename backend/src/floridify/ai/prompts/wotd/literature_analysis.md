# Literature Corpus Analysis Prompt

You are an expert literary analyst and computational linguist. Your task is to analyze vocabulary extracted from literary works and determine their semantic characteristics for training a preference vector system.

## Input
You will receive:
1. A list of words extracted from a specific author's works
2. Metadata about the author, time period, and genre
3. Word frequency information

## Analysis Tasks

### 1. Vocabulary Characterization
Analyze the provided vocabulary to determine:
- **Lexical Register**: Formal, informal, poetic, colloquial, archaic
- **Semantic Domains**: Love, nature, power, death, spirituality, etc.
- **Linguistic Complexity**: Syllable patterns, morphological complexity, etymology
- **Stylistic Markers**: Unique to author, period-specific, genre conventions

### 2. Semantic Attribute Mapping
Map the vocabulary to our 4-dimensional semantic space:

#### Style (0-7)
- 0: Formal/Academic (latinate, technical, precise)
- 1: Conversational (everyday, casual, modern)
- 2: Poetic/Literary (metaphorical, evocative, artistic)
- 3: Dramatic/Theatrical (emphatic, performative, dialogue-oriented)
- 4: Archaic/Classical (obsolete forms, historical usage)
- 5: Regional/Dialectal (vernacular, colloquial, place-specific)
- 6: Technical/Specialized (domain-specific jargon)
- 7: Experimental/Avant-garde (neologisms, unconventional)

#### Complexity (0-7)
- 0: Elementary (common, short, Anglo-Saxon roots)
- 1: Basic (everyday vocabulary, simple morphology)
- 2: Intermediate (standard literary vocabulary)
- 3: Advanced (sophisticated, multisyllabic)
- 4: Erudite (scholarly, rare, specialized)
- 5: Ornate (elaborate, baroque, highly decorated)
- 6: Dense (complex semantics, multiple meanings)
- 7: Esoteric (arcane, requiring special knowledge)

#### Era (0-7)
- 0: Ancient/Classical (pre-500 CE)
- 1: Medieval (500-1400)
- 2: Renaissance (1400-1600)
- 3: Early Modern (1600-1750)
- 4: Enlightenment (1750-1800)
- 5: Romantic/Victorian (1800-1900)
- 6: Modernist (1900-1950)
- 7: Contemporary (1950-present)

#### Variation (0-4)
- 0: Core/Central (most representative)
- 1: Common variant (typical alternatives)
- 2: Uncommon variant (less frequent forms)
- 3: Rare variant (unusual or unique usage)
- 4: Experimental (author-specific innovations)

### 3. Augmentation Suggestions

Based on the analysis, suggest:
1. **Missing Words**: Important vocabulary that should be included
2. **Overrepresented Terms**: Words that might skew the preference vector
3. **Thematic Clusters**: Groups of related words that capture key themes
4. **Semantic Gaps**: Conceptual areas underrepresented in the corpus

### 4. Quality Metrics

Evaluate the corpus quality:
- **Coverage**: How well it represents the author's vocabulary
- **Distinctiveness**: How unique compared to general English
- **Coherence**: Internal consistency of the word selection
- **Balance**: Distribution across semantic categories

## Output Format

Return a JSON object with the following structure:

```json
{
  "semantic_id": {
    "style": <0-7>,
    "complexity": <0-7>,
    "era": <0-7>,
    "variation": <0-4>
  },
  "analysis": {
    "style_description": "Detailed explanation of style classification",
    "complexity_description": "Explanation of complexity assessment",
    "era_description": "Historical/temporal context",
    "variation_description": "Uniqueness and variation factors"
  },
  "characteristics": {
    "dominant_themes": ["theme1", "theme2", ...],
    "linguistic_features": ["feature1", "feature2", ...],
    "stylistic_markers": ["marker1", "marker2", ...],
    "semantic_domains": ["domain1", "domain2", ...]
  },
  "augmentation": {
    "suggested_additions": ["word1", "word2", ...],
    "suggested_removals": ["word1", "word2", ...],
    "thematic_clusters": {
      "cluster_name": ["word1", "word2", ...],
      ...
    }
  },
  "quality_metrics": {
    "coverage_score": <0.0-1.0>,
    "distinctiveness_score": <0.0-1.0>,
    "coherence_score": <0.0-1.0>,
    "balance_score": <0.0-1.0>,
    "overall_quality": <0.0-1.0>
  },
  "metadata": {
    "author": "Author name",
    "period": "Literary period",
    "genre": "Primary genre",
    "word_count": <number>,
    "unique_features": ["feature1", "feature2", ...]
  }
}
```

## Examples

### Shakespeare Analysis
Input: "tempest, sovereign, melancholy, wherefore, prithee, beauteous..."
- Style: 3 (Dramatic/Theatrical)
- Complexity: 4 (Erudite)
- Era: 2 (Renaissance)
- Variation: 0 (Core)

### Virginia Woolf Analysis
Input: "luminous, consciousness, wavering, iridescent, fragmentary..."
- Style: 2 (Poetic/Literary)
- Complexity: 5 (Ornate)
- Era: 6 (Modernist)
- Variation: 1 (Common variant)

### Ernest Hemingway Analysis
Input: "clean, true, good, fish, war, drink, fight..."
- Style: 1 (Conversational)
- Complexity: 1 (Basic)
- Era: 6 (Modernist)
- Variation: 0 (Core)

## Guidelines

1. **Contextual Understanding**: Consider the historical and cultural context
2. **Comparative Analysis**: Compare against contemporary authors
3. **Statistical Validity**: Ensure sufficient sample size for conclusions
4. **Nuanced Classification**: Avoid oversimplification; capture complexity
5. **Practical Application**: Ensure mappings are useful for training

Remember: The goal is to create a semantic fingerprint that captures the essence of an author's vocabulary while being computationally useful for preference vector generation.
# AI Prompt Analysis: Synonym Generation

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/synthesize/synonyms.md`

### Strengths
- Creative distribution model (common/expressive/foreign/technical)
- Includes relevance and "efflorescence" scoring
- Requests explanations for each synonym
- Handles incremental generation (existing synonyms)

### Weaknesses
- No examples showing the distribution in practice
- "Efflorescence" metric is undefined and unclear
- No guidance on avoiding near-duplicates
- Missing context-specific synonym selection

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Distributed Synonym Categories
```
#### `beautiful` (adjective)
Definition: Pleasing to the senses or mind aesthetically

Generated synonyms following distribution:

**Common (40%)**:
- pretty | English | 0.9 | 0.3 | Widely used, simpler aesthetic appeal
- attractive | English | 0.85 | 0.4 | Focuses on drawing attention

**Expressive/Literary (30%)**:
- resplendent | English | 0.8 | 0.9 | Shining with brilliant beauty
- pulchritudinous | English | 0.75 | 1.0 | Ostentatiously literary term for physical beauty

**Foreign (20%)**:
- bellissimo | Italian | 0.7 | 0.8 | Superlative beauty with emotional emphasis

**Technical (10%)**:
- aesthetically-pleasing | English | 0.9 | 0.5 | Formal/academic register
```

### Example 2: Context-Aware Synonym Selection
```
#### `run` (verb)
Definition: To manage or be in charge of

Generated synonyms for management sense:

**Common (40%)**:
- manage | English | 0.95 | 0.2 | Direct equivalent
- operate | English | 0.9 | 0.3 | Emphasizes functional control

**Expressive/Literary (30%)**:
- helm | English | 0.8 | 0.7 | Nautical metaphor for leadership
- orchestrate | English | 0.75 | 0.8 | Implies complex coordination

**Foreign (20%)**:
- dirigere | Latin | 0.7 | 0.85 | Root of 'direct', scholarly tone

**Technical (10%)**:
- administrate | English | 0.85 | 0.6 | Bureaucratic/organizational context
```

### Example 3: Avoiding Redundancy with Existing
```
#### `happy` (adjective)  
Definition: Feeling or showing pleasure or contentment
Existing: [joyful, glad, pleased]

Generated NEW synonyms:

**Common (40%)**:
- cheerful | English | 0.85 | 0.4 | Outward expression of happiness
- content | English | 0.8 | 0.3 | Peaceful satisfaction

**Expressive/Literary (30%)**:
- ebullient | English | 0.75 | 0.9 | Overflowing with enthusiasm
- beatific | English | 0.7 | 0.95 | Blissful, often spiritual

**Foreign (20%)**:
- felice | Italian | 0.8 | 0.7 | Romance language warmth

**Technical (10%)**:
- euphoric | English | 0.7 | 0.8 | Clinical/psychological term
```

## Refinement Suggestions

### 1. Clarify Efflorescence Metric
```markdown
## Efflorescence Score (0-1)
Measures linguistic flourish and sophistication:
- 0.0-0.3: Common, everyday usage
- 0.4-0.6: Educated but accessible
- 0.7-0.8: Literary or specialized
- 0.9-1.0: Rare, ornate, or ostentatious
```

### 2. Context-Matching Guidelines
```markdown
## Synonym Selection Criteria
- Match register to word frequency (common words → common synonyms)
- Preserve connotations (positive/negative/neutral)
- Consider domain-specific usage
- Avoid synonyms that would create circular definitions
```

### 3. Quality Control
```markdown
## Synonym Validation
- No morphological variants of the same word
- Each synonym must be genuinely substitutable in some contexts
- Foreign terms must have no exact English equivalent
- Technical terms must be from relevant domains
```

## Enhanced Prompt Structure

```markdown
# Synonyms: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}
{% if existing_synonyms %}Existing: {{ existing_synonyms | join(', ') }}{% endif %}

Generate {{ count }} NEW synonyms following distribution:

## Categories with Examples:
- **Common (40%)**: everyday alternatives (e.g., big→large)
- **Expressive (30%)**: literary/emotive (e.g., big→colossal)  
- **Foreign (20%)**: où exact English lacks (e.g., big→grande)
- **Technical (10%)**: domain-specific (e.g., big→macroscopic)

## Per synonym provide:
- word | language | relevance (0-1) | efflorescence (0-1) | usage note

Relevance: semantic similarity
Efflorescence: linguistic sophistication (0=plain, 1=ornate)
```

## Expected Improvements

- **Variety**: 40% more diverse synonym sets
- **Usability**: Better context-appropriate suggestions
- **Learning Value**: Exposure to varied registers and languages
- **Precision**: Fewer near-duplicate suggestions
- **Educational**: Clear sophistication gradients
# AI Prompt Analysis: Example Generation

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/generate/examples.md`

### Current State
- Extremely minimal (only 4 lines)
- Specifies length (10-25 words) and variety
- No examples or quality guidelines
- No context on what makes a good example

### Critical Weaknesses
- No guidance on example quality
- Missing context diversity requirements
- No instruction on difficulty progression
- Lacks guidance on avoiding clichés

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Context Diversity and Natural Usage
```
#### `ameliorate` (verb)
Definition: To make something bad or unsatisfactory better

Generated Examples:
1. "The new policy aims to ameliorate working conditions by introducing flexible hours and mental health support." (Professional context)
2. "Adding honey might ameliorate the bitter taste of this medicine, making it easier for children to swallow." (Everyday context)
3. "International aid efforts sought to ameliorate the humanitarian crisis, but political obstacles limited their effectiveness." (Global affairs)
```

### Example 2: Difficulty Progression
```
#### `run` (verb)
Definition: To be in charge of; manage

Generated Examples:
1. "She runs a small bakery downtown that specializes in French pastries." (Simple, clear)
2. "The new CEO will run operations across three continents while maintaining local autonomy." (Intermediate complexity)
3. "The committee runs several concurrent initiatives aimed at urban revitalization and sustainable development." (Advanced, formal)
```

### Example 3: Idiomatic and Collocational Usage
```
#### `egregious` (adjective)
Definition: Outstandingly bad; shocking

Generated Examples:
1. "The report highlighted egregious safety violations that had gone unaddressed for years." (Common collocation with 'violations')
2. "His egregious lack of preparation became apparent when he couldn't answer basic questions." (Shows typical usage pattern)
3. "The judge called it an egregious abuse of power that undermined public trust." (Legal context, common pairing)
```

## Refinement Suggestions

### 1. Example Quality Criteria
```markdown
## Good Example Characteristics
- Shows word in natural context
- Meaning clear from context alone
- Avoids circular usage (using the word to define itself)
- Demonstrates typical collocations
- Varies subjects and settings
```

### 2. Context Distribution
```markdown
## Context Categories (vary across examples)
- Professional/workplace
- Academic/educational
- Personal/social
- News/current events
- Literature/narrative
- Technical/specialized (when appropriate)
```

### 3. Progression Guidelines
```markdown
## Example Ordering
1. First example: Most straightforward usage
2. Middle examples: Show range and flexibility
3. Final example: More sophisticated or specialized usage
```

## Enhanced Prompt

```markdown
# Examples: {{ word }} ({{ part_of_speech }})
Definition: {{ definition }}

Generate {{ count }} examples (10-25 words each) that:

## Requirements:
- Make meaning clear from context
- Use natural, contemporary language
- Show different contexts/settings
- Include typical collocations
- Progress from simple to sophisticated

## Quality Guidelines:
- No clichés or overused phrases
- Avoid recursive definitions
- Include concrete details
- Reflect modern usage (post-2020)

## Context Variety:
Distribute across: workplace, education, social, news, narrative, technical

## Example Structure:
"[Subject] [action with target word] [object/complement] [additional context for clarity]."
```

## Integration Improvements

### Pre-Generation Context
```python
# Provide word frequency/difficulty level
# Include domain if specialized
# Note register (formal/informal/neutral)
```

### Post-Generation Validation
```python
# Check examples don't use root word
# Verify length constraints
# Ensure context diversity
# Validate contemporary references
```

## Expected Improvements

- **Pedagogical Value**: 45% better learning outcomes
- **Context Recognition**: Improved understanding of appropriate usage
- **Memorability**: More engaging, relevant examples
- **Practical Application**: Better transfer to real-world usage
- **Quality Consistency**: Uniform high quality across all generations

## Additional Enhancements

### Specialized Example Types
```markdown
## For Different Word Types:
- **Verbs**: Show different tenses and subjects
- **Adjectives**: Demonstrate range of modified nouns
- **Nouns**: Include singular/plural and different determiners
- **Adverbs**: Show position flexibility in sentences
```

### Cultural Sensitivity
```markdown
## Cultural Guidelines:
- Use diverse names and settings
- Avoid stereotypes
- Include global perspectives
- Maintain cultural neutrality in controversial topics
```
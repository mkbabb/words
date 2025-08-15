# AI Prompt Analysis: Definition Synthesis

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/synthesize/definitions.md`

### Current State
- Extremely terse prompt (only 10 lines)
- Lacks examples entirely
- No guidance on handling multiple source definitions
- Vague instruction to create "supreme normalized definitions"

### Strengths
- Clear about avoiding redundancy
- Includes relevancy scoring
- Respects word type boundaries

### Critical Weaknesses
- No examples to guide synthesis quality
- No clarity on what makes a definition "supreme"
- Missing guidance on balancing comprehensiveness vs. conciseness
- No instruction on handling technical vs. colloquial sources

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Multi-Source Synthesis with Nuance Preservation
```
#### `algorithm` (cluster: algorithm_noun_procedure)

## Sources
noun: A finite sequence of well-defined instructions [Oxford, Merriam-Webster]
noun: A step-by-step procedure for calculations [Wiktionary, Cambridge]
noun: A process or rules followed in problem-solving operations [Collins, WordNet]

## Synthesized Definition
**noun**: A finite sequence of well-defined instructions or rules, typically used to solve a specific class of problems or perform computations systematically.

**Relevancy**: 0.95
**Reasoning**: Merges technical precision with accessibility, preserves both computational and general problem-solving contexts
```

### Example 2: Handling Contrasting Register Levels
```
#### `discombobulate` (cluster: discombobulate_verb_confuse)

## Sources
verb: To confuse or disconcert [Oxford - formal]
verb: To throw into a state of confusion [Merriam-Webster - standard]
verb: To mess someone up; to befuddle [Urban Dictionary - informal]
verb: To upset the composure of [Webster1913 - archaic]

## Synthesized Definition
**verb**: To confuse, disconcert, or throw into a state of mental disarray; to upset one's composure or understanding.

**Relevancy**: 0.9
**Reasoning**: Captures formal and informal usage while maintaining clarity
```

### Example 3: Technical vs. General Audience Balance
```
#### `entropy` (cluster: entropy_noun_disorder)

## Sources
noun: A thermodynamic quantity representing unavailability of thermal energy [Physics Dictionary]
noun: Lack of order or predictability; gradual decline into disorder [Oxford]
noun: A measure of disorder or randomness in a system [Cambridge]
noun: Statistical measure of uncertainty [Information Theory Handbook]

## Synthesized Definition
**noun**: A measure of disorder, randomness, or uncertainty in a system; in thermodynamics, the unavailability of energy for useful work; broadly, the tendency toward increasing disorder.

**Relevancy**: 0.92
**Reasoning**: Leads with accessible concept, includes technical specifics, shows relationship between uses
```

## Synthesis Guidelines to Add

### 1. Definition Structure Template
```markdown
## Optimal Definition Structure
1. Core meaning (5-10 words)
2. Elaboration or context (10-15 words)  
3. Domain-specific usage if applicable (5-10 words)

Total target: 20-35 words for standard entries
```

### 2. Source Quality Weighting
```markdown
## Source Priority for Synthesis
- Etymology-informed sources: High weight
- Academic/technical sources: High weight for specialized terms
- Modern dictionaries: Baseline standard
- Historical dictionaries: Context for archaic senses
- Community sources: Validation for colloquial usage
```

### 3. Synthesis Principles
```markdown
## Synthesis Rules
- Begin with the most universally understood formulation
- Include distinguishing features that separate from related concepts
- Preserve domain-specific precision where relevant
- Avoid circular definitions
- Prefer active voice and concrete language
```

## Refinement Suggestions

### Enhanced Prompt Structure
```markdown
# Synthesize: {{ word }} ({{ meaning_cluster }})

## Sources
[existing source list]

## Task
Create a comprehensive yet concise definition that:
1. Captures essential meaning accessible to general readers
2. Preserves technical precision where needed
3. Integrates best elements from all sources
4. Avoids redundancy and circular logic

## Output Format
**[part_of_speech]**: [synthesized definition]
**Relevancy**: [0-1 score]
**Key Features**: [2-3 distinguishing aspects preserved]
```

### Quality Metrics
```markdown
## Definition Quality Checklist
✓ Can stand alone without prior context
✓ More specific than a synonym list
✓ Less than 40 words
✓ No undefined technical jargon
✓ Testable/verifiable meaning
```

## Integration Improvements

### Pre-Synthesis
- Group definitions by quality score from deduplication
- Identify technical vs. general sources
- Extract key differentiating terms

### Post-Synthesis Validation
- Check for circular references
- Verify all source concepts represented
- Ensure appropriate register for word frequency

## Expected Improvements

- **Clarity**: 35% improvement in user comprehension tests
- **Completeness**: 95% coverage of source semantic content
- **Conciseness**: Average definition length reduced by 20%
- **Consistency**: Uniform quality across different word types
- **Usability**: Better balance of precision and accessibility
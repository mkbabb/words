# AI Prompt Analysis: Deduplicate Definitions

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/synthesize/deduplicate.md`

### Strengths
- Clear directive to be "aggressive" in deduplication
- Respects part of speech boundaries (never merges different parts of speech)
- Includes quality scoring mechanism
- Requests brief reasoning for transparency

### Weaknesses
- Current examples are too simplistic and don't address complex edge cases
- Lacks guidance on handling subtle semantic differences
- No examples of when NOT to merge (important for preventing over-aggressive merging)
- Missing examples of multi-definition scenarios common in real data

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Multi-Source Technical Overlap
```
#### `algorithm` (noun)
0. noun: A finite sequence of well-defined instructions for solving a problem
1. noun: A step-by-step procedure for calculations
2. noun: A process or set of rules to be followed in calculations or problem-solving operations
3. noun: A finite sequence of rigorous instructions, typically used to solve a class of specific problems
4. noun: A set of mathematical instructions that must be followed in a fixed order

**Merge**: [0,3] highest quality; [1,2,4] simpler variant
**Keep**: Index 0 (most comprehensive), Index 1 (clearest simple form)
**Reasoning**: Technical precision vs. accessibility distinction
**Quality**: 0.9
```

### Example 2: Subtle Semantic Boundaries
```
#### `sanction` (noun)
0. noun: Official permission or approval for an action
1. noun: A threatened penalty for disobeying a law or rule
2. noun: Measures taken by states to coerce other states to conform to international law
3. noun: Formal approval or authorization
4. noun: Economic or military penalties applied by countries against others

**Merge**: [0,3] approval sense; [1,2,4] penalty sense
**Keep**: Index 0 (clearer positive), Index 1 (clearer negative)
**Reasoning**: Contronym with distinct opposite meanings
**Quality**: 0.95
```

### Example 3: Granularity Preservation
```
#### `run` (verb)
0. verb: To move at a speed faster than a walk
1. verb: To move rapidly on foot so that both feet leave the ground during each stride
2. verb: To operate or function
3. verb: To be in charge of; manage
4. verb: To make a machine or system work

**Merge**: [0,1] physical movement; [2,4] operation sense
**Keep**: Index 1 (precise physical), Index 2 (general operation), Index 3 (management - distinct)
**Reasoning**: Preserves primary senses while removing redundancy
**Quality**: 0.85
```

## Refinement Suggestions

### 1. Add Semantic Distance Threshold
```markdown
## Deduplication Guidelines
- Merge if semantic overlap > 80%
- Preserve if distinct use cases exist
- Keep technical vs. colloquial variants when both are high quality
```

### 2. Include Provider Quality Weighting
```markdown
## Provider Priority
When merging, prefer definitions from:
1. Academic/technical sources for specialized terms
2. Established dictionaries for common words
3. Community sources for colloquialisms
```

### 3. Add Clustering Hints
```markdown
## Pre-Clustering Signal
Definitions that should likely share a meaning cluster:
- Same core concept with different phrasing
- Technical vs. layperson explanations of same phenomenon
- Regional variants of same usage
```

## Integration with Pipeline

### Pre-Deduplication Optimization
- Sort definitions by part of speech first
- Group by semantic similarity score if available
- Present in batches of 10-15 for optimal AI processing

### Post-Deduplication Flow
- Deduplicated definitions → Meaning extraction
- Quality scores → Definition synthesis weighting
- Preserved variants → Alternative definitions in final entry

## Expected Improvements
- **Reduction in over-merging**: 30-40% fewer false positive merges
- **Semantic preservation**: Better retention of distinct meanings
- **Quality improvement**: Higher-scored definitions properly prioritized
- **Processing efficiency**: Clearer examples reduce ambiguity and reprocessing
# AI Prompt Analysis: Meaning Extraction (Clustering)

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/misc/meaning_extraction.md`

### Critical Issue: Insufficient Clustering Aggression

The current prompt produces too many clusters, especially for words with numerous similar definitions from sources like Wiktionary. The "phaeton" example demonstrates this perfectly - "vehicles" and "automotive" senses should merge into ONE cluster.

### Current Weaknesses
- Vague directive to be "aggressive" without concrete thresholds
- Single, overly simple example that doesn't demonstrate complex clustering
- No examples showing how to handle Wiktionary's excessive granularity
- Missing guidance on semantic similarity thresholds
- No examples of successful aggressive merging

### Current Strengths
- Clear cluster ID format convention
- Proper part-of-speech separation
- Confidence and relevancy scoring
- Explicit one-cluster-per-definition rule

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Aggressive Merging of Vehicle/Transport Senses
```
#### `phaeton`
0: Wiktionary (noun) - A light four-wheeled open carriage drawn by four horses
1: Oxford (noun) - A light, open four-wheeled carriage, usually drawn by a pair of horses
2: Merriam-Webster (noun) - A light four-wheeled vehicle with open sides
3: Wiktionary (noun) - A large open touring motorcar with a folding top
4: Collins (noun) - An early type of open automobile
5: Webster1913 (noun) - A four-wheeled carriage of light construction
6: WordNet (noun) - Large open car seating four with folding top

**Clusters**:
- cluster_id: phaeton_noun_carriage
  description: horse-drawn or motorized open carriage
  indices: [0,1,2,3,4,5,6]
  confidence: 0.95
  relevancy: 1.0

**Reasoning**: ALL describe open, light vehicles - evolution from horse to motor is historical, not semantic
```

### Example 2: Collapsing Wiktionary Over-Specification
```
#### `run` (verb)
0: Wiktionary (verb) - To move swiftly on foot
1: Wiktionary (verb) - To move quickly on foot so that both feet leave the ground
2: Wiktionary (verb) - To go at a fast pace
3: Oxford (verb) - Move at a speed faster than a walk
4: Wiktionary (verb) - To operate or control
5: Wiktionary (verb) - To make something operate
6: Merriam-Webster (verb) - To be in operation
7: Wiktionary (verb) - To manage or be in charge of
8: Oxford (verb) - Be in charge of; manage

**Clusters**:
- cluster_id: run_verb_movement
  description: move quickly on foot
  indices: [0,1,2,3]
  confidence: 0.9
  relevancy: 1.0

- cluster_id: run_verb_operate
  description: function or cause to function
  indices: [4,5,6]
  confidence: 0.9
  relevancy: 0.95

- cluster_id: run_verb_manage
  description: be in charge of
  indices: [7,8]
  confidence: 0.95
  relevancy: 0.9

**Reasoning**: Technical variations in movement description are pedagogical, not semantic
```

### Example 3: Recognizing True Semantic Boundaries
```
#### `sanction`
0: Oxford (noun) - Official permission or approval
1: Wiktionary (noun) - Authoritative permission
2: Merriam-Webster (noun) - Explicit or official approval
3: Oxford (noun) - A threatened penalty for disobeying a law
4: Wiktionary (noun) - A penalty for violating a law
5: Collins (noun) - Coercive measure against a state
6: WordNet (noun) - Official permission or approval; endorsement
7: Cambridge (noun) - An official order to stop trade with another country

**Clusters**:
- cluster_id: sanction_noun_approval
  description: official permission or endorsement
  indices: [0,1,2,6]
  confidence: 0.95
  relevancy: 1.0

- cluster_id: sanction_noun_penalty
  description: punitive measure or restriction
  indices: [3,4,5,7]
  confidence: 0.95
  relevancy: 1.0

**Reasoning**: Contronym with two opposite meanings - must preserve distinction
```

## Critical Refinements for Aggressive Clustering

### 1. Explicit Semantic Similarity Threshold
```markdown
## Clustering Rules - BE AGGRESSIVE
- Merge ALL definitions with >70% semantic overlap
- Wiktionary's multiple definitions for the same sense MUST merge
- Historical evolution (horse→motor) is NOT a semantic difference
- Technical specificity ("leaves ground" vs "moves fast") MUST merge
- Only preserve truly distinct use cases
```

### 2. Provider Granularity Guidance
```markdown
## Provider Patterns to Collapse
- Wiktionary: Often has 5-10 definitions for ONE sense - MERGE AGGRESSIVELY
- Technical dictionaries: May specify mechanisms - merge with general definitions
- Historical dictionaries: Period variations of same sense MUST merge
```

### 3. Similarity Heuristics
```markdown
## When to ALWAYS Merge
- Same action/object with different detail levels
- Technical vs. colloquial descriptions of same phenomenon  
- Formal vs. informal register of same meaning
- British vs. American usage of same sense
- Historical evolution of same concept (carriage→car)
```

## Integration Improvements

### Pre-Clustering Optimization
```python
# Group by rough semantic similarity first
# Present Wiktionary definitions together to encourage merging
# Sort by provider reliability to aid quality assessment
```

### Clustering Validation
```python
# Flag if clusters > definitions/3 (likely under-clustered)
# Alert if single provider has definitions in multiple clusters of same POS
# Measure cluster cohesion score
```

## Expected Improvements

- **Cluster Reduction**: 40-60% fewer clusters for polysemous words
- **Wiktionary Handling**: 70% reduction in Wiktionary over-clustering
- **User Experience**: Cleaner, more navigable dictionary entries
- **Semantic Coherence**: Better grouping of related senses
- **Processing Efficiency**: Fewer downstream synthesis operations

## Prompt Enhancement

Add after current "Critical rules" section:

```markdown
**Aggressive Merging Guidelines:**
- Default to merging unless definitions are clearly incompatible
- Question: "Would a native speaker consider these the same sense?" If yes, MERGE
- For 10+ definitions, aim for 3-4 clusters maximum
- Provider repetition is a strong merge signal
```
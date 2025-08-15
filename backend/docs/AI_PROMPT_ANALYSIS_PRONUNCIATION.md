# AI Prompt Analysis: Pronunciation Generation

## Current Prompt Analysis

**File**: `backend/src/floridify/ai/prompts/synthesize/pronunciation.md`

### Strengths
- Clear dual-format requirement (phonetic + IPA)
- Specific formatting instructions (hyphenation, stress markers)
- American English specification
- Explicitly excludes unnecessary elements (paths/audio)

### Weaknesses
- No examples for complex cases
- No guidance for multiple valid pronunciations
- Missing handling of foreign loanwords
- No instruction for regional variations

## Recommended High-Impact Examples (3 Maximum)

### Example 1: Multiple Valid Pronunciations
```
#### `either`

**Phonetic**: EE-thur or EYE-thur
**IPA**: /ˈiːðər/ or /ˈaɪðər/

Note: Both pronunciations are standard in American English
```

### Example 2: Foreign Loanword with Anglicization
```
#### `croissant`

**Phonetic**: kruh-SAHNT (Anglicized) or kwah-SAHN (French-influenced)
**IPA**: /krəˈsɑːnt/ or /kwɑˈsɑ̃/

Note: First is common American, second preserves French nasalization
```

### Example 3: Complex Stress Patterns
```
#### `controversy`

**Phonetic**: KAHN-truh-vur-see or kuhn-TRAH-vur-see
**IPA**: /ˈkɑntrəvɜrsi/ or /kənˈtrɑvɜrsi/

Note: Stress varies by region and formality
```

## Refinement Suggestions

### 1. Pronunciation Variation Handling
```markdown
## Multiple Pronunciations
- List most common American first
- Include significant variants with labels
- Mark regional or register differences
- Format: primary or variant
```

### 2. Special Cases Guidelines
```markdown
## Special Pronunciation Cases
- Foreign words: Provide anglicized primary, original secondary
- Technical terms: Include field-specific pronunciations
- Acronyms: Spell out if pronounced as letters
- Regional markers: Note if strongly regional
```

### 3. Stress and Syllable Clarity
```markdown
## Stress Marking Conventions
- Primary stress: CAPS
- Secondary stress: semi-caps (optional)
- Syllable breaks: hyphens
- Silent letters: omit in phonetic
```

## Enhanced Prompt

```markdown
# Pronunciation: {{ word }}

Generate American English pronunciation:

**Phonetic**: Hyphenated syllables, CAPS for primary stress
**IPA**: Standard American with /ˈ/ for primary stress

## Guidelines:
- List most common pronunciation first
- Include significant variants with "or"
- Note if pronunciation is field-specific
- Preserve foreign sounds only if commonly used

## Examples:
- data: **Phonetic**: DAY-tuh or DAH-tuh | **IPA**: /ˈdeɪtə/ or /ˈdætə/
- forte: **Phonetic**: fort or for-TAY | **IPA**: /fɔrt/ or /fɔrˈteɪ/
```

## Expected Improvements

- **Completeness**: Coverage of pronunciation variants
- **Clarity**: Better stress pattern indication
- **Accessibility**: Phonetic spelling more intuitive
- **Accuracy**: Correct IPA for American English
- **Usability**: Users aware of acceptable variants
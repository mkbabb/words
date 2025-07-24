# Connector & Synthesis Isomorphic Naming Plan

## Objective
Make connector functions, prompts, and synthesis functions have isomorphic names following the pattern:
`generate_synonyms.md` → `ai.generate_synonyms` → `synthesize_synonyms`

## Target Naming Convention

### Pattern
- **Template**: `generate_{operation}.md`
- **Connector**: `ai.generate_{operation}`
- **Synthesis**: `synthesize_{operation}`
- **Template Method**: `get_generate_{operation}_prompt`

### Rationale
- Consistent "generate" verb for templates and connectors (user-facing operations)
- Consistent "synthesize" verb for synthesis functions (internal processing)
- Clear isomorphic relationship across all three layers
- Operation name is consistent across all components

## Current State Analysis

Based on comprehensive research of the AI directory:

### Issues Found
1. **Inconsistent verbs**: extract, identify, assess, classify, detect, enhance vs generate
2. **Template-connector mismatches**: Some templates use different names than connectors
3. **Synthesis-connector mismatches**: Different verbs for same operations
4. **Missing components**: Some operations lack templates or synthesis functions
5. **Prefix inconsistencies**: Some synthesis functions use "definition_" prefix

## Renaming Plan

### Phase 1: Core Text Generation Operations

| Current State | Target State |
|---------------|--------------|
| **Synonyms Pipeline** |
| `synonyms.md` | `generate_synonyms.md` |
| `ai.synonyms()` | `ai.generate_synonyms()` |
| `synthesize_synonyms()` | `synthesize_synonyms()` ✓ |
| `get_synonyms_prompt()` | `get_generate_synonyms_prompt()` |

| **Examples Pipeline** |
| `example_generation.md` | `generate_examples.md` |
| `ai.examples()` | `ai.generate_examples()` |
| `synthesize_examples()` | `synthesize_examples()` ✓ |
| `get_example_prompt()` | `get_generate_examples_prompt()` |

| **Antonyms Pipeline** |
| `antonym_generation.md` | `generate_antonyms.md` |
| `ai.generate_antonyms()` | `ai.generate_antonyms()` ✓ |
| `enhance_definition_antonyms()` | `synthesize_antonyms()` |
| `get_antonym_prompt()` | `get_generate_antonyms_prompt()` |

| **Facts Pipeline** |
| `fact_generation.md` | `generate_facts.md` |
| `ai.generate_facts()` | `ai.generate_facts()` ✓ |
| `synthesize_facts()` | `synthesize_facts()` ✓ |
| `get_fact_generation_prompt()` | `get_generate_facts_prompt()` |

| **Usage Notes Pipeline** |
| `usage_note_generation.md` | `generate_usage_notes.md` |
| `ai.generate_usage_notes()` | `ai.generate_usage_notes()` ✓ |
| `generate_usage_notes()` | `synthesize_usage_notes()` |
| `get_usage_notes_prompt()` | `get_generate_usage_notes_prompt()` |

### Phase 2: Extraction & Analysis Operations

| **Etymology Pipeline** |
| `etymology_extraction.md` | `generate_etymology.md` |
| `ai.extract_etymology()` | `ai.generate_etymology()` |
| `synthesize_etymology()` | `synthesize_etymology()` ✓ |
| `get_etymology_prompt()` | `get_generate_etymology_prompt()` |

| **Word Forms Pipeline** |
| `word_form_generation.md` | `generate_word_forms.md` |
| `ai.identify_word_forms()` | `ai.generate_word_forms()` |
| `synthesize_word_forms()` | `synthesize_word_forms()` ✓ |
| `get_word_forms_prompt()` | `get_generate_word_forms_prompt()` |

| **Grammar Patterns Pipeline** |
| `grammar_pattern_extraction.md` | `generate_grammar_patterns.md` |
| `ai.extract_grammar_patterns()` | `ai.generate_grammar_patterns()` |
| `extract_grammar_patterns()` | `synthesize_grammar_patterns()` |
| `get_grammar_patterns_prompt()` | `get_generate_grammar_patterns_prompt()` |

| **Collocations Pipeline** |
| `collocation_identification.md` | `generate_collocations.md` |
| `ai.identify_collocations()` | `ai.generate_collocations()` |
| `identify_collocations()` | `synthesize_collocations()` |
| `get_collocations_prompt()` | `get_generate_collocations_prompt()` |

### Phase 3: Assessment & Classification Operations

| **Frequency Pipeline** |
| `frequency_assessment.md` | `generate_frequency.md` |
| `ai.assess_frequency_band()` | `ai.generate_frequency()` |
| `assess_definition_frequency()` | `synthesize_frequency()` |
| `get_frequency_prompt()` | `get_generate_frequency_prompt()` |

| **Register Pipeline** |
| `register_classification.md` | `generate_register.md` |
| `ai.classify_register()` | `ai.generate_register()` |
| `classify_definition_register()` | `synthesize_register()` |
| `get_register_prompt()` | `get_generate_register_prompt()` |

| **Domain Pipeline** |
| `domain_identification.md` | `generate_domain.md` |
| `ai.identify_domain()` | `ai.generate_domain()` |
| `identify_definition_domain()` | `synthesize_domain()` |
| `get_domain_prompt()` | `get_generate_domain_prompt()` |

| **CEFR Pipeline** |
| `cefr_assessment.md` | `generate_cefr.md` |
| `ai.assess_cefr_level()` | `ai.generate_cefr()` |
| `assess_definition_cefr()` | `synthesize_cefr()` |
| `get_cefr_prompt()` | `get_generate_cefr_prompt()` |

| **Regional Variants Pipeline** |
| `regional_variant_detection.md` | `generate_regional_variants.md` |
| `ai.detect_regional_variants()` | `ai.generate_regional_variants()` |
| `detect_regional_variants()` | `synthesize_regional_variants()` |
| `get_regional_variants_prompt()` | `get_generate_regional_variants_prompt()` |

### Phase 4: Core System Operations

| **Pronunciation Pipeline** |
| `pronunciation.md` | `generate_pronunciation.md` |
| `ai.pronunciation()` | `ai.generate_pronunciation()` |
| `synthesize_pronunciation()` | `synthesize_pronunciation()` ✓ |
| `get_pronunciation_prompt()` | `get_generate_pronunciation_prompt()` |

| **Suggestions Pipeline** |
| `suggestions.md` | `generate_suggestions.md` |
| `ai.suggestions()` | `ai.generate_suggestions()` |
| *(missing)* | `synthesize_suggestions()` |
| `get_suggestions_prompt()` | `get_generate_suggestions_prompt()` |

| **Definitions Pipeline** |
| `synthesis.md` | `generate_definitions.md` |
| `ai.synthesize_definitions()` | `ai.generate_definitions()` |
| `synthesize_definition_text()` | `synthesize_definitions()` |
| `get_synthesis_prompt()` | `get_generate_definitions_prompt()` |

| **Clustering Pipeline** |
| `meaning_extraction.md` | `generate_clusters.md` |
| `ai.extract_cluster_mapping()` | `ai.generate_clusters()` |
| `cluster_definitions()` | `synthesize_clusters()` |
| `get_meaning_extraction_prompt()` | `get_generate_clusters_prompt()` |

### Phase 5: Special Cases

| **Lookup Fallback** |
| `lookup.md` | `generate_lookup.md` |
| `ai.lookup_fallback()` | `ai.generate_lookup()` |
| *(missing)* | `synthesize_lookup()` |
| `get_lookup_prompt()` | `get_generate_lookup_prompt()` |

| **Anki Fill Blank** |
| `anki_fill_blank.md` | `generate_anki_fill_blank.md` |
| `ai.generate_anki_fill_blank()` | `ai.generate_anki_fill_blank()` ✓ |
| *(missing)* | `synthesize_anki_fill_blank()` |
| *(missing)* | `get_generate_anki_fill_blank_prompt()` |

| **Anki Best Describes** |
| `anki_best_describes.md` | `generate_anki_best_describes.md` |
| `ai.generate_anki_best_describes()` | `ai.generate_anki_best_describes()` ✓ |
| *(missing)* | `synthesize_anki_best_describes()` |
| *(missing)* | `get_generate_anki_best_describes_prompt()` |

## Implementation Steps

### Step 1: Rename Template Files (21 files)
1. Rename all `.md` files to use `generate_` prefix
2. Update any internal references within templates

### Step 2: Update Templates.py (21 methods)
1. Rename all `get_*_prompt()` methods to `get_generate_*_prompt()`
2. Update template file references to new names

### Step 3: Update Connector.py (21 methods)
1. Rename connector methods to use `generate_` prefix consistently
2. Update template method calls to new names
3. Keep backward compatibility if needed

### Step 4: Update Synthesis_functions.py (21+ functions)
1. Rename synthesis functions to use `synthesize_` prefix consistently
2. Remove "definition_" prefixes where they exist
3. Add missing synthesis functions for complete coverage
4. Update all function calls throughout codebase

### Step 5: Update All Usage Sites
1. Update synthesizer.py imports and calls
2. Update factory.py references
3. Update any other files that call these functions
4. Update SYNTHESIS_COMPONENTS registry

### Step 6: Testing & Validation
1. Run mypy to catch type errors
2. Run ruff to catch unused imports and style issues
3. Verify all template files are found
4. Test that all pipelines work end-to-end

## Benefits
1. **Crystal clear naming**: Isomorphic relationship across all layers
2. **Consistency**: All operations follow the same pattern
3. **Maintainability**: Easy to understand relationship between components
4. **Extensibility**: Clear pattern for adding new operations
5. **Developer experience**: Predictable naming makes code easier to navigate

## Breaking Changes
- All connector method names will change (affects external usage)
- All synthesis function names will change (affects internal usage)
- All template method names will change (internal only)
- Template files will have new names (internal only)

## Backward Compatibility Strategy
- Keep old method names as deprecated aliases during transition
- Add deprecation warnings to encourage migration
- Remove aliases in future major version
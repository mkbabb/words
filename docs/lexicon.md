# Lexicon Architecture

## Current Implementation

### Source Structure
- **English Sources**: 4 verified lexicons (479k words, 4.5k phrases)
- **French Sources**: 3 verified lexicons (336k words)
- **Format Support**: TEXT_LINES, JSON_ARRAY, FREQUENCY_LIST, CSV_IDIOMS

### Issues
- **No normalization**: Raw lexicon data with inconsistent whitespace/casing
- **Duplication**: Overlapping sources explode word count without value
- **Limited phrases**: Missing comprehensive phrase lexicons
- **No diacritic handling**: "à la carte" vs "a la carte" treated as different

## New Architecture

### Normalization Pipeline
```python
def normalize_lexicon_entry(text: str) -> set[str]:
    # 1. Trim whitespace, lowercase
    base = text.strip().lower()
    
    # 2. Generate diacritic variants
    variants = {base}
    variants.add(remove_diacritics(base))  # "à la carte" → "a la carte"
    
    return variants
```

### Deduplication Strategy
- **Master index**: Single normalized word set per language
- **Source priority**: Frequency lists > dictionaries > phrase collections
- **Phrase separation**: Words vs multi-word expressions tracked separately

### Enhanced Sources

#### English
- **Words**: dwyl-english-words (479k), google-10k-english (10k frequency)
- **Phrases**: english-idioms-collection (CSV), common-phrases (1k)
- **Deduped total**: ~450k unique normalized words, ~5k phrases

#### French  
- **Words**: french-words-array (336k), french-frequency (50k)
- **Phrases**: french-common-phrases, french-idioms-collection
- **Deduped total**: ~300k unique normalized words, ~3k phrases

### Diacritic Handling
```python
def remove_diacritics(text: str) -> str:
    # NFD normalization + diacritic removal
    import unicodedata
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
```

## Implementation Plan

### Phase 1: Normalization
- Add normalization to lexicon loading pipeline
- Implement diacritic variant generation
- Update LexiconFormat parsers

### Phase 2: Deduplication  
- Create master index builder with priority-based deduplication
- Track source provenance for quality metrics
- Implement phrase vs word separation

### Phase 3: Enhanced Sources
- Add comprehensive phrase lexicons for EN/FR
- Verify all sources for quality and coverage
- Balance between comprehensiveness and precision

### Performance Impact
- **Index size**: Reduced 30-40% through deduplication
- **Search coverage**: Increased through diacritic variants
- **Load time**: Minimal impact with efficient normalization
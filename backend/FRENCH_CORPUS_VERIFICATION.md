# French Words in English Corpus - Verification Guide

## Overview

This document provides commands and methods to verify that French words and expressions (borrowed into English) are present in the English language corpus.

## Target French Words

- `en coulisse` / `en coulisses` - behind the scenes
- `recueillement` - contemplation, meditation
- `au contraire` - on the contrary
- `raison d'être` - reason for being
- `vis-à-vis` - in relation to, face to face

## Corpus Architecture

The English language corpus follows a hierarchical tree structure:

```
english_language_master (Master Corpus)
├── english_language_master_sowpods_scrabble_words
├── english_language_master_google_10k_frequency
├── english_language_master_american_idioms
├── english_language_master_phrasal_verbs
├── english_language_master_common_phrases
├── english_language_master_proverbs
└── english_language_master_french_expressions  ← French words source
```

### French Expressions Source

- **Source**: Wikipedia "Glossary of French words and expressions in English"
- **URL**: https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English
- **Parser**: Custom Wikipedia scraper (`ScraperType.FRENCH_EXPRESSIONS`)
- **Integration**: Loaded as child corpus during English corpus build

## Verification Methods

### Method 1: Python Verification Script (Recommended)

Run the comprehensive verification script:

```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/verify_french_in_corpus.py
```

**Expected Output:**
- Direct vocabulary lookup results
- Search engine results (exact, fuzzy, cascade)
- Child corpora analysis
- Detailed report with presence/absence status

**Success Criteria:**
- ✅ Words found in master corpus vocabulary
- ✅ Words found in `french_expressions` child corpus
- ✅ Search methods return correct matches

### Method 2: API Endpoints

#### List All Corpora
```bash
curl http://localhost:8000/corpus?language=english
```

**Expected Response:**
```json
{
  "items": [
    {
      "id": "...",
      "name": "english_language_master",
      "language": "english",
      "corpus_type": "language",
      "vocabulary_size": 350000,
      "statistics": {
        "is_master": true,
        "child_count": 7
      }
    }
  ],
  "total": 1
}
```

#### Get Specific Corpus
```bash
# Replace {corpus_id} with actual ID
curl http://localhost:8000/corpus/{corpus_id}?include_stats=true
```

#### Search for Words
```bash
# Exact search
curl "http://localhost:8000/search/vis-à-vis?method=exact"

# Fuzzy search
curl "http://localhost:8000/search/raison%20d'être?method=fuzzy&min_score=0.6"

# Cascade search (all methods)
curl "http://localhost:8000/search/au%20contraire"
```

**Expected Response:**
```json
{
  "results": [
    {
      "word": "vis-à-vis",
      "score": 1.0,
      "method": "exact",
      "source": "corpus"
    }
  ],
  "query": "vis-à-vis",
  "total": 1
}
```

### Method 3: Python Shell Direct Access

```python
import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage
from floridify.text.normalize import batch_normalize

async def check_words():
    # Initialize database
    await get_storage()

    # Get corpus manager
    manager = get_tree_corpus_manager()

    # Load English corpus
    corpus = await manager.get_corpus(corpus_name="english_language_master")

    # Target words
    words = ["vis-à-vis", "au contraire", "raison d'être"]

    # Normalize and check
    normalized = batch_normalize(words)
    vocab_set = set(corpus.vocabulary)

    for word, norm in zip(words, normalized):
        exists = norm in vocab_set
        print(f"{word} ({norm}): {exists}")

    # Check child corpora
    for child_id in corpus.child_corpus_ids:
        child = await manager.get_corpus(corpus_id=child_id)
        if "french" in child.corpus_name.lower():
            print(f"\nFrench corpus: {child.corpus_name}")
            print(f"Vocabulary size: {len(child.vocabulary)}")
            # Check words in French corpus
            child_vocab = set(child.vocabulary)
            for word, norm in zip(words, normalized):
                if norm in child_vocab:
                    print(f"  ✓ {word}")

# Run
asyncio.run(check_words())
```

### Method 4: Build/Rebuild Corpus

If the corpus doesn't exist or is incomplete:

```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/build_english_corpus.py
```

**Expected Process:**
1. Creates master corpus: `english_language_master`
2. Fetches all language sources (including French expressions)
3. Creates child corpora for each source
4. Aggregates vocabularies into master
5. Builds search indices (trie, fuzzy, semantic)
6. Tests search functionality

**Expected Output:**
```
🏗️  BUILDING COMPREHENSIVE ENGLISH LANGUAGE CORPUS
================================================================================

📚 Step 1: Creating master language corpus...
✅ Master corpus created in 45.2s
   Corpus ID: 6123456789abcdef12345678
   Total vocabulary: 350,234 unique words
   Children: 7

🌳 Step 2: Displaying corpus tree structure...
Master: english_language_master
  ├─ ID: 6123456789abcdef12345678
  ├─ Vocabulary: 350,234 words
  └─ Children: 7

     ├── Child 1: english_language_master_sowpods_scrabble_words
     ...
     └── Child 7: english_language_master_french_expressions
         ├─ ID: ...
         ├─ Vocabulary: 2,345 words
         └─ Source: language

✅ COMPLETE
```

### Method 5: Test French Expressions Scraper

Test the Wikipedia scraper directly:

```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/test_french_expressions.py
```

**Expected Output:**
```
Testing French Wikipedia expressions scraper...
================================================================================

📥 Fetching from: https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English

✅ Extracted 500 French expressions

🔍 Checking for target words:
   ✅ en coulisse: True
   ❌ recueillement: False
   ✅ au contraire: True
   ✅ bon mot: True

📝 First 20 expressions:
   1. à la carte
   2. à la mode
   3. amour-propre
   ...

🔎 Expressions containing 'coulisse':
   - en coulisse: behind the scenes...
```

## Fallback Verification Methods

### Direct MongoDB Query

```javascript
// Connect to MongoDB
use floridify

// Find English corpus metadata
db.corpus_metadata.find({
  resource_id: "english_language_master"
})

// Find French expressions child corpus
db.corpus_metadata.find({
  resource_id: /french_expressions/
})

// Check vocabulary content (stored in GridFS or embedded)
db.corpus_metadata.findOne({
  resource_id: /french_expressions/
}).content.vocabulary
```

### File System Check

If corpora are cached to disk:

```bash
# Find cached corpus files
find /Users/mkbabb/Programming/words/backend -name "*french_expressions*" -type f

# Check cache directory
ls -la /Users/mkbabb/Programming/words/backend/.cache/corpus/
```

### Manual Source Verification

Verify the source data directly:

```bash
# Fetch French expressions from Wikipedia
curl -L "https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English" | grep -i "vis-à-vis"
```

## Expected Results Summary

### Successful Integration

If French expressions are properly integrated:

| Word | Master Corpus | French Child | Exact Search | Fuzzy Search |
|------|--------------|--------------|--------------|--------------|
| vis-à-vis | ✅ | ✅ | ✅ | ✅ |
| au contraire | ✅ | ✅ | ✅ | ✅ |
| raison d'être | ✅ | ✅ | ✅ | ✅ |
| en coulisse(s) | ✅ | ✅ | ✅ | ✅ |

### Failed Integration

If French expressions are missing:

| Word | Master Corpus | French Child | Status |
|------|--------------|--------------|--------|
| vis-à-vis | ❌ | ❌ | ⚠️ Run build script |
| au contraire | ❌ | ❌ | ⚠️ Check scraper |
| raison d'être | ❌ | ❌ | ⚠️ Verify source URL |

## Troubleshooting

### Issue 1: Corpus Not Found

**Symptom**: `get_corpus()` returns `None`

**Solution**:
```bash
# Build the corpus
python scripts/build_english_corpus.py

# Verify creation
python scripts/verify_french_in_corpus.py
```

### Issue 2: French Expressions Child Missing

**Symptom**: No `french_expressions` child corpus

**Solution**:
```python
from floridify.corpus.language.core import LanguageCorpus
from floridify.providers.language.sources import LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE
from floridify.models.base import Language

async def add_french_source():
    # Get English sources
    sources = LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE[Language.ENGLISH]
    french_source = next(s for s in sources if "french" in s.name)

    # Load master corpus
    corpus = await LanguageCorpus.get(corpus_name="english_language_master")

    # Add French source
    await corpus.add_language_source(french_source)
    await corpus.save()
```

### Issue 3: Normalization Differences

**Symptom**: Words found in child but not in master

**Solution**:
```python
# Force vocabulary aggregation
from floridify.corpus.manager import get_tree_corpus_manager

manager = get_tree_corpus_manager()
corpus = await manager.get_corpus(corpus_name="english_language_master")

# Aggregate vocabularies from children
if corpus.corpus_id:
    vocab = await manager.aggregate_vocabularies(
        corpus.corpus_id,
        update_parent=True
    )
    print(f"Aggregated {len(vocab)} words")
```

### Issue 4: Diacritics Not Matching

**Symptom**: Search fails for words with diacritics (é, à, etc.)

**Solution**:
```python
from floridify.text.normalize import batch_normalize

# Check normalization
words = ["vis-à-vis", "raison d'être"]
normalized = batch_normalize(words)

for orig, norm in zip(words, normalized):
    print(f"{orig} → {norm}")

# Expected: both should normalize to ASCII equivalents
# vis-à-vis → vis-a-vis
# raison d'être → raison d'etre
```

## Verification Commands Summary

```bash
# Quick verification (recommended)
python scripts/verify_french_in_corpus.py

# Test scraper directly
python scripts/test_french_expressions.py

# Build/rebuild corpus
python scripts/build_english_corpus.py

# API search test
curl "http://localhost:8000/search/vis-à-vis"

# List corpora
curl "http://localhost:8000/corpus?language=english"
```

## Implementation Notes

1. **Normalization**: All words are normalized (lowercase, ASCII) for indexing
2. **Original Forms**: Original forms with diacritics are preserved in `original_vocabulary`
3. **Search**: All search methods (exact, fuzzy, semantic) work on normalized forms
4. **Display**: Results return original forms with diacritics when available

## Source Code References

- Corpus core: `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/core.py`
- Language sources: `/Users/mkbabb/Programming/words/backend/src/floridify/providers/language/sources.py`
- French scraper: `/Users/mkbabb/Programming/words/backend/src/floridify/providers/language/scraper/scrapers.py`
- Corpus manager: `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/manager.py`
- Search implementation: `/Users/mkbabb/Programming/words/backend/src/floridify/search/core.py`

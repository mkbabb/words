# Corpus Query Commands - Quick Reference

## Python Commands

### 1. Check if words exist in corpus (Direct)

```python
import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage
from floridify.text.normalize import batch_normalize

async def check_words():
    await get_storage()
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name="english_language_master")

    words = ["en coulisse", "recueillement", "au contraire", "raison d'être", "vis-à-vis"]
    normalized = batch_normalize(words)

    for word, norm in zip(words, normalized):
        exists = norm in corpus.vocabulary
        print(f"{'✅' if exists else '❌'} {word} ({norm}): {exists}")

asyncio.run(check_words())
```

### 2. Search corpus using search engine

```python
import asyncio
from floridify.search.core import Search
from floridify.search.constants import SearchMethod
from floridify.storage.mongodb import get_storage

async def search_words():
    await get_storage()
    search = await Search.from_corpus(corpus_name="english_language_master")

    words = ["vis-à-vis", "au contraire"]

    for word in words:
        results = await search.search(word, max_results=5, method=SearchMethod.FUZZY)
        if results:
            print(f"✅ {word}: {results[0].word} (score: {results[0].score:.2f})")
        else:
            print(f"❌ {word}: Not found")

asyncio.run(search_words())
```

### 3. Get corpus statistics

```python
import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage

async def corpus_stats():
    await get_storage()
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name="english_language_master")

    print(f"Corpus: {corpus.corpus_name}")
    print(f"Vocabulary: {len(corpus.vocabulary):,} words")
    print(f"Children: {len(corpus.child_corpus_ids)}")
    print(f"Is Master: {corpus.is_master}")

    # List children
    for child_id in corpus.child_corpus_ids:
        child = await manager.get_corpus(corpus_id=child_id)
        print(f"  - {child.corpus_name}: {len(child.vocabulary):,} words")

asyncio.run(corpus_stats())
```

### 4. Check French expressions child corpus

```python
import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage
from floridify.text.normalize import batch_normalize

async def check_french_corpus():
    await get_storage()
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name="english_language_master")

    # Find French expressions child
    for child_id in corpus.child_corpus_ids:
        child = await manager.get_corpus(corpus_id=child_id)
        if "french" in child.corpus_name.lower():
            print(f"Found: {child.corpus_name}")
            print(f"Size: {len(child.vocabulary):,} words")

            # Check specific words
            words = ["vis-à-vis", "au contraire"]
            normalized = batch_normalize(words)
            vocab_set = set(child.vocabulary)

            for word, norm in zip(words, normalized):
                exists = norm in vocab_set
                print(f"  {'✅' if exists else '❌'} {word}: {exists}")

asyncio.run(check_french_corpus())
```

## Shell Commands

### 1. Run verification script
```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/verify_french_in_corpus.py
```

### 2. Test French expressions scraper
```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/test_french_expressions.py
```

### 3. Build/rebuild English corpus
```bash
cd /Users/mkbabb/Programming/words/backend
python scripts/build_english_corpus.py
```

## API Commands (curl)

### 1. List all corpora
```bash
curl http://localhost:8000/corpus
```

### 2. Filter by language
```bash
curl "http://localhost:8000/corpus?language=english"
```

### 3. Get specific corpus
```bash
# Replace {corpus_id} with actual ID
curl "http://localhost:8000/corpus/{corpus_id}?include_stats=true"
```

### 4. Search for word (exact)
```bash
curl "http://localhost:8000/search/vis-à-vis?method=exact"
```

### 5. Search for word (fuzzy)
```bash
curl "http://localhost:8000/search/au%20contraire?method=fuzzy&min_score=0.6"
```

### 6. Search for word (cascade - all methods)
```bash
curl "http://localhost:8000/search/raison%20d'être"
```

### 7. Get search suggestions
```bash
curl "http://localhost:8000/search/vis/suggestions"
```

## MongoDB Commands

### 1. Find English corpus metadata
```javascript
db.corpus_metadata.find({ resource_id: "english_language_master" }).pretty()
```

### 2. Find French expressions corpus
```javascript
db.corpus_metadata.find({ resource_id: /french_expressions/ }).pretty()
```

### 3. Count all corpora
```javascript
db.corpus_metadata.countDocuments()
```

### 4. List all corpus names
```javascript
db.corpus_metadata.find({}, { resource_id: 1 }).toArray()
```

## Expected Results

### Verification Script Output
```
╔══════════════════════════════════════════════════════════════════════════════╗
║               FRENCH WORDS IN ENGLISH CORPUS VERIFICATION                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

🔍 Searching for English language corpus...
✅ Found corpus: english_language_master

================================================================================
METHOD 1: DIRECT VOCABULARY LOOKUP
================================================================================
✅ en coulisse         (en coulisse)         -> True
❌ recueillement       (recueillement)       -> False
✅ au contraire        (au contraire)        -> True
✅ raison d'être       (raison d'etre)       -> True
✅ vis-à-vis           (vis-a-vis)           -> True

================================================================================
📊 COMPREHENSIVE VERIFICATION REPORT
================================================================================

Word                      Direct     Exact      Fuzzy      Children
--------------------------------------------------------------------------------
en coulisse               ✅         ✅         ✅         1 found
recueillement             ❌         ❌         ❌         ❌
au contraire              ✅         ✅         ✅         1 found
raison d'être             ✅         ✅         ✅         1 found
vis-à-vis                 ✅         ✅         ✅         1 found
```

### API Search Output
```json
{
  "results": [
    {
      "word": "vis-à-vis",
      "score": 1.0,
      "method": "exact",
      "source": "corpus",
      "index": 234567
    }
  ],
  "query": "vis-à-vis",
  "total": 1,
  "method_used": "exact",
  "time_ms": 2.3
}
```

### Corpus Stats Output
```
Corpus: english_language_master
Vocabulary: 350,234 words
Children: 7
Is Master: True
  - english_language_master_sowpods_scrabble_words: 267,751 words
  - english_language_master_google_10k_frequency: 9,894 words
  - english_language_master_american_idioms: 1,234 words
  - english_language_master_phrasal_verbs: 567 words
  - english_language_master_common_phrases: 500 words
  - english_language_master_proverbs: 345 words
  - english_language_master_french_expressions: 2,456 words
```

## One-Liner Verification

### Python one-liner
```bash
python -c "import asyncio; from floridify.corpus.manager import get_tree_corpus_manager; from floridify.storage.mongodb import get_storage; from floridify.text.normalize import batch_normalize; asyncio.run((lambda: (await get_storage(), (lambda c: [print(f\"{'✅' if n in c.vocabulary else '❌'} {w}\") for w, n in zip(['vis-à-vis', 'au contraire'], batch_normalize(['vis-à-vis', 'au contraire']))])(await (await get_tree_corpus_manager()).get_corpus(corpus_name='english_language_master')))())))"
```

### API one-liner
```bash
for word in "vis-à-vis" "au contraire" "raison d'être"; do
  curl -s "http://localhost:8000/search/$word?method=exact" | jq -r ".results[0].word // \"NOT FOUND: $word\""
done
```

## File Locations

- Verification script: `/Users/mkbabb/Programming/words/backend/scripts/verify_french_in_corpus.py`
- French scraper test: `/Users/mkbabb/Programming/words/backend/scripts/test_french_expressions.py`
- Corpus builder: `/Users/mkbabb/Programming/words/backend/scripts/build_english_corpus.py`
- Sources config: `/Users/mkbabb/Programming/words/backend/src/floridify/providers/language/sources.py`
- Corpus core: `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/core.py`

# Enum Serialization Bug Report

## Executive Summary

**Bug**: Enum objects (`CorpusType`, `Language`) are being stored in cache/MongoDB as enum objects instead of strings, causing serialization errors when retrieved.

**Root Cause**: `model_dump()` without `mode="json"` returns enum objects, which pickle preserves through serialization.

**Location**: `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/manager.py`

**Fix**: Add `mode="json"` parameter to all `model_dump()` calls to convert enums to strings before storage.

---

## Detailed Analysis

### Data Flow Trace

1. **MongoDB → Beanie Load** (manager.py line 334-354)
   - Beanie loads `Corpus.Metadata` from MongoDB
   - Enum fields (`corpus_type`, `language`) are returned as **enum objects**
   - Type: `CorpusType.LEXICON`, `Language.ENGLISH`

2. **model_dump() Call** (manager.py lines 72, 160, 772, 793, etc.)
   ```python
   content = parent.model_dump()  # ❌ Returns enum OBJECTS
   ```
   - Without `mode="json"`, Pydantic returns enum objects in the dict
   - `content['corpus_type']` is `CorpusType.LEXICON` (not `"lexicon"`)

3. **Pickle Serialization** (compression.py line 31)
   ```python
   serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
   ```
   - Pickle **preserves enum objects** through serialization
   - After `pickle.loads()`, enum objects remain as enum objects

4. **get_versioned_content() Returns** (caching/core.py line 437-478)
   - Returns dict with **enum objects** from pickled cache
   - `content['corpus_type']` is still `CorpusType.LEXICON`

5. **content.update() Defensive Code** (manager.py lines 368-386)
   ```python
   content.update({
       "corpus_type": (
           metadata.corpus_type.value
           if isinstance(metadata.corpus_type, CorpusType)
           else metadata.corpus_type
       ),
   })
   ```
   - **This correctly converts enum objects to strings**
   - But it only fixes the metadata fields, not the content dict

6. **Corpus.model_validate()** (manager.py line 438)
   - Receives mixed content (some strings, some enum objects)
   - Corpus has field validators (lines 44-62) that handle both
   - But this is fragile and causes serialization errors later

### Why It's a Bug

1. **Storage Layer Mixing**: Enums stored as objects in some places, strings in others
2. **Serialization Failures**: When converting to JSON for API responses
3. **Validation Complexity**: Defensive code needed everywhere to handle both types
4. **Cache Pollution**: Cached data contains enum objects instead of serializable strings

### Proof of Concept

See `/Users/mkbabb/Programming/words/backend/test_enum_simple.py`:

```python
# WITHOUT mode="json"
content = metadata.model_dump()
# content['corpus_type'] is CorpusType.LEXICON (enum object)

pickled = pickle.dumps(content)
unpickled = pickle.loads(pickled)
# unpickled['corpus_type'] is STILL CorpusType.LEXICON (enum object)

# WITH mode="json"
content = metadata.model_dump(mode="json")
# content['corpus_type'] is "lexicon" (string)

pickled = pickle.dumps(content)
unpickled = pickle.loads(pickled)
# unpickled['corpus_type'] is "lexicon" (string) ✓
```

---

## The Fix

### Required Changes

Replace **ALL** `model_dump()` calls with `model_dump(mode="json")` in:
- `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/manager.py`

### Specific Lines to Fix

| Line | Current Code | Fixed Code |
|------|-------------|------------|
| 72 | `content = corpus.model_dump(mode="json")` | ✓ Already correct |
| 160 | `corpus.model_dump(mode="json")` | ✓ Already correct |
| 772 | `content=parent.model_dump()` | `content=parent.model_dump(mode="json")` |
| 793 | `content=child.model_dump()` | `content=child.model_dump(mode="json")` |
| 834 | `existing_content = corpus.model_dump()` | `existing_content = corpus.model_dump(mode="json")` |
| 1055 | `tree = corpus.model_dump(mode="json")` | ✓ Already correct |
| 1122 | `aggregated_corpus_data = parent.model_dump()` | `aggregated_corpus_data = parent.model_dump(mode="json")` |
| 1253 | `content=parent.model_dump()` | `content=parent.model_dump(mode="json")` |
| 1273 | `content=child.model_dump()` | `content=child.model_dump(mode="json")` |

### Summary

- **Total changes**: 5 lines (4 already fixed)
- **Files affected**: 1 file (manager.py)
- **Risk level**: Low (consistent with existing correct usage)

---

## Why This Works

### Pydantic Serialization Modes

```python
# mode="python" (default)
model.model_dump()  # Returns native Python types (enums stay as enum objects)

# mode="json"
model.model_dump(mode="json")  # Converts for JSON (enums → strings)
```

### What `mode="json"` Does

1. **Enums**: Converts to `.value` (string representation)
2. **Dates**: Converts to ISO format strings
3. **ObjectIds**: Converts to string representation
4. **Custom types**: Uses JSON serializers

### Why It's Safe

1. **Already used**: Lines 72, 160, 1055 already use `mode="json"`
2. **Consistent**: Matches storage format expectations
3. **Reversible**: `Corpus.model_validate()` has validators that convert strings back to enums
4. **Pickle-friendly**: Strings survive pickle serialization cleanly

---

## Verification Test

After applying the fix, run:

```bash
cd /Users/mkbabb/Programming/words/backend
source .venv/bin/activate
python test_enum_simple.py
```

Expected output:
```
model_dump(mode='json'):
  content['corpus_type'] type: <class 'str'>
  content['corpus_type'] value: lexicon
  Is enum object? False
```

---

## Alternative Fixes (Not Recommended)

### Alternative 1: Add Field Validators to Corpus.Metadata

Add validators like Corpus has (lines 44-62) to Corpus.Metadata.

**Rejected because**:
- More code duplication
- Doesn't fix the storage layer mixing
- Still requires defensive code everywhere

### Alternative 2: Custom Pickle Serializer

Override `__reduce__` to convert enums during pickle.

**Rejected because**:
- Over-engineered solution
- Harder to maintain
- `mode="json"` is standard Pydantic approach

### Alternative 3: Always Call `.value`

Manually call `.value` when passing enums.

**Rejected because**:
- Error-prone (easy to forget)
- Verbose and repetitive
- `mode="json"` handles all types consistently

---

## Conclusion

The fix is **minimal, safe, and follows Pydantic best practices**. Using `mode="json"` ensures:

1. ✓ Consistent string serialization
2. ✓ Clean pickle storage
3. ✓ No enum objects in cache
4. ✓ Proper JSON API responses
5. ✓ Alignment with existing correct usage

**Next Step**: Apply the 5 line changes to manager.py and verify with existing tests.

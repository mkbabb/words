# Serialization Flow Diagram

## Data Flow: Save to MongoDB (WRITE PATH)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Application Code                                     │
│  content = {                                                             │
│    "index_type": IndexType.TRIE,           ← Python enum                │
│    "corpus_id": PydanticObjectId("..."),   ← Python ObjectId            │
│    "count": 12345                          ← Regular int                │
│  }                                                                       │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         manager.save() - Line 166 (manager.py)                          │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ HASH CALCULATION (for deduplication)                       │         │
│  │                                                             │         │
│  │ content_str = json.dumps(content,                          │         │
│  │                          sort_keys=True,                   │         │
│  │                          default=self._json_encoder)       │         │
│  │                                                             │         │
│  │ _json_encoder converts:                                    │         │
│  │   IndexType.TRIE        → "trie"         (string)         │         │
│  │   PydanticObjectId(...) → "507f1f77..." (string)         │         │
│  │                                                             │         │
│  │ Result: '{"corpus_id":"507f...","count":12345,...}'       │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  content_hash = sha256(content_str).hexdigest()                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│      set_versioned_content() - Line 490 (core.py)                      │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ SIZE CALCULATION (to decide inline vs external)            │         │
│  │                                                             │         │
│  │ content_str = json.dumps(content,                          │         │
│  │                          sort_keys=True,                   │         │
│  │                          default=_json_default)            │         │
│  │                                                             │         │
│  │ _json_default converts:                                    │         │
│  │   IndexType.TRIE        → "trie"         (string)         │         │
│  │   PydanticObjectId(...) → "507f1f77..." (string)         │         │
│  │                                                             │         │
│  │ content_size = len(content_str.encode())                   │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  ┌─────────── IF content_size < 16KB ────────────┐                     │
│  │                                                 │                     │
│  │  INLINE STORAGE (Path A)                      │                     │
│  │  ════════════════════════                      │                     │
│  │  Line 503:                                     │                     │
│  │  versioned_data.content_inline = content       │ ← BUG: Raw dict!   │
│  │                                                 │   Enums preserved  │
│  │  (content still has enum/ObjectId objects)    │   in Python, but   │
│  │                                                 │   will become      │
│  └─────────────────────────┬───────────────────────┘   strings in      │
│                            │                           MongoDB!         │
│  ┌─────────── ELSE ────────┴──────────────────────┐                    │
│  │                                                 │                     │
│  │  EXTERNAL STORAGE (Path B)                     │                     │
│  │  ═════════════════════════                      │                     │
│  │  Line 513-527:                                  │                     │
│  │  await cache.set(                               │                     │
│  │      namespace=...,                             │                     │
│  │      key=cache_key,                             │                     │
│  │      value=content  ← Goes to FilesystemBackend │                    │
│  │  )                     Uses PICKLE              │                     │
│  │                                                 │                     │
│  │  Pickle preserves exact Python types!          │                     │
│  └─────────────────────────────────────────────────┘                    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ (Path A - Inline)
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│        Beanie Document Save - Lines 96/133 (manager.py)                │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ await versioned.insert() or versioned.save()               │         │
│  │                                                             │         │
│  │ Beanie internally calls:                                   │         │
│  │   1. model_dump() → Pydantic converts model to dict       │         │
│  │   2. Motor sends dict to MongoDB                           │         │
│  │   3. BSON encoder serializes Python types:                 │         │
│  │                                                             │         │
│  │      Top-level fields:                                     │         │
│  │        resource_type (enum) → Pydantic serializer →       │         │
│  │        "corpus" (string) → MongoDB                         │         │
│  │                                                             │         │
│  │      content_inline (dict):                                │         │
│  │        Python: {                                           │         │
│  │          "index_type": IndexType.TRIE,      ← enum        │         │
│  │          "corpus_id": PydanticObjectId(...) ← ObjectId    │         │
│  │        }                                                   │         │
│  │                                                             │         │
│  │        Pydantic serializer for dict[str, Any]:            │         │
│  │        → Recursively converts to JSON-compatible          │         │
│  │                                                             │         │
│  │        MongoDB receives:                                   │         │
│  │        {                                                   │         │
│  │          "index_type": "trie",              ← STRING!     │         │
│  │          "corpus_id": "507f1f77..."         ← STRING!     │         │
│  │        }                                                   │         │
│  └────────────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MongoDB Storage                                  │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ {                                                           │         │
│  │   "_id": ObjectId("..."),                                  │         │
│  │   "resource_id": "my_corpus",                              │         │
│  │   "resource_type": "corpus",         ← string              │         │
│  │   "namespace": "corpus",              ← string              │         │
│  │   "content_inline": {                                       │         │
│  │     "index_type": "trie",            ← STRING (was enum!)  │         │
│  │     "corpus_id": "507f1f77...",      ← STRING (was OID!)   │         │
│  │     "count": 12345                    ← int (preserved)     │         │
│  │   },                                                        │         │
│  │   "version_info": {...}                                     │         │
│  │ }                                                           │         │
│  └────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Read from MongoDB (READ PATH)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MongoDB Storage                                  │
│  {                                                                       │
│    "resource_type": "corpus",                                           │
│    "content_inline": {                                                  │
│      "index_type": "trie",           ← STRING                          │
│      "corpus_id": "507f1f77...",     ← STRING                          │
│      "count": 12345                                                     │
│    }                                                                    │
│  }                                                                      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│       manager.get_latest() - Lines 370-390 (manager.py)                │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ result = await model_class.find(                           │         │
│  │     {"resource_id": resource_id,                           │         │
│  │      "version_info.is_latest": True}                       │         │
│  │ ).sort("-_id").first_or_none()                             │         │
│  │                                                             │         │
│  │ Beanie/Pydantic reconstruction:                            │         │
│  │                                                             │         │
│  │ 1. Motor receives BSON from MongoDB                        │         │
│  │ 2. Converts BSON → Python dict                             │         │
│  │ 3. Pydantic validators reconstruct model:                  │         │
│  │                                                             │         │
│  │    Top-level field with validator:                         │         │
│  │      "resource_type": "corpus" (string from MongoDB)       │         │
│  │      → Pydantic validator sees ResourceType field          │         │
│  │      → Converts "corpus" → ResourceType.CORPUS (enum!)    │         │
│  │                                                             │         │
│  │    content_inline field (NO validator):                    │         │
│  │      {                                                     │         │
│  │        "index_type": "trie",        ← STAYS STRING!       │         │
│  │        "corpus_id": "507f1f77...",  ← STAYS STRING!       │         │
│  │        "count": 12345                                      │         │
│  │      }                                                      │         │
│  │                                                             │         │
│  │    Result model:                                           │         │
│  │      result.resource_type = ResourceType.CORPUS (enum)    │         │
│  │      result.content_inline = {                             │         │
│  │        "index_type": "trie",        ← STRING              │         │
│  │        "corpus_id": "507f1f77...",  ← STRING              │         │
│  │        "count": 12345                                      │         │
│  │      }                                                      │         │
│  └────────────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│     get_versioned_content() - Lines 437-478 (core.py)                  │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ if versioned_data.content_inline is not None:              │         │
│  │     content = versioned_data.content_inline                │         │
│  │     if isinstance(content, dict):                          │         │
│  │         return content  ← Returns dict AS-IS!             │         │
│  │                            No type reconstruction!          │         │
│  │                                                             │         │
│  │ Returns:                                                    │         │
│  │   {                                                         │         │
│  │     "index_type": "trie",        ← STRING (should be enum) │         │
│  │     "corpus_id": "507f1f77...",  ← STRING (should be OID)  │         │
│  │     "count": 12345                                          │         │
│  │   }                                                         │         │
│  └────────────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Application Code                                     │
│  content = await get_versioned_content(versioned)                       │
│                                                                          │
│  # Expected:                                                             │
│  # content["index_type"] == IndexType.TRIE (enum)                       │
│  #                                                                       │
│  # Actual:                                                               │
│  # content["index_type"] == "trie" (string!)                            │
│  #                                                                       │
│  # Bug manifests when code does:                                        │
│  # if content["index_type"] is IndexType.TRIE:  ← FAILS                │
│  #     # This never executes!                                            │
│  #                                                                       │
│  # But this works (false positive):                                     │
│  # if content["index_type"] == IndexType.TRIE:  ← PASSES                │
│  #     # Works because enum.__eq__ handles strings                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Comparison: External Storage (Works Correctly)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  EXTERNAL STORAGE PATH (>= 16KB)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SAVE:                                                                   │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ set_versioned_content() → cache.set(content)              │         │
│  │   ↓                                                        │         │
│  │ GlobalCacheManager.set() → FilesystemBackend.set()        │         │
│  │   ↓                                                        │         │
│  │ Filesystem backend (line 94-96):                          │         │
│  │   import pickle                                            │         │
│  │   data = pickle.dumps(value,                              │         │
│  │                       protocol=pickle.HIGHEST_PROTOCOL)   │         │
│  │                                                             │         │
│  │ Pickle serialization:                                      │         │
│  │   IndexType.TRIE → \\x80\\x04\\x95... (binary, exact type) │         │
│  │   PydanticObjectId → \\x80\\x04\\x95... (binary, exact)    │         │
│  │                                                             │         │
│  │ Diskcache stores binary blob to filesystem                 │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  LOAD:                                                                   │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ get_versioned_content() → cache.get(cache_key)            │         │
│  │   ↓                                                        │         │
│  │ GlobalCacheManager.get() → FilesystemBackend.get()        │         │
│  │   ↓                                                        │         │
│  │ Filesystem backend (line 72-74):                          │         │
│  │   if isinstance(data, bytes):                             │         │
│  │       import pickle                                        │         │
│  │       return pickle.loads(data)                            │         │
│  │                                                             │         │
│  │ Pickle deserialization:                                    │         │
│  │   \\x80\\x04\\x95... → IndexType.TRIE (exact enum!)         │         │
│  │   \\x80\\x04\\x95... → PydanticObjectId(...) (exact!)      │         │
│  │                                                             │         │
│  │ Returns content with EXACT PYTHON TYPES!                  │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  Result: Application receives content identical to what was saved       │
│          No type loss, no string conversion                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## The Three Serialization Contexts

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SERIALIZATION CONTEXT MATRIX                          │
├────────────────┬─────────────────┬────────────────┬──────────────────────┤
│   Context      │   Purpose       │   Method       │   Result             │
├────────────────┼─────────────────┼────────────────┼──────────────────────┤
│                │                 │                │                      │
│ 1. Hash Calc   │ Deduplication   │ json.dumps()   │ All complex types   │
│    (Line 166)  │ Content hash    │ + _json_encoder│ → strings           │
│                │                 │                │                      │
│                │ Only used for   │ Enums → str    │ Hash is consistent  │
│                │ hash generation │ OID → str      │ Dedup works         │
│                │ Not stored      │ datetime → str │ ✓ Correct           │
│                │                 │                │                      │
├────────────────┼─────────────────┼────────────────┼──────────────────────┤
│                │                 │                │                      │
│ 2. Inline      │ Small content   │ Raw assignment │ Enums/OIDs preserved│
│    Storage     │ (<16KB)         │ to Beanie      │ in Python, but      │
│    (Line 503)  │                 │ model field    │ MongoDB converts    │
│                │                 │                │ to strings on save  │
│                │ Direct MongoDB  │ Beanie →       │                      │
│                │ document field  │ BSON encoder   │ On load: Top-level  │
│                │                 │                │ fields validated,   │
│                │                 │ Top: validated │ nested dict NOT     │
│                │                 │ Nested: raw    │ ✗ BUG               │
│                │                 │                │                      │
├────────────────┼─────────────────┼────────────────┼──────────────────────┤
│                │                 │                │                      │
│ 3. External    │ Large content   │ Pickle         │ Exact Python types  │
│    Storage     │ (>=16KB)        │ serialization  │ preserved           │
│    (Line 513)  │                 │                │                      │
│                │ Filesystem      │ pickle.dumps() │ Enums stay enums    │
│                │ cache via       │ →              │ OIDs stay OIDs      │
│                │ diskcache       │ pickle.loads() │ datetime preserved  │
│                │                 │                │ ✓ Correct           │
│                │                 │                │                      │
└────────────────┴─────────────────┴────────────────┴──────────────────────┘
```

## The Bug Location

```python
# File: /Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py
# Function: set_versioned_content()
# Lines: 490-528

async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024

    if not force_external and content_size < inline_threshold:
        # ═══════════════════════════════════════════════════════════
        # BUG IS HERE - Line 503
        # ═══════════════════════════════════════════════════════════
        versioned_data.content_inline = content  # ← Assigns raw dict
        # ═══════════════════════════════════════════════════════════
        #
        # PROBLEM:
        #   - content has enums/ObjectIds (Python objects)
        #   - Assigned directly to Beanie Document field
        #   - Beanie saves to MongoDB via BSON encoder
        #   - BSON encoder converts enums → strings, ObjectIds → strings
        #   - On retrieval, Pydantic doesn't validate nested dict
        #   - Application receives strings instead of original types
        #
        # FIX OPTION 1 (Immediate):
        #   versioned_data.content_inline = json.loads(content_str)
        #   # Explicitly convert to JSON-safe dict (all strings)
        #   # Makes behavior consistent and predictable
        #
        # FIX OPTION 2 (Long-term):
        #   if _contains_complex_types(content):
        #       force_external = True  # Force pickle storage
        #   else:
        #       versioned_data.content_inline = content
        #
        # ═══════════════════════════════════════════════════════════

        versioned_data.content_location = None
        return

    # External storage (works correctly via pickle)
    cache = await get_global_cache()
    # ... rest of external storage logic
```

## Summary

**3 Serialization Paths**:
1. Hash calculation (JSON) - ✓ Works for its purpose
2. Inline storage (Beanie/BSON) - ✗ **BUG**: Type loss on round-trip
3. External storage (Pickle) - ✓ Works correctly

**The Problem**:
- Inline storage assigns raw dict with Python objects to Beanie field
- MongoDB BSON encoder converts complex types to strings
- No Pydantic validator reconstructs them on load
- Application receives strings instead of enums/ObjectIds

**The Fix**:
- Line 503 in `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
- Either: Force JSON round-trip for consistency
- Or: Force external storage for complex types
- Or: Add Pydantic validators for nested content

**Impact**:
- Small content (<16KB) affected
- Large content (≥16KB) works correctly
- Explains why some tests pass (large data) and others fail (small data)

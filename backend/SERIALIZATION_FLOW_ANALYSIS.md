# Serialization Flow Analysis - Versioning System

## Executive Summary

The versioning system has **THREE DISTINCT SERIALIZATION PATHS** with different behaviors:

1. **Hash Calculation** (manager.py line 166) - Uses JSON with custom encoder
2. **Inline Storage** (core.py line 503) - Stores raw dict in MongoDB via Beanie
3. **External Storage** (core.py line 513-527) - Uses cache system with pickle

**THE BUG**: Path #1 and #2 create a mismatch because:
- Hash uses JSON serialization (enums → strings)
- Inline storage uses Beanie (enums stay as enums in Python, but become strings in MongoDB)
- When MongoDB returns data, enums become strings but Pydantic validators reconstruct them

---

## Complete Data Flow

### SERIALIZATION (Save Path)

#### Step 1: VersionedDataManager.save() - Hash Calculation
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py`
**Line**: 166

```python
content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
content_hash = hashlib.sha256(content_str.encode()).hexdigest()
```

**What happens**:
- Input: `content` = dict with enums, ObjectIds, datetime, etc.
- Process: JSON serialization with custom encoder
- Output: String representation for hashing

**Custom Encoder** (line 643-653):
```python
def _json_encoder(self, obj: Any) -> str:
    """Custom JSON encoder for complex objects like PydanticObjectId."""
    from datetime import datetime

    if isinstance(obj, PydanticObjectId):
        return str(obj)           # ObjectId → "507f1f77bcf86cd799439011"
    if isinstance(obj, Enum):
        return str(obj.value)     # ResourceType.CORPUS → "corpus"
    if isinstance(obj, datetime):
        return obj.isoformat()    # datetime → "2025-01-09T12:00:00"
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

**Result**: All complex types converted to strings for hashing

#### Step 2: set_versioned_content() - Content Storage Decision
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
**Lines**: 490-528

```python
async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    """Store versioned content using inline or external storage."""
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024  # 16KB

    if not force_external and content_size < inline_threshold:
        # PATH A: Inline storage (< 16KB)
        versioned_data.content_inline = content  # ← Raw dict assigned!
        versioned_data.content_location = None
        return

    # PATH B: External storage (>= 16KB)
    cache = await get_global_cache()
    cache_key = (
        f"{versioned_data.resource_type.value}:{versioned_data.resource_id}:"
        f"content:{versioned_data.version_info.data_hash[:8]}"
    )

    await cache.set(
        namespace=versioned_data.namespace,
        key=cache_key,
        value=content,  # ← Goes to cache (pickle serialization)
        ttl_override=versioned_data.ttl,
    )

    versioned_data.content_location = ContentLocation(...)
    versioned_data.content_inline = None
```

**Helper Function** (line 481-487):
```python
def _json_default(obj: Any) -> str:
    """Serialize enums and Pydantic types in a stable way."""
    if isinstance(obj, PydanticObjectId):
        return str(obj)
    if isinstance(obj, Enum):
        return str(obj.value)
    return str(obj)
```

**Critical Point**:
- `content_str` is only used for SIZE calculation
- The actual `content` (raw dict with enums) is assigned to `content_inline`
- NO deserialization happens - the dict goes straight to MongoDB via Beanie

#### Step 3: Beanie Document Save
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py`
**Lines**: 96 or 133

```python
await versioned.insert(session=session)  # or
await versioned.save()
```

**What Beanie does**:
1. Calls Pydantic's `model_dump()` to convert model → dict
2. Sends dict to MongoDB via Motor driver
3. MongoDB BSON encoder converts Python types:
   - Enums → strings (via Pydantic serialization)
   - ObjectIds → BSON ObjectId
   - datetime → BSON datetime
   - dicts → BSON documents

**content_inline field in MongoDB**:
```json
{
  "_id": ObjectId("..."),
  "resource_type": "corpus",
  "content_inline": {
    "trie": {...},           // nested data
    "type": "corpus",        // ← enum became string
    "count": 12345,
    "some_id": "507f..."     // ← ObjectId became string
  }
}
```

---

### DESERIALIZATION (Get Path)

#### Step 1: MongoDB Query
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py`
**Lines**: 370-390

```python
result = (
    await model_class.find(
        {"resource_id": resource_id, "version_info.is_latest": True},
    )
    .sort("-_id")
    .first_or_none()
)
```

**What happens**:
1. MongoDB returns BSON document
2. Motor converts BSON → Python dict
3. Beanie calls Pydantic validators to reconstruct model
4. **Pydantic validators** (if defined) convert strings back to enums

**Example Beanie reconstruction**:
```python
# MongoDB returns:
{
  "resource_type": "corpus",  # string
  "content_inline": {
    "type": "corpus"  # string
  }
}

# Pydantic validator for resource_type field:
# - Sees string "corpus"
# - Converts to ResourceType.CORPUS enum
# Result: model.resource_type = ResourceType.CORPUS

# BUT content_inline has NO validator:
# - Stays as dict with string values
# Result: model.content_inline = {"type": "corpus"}  # Still a string!
```

#### Step 2: get_versioned_content() - Content Retrieval
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
**Lines**: 437-478

```python
async def get_versioned_content(versioned_data: Any) -> dict[str, Any] | None:
    """Retrieve content from a versioned data object."""

    # Inline content takes precedence
    if versioned_data.content_inline is not None:
        content = versioned_data.content_inline
        if isinstance(content, dict):
            return content  # ← Returns dict with strings instead of enums!
        return None

    # External content
    if versioned_data.content_location:
        location = versioned_data.content_location
        if location.cache_key and location.cache_namespace:
            cache = await get_global_cache()
            cached_content = await cache.get(
                namespace=location.cache_namespace,
                key=location.cache_key
            )
            # This goes through pickle deserialization
            # Enums are preserved correctly!
            return cached_content

    return None
```

---

## THE THREE BUGS

### Bug 1: Enum Serialization in content_inline

**Location**: Inline storage path
**Problem**:
- Enums in `content_inline` are serialized to strings by MongoDB
- No Pydantic validator to convert them back
- Application receives dict with string values instead of enums

**Example**:
```python
# Save:
content = {"index_type": IndexType.TRIE, "count": 100}
versioned.content_inline = content  # Enum stored

# MongoDB stores:
{"content_inline": {"index_type": "trie", "count": 100}}  # String!

# Retrieve:
retrieved = await get_versioned_content(versioned)
print(type(retrieved["index_type"]))  # <class 'str'>, not IndexType enum
```

### Bug 2: ObjectId Serialization in content_inline

**Location**: Same inline storage path
**Problem**:
- ObjectIds in nested dicts become strings
- No reconstruction back to ObjectId

**Example**:
```python
# Save:
content = {"corpus_id": PydanticObjectId("507f1f77bcf86cd799439011")}
versioned.content_inline = content

# MongoDB stores:
{"content_inline": {"corpus_id": "507f1f77bcf86cd799439011"}}  # String!

# Retrieve:
retrieved = await get_versioned_content(versioned)
print(type(retrieved["corpus_id"]))  # <class 'str'>, not PydanticObjectId
```

### Bug 3: Missing serialization.py Module

**Location**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py` line 601
**Problem**:
```python
from .serialization import serialize_content  # ← File doesn't exist!
serialized = serialize_content(content)
```

**Impact**: This code path is never reached (external storage defaults to pickle), but would crash if large Pydantic models trigger it.

---

## Why External Storage Works

**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/filesystem.py`
**Lines**: 84-100

```python
async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
    """Set with optimized serialization."""

    def _set() -> None:
        data: Any
        if isinstance(value, str | int | float | bool | type(None)):
            data = value
        elif isinstance(value, dict | list):
            data = value  # diskcache handles it
        else:
            # Use pickle for everything else
            import pickle
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

        self.cache.set(key, data, expire=expire)
```

**Why it works**:
- Pickle preserves Python object types exactly
- Enums stay as enums
- ObjectIds stay as ObjectIds
- No string conversion

---

## Root Cause Analysis

### Why the Bug Exists

1. **Mixed Serialization Strategies**:
   - Hash calculation: JSON (strings)
   - Inline storage: Beanie/MongoDB (strings after round-trip)
   - External storage: Pickle (preserves types)

2. **No Validation on content_inline**:
   - `content_inline: dict[str, Any] | None = None`
   - Pydantic doesn't know to validate nested types
   - No custom validator defined

3. **Assumption Mismatch**:
   - Code assumes `content_inline` preserves Python types
   - MongoDB/BSON doesn't preserve enum/ObjectId types in nested dicts
   - Only top-level model fields get Pydantic validation

### Why It Wasn't Caught

1. **Type Hints Are Loose**:
   ```python
   content_inline: dict[str, Any] | None = None
   ```
   - `Any` suppresses type checking
   - Should be `dict[str, str | int | float | ...]` to catch enum issues

2. **Tests May Use External Storage**:
   - Large content (>16KB) uses pickle → works correctly
   - Small content (<16KB) uses inline → broken
   - If tests mostly use large data, bug goes unnoticed

3. **String Enum Comparison Works**:
   ```python
   ResourceType.CORPUS == "corpus"  # True (Enum.__eq__ handles it)
   ```
   - Python enums compare equal to their values
   - Hides the type mismatch in some cases

---

## The Proper Fix Location

### Option 1: Fix at Deserialization (Recommended)

**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
**Function**: `get_versioned_content()`
**Lines**: 437-478

**What to do**:
Add a post-processing step to reconstruct enums and ObjectIds from the retrieved dict.

**Implementation**:
```python
async def get_versioned_content(versioned_data: Any) -> dict[str, Any] | None:
    """Retrieve content from a versioned data object."""
    from .models import BaseVersionedData

    if not isinstance(versioned_data, VersionedContent | BaseVersionedData):
        return None

    content = None

    # Inline content takes precedence
    if versioned_data.content_inline is not None:
        content = versioned_data.content_inline
    # External content
    elif versioned_data.content_location:
        location = versioned_data.content_location
        if location.cache_key and location.cache_namespace:
            cache = await get_global_cache()
            content = await cache.get(
                namespace=location.cache_namespace,
                key=location.cache_key
            )

    if content is None:
        return None

    # Post-process to fix MongoDB's string conversion
    return _reconstruct_types(content)


def _reconstruct_types(data: Any) -> Any:
    """Recursively reconstruct enums and ObjectIds from strings."""
    if isinstance(data, dict):
        return {k: _reconstruct_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_reconstruct_types(item) for item in data]
    elif isinstance(data, str):
        # Try to reconstruct ObjectId
        if len(data) == 24 and all(c in '0123456789abcdef' for c in data):
            try:
                from beanie import PydanticObjectId
                return PydanticObjectId(data)
            except Exception:
                pass

        # Try to reconstruct known enums
        # (This requires a registry or schema knowledge)
        return data
    else:
        return data
```

**Problem with Option 1**:
- Need to know which strings should be enums
- Requires schema registry or type hints
- Can't distinguish "corpus" (enum value) from "corpus" (regular string)

### Option 2: Fix at Serialization (Better)

**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
**Function**: `set_versioned_content()`
**Lines**: 490-528

**What to do**:
Always use external storage (pickle) for content with complex types, or convert to JSON-safe format before inline storage.

**Implementation A - Always External**:
```python
async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    """Store versioned content using inline or external storage."""

    # Check if content has complex types
    has_complex_types = _contains_complex_types(content)

    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024

    # Force external if complex types present
    if has_complex_types:
        force_external = True

    if not force_external and content_size < inline_threshold:
        versioned_data.content_inline = content
        versioned_data.content_location = None
        return

    # ... rest of external storage logic
```

**Implementation B - JSON Serialize for Inline**:
```python
async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    """Store versioned content using inline or external storage."""
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024

    if not force_external and content_size < inline_threshold:
        # Convert to JSON-safe dict (strings only)
        versioned_data.content_inline = json.loads(content_str)  # ← Everything is now strings
        versioned_data.content_location = None
        return

    # ... external storage
```

**Problem with Option 2B**:
- Loses type information permanently for inline storage
- Application code must handle string values
- Inconsistent with external storage behavior

### Option 3: Use Pydantic Model for content_inline (Best)

**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/models.py`
**Class**: `BaseVersionedData`

**What to do**:
Define a Pydantic model for content structure and use validators to preserve types.

**Implementation**:
```python
from typing import TypeVar, Generic

ContentType = TypeVar('ContentType', bound=BaseModel)

class BaseVersionedData(Document, Generic[ContentType]):
    """Base class for all versioned data with content management."""

    # ... existing fields ...

    content_inline: ContentType | dict[str, Any] | None = None

    @field_validator('content_inline', mode='before')
    @classmethod
    def validate_content_inline(cls, v: Any) -> Any:
        """Reconstruct enums and ObjectIds from MongoDB strings."""
        if v is None or not isinstance(v, dict):
            return v

        # Recursively fix types
        return _reconstruct_types_with_schema(v, cls.content_schema)
```

**Problem with Option 3**:
- Requires defining content schemas for each resource type
- Major refactoring
- Breaking change for existing code

---

## Recommended Solution

### Immediate Fix (Low Risk)

**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py`
**Function**: `set_versioned_content()` line 503

**Change**:
```python
# Before:
versioned_data.content_inline = content

# After:
# Ensure JSON round-trip for type consistency
content_str = json.dumps(content, sort_keys=True, default=_json_default)
versioned_data.content_inline = json.loads(content_str)
```

**Why**:
- Makes inline storage behavior explicit (everything becomes strings)
- Consistent with how MongoDB actually stores it
- Application code already handles string enums (due to `ResourceType.CORPUS == "corpus"`)
- No breaking changes

### Long-term Fix (Better Architecture)

1. **Create serialization.py**:
   - Implement proper `serialize_content()` and `deserialize_content()`
   - Handle enums, ObjectIds, datetime consistently
   - Use pickle for binary, JSON for text

2. **Add Type Registry**:
   - Map field names to expected types
   - Allow reconstruction during deserialization
   - Example: `{"corpus_id": PydanticObjectId, "index_type": IndexType}`

3. **Use Pydantic Models for Content**:
   - Define content schema per resource type
   - Leverage Pydantic's validators
   - Type-safe content access

---

## Testing the Fix

### Test Case 1: Enum Preservation
```python
async def test_enum_in_content():
    content = {
        "index_type": IndexType.TRIE,
        "resource_type": ResourceType.CORPUS,
        "count": 100
    }

    # Save
    versioned = await manager.save(
        resource_id="test",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        content=content
    )

    # Retrieve
    retrieved = await manager.get_latest("test", ResourceType.CORPUS)
    content_back = await get_versioned_content(retrieved)

    # Verify
    assert isinstance(content_back["index_type"], (IndexType, str))
    # After fix, should be string consistently
    assert content_back["index_type"] == "trie"
```

### Test Case 2: ObjectId Preservation
```python
async def test_objectid_in_content():
    obj_id = PydanticObjectId()
    content = {
        "corpus_id": obj_id,
        "name": "test"
    }

    # Save
    versioned = await manager.save(
        resource_id="test",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        content=content
    )

    # Retrieve
    retrieved = await manager.get_latest("test", ResourceType.CORPUS)
    content_back = await get_versioned_content(retrieved)

    # Verify
    assert isinstance(content_back["corpus_id"], (PydanticObjectId, str))
    # After fix, should be string consistently
    assert content_back["corpus_id"] == str(obj_id)
```

---

## Summary

**The Bug**: Enums and ObjectIds in `content_inline` are converted to strings by MongoDB but not reconstructed on retrieval.

**Root Cause**: Mixed serialization (JSON for hash, Beanie/BSON for storage, no validators for nested content).

**Fix Location**: `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py` line 503 in `set_versioned_content()`

**Immediate Fix**: Force JSON round-trip for inline storage to make string conversion explicit and consistent.

**Long-term Fix**: Create proper serialization module with type registry and Pydantic validators.

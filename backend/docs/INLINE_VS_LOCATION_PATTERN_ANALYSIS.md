# Content Inline vs Content_Location Pattern Analysis
## Floridify Caching System - January 2025

---

## Executive Summary

The Floridify caching system uses a dual-strategy storage pattern to manage content:

| Pattern | Storage Location | Threshold | Usage |
|---------|------------------|-----------|-------|
| **content_inline** | MongoDB document | < 16KB | Small content directly in metadata |
| **content_location** | Filesystem cache (L2) | ≥ 16KB | Large content via reference pointer |

**Current Status**: Implementation is **mostly consistent** with:
- ✅ Clear 16KB threshold boundary
- ✅ Mutual exclusivity enforced (never both set)
- ✅ Automatic strategy selection in `set_versioned_content()`
- ✅ Unified retrieval interface via `get_versioned_content()`

**Issues Found**: 
- 🔴 **2 inconsistent patterns** (semantic index binary data handling)
- 🟡 **3 decision points** using different thresholds/logic
- 🟡 **Documentation gaps** on when/why to override defaults
- 🟡 **No schema enforcement** preventing misuse

---

## 1. Pattern Definitions

### 1.1 content_inline
**Purpose**: Store small content directly in MongoDB document
**Definition**: `dict[str, Any] | None`
**Constraints**:
- Mandatory type: Python dict (not bytes/strings)
- Maximum size: 16KB (enforced in `set_versioned_content`)
- Mutually exclusive with `content_location`
- Used for: vocabulary lists, metadata, config

**When Inline**:
```python
# Model definition in caching/models.py:194-195
class BaseVersionedData(Document):
    content_inline: dict[str, Any] | None = None
    content_location: ContentLocation | None = None
```

**Example Usage**:
```python
# Small corpus content → inline storage
metadata.content_inline = {
    "vocabulary": ["apple", "banana"],
    "stats": {"count": 2}
}
metadata.content_location = None
```

### 1.2 content_location
**Purpose**: Reference externally stored large content
**Definition**: `ContentLocation` model with metadata
**Structure**:
```python
class ContentLocation(BaseModel):
    storage_type: StorageType  # CACHE, S3, DATABASE, MEMORY
    cache_namespace: CacheNamespace | None  # Which cache namespace
    cache_key: str | None  # Key in cache backend
    path: str | None  # S3 path or filesystem path
    compression: CompressionType | None  # ZSTD, LZ4, GZIP
    size_bytes: int  # Uncompressed size
    size_compressed: int | None  # Compressed size (if applicable)
    checksum: str  # SHA-256 hash for verification
```

**Example Usage**:
```python
# Large index content → external storage
metadata.content_location = ContentLocation(
    storage_type=StorageType.CACHE,
    cache_namespace=CacheNamespace.SEMANTIC,
    cache_key="semantic:corpus123:index:abc1",
    compression=CompressionType.ZSTD,
    size_bytes=1290000000,  # 1.29GB uncompressed
    size_compressed=390000000,  # After ZSTD
    checksum="sha256hash..."
)
metadata.content_inline = None
```

---

## 2. How Inline Content is Handled

### 2.1 Writing Inline Content
**Function**: `set_versioned_content()` in core.py:518-622

**Decision Logic**:
```python
async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    # Step 1: Handle force_external flag (used for binary data only)
    if force_external:
        # Skip JSON encoding to prevent OOM with large binary
        # Store directly to cache backend
        versioned_data.content_location = ContentLocation(...)
        versioned_data.content_inline = None
        return
    
    # Step 2: JSON encode to calculate size
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())
    
    # Step 3: Size threshold check (16KB = 16 * 1024 bytes)
    inline_threshold = 16 * 1024
    
    if content_size < inline_threshold:
        # Step 4a: INLINE - store in MongoDB
        versioned_data.content_inline = content  # Dict object, not JSON string
        versioned_data.content_location = None
        return
    
    # Step 4b: EXTERNAL - store in filesystem cache
    # Create ContentLocation metadata
    versioned_data.content_location = ContentLocation(
        cache_namespace=versioned_data.namespace,
        cache_key=cache_key,
        storage_type=StorageType.CACHE,
        size_bytes=content_size,
        checksum=hashlib.sha256(content_str.encode()).hexdigest(),
    )
    versioned_data.content_inline = None
```

**Key Points**:
1. **Serialization occurs first** (line 580) - JSON needed to calculate size
2. **Threshold is hardcoded**: 16KB (16 * 1024 bytes)
3. **Inline stores dict object**, not serialized JSON string
4. **Mutual exclusivity enforced** - if content_location set, content_inline = None

### 2.2 Reading Inline Content
**Function**: `get_versioned_content()` in core.py:466-506

**Retrieval Logic**:
```python
async def get_versioned_content(versioned_data: Any) -> dict[str, Any] | None:
    # Check if it's a versioned data object
    if not isinstance(versioned_data, BaseVersionedData):
        return None
    
    # Priority 1: Inline content (checked first)
    if versioned_data.content_inline is not None:
        # Already a dict - return directly
        content = versioned_data.content_inline
        if isinstance(content, dict):
            return content
        return None
    
    # Priority 2: External content
    if versioned_data.content_location:
        location = versioned_data.content_location
        if location.cache_key and location.cache_namespace:
            # Fetch from cache backend (L2)
            cache = await get_global_cache()
            namespace = location.cache_namespace  # Handle enum/string
            cached_content = await cache.get(namespace=namespace, key=location.cache_key)
            # Type casting
            if isinstance(cached_content, dict):
                return cached_content
            return None if cached_content is None else dict(cached_content)
    
    return None
```

**Priority Order**:
1. **Inline first** - fastest path (no I/O)
2. **Location second** - requires cache lookup
3. **None** - not found

---

## 3. How content_location is Used

### 3.1 Storing via content_location
**Process Flow**:

```
Step 1: Decide to use external storage
├─ Size check: content ≥ 16KB
├─ force_external=True flag
└─ Binary data special case

Step 2: Serialize content
└─ JSON encode to bytes

Step 3: Compress (optional)
├─ Auto-select algorithm based on size
│  ├─ < 1KB: No compression
│  ├─ 1KB-10MB: ZSTD (balanced)
│  └─ > 10MB: GZIP (max ratio)
└─ Compressed bytes

Step 4: Store in cache backend
├─ Cache.set(namespace, key, value)
└─ L2 backend (diskcache/SQLite)

Step 5: Create ContentLocation metadata
├─ Record storage_type: CACHE
├─ Record cache_namespace
├─ Record cache_key
├─ Calculate size_bytes (uncompressed)
├─ Record size_compressed
└─ Calculate checksum (SHA-256)

Step 6: Update metadata
├─ versioned.content_location = metadata
├─ versioned.content_inline = None
└─ Save to MongoDB
```

### 3.2 Retrieving via content_location
**Process Flow**:

```
Step 1: Load metadata from MongoDB
└─ versioned_data = await model.find_one()

Step 2: Get content via location
├─ Check versioned_data.content_location exists
├─ Extract: cache_namespace, cache_key
└─ (Optional: verify checksum)

Step 3: Query cache backend
├─ cache = await get_global_cache()
├─ data = await cache.get(namespace, key)
└─ Returns pickled/compressed bytes

Step 4: Deserialize
├─ If compressed: decompress_data()
├─ Unpickle (if pickled) or parse JSON
└─ Result: dict object

Step 5: Type validation
├─ Verify returned dict
└─ Return or None
```

**Example from corpus/manager.py:416**:
```python
content = await get_versioned_content(metadata)  # Handles both inline + location
if not content:
    content = {}

# Merge metadata fields
content.update({
    "corpus_id": metadata.id,
    "corpus_uuid": metadata.uuid,
    "corpus_name": metadata.resource_id,
    # ... more fields
})

# Reconstruct Corpus from content
result = Corpus.model_validate(content)
```

---

## 4. Inconsistencies and Anti-Patterns

### 4.1 Inconsistency #1: Different Thresholds
**Location**: semantic/models.py vs core.py

**core.py (Standard)**:
```python
# Line 583
inline_threshold = 16 * 1024  # 16KB
if content_size < inline_threshold:
    versioned_data.content_inline = content
```

**semantic/models.py (Special Case)**:
```python
# Lines 300-330: Binary data handling SKIPS size check
# Directly stores to external without checking size
if binary_data_to_store:
    # No size check - bypasses standard logic
    cache_key = _generate_cache_key(...)
    content_with_binary = {**content, "binary_data": binary_data_to_store}
    await cache.set(namespace=namespace, key=cache_key, value=content_with_binary)
    
    # Estimate size (rough, not accurate)
    binary_size = sum(len(v) if isinstance(v, bytes) else len(str(v))
                      for v in binary_data_to_store.values())
    content_size = binary_size + 1000  # Rough estimate
    
    versioned.content_location = ContentLocation(
        cache_namespace=versioned.namespace,
        cache_key=cache_key,
        storage_type=StorageType.CACHE,
        size_bytes=content_size,  # Estimated, not accurate
        checksum="skip-large-binary-data",  # Hash skipped!
    )
```

**Problem**: 
- ❌ No consistent threshold enforcement
- ❌ Size estimation is approximate
- ❌ Checksum skipped for "large data"
- ❌ Binary data serialization bypasses standard pipeline

### 4.2 Inconsistency #2: String vs ContentLocation Validation
**Location**: models.py:286-305

**Code**:
```python
@field_validator("content_location", mode="before")
@classmethod
def validate_content_location(cls, v: Any) -> ContentLocation | None:
    if v is None:
        return None
    if isinstance(v, ContentLocation):
        return v
    if isinstance(v, str):  # BACKWARD COMPATIBILITY HACK
        # Convert string path to ContentLocation
        return ContentLocation(
            storage_type=StorageType.S3 if v.startswith("s3://") else StorageType.CACHE,
            path=v,
            size_bytes=0,  # Unknown size
            checksum=hashlib.sha256(v.encode()).hexdigest(),  # Wrong hash!
        )
    if isinstance(v, dict):
        return ContentLocation(**v)
    return v
```

**Problem**:
- ❌ Accepts string paths for backward compatibility
- ❌ Loses type safety
- ❌ Creates minimal metadata (size_bytes=0)
- ❌ Checksum is hash of path, not content

### 4.3 Anti-Pattern: ContentLocation Equality Override
**Location**: models.py:143-147

```python
class ContentLocation(BaseModel):
    # ... fields ...
    
    def __eq__(self, other: object) -> bool:
        """Allow comparison with strings for backward compatibility."""
        if isinstance(other, str):
            return self.path == other  # Allows: location == "s3://bucket/key"
        return super().__eq__(other)
```

**Problem**:
- ❌ Breaks type safety
- ❌ Silent type coercion
- ❌ Hides bugs where code mistakenly compares with strings
- ❌ Makes it unclear what equality means

### 4.4 Inconsistency #3: force_external Flag
**Location**: core.py:527

**Issue**: Only semantic/models.py uses `force_external=True` to bypass size check

```python
# semantic/models.py:300-330 - SPECIAL HANDLING
if binary_data_to_store:
    # Uses manual store_to_cache instead of set_versioned_content
    # Avoids JSON encoding for 1290MB data
    await cache.set(
        namespace=namespace,
        key=cache_key,
        value=content_with_binary,  # Pickled directly
        ttl_override=versioned.ttl,
    )
    
    versioned.content_location = ContentLocation(...)
```

**Problem**:
- ❌ Bypasses standard `set_versioned_content()` flow
- ❌ No decompression metadata calculated
- ❌ Special casing instead of generalized solution
- ❌ Could be unified with `force_external` parameter

---

## 5. Usage Statistics

### 5.1 Code References (29 total)

| File | Inline | Location | Total |
|------|--------|----------|-------|
| **caching/models.py** | 3 | 4 | 7 |
| **caching/core.py** | 6 | 7 | 13 |
| **caching/manager.py** | 1 | 7 | 8 |
| **corpus/manager.py** | 0 | 1 | 1 |
| **search/semantic/models.py** | 0 | 3 | 3 |
| **corpus/core.py** | 0 | 1 | 1 |
| **TOTAL** | **10** | **23** | **33** |

### 5.2 Access Patterns

| Pattern | Count | Example |
|---------|-------|---------|
| Check inline first | 3 | `if versioned_data.content_inline is not None` |
| Check location | 3 | `if versioned_data.content_location:` |
| Set inline | 2 | `versioned_data.content_inline = content` |
| Set location | 5 | `versioned_data.content_location = ContentLocation(...)` |
| Mutual exclusion | 2 | Both set to None/value together |
| Unified retrieval | 6 | `get_versioned_content()` (handles both) |

### 5.3 Resource Types Using Each Pattern

| Resource Type | Inline Primary | Location Primary | Comment |
|---|---|---|---|
| **DICTIONARY** | ✅ (< 100KB) | ✅ (large responses) | Split based on size |
| **CORPUS** | ✅ (small vocab) | ✅ (large vocab) | Standard threshold |
| **SEMANTIC** | ❌ | ✅✅ (always > 16KB) | Always external (binary) |
| **LITERATURE** | ❌ | ✅✅ (always external) | Full text always large |
| **TRIE** | ❌ | ✅ (index data) | Always external |
| **SEARCH** | ✅ (metadata) | ✅ (index data) | Split pattern |

---

## 6. Decision Matrix: When to Use Each

### 6.1 Design Decision Tree

```
Is content available now?
├─ NO → Use force_external=True (skip size check)
└─ YES
    ├─ Can you JSON serialize quickly?
    │  ├─ NO (binary data) → Use force_external=True
    │  └─ YES
    │      ├─ Calculate content_size = len(json_encode(content))
    │      └─ Is content_size < 16KB?
    │         ├─ YES → Use content_inline (direct dict storage)
    │         └─ NO → Use content_location (cache reference)
    │              ├─ Compress automatically
    │              ├─ Create ContentLocation metadata
    │              └─ Store via cache.set()
    └─ Special case: Binary embeddings
       └─ Use force_external + pickle (no JSON)
```

### 6.2 Current Implementation Enforcement

| Aspect | Enforced? | Location | Strength |
|--------|-----------|----------|----------|
| Mutual exclusivity | ✅ Yes | set_versioned_content() | Strong - enforced in logic |
| Size threshold | ✅ Yes | core.py:583 | Medium - except semantic |
| Type validation (dict) | ✅ Yes | get_versioned_content() | Strong |
| Checksum verification | ❌ No | - | Weak - metadata only |
| Compression validation | ❌ No | - | Weak - metadata only |

---

## 7. What Drives the Choice

### 7.1 Primary Factors

**Factor 1: Content Size**
```
content_size < 16KB → INLINE
content_size >= 16KB → LOCATION
```

**Factor 2: Serializability**
```
JSON-serializable → Size check applies
Not serializable (binary) → force_external=True
```

**Factor 3: Resource Type Defaults**
```
SEMANTIC (embeddings) → Always LOCATION (binary)
LITERATURE (full text) → Always LOCATION (>100MB)
CORPUS (vocabulary) → Auto-select based on size
DICTIONARY → Auto-select based on size
```

**Factor 4: Performance Requirements**
```
Fast access needed → INLINE (no I/O)
Large data → LOCATION (won't fit in memory)
Concurrent access → LOCATION (avoids document size limits)
```

### 7.2 MongoDB Constraints Influencing Decision

**Document Size Limit**: 16MB per document (MongoDB hard limit)

```python
# Decision drivers:
# 1. content_inline stored IN the document → adds to document size
# 2. MongoDB documents can be up to 16MB max
# 3. 16KB threshold leaves room for metadata + other fields
# 4. Prevents: "Trying to create document > 16MB"
```

---

## 8. Redundant and Overlapping Implementations

### 8.1 Redundancy #1: Pickle vs JSON Serialization

**Location A** (core.py compression):
```python
# Line 391-394
async def _compress_data(self, data: Any, compression: CompressionType) -> bytes:
    return compress_data(data, compression)

# compression.py uses:
# pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
```

**Location B** (filesystem.py):
```python
# Line 406-420
if isinstance(data, bytes):
    if data[:2] in (b'\x80\x04', b'\x80\x05'):  # pickle magic bytes
        return pickle.loads(data)
    # Otherwise assume JSON
```

**Issue**:
- ❌ Dual serialization paths (pickle in both places)
- ❌ Magic byte detection fragile
- ❌ Inconsistent handling

### 8.2 Redundancy #2: Size Calculation

**Location A** (core.py:565):
```python
# Full JSON encoding for size calculation
content_str = json.dumps(content, sort_keys=True, default=_json_default)
content_size = len(content_str.encode())
```

**Location B** (semantic/models.py:363-368):
```python
# Rough estimate instead
binary_size = sum(
    len(v) if isinstance(v, bytes) else len(str(v))
    for v in binary_data_to_store.values()
)
content_size = binary_size + 1000  # Rough!
```

**Issue**:
- ❌ Inconsistent size calculation
- ❌ semantic version is inaccurate
- ❌ Could use actual encoded size

### 8.3 Redundancy #3: Checksum Calculation

**Standard** (core.py:619):
```python
checksum=hashlib.sha256(content_str.encode()).hexdigest()
```

**Semantic Special Case** (models.py:375):
```python
checksum="skip-large-binary-data"  # Not a real hash!
```

**String Validator** (models.py:301):
```python
checksum=hashlib.sha256(v.encode()).hexdigest()  # Hash of path, not content
```

**Issue**:
- ❌ Three different checksum strategies
- ❌ "skip-large-binary-data" is not usable for verification
- ❌ String validator produces wrong hash

---

## 9. Ideal Pattern (Standardized)

### 9.1 Proposed Standard Pattern

```python
# Unified storage decision function
async def get_storage_strategy(
    content: Any,
    namespace: CacheNamespace,
    resource_id: str,
    resource_type: ResourceType,
) -> tuple[StorageStrategy, dict[str, Any]]:
    """Determine whether to use inline or location storage.
    
    Returns:
        Tuple of (strategy, metadata)
        - strategy: StorageStrategy.INLINE or StorageStrategy.LOCATION
        - metadata: ContentLocation (if LOCATION) or dict config (if INLINE)
    """
    
    # Step 1: Determine if content is serializable
    try:
        # Quick check without full serialization
        if isinstance(content, (bytes, bytearray)):
            # Binary data → force external
            return StorageStrategy.LOCATION, {"compression": CompressionType.GZIP}
        
        # Regular dict/list → JSON serializable
        content_str = json.dumps(content, sort_keys=True, default=_json_default)
        content_bytes = content_str.encode("utf-8")
        
    except (TypeError, ValueError):
        # Not JSON serializable → force external
        return StorageStrategy.LOCATION, {"compression": CompressionType.GZIP}
    
    # Step 2: Check size threshold (16KB)
    INLINE_THRESHOLD = 16 * 1024
    
    if len(content_bytes) < INLINE_THRESHOLD:
        return StorageStrategy.INLINE, {"serialization": "dict"}
    
    # Step 3: Large content → external storage
    # Determine compression automatically
    compression = auto_select_compression(len(content_bytes))
    
    return StorageStrategy.LOCATION, {
        "compression": compression,
        "serialization": "pickle",  # Or JSON, depending on type
    }


# Unified storage interface
async def store_content(
    versioned: BaseVersionedData,
    content: Any,
    storage_strategy: StorageStrategy | None = None,
) -> None:
    """Store content with consistent strategy."""
    
    # Auto-detect strategy if not provided
    if storage_strategy is None:
        strategy, config = await get_storage_strategy(
            content,
            versioned.namespace,
            versioned.resource_id,
            versioned.resource_type,
        )
    else:
        strategy = storage_strategy
    
    # Execute storage
    if strategy == StorageStrategy.INLINE:
        versioned.content_inline = content
        versioned.content_location = None
        
    else:  # LOCATION
        # Store to cache
        cache = await get_global_cache()
        cache_key = _generate_cache_key(
            versioned.resource_type,
            versioned.resource_id,
            hashlib.sha256(json.dumps(content, sort_keys=True, default=_json_default).encode()).hexdigest()[:8]
        )
        
        await cache.set(versioned.namespace, cache_key, content)
        
        # Create metadata
        versioned.content_location = ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=versioned.namespace,
            cache_key=cache_key,
            compression=config.get("compression"),
            size_bytes=len(content_str.encode()),
            checksum=hashlib.sha256(content_str.encode()).hexdigest(),
        )
        versioned.content_inline = None
```

### 9.2 Schema Validation

```python
# Add pydantic validators to enforce invariants
class BaseVersionedData(Document):
    content_inline: dict[str, Any] | None = None
    content_location: ContentLocation | None = None
    
    @model_validator(mode="after")
    def validate_storage_mutual_exclusion(self) -> Self:
        """Enforce that only one storage method is used."""
        has_inline = self.content_inline is not None
        has_location = self.content_location is not None
        
        if has_inline and has_location:
            raise ValueError(
                f"Cannot have both content_inline and content_location. "
                f"Must use exactly one storage method. "
                f"Inline size: {len(json.dumps(self.content_inline))}, "
                f"Location: {self.content_location.path or self.content_location.cache_key}"
            )
        
        if not has_inline and not has_location:
            raise ValueError(
                "Must specify either content_inline or content_location. "
                "No content storage method specified."
            )
        
        return self
```

---

## 10. Recommendations

### 10.1 Phase 1: Fix Inconsistencies (1 day)

**Priority 1: Remove Backward Compatibility Hacks**

```diff
# models.py:143-147 - Remove string equality
- def __eq__(self, other: object) -> bool:
-     if isinstance(other, str):
-         return self.path == other
-     return super().__eq__(other)
```

**Priority 2: Unify semantic/models.py Binary Data Handling**

```python
# Instead of special casing, use:
await set_versioned_content(
    versioned_data=versioned,
    content=content_with_binary,
    force_external=True,  # Skip size check for binary
)
```

**Priority 3: Fix Checksum Calculation**

```python
# semantic/models.py - Calculate real checksums
if binary_data_to_store:
    # Create content for hashing
    temp_content = {**content, "binary_data": binary_data_to_store}
    content_str = json.dumps(temp_content, sort_keys=True, default=_json_default)
    checksum = hashlib.sha256(content_str.encode()).hexdigest()
    
    # Store with real checksum
    versioned.content_location = ContentLocation(
        # ... other fields ...
        checksum=checksum,  # Real hash!
    )
```

### 10.2 Phase 2: Enforce Schema (2 days)

**Add validation to prevent misuse**:

```python
class BaseVersionedData(Document):
    # ... existing fields ...
    
    @field_validator("content_inline")
    @classmethod
    def validate_inline_size(cls, v: Any) -> Any:
        """Ensure inline content doesn't exceed 16KB threshold."""
        if v is not None:
            content_str = json.dumps(v, sort_keys=True, default=str)
            size_bytes = len(content_str.encode())
            if size_bytes >= 16 * 1024:
                raise ValueError(
                    f"Content too large for inline storage: {size_bytes} bytes. "
                    f"Use content_location instead."
                )
        return v
    
    @model_validator(mode="after")
    def validate_storage_exclusivity(self) -> Self:
        """Exactly one storage method must be set."""
        has_inline = self.content_inline is not None
        has_location = self.content_location is not None
        
        if not (has_inline ^ has_location):  # XOR - exactly one
            raise ValueError(
                "Must use exactly one storage method: "
                f"content_inline (set={has_inline}) XOR "
                f"content_location (set={has_location})"
            )
        
        return self
```

### 10.3 Phase 3: Refactor Special Cases (3 days)

**Consolidate semantic index handling**:

```python
# semantic/models.py - Remove special casing
async def save(self, config: VersionConfig | None = None):
    # Use standard save + force_external for binary data
    versioned = await manager.save(
        resource_id=resource_id,
        resource_type=ResourceType.SEMANTIC,
        namespace=CacheNamespace.SEMANTIC,
        content=self.model_dump(exclude_none=True),
        config=config or VersionConfig(),
    )
    
    # Handle binary data uniformly
    if binary_data:
        await set_versioned_content(
            versioned_data=versioned,
            content={**versioned.model_dump(), "binary_data": binary_data},
            force_external=True,
        )
        await versioned.save()
```

---

## 11. Success Metrics

### 11.1 Code Quality

- ✅ Zero backward compatibility hacks (0 string equality overloads)
- ✅ Single size threshold (16KB) enforced everywhere
- ✅ Schema validation prevents misuse
- ✅ 100% mutual exclusion between inline/location

### 11.2 Consistency

- ✅ Checksum calculation always SHA-256 of content
- ✅ Binary data handled uniformly via `force_external`
- ✅ Compression selected automatically with same algorithm
- ✅ All retrieval goes through `get_versioned_content()`

### 11.3 Maintainability

- ✅ Single decision function (`get_storage_strategy()`)
- ✅ Clear documentation on when each pattern applies
- ✅ No special cases outside standard flow
- ✅ Comprehensive test coverage for both patterns

---

## Conclusion

The inline vs content_location pattern is **well-designed overall** but suffers from:

1. **Backward compatibility hacks** (string equality, string paths)
2. **Special casing in semantic module** (binary data bypass)
3. **Inconsistent checksums** (skipped, wrong hash type)
4. **Documentation gaps** (when/why to override defaults)

**Recommended Action**: Implement Phase 1 (Fix Inconsistencies) immediately to remove fragility, then Phase 2 (Schema Validation) to prevent future misuse.

**Estimated Effort**: 1-2 days for all phases  
**Impact**: High - eliminates special cases, improves reliability, enables future optimization

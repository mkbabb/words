# Architecture V4 - Performance Optimizations

## Key Changes Made

### ✅ DictionaryEntry Model
- Renamed from `DictionaryProviderData` to `DictionaryEntry`
- Includes all attributes from existing `DictionaryProviderData`:
  - `provider_type`, `provider_name` fields
  - Full provider information tracking
  - Error handling and fetch timestamps

### ✅ Performance Improvements

**Serialization Strategy**
```python
# Optimized type checking order (most common first)
if isinstance(value, (str, int, float, bool, None)):
    # No serialization needed for primitives
elif isinstance(value, (dict, list)):
    # Native JSON handling by diskcache
else:
    # Pickle for complex objects (Pydantic models, etc.)
    pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
```

**Deserialization with Magic Bytes**
```python
# Check pickle protocol magic bytes for fast path
if data[:2] in (b'\x80\x04', b'\x80\x05'):  # Protocol 4 or 5
    return pickle.loads(data)
else:
    # Fall back to JSON
    return json.loads(data.decode('utf-8'))
```

### ✅ Clean Error Handling
- Removed bare `except:` clauses
- Use pickle magic bytes detection instead of try/except
- Explicit protocol checks for deserialization path

### ✅ Storage Optimizations
- Single serialization per save operation
- Efficient type checking order (primitives first)
- Pickle protocol 5 for maximum performance
- Smart compression selection based on size

## Performance Characteristics

**Serialization Performance**
- Primitives: 0 overhead (pass-through)
- JSON types: Native diskcache handling
- Complex objects: Pickle protocol 5 (fastest)

**Cache Hit Path**
1. L1 Memory: ~1μs (no deserialization)
2. L2 Filesystem: ~100μs (pickle fast path)
3. External storage: ~1ms (with decompression)

**Key Design Decisions**
- Use pickle magic bytes (b'\x80\x04', b'\x80\x05') for type detection
- Preserve insertion order with dict (Python 3.7+)
- Minimize serialization calls (once per operation)
- Type-specific serialization paths for optimal performance
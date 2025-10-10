# ObjectId Serialization Research Report

## Executive Summary

Research into how Beanie's `PydanticObjectId` should be handled in Pydantic models reveals that **no custom `@field_serializer` is needed**. Beanie provides built-in serializers through Pydantic v2's core schema system that automatically convert ObjectIds to strings when using `model_dump(mode='json')`.

## Key Findings

### 1. PydanticObjectId Built-in Serialization

**Location**: `.venv/lib/python3.12/site-packages/beanie/odm/fields.py` (lines 116-220)

The `PydanticObjectId` class implements Pydantic v2's serialization protocol:

```python
class PydanticObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Type[Any], handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.definitions_schema(
            definition,
            [
                core_schema.json_or_python_schema(
                    python_schema=core_schema.no_info_plain_validator_function(
                        cls._validate
                    ),
                    json_schema=core_schema.no_info_after_validator_function(
                        cls._validate,
                        core_schema.str_schema(
                            pattern="^[0-9a-f]{24}$",
                            min_length=24,
                            max_length=24,
                        ),
                    ),
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        lambda instance: str(instance), when_used="json"
                    ),
                    ref=definition["schema_ref"],
                )
            ],
        )
```

**Key Points**:
- `serialization` parameter uses `when_used="json"`
- Automatically converts ObjectId to string during JSON serialization
- Works for single fields, optional fields, and lists of ObjectIds
- No custom serializer needed

### 2. Test Results

Created test script (`test_objectid_serialization.py`) demonstrating:

```python
class TestModel(BaseModel):
    id: PydanticObjectId
    optional_id: PydanticObjectId | None = None
    id_list: list[PydanticObjectId] = []

# Results:
# model_dump() -> ObjectId instances (Python mode)
# model_dump(mode='json') -> strings (JSON mode)
# json.dumps(model_dump(mode='json')) -> ✓ SUCCESS
```

**Output**:
```
1. Direct access:
   test.id = 68e574099fbdd484df264f43
   type(test.id) = <class 'beanie.odm.fields.PydanticObjectId'>

2. model_dump() [Python mode]:
   type(id) = <class 'beanie.odm.fields.PydanticObjectId'>

3. model_dump(mode='json') [JSON mode]:
   type(id) = <class 'str'>

4. JSON serialization:
   SUCCESS: valid JSON
```

### 3. Current Implementation Analysis

**In `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py` (line 166)**:

```python
content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
```

**Custom encoder (lines 643-653)**:
```python
def _json_encoder(self, obj: Any) -> str:
    """Custom JSON encoder for complex objects like PydanticObjectId."""
    from datetime import datetime

    if isinstance(obj, PydanticObjectId):
        return str(obj)
    if isinstance(obj, Enum):
        return str(obj.value)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

**Issues**:
1. When `content` comes from `model_dump()`, ObjectIds are still ObjectId instances
2. Custom encoder called for every ObjectId (callback overhead)
3. Duplicates functionality already in Pydantic's serializers
4. Enum handling unnecessary with `use_enum_values=True` config

### 4. Corpus Model Configuration

**In `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/core.py` (lines 97-113)**:

```python
class Corpus(BaseModel):
    corpus_id: PydanticObjectId | None = None
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "ser_json_inf_nan": "constants",
    }
```

**Configuration is correct**:
- `use_enum_values=True` handles enum serialization
- No custom field serializers needed

### 5. Usage Patterns Across Codebase

Found 39 files using `model_dump()` or `model_dump(mode='json')`:

**Correct usage (mode='json')**:
- `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/manager.py:72`
- `/Users/mkbabb/Programming/words/backend/src/floridify/search/models.py:265`
- `/Users/mkbabb/Programming/words/backend/src/floridify/api/services/loaders.py:52`

**Potential issues** (model_dump() without mode):
- `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py:183`
- `/Users/mkbabb/Programming/words/backend/src/floridify/api/repositories/word_repository.py` (various)

## How ObjectId Serialization Works

### Python Mode (model_dump())
Returns Python objects as-is:
- `PydanticObjectId` → `PydanticObjectId` instance
- `Enum` → Enum instance (or value if `use_enum_values=True`)
- `datetime` → datetime instance

### JSON Mode (model_dump(mode='json'))
Returns JSON-serializable types:
- `PydanticObjectId` → `str` (via built-in serializer)
- `Enum` → value (with `use_enum_values=True`)
- `datetime` → ISO string (via field_serializer if defined)

### Deserialization
Works automatically from strings:
```python
# From string dict
test_dict = {"id": "68e574099fbdd484df264f43"}
restored = TestModel(**test_dict)  # ✓ Works
```

## Best Practices from Beanie/Motor Documentation

1. **Use `model_dump(mode='json')` for JSON serialization**
   - Leverages Pydantic's built-in serializers
   - Handles ObjectIds, dates, enums correctly
   - No custom encoders needed

2. **Use `model_dump()` for Python operations**
   - Preserves Python types
   - Efficient for internal processing
   - Can be passed directly to MongoDB

3. **Custom serializers only when needed**
   - For custom types not handled by Pydantic
   - For special formatting requirements
   - Not needed for ObjectId, datetime, or enums

## Recommendations

### Immediate Fix for manager.py

Replace:
```python
content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
```

With:
```python
# Handle Pydantic models with built-in serialization
if hasattr(content, 'model_dump'):
    content_dict = content.model_dump(mode='json')
    content_str = json.dumps(content_dict, sort_keys=True)
else:
    # Fallback for non-Pydantic content
    content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
```

**Benefits**:
- Uses Pydantic's optimized serializers
- Correctly handles ObjectIds, enums, datetime
- Reduces callback overhead
- More maintainable (follows Pydantic best practices)
- Keeps fallback for edge cases

### Optional: Remove Custom Encoder for ObjectIds

The `_json_encoder` method can be simplified:
```python
def _json_encoder(self, obj: Any) -> str:
    """Fallback JSON encoder for non-Pydantic content."""
    from datetime import datetime

    # Only handle cases not covered by Pydantic
    if isinstance(obj, datetime):
        return obj.isoformat()
    # PydanticObjectId and Enum no longer needed here
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

Or keep it for defensive coding:
```python
def _json_encoder(self, obj: Any) -> str:
    """Fallback JSON encoder for edge cases."""
    from datetime import datetime

    # These should be handled by model_dump(mode='json'),
    # but keep as fallback for non-Pydantic content
    if isinstance(obj, PydanticObjectId):
        return str(obj)
    if isinstance(obj, Enum):
        return str(obj.value)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

### Verification

Run test scripts:
```bash
python test_objectid_serialization.py
python test_document_serialization.py
python test_objectid_json_issue.py
```

All three demonstrate that:
1. PydanticObjectId has custom serializers
2. `model_dump(mode='json')` handles ObjectIds correctly
3. No custom `@field_serializer` needed
4. Current approach works but is redundant

## Related Files

### Core Models
- `/Users/mkbabb/Programming/words/backend/src/floridify/models/base.py` - Base models (already correct)
- `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/core.py` - Corpus model (already correct)
- `/Users/mkbabb/Programming/words/backend/src/floridify/caching/models.py` - Cache models

### Manager/Serialization
- `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py` - Needs update
- `/Users/mkbabb/Programming/words/backend/src/floridify/caching/core.py` - Uses similar pattern
- `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/manager.py` - Already uses mode='json'

### Test Scripts
- `test_objectid_serialization.py` - Basic ObjectId serialization test
- `test_document_serialization.py` - Document vs BaseModel comparison
- `test_objectid_json_issue.py` - Issue reproduction and recommendations

## Conclusion

**No custom `@field_serializer` is needed for ObjectId fields**. Beanie's `PydanticObjectId` includes built-in Pydantic v2 serializers that automatically convert to strings during JSON serialization.

**The correct approach**:
1. Use `model_dump(mode='json')` before JSON serialization
2. This triggers Pydantic's built-in serializers
3. ObjectIds automatically convert to strings
4. Enums handled by `use_enum_values=True` config
5. No custom encoders needed

**Current codebase status**:
- Models configured correctly (`use_enum_values=True`)
- Some code already uses `model_dump(mode='json')` correctly
- `manager.py` can be optimized to use built-in serializers
- Custom `_json_encoder` can be simplified or kept as fallback

**Performance impact**:
- Built-in serializers are optimized (single pass)
- Custom encoder requires callback for each ObjectId (multiple passes)
- Recommended approach is faster and more maintainable
